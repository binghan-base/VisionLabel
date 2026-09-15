"""
主窗口
======

MainWindow 是整个界面的“总装车间 + 总控中心”：

1. 组装：把各个组件（模式条、画布、控制条、面板）创建出来拼到一起；
2. 控制：把组件的信号连接起来，实现完整的业务流程。

标注功能的业务闭环（本次实现的核心）：

    用户在画布拖出一个矩形
      -> 画布发 rect_drawn 信号
      -> 主窗口用“当前类别”创建 Annotation 数据，存进列表
      -> 主窗口让画布画出这个标注、让对象面板刷新列表
    用户点保存 / 切换图片
      -> 主窗口把当前标注写进同名 .json 文件
    用户切回某张图
      -> 主窗口从 .json 读出标注，让画布和面板显示出来

理解了这个闭环，就理解了整个程序的骨架。

主窗口的区域划分（QMainWindow 天生就是为这种布局设计的）：

    ┌────────────────────────────────────────────┐
    │ 菜单栏（QMenuBar）                          │
    │ 顶部工具栏（QToolBar）                      │
    ├──┬──────────────────────────┬──────────────┤
    │左│   中央区域（画布+控制条） │ 右侧停靠面板  │
    │模│                          │（QDockWidget）│
    │式│                          │              │
    │条│                          │              │
    ├──┴──────────────────────────┴──────────────┤
    │ 状态栏（QStatusBar）                        │
    └────────────────────────────────────────────┘

工程习惯：__init__ 里不写具体逻辑，而是调用一组 _create_xxx() 方法，
每个方法负责组装一个区域。这样每个方法都很短，容易阅读和修改。
"""

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QDockWidget,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from . import config, shapes as shapes_io
from .icons import make_icon
from .models.annotation_status import (
    AnnotationStatus,
    resolve_annotation_status,
)
from .models.annotation import Annotation, copy_annotations
from .shapes import AnnotationLoadError
from .services.history import AnnotationHistory
from .services.project_service import ProjectConfig, load_project, save_project
from .services.validation_service import validate_dataset
from .services.export_service import (
    export_yolo_detection, import_yolo_detection, export_coco, import_coco,
)

from .widgets.canvas_bar import CanvasBar
from .widgets.canvas_view import IMAGE_SUFFIXES, CanvasView
from .widgets.label_dialog import LabelDialog
from .widgets.mode_strip import ModeStrip
from .widgets.panels.class_panel import ClassPanel
from .widgets.panels.file_panel import FilePanel
from .widgets.panels.object_panel import ObjectPanel
from .widgets.panels.property_panel import PropertyPanel


