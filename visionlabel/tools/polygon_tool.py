"""
多边形标注工具
==============

第二个 BaseTool 实现，用于分割类标注。它的存在本身就在验证
插件架构：整个文件不需要改动画布/主窗口的既有代码，
只在画布的工具注册表里加一行就能工作。

交互流程（和 labelme 一致）：
    1. 单击左键    -> 放下一个顶点（顶点用小圆点标出）
    2. 移动鼠标    -> 虚线预览：已放顶点依次相连，最后一个点连着鼠标
    3. 单击【第一个顶点】附近 -> 闭合多边形，完成绘制
       （或者：双击 / 按回车，也能闭合）
    4. Esc         -> 放弃画了一半的多边形
    少于 3 个顶点不能构成多边形，闭合请求会被忽略。

与矩形工具的关键区别：
    矩形是“按下-拖动-松开”一次完成；多边形是“多次点击”完成。
    所以多边形工具内部要维护一个“正在绘制的顶点列表”，
    并且主要响应 mouse_press 而不是 mouse_drag。
"""

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainterPath, QPen

from .base_tool import BaseTool

# 预览线的样式（醒目的青色虚线，和任何类别颜色都不冲突）
_PREVIEW_COLOR = "#00c8ff"
# 顶点小圆点的半径（屏幕像素）
_DOT_RADIUS = 4.0


class PolygonTool(BaseTool):
    """多边形标注工具：逐点点击，回到起点闭合。"""

    key = "polygon"
    name = "多边形"
    shortcut = "P"

    MIN_POINTS = 3        # 最少几个顶点才能闭合
    CLOSE_DISTANCE = 12   # 屏幕像素：点击离起点这么近就视为“闭合”

    def __init__(self):
        # 一次绘制过程中的临时状态：
        self._vertices: list[QPointF] = []  # 已放下的顶点（场景坐标）
        self._path_item = None              # 虚线预览路径（场景图元）
        self._dot_items = []                # 顶点小圆点（场景图元列表）

    # ------------------------------------------------------------------
    # 鼠标事件（画布会在标注模式下把这些事件转发过来）
    # ------------------------------------------------------------------
    def on_mouse_press(self, canvas, pos) -> None:
        """单击左键：放下一个顶点；点在起点附近则闭合。"""
        if not self._vertices:
            # 第一个顶点：创建预览路径和起点圆点
            self._vertices.append(pos)
            self._create_preview(canvas, pos)
            return

        # 判断“是否点回了起点附近”（闭合信号）
        if (len(self._vertices) >= self.MIN_POINTS
                and self._screen_distance(canvas, pos, self._vertices[0])
                < self.CLOSE_DISTANCE):
            self._finish(canvas)
            return

        # 普通情况：追加一个顶点
        self._vertices.append(pos)
        self._add_dot(canvas, pos, is_first=False)

    def on_mouse_move(self, canvas, pos) -> None:
        """移动鼠标：更新虚线预览（顶点依次相连 + 末尾跟着鼠标）。"""
        if self._path_item is None:
            return
        path = QPainterPath(self._vertices[0])
        for v in self._vertices[1:]:
            path.lineTo(v)
        path.lineTo(pos)  # 预览的最后一截：最后一个顶点 -> 鼠标当前位置
        self._path_item.setPath(path)

    def on_mouse_release(self, canvas, pos) -> None:
        """多边形靠“点击”驱动，松开事件不需要处理（合同要求实现，留空）。"""

    def on_mouse_double_click(self, canvas, pos) -> None:
        """
        双击 = 闭合多边形（labelme 同款快捷操作）。

        细节：双击会先触发两次“单击”，可能已经误加了一个顶点，
        所以如果最后一个顶点和前一个几乎重合，先把它弹掉再闭合。
        """
        if len(self._vertices) >= 2:
            last, prev = self._vertices[-1], self._vertices[-2]
            if self._screen_distance(canvas, last, prev) < self.CLOSE_DISTANCE:
                canvas.scene().removeItem(self._dot_items.pop())
                self._vertices.pop()
        if len(self._vertices) >= self.MIN_POINTS:
            self._finish(canvas)

    def confirm(self, canvas) -> None:
        """按回车 = 闭合多边形（由画布的按键事件转发过来）。"""
        if len(self._vertices) >= self.MIN_POINTS:
            self._finish(canvas)

    def cancel(self, canvas) -> None:
        """Esc 或切换工具：放弃画了一半的多边形。"""
        self._cleanup(canvas)

    # ------------------------------------------------------------------
    # 内部实现
    # ------------------------------------------------------------------
    def _create_preview(self, canvas, pos: QPointF) -> None:
        """创建虚线预览路径和“起点”圆点（起点用更大的点提示可点击闭合）。"""
        pen = QPen(QColor(_PREVIEW_COLOR), 2, Qt.PenStyle.DashLine)
        pen.setCosmetic(True)  # 线宽固定为屏幕像素，不随缩放变粗
        self._path_item = canvas.scene().addPath(QPainterPath(pos), pen)
        self._add_dot(canvas, pos, is_first=True)

    def _add_dot(self, canvas, pos: QPointF, is_first: bool) -> None:
        """在顶点处画一个小圆点；起点画得更大，提示“点我闭合”。"""
        r = _DOT_RADIUS * (1.6 if is_first else 1.0)
        color = QColor(_PREVIEW_COLOR)
        dot = canvas.scene().addEllipse(-r, -r, 2 * r, 2 * r,
                                        QPen(Qt.PenStyle.NoPen), color)
        # ItemIgnoresTransformations：圆点始终以屏幕像素大小显示，
        # 画布放大时圆点不会跟着变成大圆盘
        dot.setFlag(dot.GraphicsItemFlag.ItemIgnoresTransformations)
        dot.setPos(pos)
        self._dot_items.append(dot)

    def _finish(self, canvas) -> None:
        """闭合：把顶点列表交给画布（画布负责坐标换算和通知主窗口）。"""
        vertices = list(self._vertices)  # 复制一份再清理，避免引用纠缠
        self._cleanup(canvas)
        canvas.finish_new_polygon(vertices)

    def _cleanup(self, canvas) -> None:
        """删除预览用的全部图元并重置状态。"""
        if self._path_item is not None:
            canvas.scene().removeItem(self._path_item)
            self._path_item = None
        for dot in self._dot_items:
            canvas.scene().removeItem(dot)
        self._dot_items.clear()
        self._vertices.clear()

    @staticmethod
    def _screen_distance(canvas, p1: QPointF, p2: QPointF) -> float:
        """
        计算两个场景点的距离，单位换算成【屏幕像素】。

        为什么要换算？“点回起点附近就闭合”的“附近”应该是屏幕上
        看起来近（比如 12 个屏幕像素），而不是图片上的固定像素数 ——
        否则画布缩得很小的时候，屏幕上看着明明点中了却无法闭合。
        场景距离 × 当前缩放系数（transform().m11()）= 屏幕距离。
        """
        dx, dy = p1.x() - p2.x(), p1.y() - p2.y()
        scene_dist = (dx * dx + dy * dy) ** 0.5  # 欧氏距离（场景坐标）
        return scene_dist * canvas.transform().m11()
