"""
标注图元（画布上的“可见标注”）
==============================

数据模型 Annotation（models/annotation.py）只是一堆数字，看不见摸不着。
这个文件定义的图元类是标注在画布上的“化身” ——
可以被看见、被点选、被拖动、被调整大小的图形。

目前有两种图元，对应两种标注类型：
    ShapeRectItem     矩形（继承 Qt 的 QGraphicsRectItem）
    ShapePolygonItem  多边形（继承 Qt 的 QGraphicsPolygonItem）

两者共享的逻辑（类别标签、选中样式、拖动后回写数据）抽在
ShapeItemMixin 这个“混入类”（Mixin）里 —— 这是 Python 多继承的
经典用法：Mixin 不单独使用，和 Qt 图元类搭配继承，
让两个图元类都能复用同一套行为，又不重复代码。

数据与图形的关系（经典的“模型-视图”思想）：
    Shape        数据（图片坐标、类别）—— 负责“是什么”
    ShapeXxxItem 屏幕上的图形           —— 负责“长什么样、怎么交互”
    图元持有 Annotation 的引用，用户拖动/拉伸图形时把新位置写回 Annotation，
    保证“屏幕上看到的”和“存到文件的”永远一致。

撤销功能配合说明：
    图元每次“几何变化”（拖动、拉伸角点）后都会通过画布的
    notify_shape_moved() 通知主窗口，主窗口据此把这次修改记入
    撤销栈（Ctrl+Z 可回退）。图元自己不管撤销，只负责上报。
"""

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPen, QPolygonF
from PySide6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsPolygonItem,
    QGraphicsRectItem,
    QGraphicsSimpleTextItem,
)

from ..models.annotation import Annotation

# 填充色的透明度（0-255）：30 表示淡淡的底色，既不挡图片又能看清范围
_FILL_ALPHA = 30

# 矩形角点把手的直径（屏幕像素）
_HANDLE_SIZE = 10


class _HandleItem(QGraphicsEllipseItem):
    """
    矩形角点上的“调整把手” —— 选中矩形时出现在四个角的小圆点，
    拖动它可以调整矩形大小。

    它是矩形的【子图元】：父图元移动时自动跟随，无需手动同步位置。
    事件处理上有一个关键点：把手的 mousePressEvent 里调用了
    event.accept()，表示“这个点击我处理了”，Qt 就不会再把它
    传给父图元 —— 否则拖动把手会被当成“拖动整个矩形”。
    """

    def __init__(self, corner: int, parent: "ShapeRectItem"):
        """
        参数：
            corner  角的编号：0=左上 1=右上 2=右下 3=左下
            parent  所属的矩形图元
        """
        # 先以 (0,0) 为中心的圆创建，位置由父图元的 _layout_parts() 摆放
        half = _HANDLE_SIZE / 2
        super().__init__(-half, -half, _HANDLE_SIZE, _HANDLE_SIZE, parent)
        self._corner = corner
        # 不再额外保存 self._parent_rect_item = parent。
        # QGraphicsItem 本身已经通过 parentItem() 维护父子关系；
        # 再保存一份 Python 强引用会形成 parent -> handles -> parent 的引用环，
        # 与 Qt 的 C++ 父子所有权叠加后会让销毁时机更难预测。

        # ItemIgnoresTransformations：始终以屏幕像素大小绘制，
        # 画布放得再小把手也一样大，保证永远点得中
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations)

        # 把手不接受“选中/移动”，它只是父图元的操作手柄
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)

        # 对角线方向的光标：左上/右下用 \ 形，右上/左下用 / 形
        if corner in (0, 2):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        else:
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)

    # ------------------------------------------------------------------
    # Qt 事件回调
    # ------------------------------------------------------------------
    def mousePressEvent(self, event) -> None:
        # 关键：accept 表示事件到此为止，不再传给父图元，
        # 避免“拖把手”变成“拖整个矩形”
        event.accept()

    def mouseMoveEvent(self, event) -> None:
        """拖动把手中：把屏幕位置换算成矩形局部坐标，让父图元调整大小。"""
        # scenePos() 是场景坐标；父图元由 Qt 自己维护。
        # 不持有额外 Python 强引用，避免 Qt/Python 双重所有权形成引用环。
        parent = self.parentItem()
        if parent is not None:
            local_pos = parent.mapFromScene(event.scenePos())
            parent.resize_corner(self._corner, local_pos)
        event.accept()

    def mouseReleaseEvent(self, event) -> None:
        event.accept()


