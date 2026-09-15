"""
标签输入弹窗
============

用户每画完一个标注，就弹出这个对话框，让用户给标注选/填类别。

设计参照 labelme，行为规则（与用户需求一一对应）：
1. 弹窗里列出所有已知标签，点选即可；
2. 想要的标签不存在？直接在输入框里打字，回车就创建了新标签；
3. 输入框默认填入“上一个标注用的标签”并全选 ——
   连续标同一类目标时，一路回车就行，零输入成本；
4. 输入框带自动补全（QCompleter），打字时实时匹配已有标签；
5. 按 Esc / 点取消 = 放弃刚才画的这个标注。

关于“模态对话框”：
    exec() 会以“模态”方式弹出对话框 —— 弹窗期间主窗口被冻结，
    用户只能跟弹窗交互，直到点确定/取消。这正是我们想要的效果：
    画完框必须先给出标签，流程不会乱。
"""

from PySide6.QtCore import Qt, QStringListModel
from PySide6.QtWidgets import (
    QCompleter,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QListWidget,
    QVBoxLayout,
)


class LabelDialog(QDialog):
    """“输入/选择标签”对话框。继承 Qt 的 QDialog（对话框基类）。"""

    def __init__(self, labels: list[str], last_label: str | None, parent=None):
        """
        参数：
            labels      当前项目里已知的所有标签（供点选和自动补全）
            last_label  上一个标注用的标签（作为默认值预填进输入框）
            parent      父窗口（Qt 用父子关系管理窗口层级和内存）
        """
        super().__init__(parent)
        self.setWindowTitle("输入标签")
        self.setMinimumWidth(280)

        layout = QVBoxLayout(self)

        # ---- 提示文字 ----
        hint = QLabel("选择已有标签，或直接输入新标签名：")
        layout.addWidget(hint)

        # ---- 输入框（带自动补全）----
        self.edit = QLineEdit()
        # QCompleter：输入时弹出匹配建议。QStringListModel 是补全的数据源
        completer = QCompleter(QStringListModel(labels), self)
        # 默认补全是“开头匹配”，改成“包含匹配”更宽松好用
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.edit.setCompleter(completer)
        layout.addWidget(self.edit)

        # ---- 已有标签列表（单击填入输入框，双击直接确定）----
        self.list = QListWidget()
        self.list.addItems(labels)
        layout.addWidget(self.list)

        # ---- 确定 / 取消按钮 ----
        # QDialogButtonBox 是 Qt 自带的“对话框按钮排”
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText("确定")
        self.buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        layout.addWidget(self.buttons)

        # ---- 行为连接 ----
        self.buttons.accepted.connect(self.accept)  # 确定 -> 对话框以“接受”关闭
        self.buttons.rejected.connect(self.reject)  # 取消 -> 以“拒绝”关闭
        # 单击列表项：把标签填进输入框，方便再修改
        self.list.currentTextChanged.connect(self.edit.setText)
        # 双击列表项：直接确定（少点一次鼠标）
        self.list.itemDoubleClicked.connect(lambda _item: self.accept())

        # ---- 默认值的细节（对应需求 3）----
        if last_label:
            self.edit.setText(last_label)
            self.edit.selectAll()  # 全选：想换标签直接打字覆盖，想沿用直接回车
            # 列表里也高亮这一项，视觉上一眼能看出“当前默认”
            matches = self.list.findItems(last_label, Qt.MatchFlag.MatchExactly)
            if matches:
                self.list.setCurrentItem(matches[0])

        # 焦点落在输入框，弹窗一出就能打字
        self.edit.setFocus()

    def label_text(self) -> str:
        """返回用户最终输入的标签名（去掉首尾空白）。"""
        return self.edit.text().strip()

    # ------------------------------------------------------------------
    # 便捷入口：一句调用 = 弹窗 + 拿到结果
    # ------------------------------------------------------------------
    @staticmethod
    def get_label(parent, labels: list[str], last_label: str | None) -> str | None:
        """
        弹出对话框并等待用户操作。

        返回：
            用户确定的标签名（非空字符串）；用户取消则返回 None。
        用 @staticmethod 包一层，主窗口调用起来就是一行：
            label = LabelDialog.get_label(self, self._labels, self._last_label)
        """
        dialog = LabelDialog(labels, last_label, parent)
        # exec() 返回“接受(QDialog.Accepted=1)”还是“拒绝(Rejected=0)”
        if dialog.exec() == QDialog.DialogCode.Accepted:
            text = dialog.label_text()
            return text if text else None  # 空白标签视为取消
        return None
