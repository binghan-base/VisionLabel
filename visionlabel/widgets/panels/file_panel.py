"""
文件列表面板
============

显示当前文件夹里的所有图片，以及每张图片的标注状态：
    ✓ 已标注  ✓ 空标注  ○ 未标注  ● 未保存  ⚠ 标注损坏

用户点击某一行时，通过 file_selected 信号广播行号，
主窗口收到后加载对应的图片。
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QListWidget, QListWidgetItem

from ...models.annotation_status import AnnotationStatus

# 状态 -> (显示文字, 颜色)。集中定义在这里，改样式只改这一处。
_STATUS_STYLE = {
    AnnotationStatus.DONE: ("✓ 已标注", "#1a9e54"),
    AnnotationStatus.EMPTY: ("✓ 空标注", "#1677ff"),
    AnnotationStatus.TODO: ("○ 未标注", "#999999"),
    AnnotationStatus.DIRTY: ("● 未保存", "#fa8c16"),
    AnnotationStatus.ERROR: ("⚠ 标注损坏", "#d4380d"),
}


class FilePanel(QListWidget):
    """文件列表面板。直接继承 QListWidget，自己就是一个列表。"""

    # 信号：用户点击了第几行（从 0 开始）
    file_selected = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)

        # 初始状态：还没有打开文件夹时的占位提示
        placeholder = QListWidgetItem("（尚未打开文件夹）")
        placeholder.setFlags(Qt.ItemFlag.NoItemFlags)  # 不可选中、不可点击
        placeholder.setForeground(QColor("#999999"))
        self.addItem(placeholder)

        # 用户点击/键盘切换行时，广播行号
        self.currentRowChanged.connect(self._on_row_changed)

    def set_files(self, names: list[str], statuses: list[AnnotationStatus]) -> None:
        """
        用真实的文件列表刷新面板（打开文件夹后由主窗口调用）。

        参数：
            names     文件名列表
            statuses  对应的 AnnotationStatus 列表，与 names 等长、顺序一致。
                      与 names 等长、顺序一致
        """
        self.blockSignals(True)  # 刷新期间不广播选中变化
        self.clear()
        for name, status in zip(names, statuses):
            status_text, status_color = _STATUS_STYLE[status]
            item = QListWidgetItem(f"{name:<14}{status_text}")
            # 把纯文件名存进列表项自带的“小口袋”（UserRole），
            # 以后更新状态文字时直接从口袋里取，不用从显示文字里反推
            item.setData(Qt.ItemDataRole.UserRole, name)
            item.setForeground(QColor(status_color))
            self.addItem(item)
        self.blockSignals(False)

    def set_status(self, row: int, status: AnnotationStatus) -> None:
        """
        更新某一行的标注状态（保存标注后由主窗口调用，
        把“○ 未标注”变成“✓ 已标注”）。
        """
        if not (0 <= row < self.count()):
            return
        item = self.item(row)
        status_text, status_color = _STATUS_STYLE[status]
        # 从创建时存好的“小口袋”里取回纯文件名，重新拼显示文字
        name = item.data(Qt.ItemDataRole.UserRole)
        item.setText(f"{name:<14}{status_text}")
        item.setForeground(QColor(status_color))

    def set_current(self, row: int) -> None:
        """高亮某一行（切换图片时由主窗口调用，保持列表高亮同步）。"""
        self.blockSignals(True)
        self.setCurrentRow(row)
        self.blockSignals(False)

    def _on_row_changed(self, row: int) -> None:
        """内部槽函数：行号有效时才广播（清空列表时 row 是 -1，忽略）。"""
        if row >= 0:
            self.file_selected.emit(row)