class ShapeItemMixin:
    """
    混入类：两种标注图元共用的逻辑。

    不单独使用，而是和 Qt 图元类一起做多继承，例如：
        class ShapeRectItem(ShapeItemMixin, QGraphicsRectItem)
    这样 ShapeRectItem 就同时拥有 Qt 矩形图元的能力
    和这里定义的标注行为（Python 按 MRO 顺序查找方法）。
    """

    def _init_shape_item(self, shape: Annotation, color: str) -> None:
        """公共初始化：存引用、开交互开关、画样式、加标签。"""
        # 注意：这个属性必须叫 shape_data，不能叫 shape！
        # QGraphicsItem 自带一个内置虚方法 shape()（用于碰撞检测），
        # 如果我们定义同名属性把它覆盖掉，Qt 内部一调用就会崩溃：
        # TypeError: 'Shape' object is not callable
        # （矩形碰巧不调它所以没事，多边形的 boundingRect() 会调 ——
        #   这是真实踩过的坑，教训：给 Qt 类的子类加属性时，
        #   避开框架已有的方法名）
        self.shape_data = shape
        self._color = color
        self._selected = False     # 记录当前是否选中（改颜色时要恢复样式）
        self._label_item = None    # 类别标签子图元（_make_label 里创建）

        # 打开 Qt 自带的两个交互开关：
        # ItemIsSelectable 可以被鼠标点选；ItemIsMovable 可以被拖动
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        # ItemSendsGeometryChanges：位置变化时通知 itemChange()。
        # 这【不是】默认开启的！不开它，ItemPositionHasChanged 永远不会触发，
        # 拖动后新坐标就不会写回数据模型（自验脚本抓出来的真实 bug）
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)

        self._apply_style(selected=False)
        self._make_label(shape.label, color)

    # ------------------------------------------------------------------
    # Qt 回调
    # ------------------------------------------------------------------
    def itemChange(self, change, value):
        """
        图元状态变化时 Qt 会调用这个方法。

        我们关心 ItemPositionHasChanged（拖动后位置变了）：
        此时把图元的当前位置写回数据模型 Annotation。
        场景坐标和图片坐标的“距离”一致（只差固定偏移），
        所以位移可以直接反映到图片坐标上。
        """
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self._sync_back_to_model()
        # 注意：多继承下 super() 会按 MRO 找到 Qt 图元类的 itemChange，
        # 必须调用它，否则选中/移动等默认行为会失效
        return super().itemChange(change, value)

    # ------------------------------------------------------------------
    # 对外方法
    # ------------------------------------------------------------------
    def set_selected_style(self, selected: bool) -> None:
        """切换选中/未选中的外观（由画布的选中变化信号驱动）。"""
        self._selected = selected
        self._apply_style(selected)

    def update_label(self, text: str, color: str) -> None:
        """
        修改这个标注的类别显示（文字 + 颜色）。

        在对象面板里双击改标签时由主窗口调用；
        改完文字还要改颜色，并保持当前的选中/未选中样式。
        """
        self._color = color
        if self._label_item is not None:
            self._label_item.setText(text)
            self._label_item.setBrush(QBrush(QColor(color)))
        self._apply_style(self._selected)

    # ------------------------------------------------------------------
    # 子类必须实现的方法
    # ------------------------------------------------------------------
    def _scene_points(self) -> list:
        """
        返回当前形状在【场景坐标】下的顶点列表（含拖动位移）。
        矩形子类返回左上角+右下角；多边形子类返回全部顶点。
        """
        raise NotImplementedError  # 子类必须实现，否则调用即报错

    # ------------------------------------------------------------------
    # 内部实现
    # ------------------------------------------------------------------
    def _make_label(self, text: str, color: str) -> None:
        """在形状左上角外侧加一个类别标签（如 “person”）。"""
        # 把文字做成这个图元的“子图元”：父图元移动时子图元自动跟着动，
        # 我们完全不用写跟随代码 —— 这是 Qt 图元的父子机制
        label = QGraphicsSimpleTextItem(text, parent=self)
        label.setBrush(QBrush(QColor(color)))  # 文字颜色 = 类别颜色
        font = QFont()
        font.setPointSize(9)
        label.setFont(font)

        # 标签锚点 = 形状外接框的左上角（在图元自己的局部坐标系里）
        anchor = self.boundingRect().topLeft()
        label.setPos(anchor.x(), anchor.y() - 22)

        # ItemIgnoresTransformations：标签始终以屏幕像素大小绘制，
        # 画布放大缩小标签文字都保持同样大小，不会糊也不会变得巨大
        label.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations)

        self._label_item = label

    def _apply_style(self, selected: bool) -> None:
        """根据是否选中设置边框和填充。"""
        color = QColor(self._color)
        pen = QPen(color, 3 if selected else 2)
        pen.setCosmetic(True)  # 线宽固定为屏幕像素，不随缩放变粗
        if selected:
            pen.setStyle(Qt.PenStyle.DashLine)  # 选中时用虚线高亮
        self.setPen(pen)

        fill = QColor(color)
        fill.setAlpha(_FILL_ALPHA + (20 if selected else 0))
        self.setBrush(QBrush(fill))

    def _sync_back_to_model(self) -> None:
        """把图元当前的位置写回 Annotation，并通知主窗口“形状变了”。"""
        # 场景坐标 -> 图片坐标需要图片尺寸，图元自己不知道，
        # 借助显示这个场景的画布来完成（scene().views()[0] 就是画布）
        views = self.scene().views()
        if not views:
            return  # 极端情况：图元还没被显示，没有画布可用
        canvas = views[0]
        self.shape_data.points = [canvas.scene_point_to_image(p)
                                  for p in self._scene_points()]
        # 通知主窗口：形状被移动/变形了（主窗口会标记“未保存”并记撤销）
        canvas.notify_shape_moved(self.shape_data)


