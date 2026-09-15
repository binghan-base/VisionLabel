"""
矩形框标注工具
==============

第一个 BaseTool 的具体实现，也是理解“插件式工具”的最好样本。

交互流程（和 labelImg 一致）：
    1. 按下左键  -> 记录起点，创建一个虚线预览框
    2. 拖动鼠标  -> 预览框实时跟随（起点固定，另一个角跟着鼠标走）
    3. 松开左键  -> 如果框够大，通知画布“矩形画好了”；
                    如果太小（基本是误触），丢弃
    4. 画框途中按 Esc / 切换工具 -> 取消，删掉预览框

注意：这个工具只负责“画出一个矩形区域”，它不知道类别、
不知道保存 —— 矩形画好后由画布发信号通知主窗口，
主窗口再决定用什么类别、怎么存。“各司其职”是这套架构的核心。
"""

from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor, QPen

from .base_tool import BaseTool

# 预览框的样式（醒目的青色虚线，和任何类别颜色都不冲突）
_PREVIEW_COLOR = "#00c8ff"


class RectTool(BaseTool):
    """矩形框标注工具：拖拽画出矩形。"""

    key = "rect"
    name = "矩形框"
    shortcut = "R"

    # 最小有效尺寸（场景像素）：小于这个尺寸视为误触，不生成标注
    MIN_SIZE = 3.0

    def __init__(self):
        # 一次绘制过程中的临时状态：
        self._start = None       # 起点（场景坐标），None 表示当前没在画
        self._preview = None     # 虚线预览框（场景中的临时图元）

    # ------------------------------------------------------------------
    # 鼠标事件（画布会在标注模式下把这些事件转发过来）
    # ------------------------------------------------------------------
    def on_mouse_press(self, canvas, pos) -> None:
        """按下左键：记录起点，并在场景中创建一个虚线预览框。"""
        self._start = pos

        # QPen 的 setCosmetic(True) 是个重要细节：
        # “装饰线”宽度固定为屏幕上的 2 像素，不随画布缩放变粗变细，
        # 否则放大图片后预览线会变成粗得离谱的色块
        pen = QPen(QColor(_PREVIEW_COLOR), 2)
        pen.setCosmetic(True)

        # 先创建一个零尺寸的矩形，拖动时不断更新它的范围
        self._preview = canvas.scene().addRect(QRectF(pos, pos), pen)

    def on_mouse_move(self, canvas, pos) -> None:
        """拖动中：用“起点”和“当前鼠标位置”更新预览框。"""
        if self._preview is None:
            return
        # QRectF(起点, 终点).normalized() 自动处理“往左上拖”的情况，
        # 保证得到的矩形宽、高一定是正数
        self._preview.setRect(QRectF(self._start, pos).normalized())

    def on_mouse_release(self, canvas, pos) -> None:
        """松开左键：完成绘制（或因为太小而丢弃）。"""
        if self._preview is None:
            return

        rect = QRectF(self._start, pos).normalized()
        self._cleanup(canvas)  # 无论成功与否，预览框都要删掉

        # 过滤误触：点了一下没拖动、或框太小，都不算有效标注
        if rect.width() < self.MIN_SIZE or rect.height() < self.MIN_SIZE:
            return

        # 通知画布“矩形画好了”。画布会换算成图片坐标并发信号给主窗口，
        # 之后的归类、显示、保存都不是这个工具的职责
        canvas.finish_new_rect(rect)

    def cancel(self, canvas) -> None:
        """Esc 或切换工具：取消正在进行的绘制。"""
        self._cleanup(canvas)

    # ------------------------------------------------------------------
    # 内部辅助
    # ------------------------------------------------------------------
    def _cleanup(self, canvas) -> None:
        """删除预览框并重置状态。"""
        if self._preview is not None:
            canvas.scene().removeItem(self._preview)  # 从场景中移除图元
            self._preview = None
        self._start = None
