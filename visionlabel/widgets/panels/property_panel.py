"""
属性面板
========

显示当前选中标注对象的详细信息：类别、位置、分组、备注。

实现：QFormLayout（表单布局），左边是字段名、右边是值。
主窗口在“选中变化”时调用 show_shape() 更新显示；
没有选中任何标注时调用 clear() 显示空状态。
"""

from PySide6.QtWidgets import QFormLayout, QLabel, QLineEdit, QWidget

from ...models.annotation import Annotation


class PropertyPanel(QWidget):
    """属性面板。"""

    def __init__(self, parent=None):
        super().__init__(parent)

        # QFormLayout：两列布局，自动对齐“字段名”和“值”
        layout = QFormLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # 这些 QLabel 保存为成员变量，显示新标注时直接改文字即可，
        # 不用每次重建界面
        self._label_label = QLabel("—")
        self._rect_label = QLabel("—")
        self._group_label = QLabel("—")
        layout.addRow("类别", self._label_label)
        layout.addRow("位置", self._rect_label)
        layout.addRow("分组", self._group_label)

        # 备注允许用户填写，所以用可编辑的 QLineEdit
        # （“保存备注到标注数据”的功能后续实现）
        self.note_edit = QLineEdit()
        self.note_edit.setPlaceholderText("选中标注后可添加备注…")
        layout.addRow("备注", self.note_edit)

    def show_shape(self, shape: Annotation) -> None:
        """显示一个标注对象的属性。"""
        self._label_label.setText(shape.label)
        if shape.shape_type == "rect":
            x, y, w, h = shape.rect()
            self._rect_label.setText(
                f"x:{x:.0f}  y:{y:.0f}  w:{w:.0f}  h:{h:.0f}"
            )
        else:
            # 其他类型的标注（多边形/关键点）后续再细化显示
            self._rect_label.setText(f"{len(shape.points)} 个点")

    def clear(self) -> None:
        """没有选中任何标注时，恢复空状态。"""
        self._label_label.setText("—")
        self._rect_label.setText("—")
        self._group_label.setText("—")
        self.note_edit.clear()