class ShapeRectItem(ShapeItemMixin, QGraphicsRectItem):
    """矩形标注的图元，选中时四角出现把手，可拖动调整大小。"""

    def __init__(self, shape: Annotation, scene_rect: QRectF, color: str):
        """
        参数：
            shape       对应的数据模型（图片坐标的矩形）
            scene_rect  矩形在【场景坐标】里的范围（画布负责换算好）
            color       类别颜色（边框和标签用它）
        """
        super().__init__(scene_rect)
        self._init_shape_item(shape, color)
        self._make_handles()

    def _scene_points(self) -> list:
        """矩形的场景顶点：左上角 + 右下角。mapToScene 自动含拖动位移。"""
        return [self.mapToScene(self.rect().topLeft()),
                self.mapToScene(self.rect().bottomRight())]

    # ------------------------------------------------------------------
    # 角点把手
    # ------------------------------------------------------------------
    def _make_handles(self) -> None:
        """在四个角创建把手（默认隐藏，选中时才显示）。"""
        self._handles = [_HandleItem(corner, self) for corner in range(4)]
        for handle in self._handles:
            handle.setVisible(False)
        self._layout_parts()

    def set_selected_style(self, selected: bool) -> None:
        """重写：除了换样式，还要显示/隐藏角点把手。"""
        super().set_selected_style(selected)
        for handle in self._handles:
            handle.setVisible(selected)

    def resize_corner(self, corner: int, local_pos) -> None:
        """
        把某个角拖到 local_pos（矩形局部坐标），对角保持不动。

        实现思路：矩形由“两个对角点”决定，拖一个角时另一个角就是锚点，
        用 QRectF(锚点, 新位置).normalized() 得到新矩形 ——
        normalized() 会自动处理“拖过锚点导致宽高为负”的情况，
        所以把手可以穿过对角继续拖，矩形会自然地翻转方向。
        """
        rect = self.rect()
        corners = [rect.topLeft(), rect.topRight(),
                   rect.bottomRight(), rect.bottomLeft()]
        anchor = corners[(corner + 2) % 4]  # +2 取对角
        self.setRect(QRectF(anchor, local_pos).normalized())

        # 矩形变了，标签和把手的位置都要跟着更新
        self._layout_parts()
        # 写回数据模型并通知主窗口（此时还没有拖动位移，
        # mapToScene 得到的仍是真实场景坐标，回写是安全的）
        self._sync_back_to_model()

    def _layout_parts(self) -> None:
        """根据当前矩形摆放标签和四个把手（局部坐标）。"""
        rect = self.rect()
        if self._label_item is not None:
            self._label_item.setPos(rect.topLeft().x(), rect.topLeft().y() - 22)
        corners = [rect.topLeft(), rect.topRight(),
                   rect.bottomRight(), rect.bottomLeft()]
        for handle, pos in zip(self._handles, corners):
            handle.setPos(pos)


class ShapePolygonItem(ShapeItemMixin, QGraphicsPolygonItem):
    """多边形标注的图元（暂不支持顶点编辑，整体可拖动）。"""

    def __init__(self, shape: Annotation, scene_polygon: QPolygonF, color: str):
        """
        参数：
            shape          对应的数据模型（图片坐标的顶点列表）
            scene_polygon  多边形在【场景坐标】下的顶点（画布负责换算好）
            color          类别颜色（边框和标签用它）
        """
        super().__init__(scene_polygon)
        self._init_shape_item(shape, color)

    def _scene_points(self) -> list:
        """多边形的场景顶点：全部顶点。mapToScene 自动含拖动位移。"""
        return [self.mapToScene(p) for p in self.polygon()]