class MainWindow(QMainWindow):
    """VisionLabel 主窗口。"""

    def __init__(self):
        super().__init__()

        self.setWindowTitle(f"{config.APP_NAME} — 未打开项目")
        self.resize(config.WINDOW_WIDTH, config.WINDOW_HEIGHT)

        # ---- 数据状态（整个程序的“单一数据源”）----
        self._folder: Path | None = None        # 当前打开的图片文件夹  # “self.folder”是变量名 “：”是类型注解标记 “Path|None”是类型 “=None”是初值
        self._image_files: list[Path] = []      # 图片文件的完整路径列表
        self._current_index = -1                # 当前图片的位置（-1 = 未加载）
        self._image_size = (0, 0)               # 当前图片的 (宽, 高)
        self._current_shapes: list[Annotation] = []  # 当前图片上的所有标注
        self._dirty = False                     # 有未保存的修改？

        # ---- 标签状态（标签不是内置的，全部来自用户）----
        # 两个来源：打开文件夹时从已有 .json 标注里读出；用户标注时现场创建
        self._labels: list[str] = []            # 所有已知标签（顺序=快捷键序号）
        self._label_colors: dict[str, str] = {}  # 标签 -> 颜色（按创建顺序取色盘）
        self._last_label: str | None = None     # 上一个标注用的标签（弹窗默认值）

        # ---- 撤销/重做状态（快照式，每张图片独立）----
        # 思路：每次修改标注【之前】把整张图的标注列表深拷贝一份压入
        # 历史服务内部维护 undo/redo 两个栈；主窗口只调用统一接口。
        # 栈里存的是“数据快照”，不涉及界面，所以任何修改（新建/删除/
        # 拖动/改名……）都能用同一套机制撤销。
        self._history = AnnotationHistory(max_steps=100)
        # 项目配置把“任务”和“类别”持久化，检测/分割/分类互不混用。
        self._project = ProjectConfig()
        # 拖动/拉伸会产生一连串微小位移，但应该只算“一次”操作：
        # 画布在用户按下标注的瞬间发 shape_drag_started 信号，
        # 我们在此存一份快照；之后收到的第一个 shape_moved 才把它入栈。
        self._pending_snapshot: list[Annotation] | None = None

        # 分区域组装界面（每个方法的职责见各自的注释）
        self._create_actions()    # 1. 先创建所有“操作”（按钮/菜单共用它）
        self._create_menus()      # 2. 菜单栏
        self._create_toolbars()   # 3. 顶部工具栏 + 左侧模式条
        self._create_central()    # 4. 中央区域（画布 + 画布控制条）
        self._create_docks()      # 5. 右侧四个停靠面板
        self._create_statusbar()  # 6. 底部状态栏
        self._connect_signals()   # 7. 把所有组件的信号连接起来（“总控”的关键）

        # 初始为“选择/编辑”模式
        self.canvas.set_mode("select")
        # 撤销/重做按钮一开始应该是灰的（还没有任何可撤销的操作）
        self._update_undo_actions()

    # ------------------------------------------------------------------
    # 1. 操作（QAction）
    # ------------------------------------------------------------------
    def _create_actions(self) -> None:
        """
        创建所有 QAction。

        QAction 是 Qt 里“一个操作”的抽象：同一个 QAction 可以同时
        挂在菜单项和工具栏按钮上，文字、图标、快捷键、可用状态自动同步。
        所以先在这里统一创建，后面菜单和工具栏直接使用。
        """
        # 图标统一来自 resources/icons/（Lucide 图标库），
        # make_icon("xxx") 对应 resources/icons/xxx.svg，见 icons.py

        # ---- 文件类 ----
        self.action_open_dir = QAction(make_icon("folder-open"), "打开文件夹…", self)
        self.action_open_dir.setShortcut(QKeySequence.StandardKey.Open)  # Ctrl+O

        self.action_save = QAction(make_icon("save"), "保存", self)
        self.action_save.setToolTip("保存当前标注；空图片不会因此新建空 JSON")

        # Ctrl+S 与普通“保存”按钮故意分开：
        # - Ctrl+S：用户主动确认当前状态；即使没有标注，也允许生成空 JSON
        # - 普通保存按钮：空图片不生成新的 JSON
        self.shortcut_save = QShortcut(QKeySequence.StandardKey.Save, self)

        self.action_save_empty = QAction(make_icon("json_save"), "保存空标签", self)
        self.action_save_empty.setToolTip("将当前无标注图像保存为“已检查（无目标）”")

        self.action_export_yolo = QAction("导出 YOLO 检测标注…", self)
        self.action_export_yolo.setShortcut("Ctrl+E")
        self.action_import_yolo = QAction("导入 YOLO 检测标注…", self)
        self.action_export_coco = QAction("导出 COCO 标注…", self)
        self.action_import_coco = QAction("导入 COCO 标注…", self)

        self.action_quit = QAction("退出", self)
        self.action_quit.setShortcut("Ctrl+Q")
        self.action_quit.triggered.connect(self.close)

        # ---- 翻页类（放在“视图”菜单里，快捷键 A / D）----
        self.action_prev = QAction(make_icon("chevron-left"), "上一张", self)
        self.action_prev.setShortcut("A")
        self.action_next = QAction(make_icon("chevron-right"), "下一张", self)
        self.action_next.setShortcut("D")

        # ---- 缩放类 ----
        self.action_zoom_in = QAction(make_icon("zoom-in"), "放大", self)
        self.action_zoom_in.setShortcut(QKeySequence.StandardKey.ZoomIn)    # Ctrl+=
        self.action_zoom_out = QAction(make_icon("zoom-out"), "缩小", self)
        self.action_zoom_out.setShortcut(QKeySequence.StandardKey.ZoomOut)  # Ctrl+-
        self.action_fit = QAction(make_icon("maximize"), "适应窗口", self)
        self.action_fit.setShortcut("F")
        self.action_actual = QAction("原始大小", self)
        self.action_actual.setShortcut("Ctrl+0")

        # ---- 编辑类 ----
        self.action_undo = QAction(make_icon("undo"), "撤销", self)
        self.action_undo.setShortcut(QKeySequence.StandardKey.Undo)      # Ctrl+Z

        self.action_redo = QAction(make_icon("redo"), "重做", self)
        self.action_redo.setShortcut(QKeySequence.StandardKey.Redo)      # Ctrl+Y

        self.action_duplicate = QAction(make_icon("copy"), "复制标注", self)
        self.action_duplicate.setShortcut("Ctrl+D")

        self.action_delete = QAction(make_icon("trash"), "删除", self)
        self.action_delete.setShortcut(QKeySequence.StandardKey.Delete)  # Del

        # ---- 视图类 ----
        self.action_toggle_shapes = QAction(make_icon("eye"), "显隐标注", self)
        self.action_toggle_shapes.setShortcut("Ctrl+H")
        self.action_toggle_shapes.setCheckable(True)   # 这是个“开关”类操作
        self.action_toggle_shapes.setChecked(True)

        # ---- 工具类 ----
        self.action_verify = QAction(make_icon("check"), "校验", self)
        self.action_ai = QAction(make_icon("sparkle", "#5b4bb3"), "AI 预标注", self)

        # ---- 帮助类 ----
        self.action_about = QAction("关于 VisionLabel", self)

        # ---- 类别切换的快捷键：数字键 1~9 ----
        # 标签是用户动态创建的，数量不固定，所以 1~9 九个快捷键先全注册，
        # 按下时再检查对应序号的标签是否存在（不存在就忽略）
        for i in range(9):
            action = QAction(f"切换到类别 {i + 1}", self)
            action.setShortcut(str(i + 1))
            # lambda 里的 i=i 是个经典细节：把循环变量“固定”进当前这次
            # 迭代的 lambda 里，否则所有 lambda 共享同一个 i 的最终值
            action.triggered.connect(
                lambda checked=False, i=i: self._select_class_by_index(i)
            )
            self.addAction(action)  # addAction 让快捷键在主窗口范围内生效

    # ------------------------------------------------------------------
    # 2. 菜单栏
    # ------------------------------------------------------------------
    def _create_menus(self) -> None:
        """创建菜单栏。menuBar() 是 QMainWindow 自带的菜单栏。"""
        bar = self.menuBar()

        # 菜单名里的 (&X) 表示 Alt+X 可以快速打开这个菜单
        menu_file = bar.addMenu("文件(&F)")
        menu_file.addAction(self.action_open_dir)
        menu_file.addAction(self.action_save)
        menu_file.addSeparator()  # 分隔线，把菜单项分组
        menu_import = menu_file.addMenu("导入")
        menu_import.addAction(self.action_import_yolo)
        menu_import.addAction(self.action_import_coco)
        menu_export = menu_file.addMenu("导出")
        menu_export.addAction(self.action_export_yolo)
        menu_export.addAction(self.action_export_coco)
        menu_file.addSeparator()
        menu_file.addAction(self.action_quit)

        menu_edit = bar.addMenu("编辑(&E)")
        menu_edit.addAction(self.action_undo)
        menu_edit.addAction(self.action_redo)
        menu_edit.addSeparator()
        menu_edit.addAction(self.action_duplicate)
        menu_edit.addAction(self.action_delete)

        # “视图”菜单在 _create_docks() 里还会补充各面板的开关项
        self.menu_view = bar.addMenu("视图(&V)")
        self.menu_view.addAction(self.action_prev)
        self.menu_view.addAction(self.action_next)
        self.menu_view.addSeparator()
        self.menu_view.addAction(self.action_zoom_in)
        self.menu_view.addAction(self.action_zoom_out)
        self.menu_view.addAction(self.action_fit)
        self.menu_view.addAction(self.action_actual)
        self.menu_view.addSeparator()
        self.menu_view.addAction(self.action_toggle_shapes)

        # “标注”菜单的模式切换项由模式条创建，在 _create_toolbars() 里补充
        self.menu_annotate = bar.addMenu("标注(&A)")

        menu_tools = bar.addMenu("工具(&T)")
        menu_tools.addAction(self.action_ai)
        menu_tools.addAction(self.action_verify)

        menu_help = bar.addMenu("帮助(&H)")
        menu_help.addAction(self.action_about)

    # ------------------------------------------------------------------
    # 3. 工具栏（顶部 + 左侧模式条）
    # ------------------------------------------------------------------
    def _create_toolbars(self) -> None:
        """创建顶部工具栏和左侧模式条。"""
        # ---- 顶部工具栏：只放高频标注工具 ----
        toolbar = QToolBar("主工具栏", self)
        toolbar.setObjectName("main_toolbar")  # setObjectName 用于保存/恢复窗口布局
        toolbar.setMovable(False)
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.addToolBar(toolbar)

        # 注意：这里添加的都是 _create_actions() 里创建好的 QAction
        toolbar.addAction(self.action_open_dir)
        toolbar.addAction(self.action_save)
        toolbar.addAction(self.action_save_empty)
        toolbar.addSeparator()
        toolbar.addAction(self.action_undo)
        toolbar.addAction(self.action_redo)
        toolbar.addSeparator()
        toolbar.addAction(self.action_duplicate)
        toolbar.addAction(self.action_delete)
        toolbar.addSeparator()
        toolbar.addAction(self.action_toggle_shapes)
        toolbar.addAction(self.action_verify)
        toolbar.addSeparator()
        toolbar.addAction(self.action_ai)

        # ---- 左侧模式条（独立的组件类，见 widgets/mode_strip.py）----
        self.mode_strip = ModeStrip(self)
        self.mode_strip.setObjectName("mode_strip")
        # 指定它停靠在主窗口的左侧区域
        self.addToolBar(Qt.ToolBarArea.LeftToolBarArea, self.mode_strip)

        # 把模式条管理的“模式切换操作”补充进“标注”菜单，
        # 同一个 QAction 出现在两处，状态自动同步
        self.menu_annotate.addActions(self.mode_strip.actions())

    # ------------------------------------------------------------------
    # 4. 中央区域
    # ------------------------------------------------------------------
    def _create_central(self) -> None:
        """
        中央区域 = 画布（上）+ 画布控制条（下），竖向排列。

        QMainWindow 的中央区域只能放“一个”控件，
        所以用一个普通 QWidget 当容器，里面用 QVBoxLayout 竖向排列两者。
        """
        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)  # 容器不留边距，画布铺满
        layout.setSpacing(0)                   # 画布和控制条之间无缝衔接

        self.canvas = CanvasView(container)
        self.canvas_bar = CanvasBar(container)

        layout.addWidget(self.canvas, stretch=1)  # stretch=1：画布占满剩余空间
        layout.addWidget(self.canvas_bar)         # 控制条高度固定

        self.setCentralWidget(container)

    # ------------------------------------------------------------------
    # 5. 右侧停靠面板
    # ------------------------------------------------------------------
    def _create_docks(self) -> None:
        """
        创建右侧的四个停靠面板（QDockWidget）。

        QDockWidget 是 Qt 的“停靠窗口”：可以拖动换位、拖出变成
        浮动窗口、点 × 关闭。用户关闭后可在“视图”菜单里重新打开。
        """
        # 面板控件保存为成员变量，后面 _connect_signals() 要用到
        self.class_panel = ClassPanel()
        self.object_panel = ObjectPanel()
        self.property_panel = PropertyPanel()
        self.file_panel = FilePanel()

        # (面板标题, 面板控件)。集中定义，下面循环创建，避免重复代码。
        panels = [
            ("类别",     self.class_panel),
            ("标注对象", self.object_panel),
            ("属性",     self.property_panel),
            ("文件列表", self.file_panel),
        ]

        previous_dock = None
        for title, widget in panels:
            dock = QDockWidget(title, self)
            dock.setObjectName(f"dock_{title}")  # 布局保存需要唯一的 objectName
            dock.setWidget(widget)
            # 全部放在右侧停靠区
            self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)

            # 关键一步：默认情况下多个 dock 会堆叠成“标签页”，
            # 用 splitDockWidget 让它们在右侧区域里上下排列
            if previous_dock is not None:
                self.splitDockWidget(previous_dock, dock, Qt.Orientation.Vertical)
            previous_dock = dock

            # 把每个面板的“显示/隐藏开关”加进“视图”菜单
            # toggleViewAction() 是 QDockWidget 自动提供的开关操作
            self.menu_view.addAction(dock.toggleViewAction())

    # ------------------------------------------------------------------
    # 6. 状态栏
    # ------------------------------------------------------------------
    def _create_statusbar(self) -> None:
        """
        创建底部状态栏。

        状态栏分两种信息：
        - 临时消息：showMessage() 显示，几秒后自动消失（如“已保存”）
        - 常驻控件：addPermanentWidget() 添加，一直显示（如坐标、进度）
        """
        status = self.statusBar()

        # 左侧常驻：光标坐标和图片尺寸
        self.label_coord = QLabel("x: -, y: -")
        self.label_size = QLabel("- × -")
        status.addWidget(self.label_coord)
        status.addWidget(self.label_size)

        # 右侧常驻：标注进度（文字 + 进度条）
        self.label_progress = QLabel("0 / 0")
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedWidth(140)
        self.progress_bar.setTextVisible(False)  # 进度条上不重复显示文字
        status.addPermanentWidget(self.label_progress)
        status.addPermanentWidget(self.progress_bar)

        # 一条临时消息：程序启动后显示 5 秒
        status.showMessage("就绪 — 点击「打开文件夹」开始标注", 5000)

    # ------------------------------------------------------------------
    # 7. 信号连接（总控）
    # ------------------------------------------------------------------
    def _connect_signals(self) -> None:
        """
        把各组件的信号连接到对应的处理函数（槽函数）。

        读法示例：self.canvas_bar.prev_clicked.connect(self._prev_image)
        意思是“当控制条的‘上一张’被点击时，执行主窗口的 _prev_image()”。
        """
        # ---- 菜单/工具栏上的操作 ----
        self.action_open_dir.triggered.connect(self._open_directory)
        # 普通保存：有标注就保存；空图片不主动生成空 JSON
        self.action_save.triggered.connect(
            lambda _checked=False: self._save_current(save_empty=False)
        )

        # Ctrl+S：明确的主动保存。空图片也保存 shapes=[] 的 JSON。
        self.shortcut_save.activated.connect(
            lambda: self._save_current(save_empty=True)
        )

        # 专用“保存空标签”按钮：只允许无标注图片使用。
        self.action_save_empty.triggered.connect(
            lambda _checked=False: self._save_empty_annotation()
        )
        self.action_prev.triggered.connect(self._prev_image)
        self.action_next.triggered.connect(self._next_image)
        self.action_delete.triggered.connect(self._delete_selected)
        self.action_undo.triggered.connect(self._undo)
        self.action_redo.triggered.connect(self._redo)
        self.action_duplicate.triggered.connect(self._duplicate_selected)
        self.action_zoom_in.triggered.connect(self.canvas.zoom_in)
        self.action_zoom_out.triggered.connect(self.canvas.zoom_out)
        self.action_fit.triggered.connect(self.canvas.fit)
        self.action_actual.triggered.connect(self.canvas.actual_size)
        # “显隐标注”是开关型操作：toggled 信号自带 True/False 参数
        self.action_toggle_shapes.toggled.connect(self.canvas.set_shapes_visible)
        self.action_verify.triggered.connect(self._validate_project)
        self.action_export_yolo.triggered.connect(self._export_yolo)
        self.action_import_yolo.triggered.connect(self._import_yolo)
        self.action_export_coco.triggered.connect(self._export_coco)
        self.action_import_coco.triggered.connect(self._import_coco)

        # ---- 画布控制条 ----
        self.canvas_bar.prev_clicked.connect(self._prev_image)
        self.canvas_bar.next_clicked.connect(self._next_image)
        self.canvas_bar.page_jumped.connect(self._on_page_jumped)
        self.canvas_bar.zoom_in_clicked.connect(self.canvas.zoom_in)
        self.canvas_bar.zoom_out_clicked.connect(self.canvas.zoom_out)
        self.canvas_bar.fit_clicked.connect(self.canvas.fit)
        self.canvas_bar.actual_size_clicked.connect(self.canvas.actual_size)

        # ---- 画布 ----
        self.canvas.image_loaded.connect(self._on_image_loaded)
        self.canvas.zoom_changed.connect(self.canvas_bar.set_zoom)
        self.canvas.rect_drawn.connect(self._on_rect_drawn)
        self.canvas.polygon_drawn.connect(self._on_polygon_drawn)
        self.canvas.shape_selected.connect(self._on_canvas_shape_selected)
        self.canvas.shape_drag_started.connect(self._on_shape_drag_started)
        self.canvas.shape_moved.connect(self._on_shape_moved)
        # lambda：把信号的两个参数 x, y 拼成一行文字显示到状态栏
        self.canvas.mouse_moved.connect(
            lambda x, y: self.label_coord.setText(f"x: {x}, y: {y}")
        )

        # ---- 右侧面板 ----
        self.file_panel.file_selected.connect(self._goto_image)
        self.class_panel.class_selected.connect(self._on_class_selected)
        self.object_panel.object_selected.connect(self._on_object_row_selected)
        self.object_panel.edit_requested.connect(self._on_edit_label_requested)

        # ---- 模式条：切换标注模式 ----
        self.mode_strip.mode_changed.connect(self._on_mode_changed)

    # ==================================================================
    # 业务逻辑：打开文件夹与翻页
    # ==================================================================
    def _confirm_save_before_leave(self) -> bool:
        """
        离开当前内容前，处理尚未保存的修改。

        返回值：
            True：允许继续打开新文件夹或关闭程序。
            False：取消当前操作，继续留在原项目。
        """
        if (self._folder is None
            or self._current_index < 0
            or not self._dirty):
            return True
        # 只有确实存在未保存的修改时，才创建并显示对话框。
        box = QMessageBox(self)
        box.setWindowTitle("未保存的修改")
        box.setText("当前图片有未保存的标注修改，\n是否在退出前保存？")
        box.setIcon(QMessageBox.Icon.Question)
        btn_save = box.addButton("是", QMessageBox.ButtonRole.AcceptRole)
        btn_discard = box.addButton("否", QMessageBox.ButtonRole.DestructiveRole)
        btn_cancel = box.addButton("关闭", QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(btn_save)
        box.exec()
        if not self._dirty: # 没有未保存的修改，直接允许继续
            return True
        elif box.clickedButton() is btn_save:# 选择“是“，把保存结果直接返回
            return self._save_current()
        elif box.clickedButton() is btn_discard:
            return True
        return False

    def _reset_project_state(self) -> None:
        """
        清空旧项目留下的运行状态。

        只清理内存和界面，不删除磁盘上的图片或 JSON 文件。
        """
        # 清空当前项目和图片状态
        self._folder = None
        self._image_files = []
        self._current_index = -1
        self._image_size = (0, 0)
        self._current_shapes = []
        self._dirty = False

        # 清空旧项目的类别状态
        self._labels = []
        self._label_colors = {}
        self._last_label = None

        # 清空撤销和重做记录
        self._history.clear()
        self._pending_snapshot = None
        self._project = ProjectConfig()
        self._update_undo_actions()

        # 清空画布和右侧面板
        self.canvas.clear_shapes()
        self.class_panel.set_classes([])
        self.object_panel.set_objects([], self._label_color)
        self.property_panel.clear()

        # 新项目默认显示标注
        self.action_toggle_shapes.setChecked(True)

    def _open_directory(self) -> None:
        """
        弹出文件夹选择框，并把用户选择的目录交给统一的项目加载流程。

        这个方法本身只负责“获取路径”，不负责扫描图片、加载项目配置或刷新 UI。
        这些真正的业务步骤集中在后续的目录加载函数中。这样做的好处是：
        - 菜单“打开文件夹”可以复用同一套加载逻辑；
        - 以后做“最近项目”“拖拽打开文件夹”时，也能直接复用；
        - QFileDialog 这种纯 UI 行为不会和项目业务逻辑混在一起。
        """
        folder = QFileDialog.getExistingDirectory(self, "选择图片文件夹")
        if not folder:
            return
        self.open_folder(Path(folder))

    def _ask_recover_corrupt_annotation(
            self,
            image_path: Path,
            error: AnnotationLoadError,
    ) -> bool:
        """
        询问用户是否备份损坏JSON，
        并将该图片作为空标注重新开始。
        """
        box = QMessageBox(self)
        box.setWindowTitle("标注文件损坏")
        box.setIcon(QMessageBox.Icon.Warning)
        box.setText(
            f"{image_path.name} 的标注文件无法读取。"
        )
        box.setInformativeText(
            f"{error}\n\n"
            "可以取消操作并保留原文件，或者先备份损坏文件，"
            "再把这张图片作为空标注重新打开。"
        )

        btn_recover = box.addButton(
            "备份并重新标注",
            QMessageBox.ButtonRole.AcceptRole,
        )
        btn_cancel = box.addButton(
            "取消",
            QMessageBox.ButtonRole.RejectRole,
        )

        # 默认选择“取消”，避免用户误按回车覆盖原工作流程
        box.setDefaultButton(btn_cancel)
        box.setEscapeButton(btn_cancel)
        box.exec()

        return box.clickedButton() is btn_recover

    def _backup_corrupt_annotation(
            self,
            image_path: Path,
    ) -> Path | None:
        """
        把损坏JSON重命名为唯一备份。

        返回值：
            Path：备份成功后的文件路径；
            None：备份失败。
        """
        source_path = shapes_io.json_path_for(image_path)

        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

        backup_path = source_path.with_name(
            f"{source_path.name}.corrupt_{timestamp}.bak"
        )

        # 同一秒内出现同名备份时，增加数字序号
        number = 1

        while backup_path.exists():
            backup_path = source_path.with_name(
                f"{source_path.name}.corrupt_"
                f"{timestamp}_{number}.bak"
            )
            number += 1

        try:
            # replace()在这里相当于重命名
            source_path.replace(backup_path)

        except OSError as error:
            QMessageBox.critical(
                self,
                "备份失败",
                f"无法备份损坏的标注文件：\n"
                f"{source_path}\n\n"
                f"原因：{error}\n\n"
                "为避免数据丢失，已取消重新标注。",
            )
            return None

        return backup_path

    def open_folder(self, folder: Path) -> bool:
        """
        打开一个图片文件夹。

        执行顺序：
            1. 扫描并检查新文件夹；
            2. 处理当前项目未保存的修改；
            3. 清空旧项目状态；
            4. 加载新项目。
        """
        try:
            folder = Path(folder) # 保证 folder 是 Path 对象
            # 先扫描新文件夹
            files = sorted(
                path
                for path in folder.iterdir()
                if path.is_file()
                and path.suffix.lower() in IMAGE_SUFFIXES
            )
        except (OSError, TypeError) as error:
            QMessageBox.warning(
                self,
                "无法打开文件夹",
                f"文件夹无法读取：\n{folder}\\n原因：{error}",
            )
            return False
        # 新文件夹没有图片时，不影响当前正在使用的项目
        if not files:
            QMessageBox.information(
                self,
                "没有找到图片",
                "所选文件夹里没有支持的图片文件\n"
                "（jpg / png / bmp / webp / tif）。",
            )
            return False
        # 提前读取第一张图片，但暂时不改变画布和当前项目
        # 有图片后缀不代表文件内容一定有效
        first_pixmap = QPixmap(str(files[0]))

        if first_pixmap.isNull():
            QMessageBox.warning(
                self,
                "无法打开图片",
                f"文件夹中的第一张图片无法读取：\n{files[0]}\n\n"
                "原项目将保持不变。",
            )
            return False

        first_annotation_error = None

        try:
            first_shapes = shapes_io.load_shapes(files[0])
        except AnnotationLoadError as error:
            first_shapes = []
            first_annotation_error = error

            if not self._ask_recover_corrupt_annotation(
                files[0],
                error,
            ):
                return False

        # 新文件夹有效后，再询问是否保存当前项目
        if not self._confirm_save_before_leave():
            self.statusBar().showMessage(
                "已取消打开新文件夹",
                3000,
            )
            return False

        if first_annotation_error is not None:
            backup_path = self._backup_corrupt_annotation(
                files[0],
            )
            if backup_path is None:
                return False

        # 用户允许离开当前项目，清空旧状态
        self._reset_project_state()

        # 设置新项目的数据
        self._folder = folder
        self._image_files = files
        try:
            self._project = load_project(folder)
        except (OSError, ValueError, TypeError) as error:
            QMessageBox.warning(self, "项目配置读取失败", f"将使用默认项目配置。\n\n{error}")
            self._project = ProjectConfig()

        # 先恢复当前任务已保存的类别
        self._load_active_task_labels()

        # 收集图片名称、标注状态和已有类别
        names = []
        statuses = []

        for path in files:
            names.append(path.name)

            try:
                existing_shapes = shapes_io.load_shapes(path)
            except AnnotationLoadError as error:
                statuses.append(AnnotationStatus.ERROR)
                continue

            statuses.append(
                resolve_annotation_status(
                    annotation_count=len(existing_shapes),
                    annotation_file_exists=shapes_io.json_path_for(path).exists(),
                )
            )

            for shape in existing_shapes:
                self._register_label(shape.label, self._task_for_shape_type(shape.shape_type))

        # 更新文件列表
        self.file_panel.set_files(names, statuses)

        # 更新窗口标题
        self.setWindowTitle(
            f"{config.APP_NAME} — {self._folder.name}"
        )

        # 加载第一张图片
        return self._goto_image(
            0,
            prepared_pixmap=first_pixmap,
            prepared_shapes=first_shapes,
        )

    def _goto_image(self,
                    index: int,
                    prepared_pixmap: QPixmap | None = None,
                    prepared_shapes: list[Annotation] | None = None,
                    ) -> bool:
        """跳转到第 index 张图片（index 从 0 开始）。"""
        if not (0 <= index < len(self._image_files)):
            return False  # 越界（没有图片或到头了），直接忽略
        if index == self._current_index:
            return True  # 已经是当前这张，不用重复加载

        # 切换前：如果当前图片有未保存的修改，先自动保存，
        # 避免用户辛苦画的框因为翻页丢失（labelImg 的默认行为也是这样）
        if self._dirty and not self._save_current():
            self.statusBar().showMessage(
                "保存失败，已取消切换图片",
                5000,
            )
            return False

        path = self._image_files[index]

        # 先在内存中验证目标图片，不改变当前画布
        next_pixmap = (
            prepared_pixmap
            if prepared_pixmap is not None
            else QPixmap(str(path))
        )

        if next_pixmap.isNull():
            QMessageBox.warning(
                self,
                "无法打开",
                f"图片无法读取：\n{path}",
            )

            self.file_panel.set_current(
                self._current_index
            )
            return False

        # 先检查标注文件，确认JSON安全后才改变画布
        if prepared_shapes is None:
            try:
                next_shapes = shapes_io.load_shapes(path)
            except AnnotationLoadError as error:
                # 先询问用户是否希望备份并重新标注
                if not self._ask_recover_corrupt_annotation(
                        path,
                        error,
                ):
                    self.file_panel.set_current(
                        self._current_index
                    )
                    return False

                # 用户明确同意后才执行备份
                backup_path = self._backup_corrupt_annotation(
                    path
                )

                if backup_path is None:
                    self.file_panel.set_current(
                        self._current_index
                    )
                    return False

                # 损坏JSON已经备份，从空标注开始
                next_shapes = []

                # 文件列表从“标注损坏”恢复成“未标注”
                self.file_panel.set_status(
                    index,
                    AnnotationStatus.TODO,
                )

                self.statusBar().showMessage(
                    f"损坏标注已备份为："
                    f"{backup_path.name}",
                    5000,
                )

        else:
            next_shapes = prepared_shapes

        if not self.canvas.load_image(path, next_pixmap):
            QMessageBox.warning(
                self,
                "无法打开",
                f"图片无法读取：\n{path}",
            )
            self.file_panel.set_current(self._current_index)
            return False
        self._current_index = index

        # 每张图的撤销历史互相独立：切换图片时清空上一张的撤销栈，
        # 避免“在新图片上按 Ctrl+Z 却恢复到上一张图的状态”这种错乱
        self._history.clear()
        self._pending_snapshot = None
        self._update_undo_actions()

        # ---- 加载这张图的标注并显示 ----
        self._current_shapes = next_shapes
        for shape in self._current_shapes:
            self._register_label(shape.label, self._task_for_shape_type(shape.shape_type))  # 兼容手工标注文件
            self.canvas.add_shape_item(shape, self._label_color(shape.label))
        self.object_panel.set_objects(self._current_shapes, self._label_color)
        self.property_panel.clear()
        self._mark_dirty(False)

        # ---- 同步更新各处的显示 ----
        total = len(self._image_files)
        self.file_panel.set_current(index)                     # 文件列表高亮
        self.canvas_bar.set_page(index + 1, total)             # 页码（显示从 1 开始）
        self.label_progress.setText(f"{index + 1} / {total}")  # 状态栏进度
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(index + 1)
        self.statusBar().showMessage(f"已加载：{path.name}", 3000)
        return True

    def _prev_image(self) -> None:
        """上一张。"""
        self._goto_image(self._current_index - 1)

    def _next_image(self) -> None:
        """下一张。"""
        self._goto_image(self._current_index + 1)

    def _on_page_jumped(self, page: int) -> None:
        """用户在页码框输入页码并回车（页码从 1 开始，内部从 0 开始）。"""
        self._goto_image(page - 1)

    def _on_image_loaded(self, width: int, height: int) -> None:
        """图片加载完成后，记住尺寸并更新状态栏显示。"""
        self._image_size = (width, height)
        self.label_size.setText(f"{width} × {height}")

    # ==================================================================
    # 业务逻辑：标注
    # ==================================================================
    def _on_rect_drawn(self, x: float, y: float, w: float, h: float) -> None:
        """用户画好了一个矩形（画布已完成图片坐标换算）。"""
        # 矩形的 points 约定：左上角 + 右下角两个点
        self._create_shape("rect", [(x, y), (x + w, y + h)])

    def _on_polygon_drawn(self, points: list) -> None:
        """用户闭合了一个多边形（points 是图片坐标的顶点列表）。"""
        self._create_shape("polygon", points)

    def _create_shape(self, shape_type: str, points: list) -> None:
        """
        所有标注类型共用的“新建标注”流程：

        1. 弹窗让用户选/填标签（labelme 同款交互）：
           - 默认填入上一个标注用的标签，一路回车即可连续标同类目标；
           - 输入列表里没有的名字 = 创建新标签；
           - 按 Esc / 取消 = 放弃刚才画的标注。
        2. 用户确定后才真正创建 Annotation 数据、画到画布、刷新面板。

        新增标注类型时，信号处理函数只需像上面两个一样，
        拼好 points 再调用这个方法 —— 弹窗、注册、保存逻辑全复用。
        """
        label = LabelDialog.get_label(self, self._labels, self._last_label)
        if label is None:
            # 用户取消了：这个标注不算数（画布上只有过预览，已被工具清理）
            self.statusBar().showMessage("已放弃这个标注", 2000)
            return

        # 新标签会被自动注册（已有标签则什么也不做）
        self._register_label(label, self._task_for_shape_type(shape_type))
        self._last_label = label  # 记住它，作为下一个弹窗的默认值

        self._push_undo()  # 修改前先存快照（撤销用）
        shape = Annotation(label=label, shape_type=shape_type, points=points)
        self._current_shapes.append(shape)
        self.canvas.add_shape_item(shape, self._label_color(label))
        self.object_panel.set_objects(self._current_shapes, self._label_color)
        self._mark_dirty(True)
        self.statusBar().showMessage(
            f"已添加 {label}（本图共 {len(self._current_shapes)} 个标注）", 3000
        )

    def _delete_selected(self) -> None:
        """删除画布上当前选中的标注（Del 键 / 工具栏删除按钮）。"""
        # 先确认有东西可删，再存快照 —— 空操作不该进撤销栈
        if not self.canvas.selected_shapes():
            return
        self._push_undo()  # 修改前先存快照（撤销用）
        removed = self.canvas.delete_selected_shapes()
        for shape in removed:
            self._current_shapes.remove(shape)  # 同步删除数据模型里的记录
        self.object_panel.set_objects(self._current_shapes, self._label_color)
        self.property_panel.clear()
        self._mark_dirty(True)
        self.statusBar().showMessage(f"已删除 {len(removed)} 个标注", 3000)

    def _duplicate_selected(self) -> None:
        """
        复制当前选中的标注（Ctrl+D）。

        复制体整体向右下偏移 12 像素，这样它和原框错开，
        用户一眼能看到“复制成功了”（labelImg 也是这么做的）。
        """
        selected = self.canvas.selected_shapes()
        if not selected:
            return
        self._push_undo()  # 修改前先存快照（撤销用）
        last_item = None
        for src in selected:
            copy = src.translated_copy(12, 12)
            self._current_shapes.append(copy)
            last_item = self.canvas.add_shape_item(
                copy, self._label_color(copy.label))
        self.object_panel.set_objects(self._current_shapes, self._label_color)
        self._mark_dirty(True)
        # 选中最后一个复制体，方便用户接着拖动它
        if last_item is not None:
            last_item.setSelected(True)
        self.statusBar().showMessage(f"已复制 {len(selected)} 个标注", 3000)

    def _on_edit_label_requested(self, row: int) -> None:
        """
        用户在对象面板双击某一行：弹出标签对话框修改这个标注的标签。

        对话框里预填当前标签，用户可以直接改名、换成已有标签、
        或输入新名字创建新标签。
        """
        if not (0 <= row < len(self._current_shapes)):
            return
        shape = self._current_shapes[row]
        new_label = LabelDialog.get_label(self, self._labels, shape.label)
        if new_label is None or new_label == shape.label:
            return  # 取消或没改动：什么都不做
        self._push_undo()  # 修改前先存快照（撤销用）
        self._register_label(new_label, self._task_for_shape_type(shape.shape_type))
        shape.label = new_label
        # 画布上的图元也要同步换文字和颜色
        item = self.canvas.find_item(shape)
        if item is not None:
            item.update_label(new_label, self._label_color(new_label))
        self.object_panel.set_objects(self._current_shapes, self._label_color)
        self.property_panel.show_shape(shape)
        self._mark_dirty(True)
        self.statusBar().showMessage(f"标签已改为：{new_label}", 3000)

    def _on_canvas_shape_selected(self, shape) -> None:
        """
        画布上的选中变化（用户点选/框选/取消选中一个标注）：
        同步右侧的对象列表高亮和属性面板。
        """
        if shape is None:
            self.object_panel.clear_selection()
            self.property_panel.clear()
            return
        # 用“is”（对象身份）而不是“==”（值相等）查找：
        # 两个一模一样的框是两条不同的标注，值相等会找错
        row = next((i for i, s in enumerate(self._current_shapes)
                    if s is shape), -1)
        if row >= 0:
            self.object_panel.set_current(row)
            self.property_panel.show_shape(shape)

    def _on_object_row_selected(self, row: int) -> None:
        """用户在对象列表点击某一行：画布上选中对应的标注。"""
        if 0 <= row < len(self._current_shapes):
            self.canvas.select_shape(self._current_shapes[row])

    def _on_class_selected(self, index: int) -> None:
        """
        用户在类别面板点击了某个标签（或按了数字键）：
        把它设为“当前标签”，也就是下一个标注弹窗里的默认值。
        """
        if 0 <= index < len(self._labels):
            self._last_label = self._labels[index]
            self.statusBar().showMessage(
                f"当前标签：{self._last_label}（画框时默认使用它）", 3000
            )

    def _select_class_by_index(self, index: int) -> None:
        """数字键 1~9 的处理：标签存在才切换（标签是动态创建的，可能没有那么多）。"""
        if 0 <= index < len(self._labels):
            self.class_panel.set_current(index)

    # ------------------------------------------------------------------
    # 标签管理（标签不是内置的，全部来自用户/已有标注文件）
    # ------------------------------------------------------------------
    def _task_for_shape_type(self, shape_type: str) -> str:
        """把几何标注类型映射到项目任务；以后新增类型只在这里扩展。"""
        return {"rect": "detection", "polygon": "segmentation"}.get(shape_type, self._project.active_task)

    def _load_active_task_labels(self) -> None:
        """把当前任务的持久化类别装入界面。"""
        self._labels = list(self._project.classes_for())
        self._label_colors = {name: config.palette_color(i) for i, name in enumerate(self._labels)}
        self._last_label = self._labels[0] if self._labels else None
        if hasattr(self, "class_panel"):
            self._rebuild_class_panel()

    def _set_active_task(self, task: str) -> None:
        """
        切换当前项目任务，并同步该任务自己的类别列表。

        目前模式与任务的关系是：
            rect    -> detection
            polygon -> segmentation

        切换任务只影响“当前类别上下文”，不会删除其他任务已经保存的类别。
        若已经打开项目，还会立即把 active_task 写入项目配置文件。
        """
        if task not in ("detection", "segmentation", "classification"):
            return
        self._project.active_task = task
        self._load_active_task_labels()
        if self._folder is not None:
            try:
                save_project(self._folder, self._project)
            except OSError:
                pass

    def _register_label(self, label: str, task: str | None = None) -> None:
        """
        把一个类别登记到项目配置，并在必要时刷新当前类别面板。

        ``task or self._project.active_task`` 是常见 Python 写法：
        如果调用方没有明确给 task，就使用项目当前任务。

        注意：如果登记的是“非当前任务”的类别，只写项目配置，不把它混入
        当前界面的 self._labels，从而保证检测/分割/分类类别互不污染。
        """
        task = task or self._project.active_task
        self._project.add_class(label, task)
        if self._folder is not None:
            try:
                save_project(self._folder, self._project)
            except OSError:
                pass
        if task != self._project.active_task:
            return
        if label not in self._label_colors:
            self._labels.append(label)
            self._label_colors[label] = config.palette_color(len(self._labels) - 1)
            self._rebuild_class_panel()

    def _label_color(self, label: str) -> str:
        """
        返回某类别的显示颜色。

        如果类别来自手工 JSON、当前颜色表还没有它，则现场分配一个颜色。
        这个“惰性补齐”可以避免显示旧数据时因为缺颜色而失败。
        """
        if label not in self._label_colors:
            self._label_colors[label] = config.palette_color(len(self._label_colors))
        return self._label_colors.get(label, config.FALLBACK_COLOR)

    def _rebuild_class_panel(self) -> None:
        """
        用当前任务的 ``_labels`` 与 ``_label_colors`` 重建右侧类别列表。

        列表推导式把两个内部结构组合成 ClassPanel 需要的：
            [(类别名, 颜色), ...]
        """
        self.class_panel.set_classes([
            (name, self._label_colors[name])
            for name in self._labels
        ])

    def _on_mode_changed(self, mode_key: str) -> None:
        """
        左侧模式条发生变化时的总入口。

        一次模式切换包含两层同步：
        1. 告诉 CanvasView 当前鼠标应该由哪个 Tool 处理；
        2. 根据几何类型切换项目任务，从而显示对应任务自己的类别。
        """
        self.canvas.set_mode(mode_key)
        if mode_key == "rect":
            self._set_active_task("detection")
        elif mode_key == "polygon":
            self._set_active_task("segmentation")
        names = {m["key"]: m["name"] for m in config.MODES}
        self.statusBar().showMessage(f"当前模式：{names.get(mode_key, mode_key)}", 3000)

    # ==================================================================
    # 业务逻辑：撤销 / 重做（快照式）
    # ==================================================================
    def _push_undo(self, snapshot: list[Annotation] | None = None) -> None:
        """
        把“修改前状态”送入 AnnotationHistory。

        snapshot=None：直接复制当前 ``_current_shapes``；
        snapshot!=None：使用调用方预先保存的快照（拖动/拉伸场景）。
        """
        if snapshot is None:
            self._history.record(self._current_shapes)
        else:
            self._history.record_snapshot(snapshot)
        self._update_undo_actions()

    def _undo(self) -> None:
        """执行一次撤销；History 只给数据快照，界面恢复统一交给 _restore_shapes。"""
        snapshot = self._history.undo(self._current_shapes)
        if snapshot is None:
            return
        self._restore_shapes(snapshot)
        self.statusBar().showMessage("已撤销", 2000)

    def _redo(self) -> None:
        """执行一次重做；没有可重做历史时静默返回。"""
        snapshot = self._history.redo(self._current_shapes)
        if snapshot is None:
            return
        self._restore_shapes(snapshot)
        self.statusBar().showMessage("已重做", 2000)

    def _restore_shapes(self, snapshot: list[Annotation]) -> None:
        """
        根据历史快照同时恢复“数据模型 + 画布 + 对象面板”。

        这里必须深拷贝 snapshot，不能让历史栈里的对象重新成为当前可编辑对象，
        否则用户继续移动框时会污染历史记录。
        """
        self._current_shapes = copy_annotations(snapshot)
        self.canvas.clear_shapes()
        for shape in self._current_shapes:
            self.canvas.add_shape_item(shape, self._label_color(shape.label))
        self.object_panel.set_objects(self._current_shapes, self._label_color)
        self.property_panel.clear()
        self._mark_dirty(True)
        self._update_undo_actions()

    def _update_undo_actions(self) -> None:
        """根据 History 是否有记录，同步撤销/重做 QAction 的灰显状态。"""
        self.action_undo.setEnabled(self._history.can_undo)
        self.action_redo.setEnabled(self._history.can_redo)

    # ------------------------------------------------------------------
    # 拖动 / 拉伸的撤销与“未保存”标记
    # ------------------------------------------------------------------
    def _on_shape_drag_started(self, _item) -> None:
        """用户按住某个标注准备拖动/拉伸：此刻存一份快照备用。"""
        self._pending_snapshot = copy_annotations(self._current_shapes)

    def _on_shape_moved(self, _shape) -> None:
        """
        某个标注的位置或大小被改变了（拖动、拉角点都会触发）。

        一次拖动会产生一连串位移事件，但只应记一次撤销：
        拖动开始时存的快照在【第一个】位移事件里入栈，然后置空。
        """
        if self._pending_snapshot is not None:
            self._push_undo(self._pending_snapshot)
            self._pending_snapshot = None
        self._mark_dirty(True)  # 移动也是修改，要标“未保存”
        # 属性面板如果正在显示这个标注，同步刷新坐标显示
        self.property_panel.show_shape(_shape)

    # ==================================================================
    # 业务逻辑：保存
    # ==================================================================
    def _save_empty_annotation(self) -> None:
        """明确将当前无标注图片保存为“已检查（无目标）”."""
        if self._current_index < 0:
            return

        if self._current_shapes:
            QMessageBox.information(
                self,
                "当前图片已有标注",
                "“保存空标签”只用于没有任何标注对象的图片。\n"
                "当前图片已有标注，请使用普通保存按钮。",
            )
            return

        if self._save_current(save_empty=True):
            self.statusBar().showMessage(
                "已保存空标签：当前图片已检查，无目标",
                3000,
            )

    def _save_current(self, save_empty: bool = False) -> bool:
        """
        把当前图片的标注保存到同名 JSON 文件。

        返回值：
            True：保存成功，可以继续切图或退出。
            False：保存失败，禁止切图或退出。
        """
        # 当前还没有打开任何图片，不需要保存
        if self._current_index < 0:
            return True

        # 取得当前图片路径
        path = self._image_files[self._current_index]

        # self._image_size 保存的是一个元组：(图片宽度, 图片高度)
        # 这里使用“序列解包”，分别赋值给 w 和 h
        w, h = self._image_size

        try:
            # 一个细节：普通“保存”按钮点击在“没有标注、也没有任何修改”的图片上时，
            # 不应创建空 JSON，也不应把之前通过 Ctrl+S / “保存空标签”明确保存的
            # 空 JSON 删除掉。因此这种情况下完全不碰磁盘。
            should_write = bool(self._current_shapes) or save_empty or self._dirty

            if should_write:
                # save_shapes() 的参数顺序是：
                # 图片路径、图片宽度、图片高度、标注列表
                shapes_io.save_shapes(
                    path,
                    w,
                    h,
                    self._current_shapes,
                    save_empty=save_empty,
                )

        except OSError as error:
            QMessageBox.critical(
                self,
                "保存失败",
                f"标注文件写入失败：\n"
                f"{path}\n\n"
                f"原因：{error}\n\n"
                "请检查文件夹是否可写，或文件是否被其他程序占用。",
            )

            # 保存失败，通知调用者不能继续切图或退出
            return False


        # 保存成功后，统一清除“未保存”状态。
        # _mark_dirty(False) 会调用统一状态计算逻辑，把文件列表恢复为
        # DONE / EMPTY / TODO 中正确的一种状态。
        self._mark_dirty(False)

        self.statusBar().showMessage(
            f"已保存：{path.name}",
            3000,
        )

        # 保存成功
        return True

    def _current_annotation_status(self) -> AnnotationStatus | None:
        """
        计算当前图片的统一标注状态。

        这里只关心三个事实：
        1. 当前有多少个标注对象；
        2. 对应 JSON 是否存在；
        3. 当前内容是否有未保存修改。

        因此以后增加 Polygon、Point、Keypoint 等类型时，这里无需修改。
        """
        if not (0 <= self._current_index < len(self._image_files)):
            return None

        path = self._image_files[self._current_index]
        return resolve_annotation_status(
            annotation_count=len(self._current_shapes),
            annotation_file_exists=shapes_io.json_path_for(path).exists(),
            dirty=self._dirty,
        )

    def _refresh_current_file_status(self) -> None:
        """把当前图片的统一状态同步到左侧文件列表。"""
        status = self._current_annotation_status()
        if status is None:
            return
        self.file_panel.set_status(self._current_index, status)

    def _mark_dirty(self, dirty: bool) -> None:
        """
        记录“有没有未保存的修改”，并同步标题栏和文件列表。

        注意：DIRTY 是编辑状态，不是一种具体标注类型。
        无论当前编辑 Rectangle、Polygon 还是 Point，都使用同一逻辑。
        """
        self._dirty = dirty
        self._refresh_current_file_status()

        if self._folder is not None:
            dot = " ●" if dirty else ""
            self.setWindowTitle(f"{config.APP_NAME} — {self._folder.name}{dot}")

    # ==================================================================
    # 第26-27步：数据校验与格式导入/导出
    # ==================================================================
    @staticmethod
    def _read_image_size(path: Path) -> tuple[int, int]:
        """
        读取图片尺寸，供 Validation / Export Service 通过“依赖注入”调用。

        Service 层不直接依赖 QPixmap，而是接收这个函数，因此更容易独立测试。
        """
        pixmap = QPixmap(str(path))
        return (pixmap.width(), pixmap.height()) if not pixmap.isNull() else (0, 0)

    def _validate_project(self) -> None:
        """
        执行全项目数据校验，并把纯数据校验结果转换成 Qt 提示框。

        这体现了分层原则：validation_service 负责“发现问题”，
        MainWindow 只负责“如何展示问题”。
        """
        if not self._image_files:
            return
        issues = validate_dataset(self._image_files, self._read_image_size)
        if not issues:
            QMessageBox.information(self, "数据校验", "校验通过：没有发现损坏 JSON、越界坐标或退化标注。")
            return
        text = "\n".join(f"[{x.level}] {x.image}: {x.message}" for x in issues[:50])
        if len(issues) > 50:
            text += f"\n……其余 {len(issues)-50} 项未显示"
        QMessageBox.warning(self, "数据校验结果", f"发现 {len(issues)} 个问题：\n\n{text}")

    def _ensure_detection_classes(self) -> list[str]:
        """
        为 YOLO 导出准备检测类别。

        优先使用项目配置中持久化的 detection 类别；如果旧项目还没有配置文件，
        就从现有 rect Annotation 中按首次出现顺序推导类别，保证向后兼容。
        """
        classes = list(self._project.classes_for("detection"))
        if not classes:
            classes = list(dict.fromkeys(a.label for p in self._image_files for a in self._safe_load(p) if a.shape_type == "rect"))
        return classes

    def _safe_load(self, path: Path) -> list[Annotation]:
        """
        “尽力读取”辅助函数：读取损坏时返回空列表。

        仅用于类别推导这种非关键统计；真正打开图片时仍使用严格读取流程，
        不能用这个函数把损坏 JSON 悄悄当成空标注。
        """
        try:
            return shapes_io.load_shapes(path)
        except AnnotationLoadError:
            return []

    def _export_yolo(self) -> None:
        """UI 层的 YOLO 导出入口：选择目录、准备类别、调用 export_service。"""
        if not self._folder:
            return
        out = QFileDialog.getExistingDirectory(self, "选择 YOLO 导出目录")
        if not out:
            return
        classes = self._ensure_detection_classes()
        if not classes:
            QMessageBox.warning(self, "无法导出", "当前项目没有检测类别。")
            return
        try:
            n = export_yolo_detection(self._image_files, Path(out), classes, self._read_image_size)
        except Exception as error:
            QMessageBox.critical(self, "YOLO 导出失败", str(error)); return
        QMessageBox.information(self, "YOLO 导出完成", f"已导出 {n} 个矩形标注。")

    def _import_yolo(self) -> None:
        """
        UI 层的 YOLO 导入入口。

        导入完成后重新 open_folder()，让文件状态、画布和项目类别从磁盘重新同步，
        避免只更新一部分界面造成“内存状态与文件状态不一致”。
        """
        if not self._folder:
            return
        folder = QFileDialog.getExistingDirectory(self, "选择 YOLO 标签目录（应包含 classes.txt）")
        if not folder:
            return
        classes_file = Path(folder) / "classes.txt"
        if not classes_file.exists():
            QMessageBox.warning(self, "无法导入", "目录中没有 classes.txt。")
            return
        classes = [x.strip() for x in classes_file.read_text(encoding="utf-8").splitlines() if x.strip()]
        try:
            n = import_yolo_detection(self._image_files, Path(folder), classes, self._read_image_size)
        except Exception as error:
            QMessageBox.critical(self, "YOLO 导入失败", str(error)); return
        for label in classes:
            self._register_label(label, "detection")
        self.open_folder(self._folder)
        QMessageBox.information(self, "YOLO 导入完成", f"已导入 {n} 个矩形标注。")

    def _export_coco(self) -> None:
        """UI 层的 COCO 导出入口：合并 detection/segmentation 类别后调用服务。"""
        if not self._folder:
            return
        filename, _ = QFileDialog.getSaveFileName(self, "导出 COCO JSON", str(self._folder / "annotations_coco.json"), "JSON (*.json)")
        if not filename:
            return
        classes = list(dict.fromkeys(self._project.classes_for("detection") + self._project.classes_for("segmentation")))
        try:
            n = export_coco(self._image_files, Path(filename), classes, self._read_image_size)
        except Exception as error:
            QMessageBox.critical(self, "COCO 导出失败", str(error)); return
        QMessageBox.information(self, "COCO 导出完成", f"已导出 {n} 个矩形/多边形标注。")

    def _import_coco(self) -> None:
        """
        UI 层的 COCO 导入入口。

        当前 COCO 类别可能同时用于 bbox 和 polygon，因此导入后把类别分别登记到
        detection 与 segmentation 两个任务，再重新打开项目刷新界面。
        """
        if not self._folder:
            return
        filename, _ = QFileDialog.getOpenFileName(self, "导入 COCO JSON", str(self._folder), "JSON (*.json)")
        if not filename:
            return
        try:
            n, labels = import_coco(self._image_files, Path(filename))
        except Exception as error:
            QMessageBox.critical(self, "COCO 导入失败", str(error)); return
        for label in labels:
            self._register_label(label, "detection")
            self._register_label(label, "segmentation")
        self.open_folder(self._folder)
        QMessageBox.information(self, "COCO 导入完成", f"已导入 {n} 个标注。")

    # ==================================================================
    # 关闭保护
    # ==================================================================
    def closeEvent(self, event) -> None:
        """
        用户关闭程序时，检查是否存在未保存的修改。
        """
        if self._confirm_save_before_leave():
            event.accept()
        else:
            event.ignore()