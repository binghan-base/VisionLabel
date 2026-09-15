"""
左侧标注模式条
==============

一条竖向的工具栏，每个按钮对应一种标注模式（选择/矩形框/多边形/关键点……）。

实现要点（Qt 知识）：
- 直接用 Qt 自带的 QToolBar，设置为竖向，放在主窗口左侧；
- 按钮不是写死的，而是遍历 config.MODES 列表自动生成 ——
  新增标注类型时只需改配置，不用改这里的代码；
- 所有模式按钮属于同一个 QActionGroup（互斥组），
  任意时刻只有一个按钮处于“按下”状态，就像收音机选台按钮。
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import QToolBar, QToolButton

from .. import config
from ..icons import make_icon


class ModeStrip(QToolBar):
    """左侧竖向模式条。继承 QToolBar，自己就是一种工具栏。"""

    # Qt 信号（Signal）：当用户切换模式时，这个组件会“广播”一条消息，
    # 携带新模式的 key。谁关心这件事，谁就来连接（connect）这个信号。
    # 这是 Qt 最核心的“信号与槽”机制，用于组件之间解耦通信。
    mode_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__("标注模式", parent)

        # ---- 外观设置 ----
        self.setOrientation(Qt.Orientation.Vertical)      # 竖向排列
        self.setMovable(False)                            # 不允许用户拖走
        # 按钮样式：图标在上、文字在下（适合模式切换按钮）
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)

        # ---- 互斥组：保证任意时刻只有一个模式被选中 ----
        self._group = QActionGroup(self)
        self._group.setExclusive(True)

        # 保存 {模式key: 对应的QAction}，方便以后按 key 查找
        self._actions: dict[str, QAction] = {}

        self._build_buttons()

    def _build_buttons(self) -> None:
        """根据 config.MODES 自动生成按钮。"""
        for index, mode in enumerate(config.MODES):
            # config 中“预留扩展位”之前用一个分隔线隔开，视觉上分组
            if not mode["enabled"] and index > 0 and config.MODES[index - 1]["enabled"]:
                self.addSeparator()

            # QAction 是 Qt 里“一个操作”的抽象：同一个 QAction
            # 可以同时出现在工具栏按钮和菜单项上，状态自动同步。
            action = QAction(make_icon(mode["icon"]), mode["name"], self)
            action.setCheckable(True)                     # 可以处于“按下”状态
            action.setEnabled(mode["enabled"])            # 预留位显示为灰色
            if mode["shortcut"]:
                action.setShortcut(mode["shortcut"])      # 快捷键（如 V/R/P/K）
                action.setToolTip(f'{mode["name"]} ({mode["shortcut"]})')

            # 用字典把模式的 key 存进 action 自带的小口袋，
            # 用户点击时就能知道点的是哪个模式
            action.setData(mode["key"])

            self._group.addAction(action)   # 加入互斥组
            self.addAction(action)          # 显示到工具栏上
            self._actions[mode["key"]] = action

        # 默认选中第一个可用模式（“选择/编辑”）
        first_key = config.MODES[0]["key"]
        self._actions[first_key].setChecked(True)

        # 当互斥组里有按钮被触发时，对外广播 mode_changed 信号
        self._group.triggered.connect(self._on_triggered)

    def _on_triggered(self, action: QAction) -> None:
        """内部槽函数：把 QAction 翻译成模式 key，再广播出去。"""
        self.mode_changed.emit(action.data())

    def current_mode(self) -> str:
        """返回当前选中的模式 key。"""
        checked = self._group.checkedAction()
        return checked.data() if checked else ""
