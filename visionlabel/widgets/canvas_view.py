"""
中央画布
========

显示图片和标注的地方，是整个软件最核心的组件。

技术选型（为什么用 QGraphicsView 而不是普通 QWidget）：
    QGraphicsView 是 Qt 的“2D 图形视图框架”，天生支持：
    - 缩放、平移（scale() / fitInView() 一行搞定）
    - “图元”（QGraphicsItem）模型：图片、每个标注框都是一个图元，
      框架自动管理绘制、点选、拖动 —— 本文件大量受益于这个模型

这个类的三大职责：
    1. 显示图片（load_image）
    2. 视图控制（缩放 / 平移 / 适应窗口）
    3. 标注模式调度：根据当前模式，把鼠标事件转发给对应的标注工具
       （矩形框工具等），或让 Qt 处理点选/拖动（选择模式）

坐标系约定（非常重要，读懂这个就懂了坐标换算）：
    图片的【中心】放在场景坐标原点 (0, 0)。
    所以：场景坐标 = 图片坐标 - (宽/2, 高/2)
          图片坐标 = 场景坐标 + (宽/2, 高/2)
    所有换算都集中在本文件的几个 _to_image / _to_scene 方法里，
    其他地方（工具、主窗口）调用即可，不用自己记规则。

对外接口：
    方法：load_image() / set_mode() / add_shape_item() / clear_shapes()
          delete_selected_shapes() / select_shape() / zoom_in() 等
    信号：image_loaded(宽, 高)       图片加载完成
          zoom_changed(百分比)       缩放比例变化
          mouse_moved(x, y)          鼠标在图片上的坐标
          rect_drawn(x, y, w, h)     用户画好了一个矩形（图片坐标）
          shape_selected(Annotation|None) 画布上的选中对象变化
          shape_drag_started(图元)   用户按住某个标注准备拖动/拉伸（撤销快照用）
          shape_moved(Shape)         某个标注的位置或大小被改变了
"""

from pathlib import Path

from PySide6.QtCore import Qt, QPointF, QRectF, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import QGraphicsScene, QGraphicsView

from ..models.annotation import Annotation
from ..tools.polygon_tool import PolygonTool
from ..tools.rect_tool import RectTool
from .shape_item import ShapeItemMixin, ShapePolygonItem, ShapeRectItem

# 支持的图片格式（打开文件夹时按后缀名筛选）
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}

# 模式 key -> 对应的工具实例。
# 新增标注工具时，在这里登记一行即可（插件注册点）。
def _build_tools() -> dict:
    """
    创建“模式 key -> 标注工具实例”的注册表。

    CanvasView 不需要知道 RectangleTool / PolygonTool 的内部实现，
    只按当前 mode 找到对应 Tool，再把鼠标事件转发给它。
    以后新增 PointTool 时，也应优先在这个注册点接入，而不是继续往鼠标事件里堆 if/elif。
    """
    return {
        "rect": RectTool(),
        "polygon": PolygonTool(),   # 插件式扩展：一行接入新工具
        # "point": PointTool(),     # 后续扩展：关键点工具
    }


