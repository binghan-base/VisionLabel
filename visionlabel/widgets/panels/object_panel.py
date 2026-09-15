"""
标注对象面板
============

显示“当前这张图片上”已经标注的所有对象（矩形框、多边形……）。
每一行：标注类型的图标（用类别颜色着色）+ 类别名。

交互（双向同步，是“信号与槽”的好例子）：
- 用户点击列表某一行 -> 广播 object_selected -> 画布上对应的框被选中
- 用户在画布上点选一个框 -> 主窗口调用 set_current -> 列表高亮对应行
  （两个方向都可能发起，但数据只有一份：主窗口的标注列表，
    列表第几行就对应列表里的第几个 Shape）
"""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QListWidget, QListWidgetItem

from ...icons import make_icon
from ...models.annotation import Annotation


class ObjectPanel(QListWidget):
    """标注对象列表面板。"""

    # 信号：用户点击了第几行（从 0 开始，与标注列表的下标一致）
    object_selected = Signal(int)
    # 信号：用户双击了第几行（主窗口据此弹出“修改标签”对话框）
    edit_requested = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlternatingRowColors(True)
        self.currentRowChanged.connect(self._on_row_changed)
        # itemDoubleClicked 是 QListWidget 自带的信号，参数是被双击的“项”，
        # 我们用 self.row() 把“项”换算成行号再广播出去
        self.itemDoubleClicked.connect(
            lambda item: self.edit_requested.emit(self.row(item))
        )

    def set_objects(self, shapes: list[Annotation], color_of) -> None:
        """
        用一张图片的标注列表刷新面板（切换图片、增删标注后调用）。

        参数：
            shapes    标注列表
            color_of  一个函数：传入标签名，返回颜色。
                      标签和颜色的对应关系由主窗口管理（标签是用户
                      动态创建的），面板不自己保管这份数据，用时现查。

        注意一个细节：刷新列表会触发 currentRowChanged 信号，
        进而可能引发“选中状态”的连锁刷新。这里用 blockSignals
        暂时屏蔽信号，刷新完再恢复 —— 这是处理这类联动的常用手法。
        """
        self.blockSignals(True)   # 暂停发信号
        self.clear()
        for shape in shapes:
            item = QListWidgetItem(shape.label)
            # 图标同时表达两个信息：形状（矩形/多边形/关键点）+ 类别颜色
            item.setIcon(make_icon(shape.shape_type, color_of(shape.label)))
            self.addItem(item)
        self.blockSignals(False)  # 恢复发信号

    def set_current(self, row: int) -> None:
        """高亮某一行（画布上的标注被选中时由主窗口调用）。"""
        if 0 <= row < self.count():
            self.blockSignals(True)   # 同样屏蔽信号，防止和画布来回触发
            self.setCurrentRow(row)
            self.blockSignals(False)

    def clear_selection(self) -> None:
        """取消高亮（画布上没有选中任何标注时调用）。"""
        self.blockSignals(True)
        self.setCurrentRow(-1)
        self.blockSignals(False)

    def _on_row_changed(self, row: int) -> None:
        """内部槽函数：行号有效时才广播。"""
        if row >= 0:
            self.object_selected.emit(row)
