"""
类别面板
========

显示项目里的所有标注类别（标签）。

重要变化：标签不再是内置的！这个面板的内容由主窗口动态填充 ——
标签有两个来源：
1. 打开文件夹时，从已有标注文件（.json）里读出来的标签；
2. 用户标注时在弹窗里现场输入的新标签。

每一行：快捷键数字、颜色标识、标签名。
交互：点击某一行设为“当前标签”（下一个弹窗的默认值），
数字键 1~9 也可以切换（快捷键在主窗口注册）。
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QListWidget, QListWidgetItem

from ...icons import color_swatch


class ClassPanel(QListWidget):
    """类别列表面板。直接继承 QListWidget，自己就是一个列表。"""

    # 信号：用户选择了第几个标签（从 0 开始）
    class_selected = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlternatingRowColors(True)  # 隔行变色，便于阅读
        self.currentRowChanged.connect(self._on_row_changed)
        self._show_placeholder()

    def set_classes(self, classes: list[tuple[str, str]]) -> None:
        """
        用标签列表刷新面板。

        参数：
            classes  [(标签名, 颜色), ...]，顺序即快捷键序号
        """
        self.blockSignals(True)  # 刷新期间不广播选中变化
        self.clear()
        if not classes:
            self._show_placeholder()
        else:
            for index, (name, color) in enumerate(classes, start=1):
                item = QListWidgetItem(f"{index}  {name}")
                item.setIcon(color_swatch(color))  # 行首的颜色小方块
                self.addItem(item)
        self.blockSignals(False)

    def set_current(self, index: int) -> None:
        """把某个标签设为当前标签（数字快捷键切换时由主窗口调用）。"""
        if 0 <= index < self.count():
            self.setCurrentRow(index)

    def _show_placeholder(self) -> None:
        """没有任何标签时的引导提示。"""
        item = QListWidgetItem("（暂无标签，画一个框创建）")
        item.setFlags(Qt.ItemFlag.NoItemFlags)  # 不可选中
        item.setForeground(QColor("#999999"))
        self.addItem(item)

    def _on_row_changed(self, row: int) -> None:
        """内部槽函数：行号有效时才广播。"""
        if row >= 0:
            self.class_selected.emit(row)
