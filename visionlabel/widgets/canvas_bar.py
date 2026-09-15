"""
画布控制条
==========

固定在画布正下方的一条深色控制条，放“视图控制”类按钮：
翻页（上一张/页码跳转/下一张）和缩放（缩小/放大/适应窗口/1:1）。

设计原则：这个组件只负责“把用户的点击翻译成信号广播出去”，
具体做什么（加载上一张？执行缩放？）由主窗口决定 ——
组件之间通过信号解耦，组件本身不包含业务逻辑。
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QStyle,
    QStyleOption,
    QWidget,
)

from ..icons import make_icon

# 深色控制条上的图标/文字颜色
ICON_COLOR = "#cfd2d8"


class CanvasBar(QWidget):
    """画布下方的控制条（翻页 + 缩放）。"""

    # ---- 信号：用户点击了某个按钮（具体动作由主窗口决定）----
    prev_clicked = Signal()
    next_clicked = Signal()
    page_jumped = Signal(int)        # 用户在页码框输入并回车（页码从 1 开始）
    zoom_in_clicked = Signal()
    zoom_out_clicked = Signal()
    fit_clicked = Signal()
    actual_size_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(42)  # 高度固定，宽度随窗口伸缩

        # 样式表（QSS，语法类似网页 CSS）：深色背景，与画布融为一体
        self.setStyleSheet("""
            CanvasBar { background: #2e2f34; border-top: 1px solid #24252a; }
            QPushButton {
                color: #cfd2d8; background: transparent;
                border: none; border-radius: 6px; padding: 6px 12px;
            }
            QPushButton:hover { background: #3d3f46; }
            QPushButton:disabled { color: #6a6c73; }
            QLabel { color: #9a9da5; }
            QLineEdit {
                color: white; background: #24252a;
                border: 1px solid #4a4b52; border-radius: 4px;
                padding: 3px 6px;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 8, 0)  # 控件与边缘的留白
        layout.setSpacing(6)                   # 控件之间的间距

        # ---- 左侧占位弹簧：和末尾的右侧弹簧配合，把内容挤到中间 ----
        layout.addStretch()

        # ---- 翻页区 ----
        self.btn_prev = QPushButton(make_icon("chevron-left", ICON_COLOR), "上一张")
        self.btn_prev.setToolTip("上一张 (A)")

        # 页码输入框：显示当前页，输入数字回车可跳转
        self.page_edit = QLineEdit("-")
        self.page_edit.setFixedWidth(56)
        self.page_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_total = QLabel("/ -")

        self.btn_next = QPushButton(make_icon("chevron-right", ICON_COLOR), "下一张")
        self.btn_next.setToolTip("下一张 (D)")

        layout.addWidget(self.btn_prev)
        layout.addWidget(self.page_edit)
        layout.addWidget(self.page_total)
        layout.addWidget(self.btn_next)

        layout.addWidget(self._make_separator())

        # ---- 缩放区 ----
        self.btn_zoom_out = QPushButton(make_icon("zoom-out", ICON_COLOR), "缩小")
        self.zoom_label = QLabel("-")
        self.zoom_label.setStyleSheet("color: white; min-width: 44px;")
        self.zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.btn_zoom_in = QPushButton(make_icon("zoom-in", ICON_COLOR), "放大")
        self.btn_fit = QPushButton(make_icon("maximize", ICON_COLOR), "适应窗口")
        self.btn_fit.setToolTip("适应窗口 (F)")
        self.btn_actual = QPushButton("1:1")
        self.btn_actual.setToolTip("原始大小 (Ctrl+0)")

        layout.addWidget(self.btn_zoom_out)
        layout.addWidget(self.zoom_label)
        layout.addWidget(self.btn_zoom_in)
        layout.addWidget(self.btn_fit)
        layout.addWidget(self.btn_actual)

        # ---- 右侧占位弹簧 ----
        layout.addStretch()

        # ---- 把按钮的 clicked 信号“转发”成本组件的对外信号 ----
        # 这样主窗口只需要关心 CanvasBar 的信号，不用知道里面有哪些按钮
        self.btn_prev.clicked.connect(self.prev_clicked)
        self.btn_next.clicked.connect(self.next_clicked)
        self.btn_zoom_in.clicked.connect(self.zoom_in_clicked)
        self.btn_zoom_out.clicked.connect(self.zoom_out_clicked)
        self.btn_fit.clicked.connect(self.fit_clicked)
        self.btn_actual.clicked.connect(self.actual_size_clicked)
        self.page_edit.returnPressed.connect(self._on_page_edit_return)

    # ------------------------------------------------------------------
    # 对外方法：主窗口用来更新显示
    # ------------------------------------------------------------------
    def set_page(self, current: int, total: int) -> None:
        """更新页码显示。current 从 1 开始；total 为 0 表示没有图片。"""
        if total <= 0:
            self.page_edit.setText("-")
            self.page_total.setText("/ -")
        else:
            self.page_edit.setText(str(current))
            self.page_total.setText(f"/ {total}")

    def set_zoom(self, percent: int) -> None:
        """更新缩放百分比显示。"""
        self.zoom_label.setText(f"{percent}%")

    # ------------------------------------------------------------------
    # 内部实现
    # ------------------------------------------------------------------
    def _on_page_edit_return(self) -> None:
        """用户在页码框按下回车：解析数字并广播跳转请求。"""
        text = self.page_edit.text().strip()
        if text.isdigit():
            self.page_jumped.emit(int(text))
        self.page_edit.clearFocus()  # 交出焦点，让 A/D 等快捷键恢复可用

    def paintEvent(self, event) -> None:
        """
        Qt 的一个“坑”：普通的 QWidget 子类即使设置了样式表背景，
        默认也不会把背景画出来（按钮等控件没这个问题）。
        解决办法是像下面这样，在 paintEvent 里让当前风格
        把样式表描述的背景画出来 —— 这是 Qt 官方文档推荐的标准写法。
        """
        option = QStyleOption()
        option.initFrom(self)  # 把控件的几何、状态、样式表信息收集进来
        painter = QPainter(self)
        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, option, painter, self)

    @staticmethod
    def _make_separator() -> QFrame:
        """创建一条竖直分隔线（Qt 没有现成的“分隔线控件”，用 QFrame 模拟）。"""
        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setStyleSheet("color: #4a4b52;")  # 分隔线的颜色
        return line