class CanvasView(QGraphicsView):
    """中央画布。继承 QGraphicsView。"""

    # ---- 信号：画布发生了什么，通过信号“广播”给主窗口 ----
    image_loaded = Signal(int, int)   # 参数：图片宽、高（像素）
    zoom_changed = Signal(int)        # 参数：缩放百分比（如 87 表示 87%）
    mouse_moved = Signal(int, int)    # 参数：鼠标在图片上的坐标 x, y
    rect_drawn = Signal(float, float, float, float)  # 参数：图片坐标 x, y, 宽, 高
    polygon_drawn = Signal(object)    # 参数：图片坐标的顶点列表 [(x,y), ...]
    shape_selected = Signal(object)   # 参数：选中的 Annotation，取消选中时是 None
    shape_drag_started = Signal(object)  # 参数：被按住的标注图元（撤销快照时机）
    shape_moved = Signal(object)      # 参数：被移动/变形的 Annotation（标脏 + 撤销用）

    # 滚轮每滚一格的缩放倍率（1.25 = 放大 25%）
    ZOOM_IN_FACTOR = 1.25
    ZOOM_OUT_FACTOR = 0.8  # = 1 / 1.25，保证放大再缩小能回到原样

    # 缩放范围限制：最小 2%（看超大图的全貌），最大 5000%（逐像素检查）
    ZOOM_MIN = 0.02
    ZOOM_MAX = 50.0

    def __init__(self, parent=None):
        super().__init__(parent)

        # QGraphicsView 是“窗口”，QGraphicsScene 是“场景”：
        # 所有要显示的东西（图元）都放进场景，视图负责把场景画出来。
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)

        # ---- 外观设置 ----
        self.setBackgroundBrush(QColor("#38393e"))       # 深灰背景
        self.setFrameShape(QGraphicsView.Shape.NoFrame)  # 去掉边框
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # ---- 交互设置 ----
        # 滚轮缩放时以“鼠标所在位置”为中心（图片会跟着鼠标走，符合直觉）
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        # 不按住鼠标也能收到 mouseMoveEvent（用于状态栏实时显示坐标、绘制预览）
        self.setMouseTracking(True)
        # 隐藏滚动条：平移画布用“按住空格拖动”（labelme/Photoshop 同款交互），
        # 露出滚动条既占地方又破坏深色画布的整体感
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # ---- 内部状态 ----
        self._pixmap: QPixmap | None = None   # 当前图片（None 表示未加载）
        self._image_item = None               # 图片在场景中的图元
        self._fit_mode = True                 # “适应窗口”模式下窗口变化时自动重排

        # ---- 标注相关状态 ----
        self._tools = _build_tools()  # {模式key: 工具实例}
        self._tool = None             # 当前激活的标注工具（None = 选择模式）
        self._shape_items: list[ShapeRectItem] = []  # 当前图片上的标注图元

        # 场景中“选中集”变化时，同步高亮样式并广播给主窗口
        self._scene.selectionChanged.connect(self._on_selection_changed)

        self._show_placeholder()

    # ==================================================================
    # 图片加载
    # ==================================================================
    def load_image(self, path: Path , prepared_pixmap : QPixmap | None = None) -> bool:
        """加载并显示一张图片。成功返回 True，失败返回 False。"""
        pixmap = (
            prepared_pixmap
            if prepared_pixmap is not None
            else QPixmap(str(path))
        )
        if pixmap.isNull():  # 文件损坏或格式不支持时 QPixmap 是“空”的
            return False

        # ---- 安全切换 Scene：不要在交互回调中直接 clear() ----
        # QGraphicsScene.clear() 会立即删除场景拥有的全部 C++ 图元。
        # 如果旧图元正处于选中/鼠标事件/selectionChanged 的调用链中，
        # 立即删除可能让 Qt 后续继续访问已经释放的对象；Windows 下这类
        # C++ 层错误常表现为 0xC0000374（heap corruption），Python 无 traceback。
        #
        # 更稳妥的做法是：
        #   1. 先取消正在绘制的临时图元；
        #   2. 断开旧 Scene 的选择信号；
        #   3. 创建并切换到一个全新的 Scene；
        #   4. 对旧 Scene 调 deleteLater()，让 Qt 在当前事件处理结束后再释放。
        # 这样即使用户刚选中矩形、角点把手刚显示出来就立刻切图，
        # 旧图元也不会在当前输入事件的中途被销毁。
        if self._tool is not None:
            self._tool.cancel(self)

        old_scene = self._scene
        try:
            old_scene.selectionChanged.disconnect(self._on_selection_changed)
        except (RuntimeError, TypeError):
            pass
        old_scene.blockSignals(True)

        # 先丢掉“当前画布”对旧图元的 Python 引用。旧 Scene 仍然拥有
        # C++ 图元，直到 deleteLater 真正执行，因此这里不会制造悬空指针。
        self._shape_items.clear()
        self._image_item = None

        new_scene = QGraphicsScene(self)
        new_scene.selectionChanged.connect(self._on_selection_changed)
        self.setScene(new_scene)
        self._scene = new_scene

        # 延迟销毁旧 Scene，而不是 old_scene.clear() 立即销毁其 item。
        old_scene.deleteLater()

        self._pixmap = pixmap
        self._image_item = self._scene.addPixmap(pixmap)

        w, h = pixmap.width(), pixmap.height()
        # 图片中心对齐场景原点；场景范围比图片大一圈，方便平移查看边缘
        self._image_item.setOffset(-w / 2, -h / 2)
        margin = 60
        self._scene.setSceneRect(-w / 2 - margin, -h / 2 - margin,
                                 w + margin * 2, h + margin * 2)

        self.fit()  # 新图片默认“适应窗口”显示
        self.image_loaded.emit(w, h)
        return True

    # ==================================================================
    # 标注模式调度
    # ==================================================================
    def set_mode(self, mode_key: str) -> None:
        """
        切换标注模式（由模式条的信号驱动）。

        - "select"：选择/编辑模式，没有激活工具，鼠标事件交给 Qt
                    处理（点选、拖动已有标注）；
        - 其他：    激活对应的标注工具，鼠标事件优先转发给工具。
        """
        # 切换前先让旧工具清理现场（比如删掉画了一半的预览框）
        if self._tool is not None:
            self._tool.cancel(self)

        self._tool = self._tools.get(mode_key)  # 查不到就是选择模式

        if self._tool is None:
            # 选择模式：RubberBandDrag 表示左键在空白处拖动可以框选多个标注
            self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
            self.viewport().setCursor(Qt.CursorShape.ArrowCursor)
        else:
            # 标注模式：NoDrag，鼠标事件由工具全权处理；光标换成十字线
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.viewport().setCursor(Qt.CursorShape.CrossCursor)

    # ==================================================================
    # 标注图元的管理
    # ==================================================================
    def finish_new_rect(self, scene_rect: QRectF) -> None:
        """
        供矩形工具调用：用户在场景里画好了一个矩形。
        画布在这里完成“场景坐标 -> 图片坐标”的换算，
        然后发信号通知主窗口（主窗口负责类别、保存等后续）。
        """
        x, y, w, h = self.scene_rect_to_image(scene_rect)
        self.rect_drawn.emit(x, y, w, h)

    def finish_new_polygon(self, scene_points: list) -> None:
        """
        供多边形工具调用：用户在场景里闭合了一个多边形。
        顶点逐个换算成图片坐标，然后发信号通知主窗口。
        """
        image_points = [self.scene_point_to_image(p) for p in scene_points]
        self.polygon_drawn.emit(image_points)

    def add_shape_item(self, shape: Annotation, color: str):
        """
        把一个标注数据显示到画布上，返回创建出来的图元。

        按标注类型分发到对应的图元类 —— 新增图元类型时在这里加分支。
        """
        if shape.shape_type == "rect":
            scene_rect = self.image_rect_to_scene(shape.rect())
            item = ShapeRectItem(shape, scene_rect, color)
        elif shape.shape_type == "polygon":
            scene_polygon = QPolygonF(
                [self.image_point_to_scene(x, y) for x, y in shape.points]
            )
            item = ShapePolygonItem(shape, scene_polygon, color)
        else:
            # 暂未支持的类型：不崩溃，打个警告（便于发现忘接的分支）
            print(f"[警告] 暂不支持的标注类型: {shape.shape_type}")
            return None
        self._scene.addItem(item)
        self._shape_items.append(item)
        return item

    def clear_shapes(self) -> None:
        """清除画布上的所有标注图元（切换图片时调用）。"""
        for item in self._shape_items:
            self._scene.removeItem(item)
        self._shape_items.clear()

    def delete_selected_shapes(self) -> list[Annotation]:
        """
        删除当前选中的标注图元，返回被删除的 Shape 列表
        （主窗口拿到后同步删除数据模型里的记录）。
        """
        removed = []
        for item in self._scene.selectedItems():
            # ShapeItemMixin 是所有标注图元的公共混入类，
            # isinstance 判断天然兼容矩形、多边形及以后新增的图元类型
            if isinstance(item, ShapeItemMixin):
                removed.append(item.shape_data)
                self._shape_items.remove(item)
                self._scene.removeItem(item)
        return removed

    def select_shape(self, shape: Annotation) -> None:
        """
        选中某个标注对应的图元（用户在右侧对象列表点击时调用），
        并让画布滚动到能看见它。
        """
        self._scene.clearSelection()
        for item in self._shape_items:
            if item.shape_data is shape:  # “is”：比较是不是同一个对象
                item.setSelected(True)
                self.ensureVisible(item, 80, 80)  # 留出 80 像素边距
                break

    def selected_shapes(self) -> list[Annotation]:
        """返回当前画布上所有被选中标注的 Shape（复制功能用）。"""
        return [item.shape_data for item in self._shape_items
                if item.isSelected()]

    def set_shapes_visible(self, visible: bool) -> None:
        """显示/隐藏全部标注图元（“显示标注”开关，不影响数据）。"""
        for item in self._shape_items:
            item.setVisible(visible)

    def notify_shape_moved(self, shape: Annotation) -> None:
        """
        供图元调用：某个标注的位置或大小被改变了。
        画布把这个事件转成信号广播给主窗口
        （主窗口据此标记“有未保存修改”并把修改记入撤销栈）。
        """
        self.shape_moved.emit(shape)

    def find_item(self, shape: Annotation):
        """按数据对象查找对应的图元（修改标签时同步更新显示用）。"""
        for item in self._shape_items:
            if item.shape_data is shape:
                return item
        return None

    # ==================================================================
    # 坐标换算（场景坐标 <-> 图片坐标，所有换算集中在这里）
    # ==================================================================
    def scene_point_to_image(self, p: QPointF) -> tuple[float, float]:
        """场景坐标点 -> 图片坐标 (x, y)。换算规则：加半个图片宽高。"""
        w, h = self._pixmap.width(), self._pixmap.height()
        return p.x() + w / 2, p.y() + h / 2

    def image_point_to_scene(self, x: float, y: float) -> QPointF:
        """图片坐标 (x, y) -> 场景坐标点。换算规则：减半个图片宽高。"""
        w, h = self._pixmap.width(), self._pixmap.height()
        return QPointF(x - w / 2, y - h / 2)

    def scene_rect_to_image(self, rect: QRectF) -> tuple[float, float, float, float]:
        """场景坐标系的矩形 -> 图片坐标的 (x, y, 宽, 高)。"""
        w, h = self._pixmap.width(), self._pixmap.height()
        return rect.x() + w / 2, rect.y() + h / 2, rect.width(), rect.height()

    def scene_rect_to_image_points(self, rect: QRectF) -> list[tuple[float, float]]:
        """场景坐标系的矩形 -> 图片坐标的 [左上角, 右下角] 两个点。"""
        x, y, w, h = self.scene_rect_to_image(rect)
        return [(x, y), (x + w, y + h)]

    def image_rect_to_scene(self, image_rect: tuple) -> QRectF:
        """图片坐标的 (x, y, 宽, 高) -> 场景坐标系的矩形。"""
        x, y, w, h = image_rect
        pw, ph = self._pixmap.width(), self._pixmap.height()
        return QRectF(x - pw / 2, y - ph / 2, w, h)

    # ==================================================================
    # 视图控制（缩放 / 平移）
    # ==================================================================
    def zoom_in(self) -> None:
        """放大一档。"""
        self._apply_zoom(self.ZOOM_IN_FACTOR)

    def zoom_out(self) -> None:
        """缩小一档。"""
        self._apply_zoom(self.ZOOM_OUT_FACTOR)

    def fit(self) -> None:
        """适应窗口：整张图片恰好完整显示在画布中。"""
        if self._image_item is None:
            return
        self._fit_mode = True
        self.fitInView(self._image_item, Qt.AspectRatioMode.KeepAspectRatio)
        self._emit_zoom()

    def actual_size(self) -> None:
        """原始大小：图片 1 个像素 = 屏幕 1 个像素（100%）。"""
        self._fit_mode = False
        self.resetTransform()  # 重置所有缩放，回到 100%
        self._emit_zoom()

    # ==================================================================
    # Qt 事件处理（用户在画布上的操作会触发这些函数）
    # ==================================================================
    def wheelEvent(self, event) -> None:
        """滚轮 = 缩放（以鼠标为中心）。"""
        if self._pixmap is None:
            return  # 还没加载图片时不响应
        if event.angleDelta().y() > 0:
            self.zoom_in()   # 滚轮向上滚 = 放大
        else:
            self.zoom_out()

    def keyPressEvent(self, event) -> None:
        """空格 = 临时抓手模式（平移）；Esc = 取消绘制；回车 = 完成绘制。"""
        if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
            self._saved_drag_mode = self.dragMode()  # 记住当前模式，松开空格恢复
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            return
        if event.key() == Qt.Key.Key_Escape and self._tool is not None:
            self._tool.cancel(self)  # 放弃画了一半的标注
            return
        # 回车 = 完成绘制（多边形等工具用）。
        # getattr 的用法：工具有 confirm 方法才调用，没有也不报错 ——
        # 这样“可选方法”就不用在基类里强制定义了
        if (event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
                and self._tool is not None
                and hasattr(self._tool, "confirm")):
            self._tool.confirm(self)
            return
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event) -> None:
        """松开空格 = 恢复之前的模式。"""
        if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
            self.setDragMode(getattr(self, "_saved_drag_mode",
                                     QGraphicsView.DragMode.NoDrag))
            return
        super().keyReleaseEvent(event)

    def mousePressEvent(self, event) -> None:
        """鼠标按下：标注模式下转给工具；否则交给 Qt（点选/拖动/平移）。"""
        # 空格平移优先：抓手模式下事件必须交给 Qt 的拖拽逻辑
        if self.dragMode() == QGraphicsView.DragMode.ScrollHandDrag:
            super().mousePressEvent(event)
            return
        # 标注模式：左键事件由当前工具全权处理，
        # 不调用 super() —— 否则事件会继续传给底下的标注图元，
        # 画新框时会误选中/误拖动已有的框
        if self._tool is not None and event.button() == Qt.MouseButton.LeftButton:
            self._tool.on_mouse_press(self, self.mapToScene(event.position().toPoint()))
            return
        # 选择模式：如果按在了某个标注（或其角点把手）上，
        # 先广播“拖动开始”——主窗口会在此刻存一份撤销快照，
        # 这样之后的拖动/拉伸无论产生多少次位移都只算一次操作
        if event.button() == Qt.MouseButton.LeftButton:
            item = self._shape_at(self.mapToScene(event.position().toPoint()))
            if item is not None:
                self.shape_drag_started.emit(item)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        """鼠标移动：转发给工具（更新预览），并广播图片坐标给状态栏。"""
        super().mouseMoveEvent(event)
        if self._pixmap is None:
            return
        scene_pos = self.mapToScene(event.position().toPoint())
        if self._tool is not None:
            self._tool.on_mouse_move(self, scene_pos)
        # 场景坐标 -> 图片坐标（内联换算，仅用于状态栏显示）
        w, h = self._pixmap.width(), self._pixmap.height()
        x, y = int(scene_pos.x() + w / 2), int(scene_pos.y() + h / 2)
        if 0 <= x < w and 0 <= y < h:  # 只在图片范围内报告坐标
            self.mouse_moved.emit(x, y)

    def mouseReleaseEvent(self, event) -> None:
        """鼠标松开：标注模式下转给工具（完成绘制）。"""
        if (self._tool is not None
                and event.button() == Qt.MouseButton.LeftButton
                and self.dragMode() != QGraphicsView.DragMode.ScrollHandDrag):
            self._tool.on_mouse_release(self, self.mapToScene(event.position().toPoint()))
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        """鼠标双击：转发给工具（多边形用双击快速闭合）。"""
        if (self._tool is not None
                and event.button() == Qt.MouseButton.LeftButton
                and hasattr(self._tool, "on_mouse_double_click")):
            self._tool.on_mouse_double_click(
                self, self.mapToScene(event.position().toPoint()))
            return
        super().mouseDoubleClickEvent(event)

    def resizeEvent(self, event) -> None:
        """窗口大小变化时，如果处于“适应窗口”模式就自动重新适应。"""
        super().resizeEvent(event)
        if self._fit_mode and self._image_item is not None:
            self.fit()

    # ==================================================================
    # 内部辅助方法
    # ==================================================================
    def _show_placeholder(self) -> None:
        """在场景中央显示“尚未打开图片”的引导提示。"""
        self._scene.addRect(
            -380, -260, 760, 520,
            QPen(QColor("#5a5b62"), 2, Qt.PenStyle.DashLine),
        )
        text = self._scene.addText("点击左上角「打开文件夹」开始标注")
        font = QFont()
        font.setPointSize(16)
        text.setFont(font)
        text.setDefaultTextColor(QColor("#9a9da5"))
        # 文字水平居中：左边界向左移动自身宽度的一半
        text.setPos(-text.boundingRect().width() / 2, -20)
        self._scene.setSceneRect(-500, -350, 1000, 700)

    def _apply_zoom(self, factor: float) -> None:
        """以 factor 倍率缩放（手动缩放后退出“适应窗口”模式）。"""
        if self._pixmap is None:
            return
        # 限制缩放范围：当前比例乘以倍率后超出 [ZOOM_MIN, ZOOM_MAX]
        # 就贴到边界上，防止无限缩小到看不见 / 无限放大到性能崩溃
        new_scale = self.transform().m11() * factor
        new_scale = max(self.ZOOM_MIN, min(self.ZOOM_MAX, new_scale))
        self._fit_mode = False
        self.resetTransform()          # 先清零，再缩放到目标值（比叠加更精确）
        self.scale(new_scale, new_scale)
        self._emit_zoom()

    def _shape_at(self, scene_pos: QPointF):
        """
        查找某个场景坐标下的标注图元（找不到返回 None）。

        点击位置最上层的图元可能是矩形的“角点把手”（它是矩形的子图元），
        所以沿 parentItem() 链向上找，直到找到真正的标注图元为止。
        """
        item = self._scene.itemAt(scene_pos, self.transform())
        while item is not None and not isinstance(item, ShapeItemMixin):
            item = item.parentItem()
        return item

    def _emit_zoom(self) -> None:
        """读取当前真实的缩放比例并广播。transform().m11() 是横向缩放系数。"""
        self.zoom_changed.emit(round(self.transform().m11() * 100))

    def _on_selection_changed(self) -> None:
        """
        场景中的选中集变化时（用户点选/框选/取消选中）：
        1. 刷新所有标注图元的外观（选中的画虚线高亮）
        2. 把选中的 Annotation 广播给主窗口（同步右侧的对象列表和属性面板）
        """
        selected_shape = None
        for item in self._shape_items:
            is_sel = item.isSelected()
            item.set_selected_style(is_sel)
            if is_sel and selected_shape is None:
                selected_shape = item.shape_data  # 多选时只取第一个同步给面板
        self.shape_selected.emit(selected_shape)
