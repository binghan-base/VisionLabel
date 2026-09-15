# VisionLabel 文件与函数索引

这份索引用于在 PyCharm 中快速定位功能。说明优先取源码 docstring 的第一行；没有 docstring 的项目则给出结构性名称。

## `main.py`

VisionLabel 程序入口

- **`_install_crash_logging()`**：安装“黑匣子”：程序万一崩溃，把错误详情写进 crash.log 文件。
- **`main()`**：创建应用、显示主窗口、进入事件循环，返回程序退出码。

## `visionlabel/__init__.py`

VisionLabel 主 Python 包

（本文件主要用于包导出或常量定义。）

## `visionlabel/config.py`

全局配置与常量

- **`palette_color()`**：按序号从颜色盘取色；序号超过颜色数量时循环使用。

## `visionlabel/icons.py`

图标加载器

- **`make_icon()`**：按名字加载一个 SVG 图标，可指定颜色。
- **`_render_svg()`**：把一个 SVG 文件渲染成指定大小的位图（QPixmap）。
- **`_tint()`**：把一张图“染”成指定颜色（保留透明度）。
- **`color_swatch()`**：生成一个纯色小方块（圆角），用于类别列表里的“颜色标识”。

## `visionlabel/main_window.py`

主窗口

- **class `MainWindow`**：VisionLabel 主窗口。
  - `__init__()`：内部方法；结合源码段落注释阅读
  - `_create_actions()`：创建所有 QAction。
  - `_create_menus()`：创建菜单栏。menuBar() 是 QMainWindow 自带的菜单栏。
  - `_create_toolbars()`：创建顶部工具栏和左侧模式条。
  - `_create_central()`：中央区域 = 画布（上）+ 画布控制条（下），竖向排列。
  - `_create_docks()`：创建右侧的四个停靠面板（QDockWidget）。
  - `_create_statusbar()`：创建底部状态栏。
  - `_connect_signals()`：把各组件的信号连接到对应的处理函数（槽函数）。
  - `_confirm_save_before_leave()`：离开当前内容前，处理尚未保存的修改。
  - `_reset_project_state()`：清空旧项目留下的运行状态。
  - `_open_directory()`：内部方法；结合源码段落注释阅读
  - `_ask_recover_corrupt_annotation()`：询问用户是否备份损坏JSON，
  - `_backup_corrupt_annotation()`：把损坏JSON重命名为唯一备份。
  - `open_folder()`：打开一个图片文件夹。
  - `_goto_image()`：跳转到第 index 张图片（index 从 0 开始）。
  - `_prev_image()`：上一张。
  - `_next_image()`：下一张。
  - `_on_page_jumped()`：用户在页码框输入页码并回车（页码从 1 开始，内部从 0 开始）。
  - `_on_image_loaded()`：图片加载完成后，记住尺寸并更新状态栏显示。
  - `_on_rect_drawn()`：用户画好了一个矩形（画布已完成图片坐标换算）。
  - `_on_polygon_drawn()`：用户闭合了一个多边形（points 是图片坐标的顶点列表）。
  - `_create_shape()`：所有标注类型共用的“新建标注”流程：
  - `_delete_selected()`：删除画布上当前选中的标注（Del 键 / 工具栏删除按钮）。
  - `_duplicate_selected()`：复制当前选中的标注（Ctrl+D）。
  - `_on_edit_label_requested()`：用户在对象面板双击某一行：弹出标签对话框修改这个标注的标签。
  - `_on_canvas_shape_selected()`：画布上的选中变化（用户点选/框选/取消选中一个标注）：
  - `_on_object_row_selected()`：用户在对象列表点击某一行：画布上选中对应的标注。
  - `_on_class_selected()`：用户在类别面板点击了某个标签（或按了数字键）：
  - `_select_class_by_index()`：数字键 1~9 的处理：标签存在才切换（标签是动态创建的，可能没有那么多）。
  - `_task_for_shape_type()`：把几何标注类型映射到项目任务；以后新增类型只在这里扩展。
  - `_load_active_task_labels()`：把当前任务的持久化类别装入界面。
  - `_set_active_task()`：切换当前项目任务，并同步该任务自己的类别列表。
  - `_register_label()`：把一个类别登记到项目配置，并在必要时刷新当前类别面板。
  - `_label_color()`：返回某类别的显示颜色。
  - `_rebuild_class_panel()`：用当前任务的 ``_labels`` 与 ``_label_colors`` 重建右侧类别列表。
  - `_on_mode_changed()`：左侧模式条发生变化时的总入口。
  - `_push_undo()`：把“修改前状态”送入 AnnotationHistory。
  - `_undo()`：执行一次撤销；History 只给数据快照，界面恢复统一交给 _restore_shapes。
  - `_redo()`：执行一次重做；没有可重做历史时静默返回。
  - `_restore_shapes()`：根据历史快照同时恢复“数据模型 + 画布 + 对象面板”。
  - `_update_undo_actions()`：根据 History 是否有记录，同步撤销/重做 QAction 的灰显状态。
  - `_on_shape_drag_started()`：用户按住某个标注准备拖动/拉伸：此刻存一份快照备用。
  - `_on_shape_moved()`：某个标注的位置或大小被改变了（拖动、拉角点都会触发）。
  - `_save_empty_annotation()`：明确将当前无标注图片保存为“已检查（无目标）”.
  - `_save_current()`：把当前图片的标注保存到同名 JSON 文件。
  - `_current_annotation_status()`：计算当前图片的统一标注状态。
  - `_refresh_current_file_status()`：把当前图片的统一状态同步到左侧文件列表。
  - `_mark_dirty()`：记录“有没有未保存的修改”，并同步标题栏和文件列表。
  - `_read_image_size()`：读取图片尺寸，供 Validation / Export Service 通过“依赖注入”调用。
  - `_validate_project()`：执行全项目数据校验，并把纯数据校验结果转换成 Qt 提示框。
  - `_ensure_detection_classes()`：为 YOLO 导出准备检测类别。
  - `_safe_load()`：“尽力读取”辅助函数：读取损坏时返回空列表。
  - `_export_yolo()`：UI 层的 YOLO 导出入口：选择目录、准备类别、调用 export_service。
  - `_import_yolo()`：UI 层的 YOLO 导入入口。
  - `_export_coco()`：UI 层的 COCO 导出入口：合并 detection/segmentation 类别后调用服务。
  - `_import_coco()`：UI 层的 COCO 导入入口。
  - `closeEvent()`：用户关闭程序时，检查是否存在未保存的修改。

## `visionlabel/models/__init__.py`

models：纯数据模型层

（本文件主要用于包导出或常量定义。）

## `visionlabel/models/annotation.py`

通用标注数据模型

- **class `AnnotationTypeSpec`**：一种标注类型在“数据层”的声明。
  - `validate_point_count()`：检查点数量是否满足当前标注类型的约束。
- **`register_annotation_type()`**：注册一种新的标注数据类型。
- **`get_annotation_type_spec()`**：取得某种标注类型的规则；尚未注册时给出明确错误。
- **`registered_annotation_types()`**：返回当前已经注册的标注类型（只读快照）。
- **class `Annotation`**：一条通用标注数据。
  - `__post_init__()`：直接创建 Annotation 时也执行一次基础规范化与校验。
  - `annotation_type()`：shape_type 的通用语义别名。
  - `validate()`：根据注册表检查当前标注的数据是否满足对应类型的约束。
  - `clone()`：深拷贝当前标注，撤销/重做快照使用它。
  - `translated_copy()`：返回一份整体平移后的副本。
  - `move_by()`：把当前几何点整体平移 dx、dy 个图片像素。
  - `rect()`：矩形兼容辅助方法：返回 (x, y, width, height)。
  - `to_dict()`：转换成可直接写入 JSON 的普通字典。
  - `from_dict()`：检查 JSON 字典并创建 Annotation。
  - `_normalise_label()`：内部方法；结合源码段落注释阅读
  - `_normalise_type()`：内部方法；结合源码段落注释阅读
  - `_normalise_points()`：内部方法；结合源码段落注释阅读
- **`copy_annotations()`**：深拷贝一组标注，主要用于撤销/重做快照。

## `visionlabel/models/annotation_status.py`

标注状态模型

- **class `AnnotationStatus`**：一张图片在文件列表中的统一状态。
- **`resolve_annotation_status()`**：根据几个与具体标注类型无关的事实计算最终状态。

## `visionlabel/services/__init__.py`

services：业务服务层

（本文件主要用于包导出或常量定义。）

## `visionlabel/services/export_service.py`

标注格式导入 / 导出服务

- **`_rect_xyxy()`**：把内部 rect 的 (x, y, width, height) 转成 (x1, y1, x2, y2)。
- **`export_yolo_detection()`**：把 VisionLabel 的矩形标注导出为 YOLO Detection 格式。
- **`import_yolo_detection()`**：导入 YOLO Detection 标签，并写回 VisionLabel 同名 JSON。
- **`export_coco()`**：导出基础 COCO JSON。
- **`import_coco()`**：导入基础 COCO bbox / polygon segmentation。

## `visionlabel/services/history.py`

撤销 / 重做历史服务

- **class `AnnotationHistory`**：与具体标注类型无关的撤销/重做历史管理器。
  - `can_undo()`：是否至少存在一步可撤销操作。用于控制“撤销”按钮是否可用。
  - `can_redo()`：是否至少存在一步可重做操作。用于控制“重做”按钮是否可用。
  - `clear()`：清空当前图片的全部历史。
  - `record()`：把当前 Annotation 列表作为“一步历史”记录到 undo 栈。
  - `record_snapshot()`：记录调用方事先保存好的快照。
  - `undo()`：撤销一步，并返回应该恢复的 Annotation 列表。
  - `redo()`：重做一步，并返回应该恢复的 Annotation 列表。

## `visionlabel/services/project_service.py`

项目配置服务

- **class `ProjectConfig`**：VisionLabel 的项目级配置数据模型。
  - `__post_init__()`：dataclass 完成 __init__ 后自动调用，用来做数据清洗和兼容保护。
  - `classes_for()`：返回某个任务的类别列表。
  - `add_class()`：向指定任务添加类别；空类别和重复类别都会被忽略。
  - `to_dict()`：转换成 json.dumps() 可以直接序列化的普通字典。
  - `from_dict()`：从 JSON 字典恢复 ProjectConfig。
- **`project_path()`**：根据项目图片文件夹计算配置文件的完整路径。
- **`load_project()`**：从项目文件夹读取配置。
- **`save_project()`**：把项目配置安全写入磁盘，并返回最终配置路径。

## `visionlabel/services/validation_service.py`

数据校验服务

- **class `ValidationIssue`**：一条数据问题记录。
- **`validate_annotation()`**：校验【单条 Annotation】，返回问题文字列表。
- **`validate_dataset()`**：校验整个图片集合，并汇总所有 ValidationIssue。

## `visionlabel/shapes.py`

标注 JSON 读写

- **class `AnnotationLoadError`**：标注文件存在，但内容无法被 VisionLabel 安全读取。
- **`json_path_for()`**：计算一张图片对应的标注文件路径。
- **`save_shapes()`**：保存当前图片的标注。
- **`load_shapes()`**：读取一张图片的标注文件。

## `visionlabel/tools/__init__.py`

tools：标注工具层

（本文件主要用于包导出或常量定义。）

## `visionlabel/tools/base_tool.py`

标注工具基类（插件接口）

- **class `BaseTool`**：所有标注工具的抽象基类。
  - `on_mouse_press()`：鼠标左键按下（比如：记录矩形起点 / 添加多边形顶点）。
  - `on_mouse_move()`：鼠标移动（比如：实时更新正在绘制的预览图形）。
  - `on_mouse_release()`：鼠标左键松开（比如：完成矩形绘制）。
  - `cancel()`：用户按 Esc 或切换到别的工具时调用，用于清理现场

## `visionlabel/tools/polygon_tool.py`

多边形标注工具

- **class `PolygonTool`**：多边形标注工具：逐点点击，回到起点闭合。
  - `__init__()`：内部方法；结合源码段落注释阅读
  - `on_mouse_press()`：单击左键：放下一个顶点；点在起点附近则闭合。
  - `on_mouse_move()`：移动鼠标：更新虚线预览（顶点依次相连 + 末尾跟着鼠标）。
  - `on_mouse_release()`：多边形靠“点击”驱动，松开事件不需要处理（合同要求实现，留空）。
  - `on_mouse_double_click()`：双击 = 闭合多边形（labelme 同款快捷操作）。
  - `confirm()`：按回车 = 闭合多边形（由画布的按键事件转发过来）。
  - `cancel()`：Esc 或切换工具：放弃画了一半的多边形。
  - `_create_preview()`：创建虚线预览路径和“起点”圆点（起点用更大的点提示可点击闭合）。
  - `_add_dot()`：在顶点处画一个小圆点；起点画得更大，提示“点我闭合”。
  - `_finish()`：闭合：把顶点列表交给画布（画布负责坐标换算和通知主窗口）。
  - `_cleanup()`：删除预览用的全部图元并重置状态。
  - `_screen_distance()`：计算两个场景点的距离，单位换算成【屏幕像素】。

## `visionlabel/tools/rect_tool.py`

矩形框标注工具

- **class `RectTool`**：矩形框标注工具：拖拽画出矩形。
  - `__init__()`：内部方法；结合源码段落注释阅读
  - `on_mouse_press()`：按下左键：记录起点，并在场景中创建一个虚线预览框。
  - `on_mouse_move()`：拖动中：用“起点”和“当前鼠标位置”更新预览框。
  - `on_mouse_release()`：松开左键：完成绘制（或因为太小而丢弃）。
  - `cancel()`：Esc 或切换工具：取消正在进行的绘制。
  - `_cleanup()`：删除预览框并重置状态。

## `visionlabel/widgets/__init__.py`

widgets：Qt 界面组件层

（本文件主要用于包导出或常量定义。）

## `visionlabel/widgets/canvas_bar.py`

画布控制条

- **class `CanvasBar`**：画布下方的控制条（翻页 + 缩放）。
  - `__init__()`：内部方法；结合源码段落注释阅读
  - `set_page()`：更新页码显示。current 从 1 开始；total 为 0 表示没有图片。
  - `set_zoom()`：更新缩放百分比显示。
  - `_on_page_edit_return()`：用户在页码框按下回车：解析数字并广播跳转请求。
  - `paintEvent()`：Qt 的一个“坑”：普通的 QWidget 子类即使设置了样式表背景，
  - `_make_separator()`：创建一条竖直分隔线（Qt 没有现成的“分隔线控件”，用 QFrame 模拟）。

## `visionlabel/widgets/canvas_view.py`

中央画布

- **`_build_tools()`**：模块级函数；结合源码段落注释阅读
- **class `CanvasView`**：中央画布。继承 QGraphicsView。
  - `__init__()`：内部方法；结合源码段落注释阅读
  - `load_image()`：加载并显示一张图片。成功返回 True，失败返回 False。
  - `set_mode()`：切换标注模式（由模式条的信号驱动）。
  - `finish_new_rect()`：供矩形工具调用：用户在场景里画好了一个矩形。
  - `finish_new_polygon()`：供多边形工具调用：用户在场景里闭合了一个多边形。
  - `add_shape_item()`：把一个标注数据显示到画布上，返回创建出来的图元。
  - `clear_shapes()`：清除画布上的所有标注图元（切换图片时调用）。
  - `delete_selected_shapes()`：删除当前选中的标注图元，返回被删除的 Shape 列表
  - `select_shape()`：选中某个标注对应的图元（用户在右侧对象列表点击时调用），
  - `selected_shapes()`：返回当前画布上所有被选中标注的 Shape（复制功能用）。
  - `set_shapes_visible()`：显示/隐藏全部标注图元（“显示标注”开关，不影响数据）。
  - `notify_shape_moved()`：供图元调用：某个标注的位置或大小被改变了。
  - `find_item()`：按数据对象查找对应的图元（修改标签时同步更新显示用）。
  - `scene_point_to_image()`：场景坐标点 -> 图片坐标 (x, y)。换算规则：加半个图片宽高。
  - `image_point_to_scene()`：图片坐标 (x, y) -> 场景坐标点。换算规则：减半个图片宽高。
  - `scene_rect_to_image()`：场景坐标系的矩形 -> 图片坐标的 (x, y, 宽, 高)。
  - `scene_rect_to_image_points()`：场景坐标系的矩形 -> 图片坐标的 [左上角, 右下角] 两个点。
  - `image_rect_to_scene()`：图片坐标的 (x, y, 宽, 高) -> 场景坐标系的矩形。
  - `zoom_in()`：放大一档。
  - `zoom_out()`：缩小一档。
  - `fit()`：适应窗口：整张图片恰好完整显示在画布中。
  - `actual_size()`：原始大小：图片 1 个像素 = 屏幕 1 个像素（100%）。
  - `wheelEvent()`：滚轮 = 缩放（以鼠标为中心）。
  - `keyPressEvent()`：空格 = 临时抓手模式（平移）；Esc = 取消绘制；回车 = 完成绘制。
  - `keyReleaseEvent()`：松开空格 = 恢复之前的模式。
  - `mousePressEvent()`：鼠标按下：标注模式下转给工具；否则交给 Qt（点选/拖动/平移）。
  - `mouseMoveEvent()`：鼠标移动：转发给工具（更新预览），并广播图片坐标给状态栏。
  - `mouseReleaseEvent()`：鼠标松开：标注模式下转给工具（完成绘制）。
  - `mouseDoubleClickEvent()`：鼠标双击：转发给工具（多边形用双击快速闭合）。
  - `resizeEvent()`：窗口大小变化时，如果处于“适应窗口”模式就自动重新适应。
  - `_show_placeholder()`：在场景中央显示“尚未打开图片”的引导提示。
  - `_apply_zoom()`：以 factor 倍率缩放（手动缩放后退出“适应窗口”模式）。
  - `_shape_at()`：查找某个场景坐标下的标注图元（找不到返回 None）。
  - `_emit_zoom()`：读取当前真实的缩放比例并广播。transform().m11() 是横向缩放系数。
  - `_on_selection_changed()`：场景中的选中集变化时（用户点选/框选/取消选中）：

## `visionlabel/widgets/label_dialog.py`

标签输入弹窗

- **class `LabelDialog`**：“输入/选择标签”对话框。继承 Qt 的 QDialog（对话框基类）。
  - `__init__()`：参数：
  - `label_text()`：返回用户最终输入的标签名（去掉首尾空白）。
  - `get_label()`：弹出对话框并等待用户操作。

## `visionlabel/widgets/mode_strip.py`

左侧标注模式条

- **class `ModeStrip`**：左侧竖向模式条。继承 QToolBar，自己就是一种工具栏。
  - `__init__()`：内部方法；结合源码段落注释阅读
  - `_build_buttons()`：根据 config.MODES 自动生成按钮。
  - `_on_triggered()`：内部槽函数：把 QAction 翻译成模式 key，再广播出去。
  - `current_mode()`：返回当前选中的模式 key。

## `visionlabel/widgets/panels/__init__.py`

panels：右侧停靠面板

（本文件主要用于包导出或常量定义。）

## `visionlabel/widgets/panels/class_panel.py`

类别面板

- **class `ClassPanel`**：类别列表面板。直接继承 QListWidget，自己就是一个列表。
  - `__init__()`：内部方法；结合源码段落注释阅读
  - `set_classes()`：用标签列表刷新面板。
  - `set_current()`：把某个标签设为当前标签（数字快捷键切换时由主窗口调用）。
  - `_show_placeholder()`：没有任何标签时的引导提示。
  - `_on_row_changed()`：内部槽函数：行号有效时才广播。

## `visionlabel/widgets/panels/file_panel.py`

文件列表面板

- **class `FilePanel`**：文件列表面板。直接继承 QListWidget，自己就是一个列表。
  - `__init__()`：内部方法；结合源码段落注释阅读
  - `set_files()`：用真实的文件列表刷新面板（打开文件夹后由主窗口调用）。
  - `set_status()`：更新某一行的标注状态（保存标注后由主窗口调用，
  - `set_current()`：高亮某一行（切换图片时由主窗口调用，保持列表高亮同步）。
  - `_on_row_changed()`：内部槽函数：行号有效时才广播（清空列表时 row 是 -1，忽略）。

## `visionlabel/widgets/panels/object_panel.py`

标注对象面板

- **class `ObjectPanel`**：标注对象列表面板。
  - `__init__()`：内部方法；结合源码段落注释阅读
  - `set_objects()`：用一张图片的标注列表刷新面板（切换图片、增删标注后调用）。
  - `set_current()`：高亮某一行（画布上的标注被选中时由主窗口调用）。
  - `clear_selection()`：取消高亮（画布上没有选中任何标注时调用）。
  - `_on_row_changed()`：内部槽函数：行号有效时才广播。

## `visionlabel/widgets/panels/property_panel.py`

属性面板

- **class `PropertyPanel`**：属性面板。
  - `__init__()`：内部方法；结合源码段落注释阅读
  - `show_shape()`：显示一个标注对象的属性。
  - `clear()`：没有选中任何标注时，恢复空状态。

## `visionlabel/widgets/shape_item.py`

标注图元（画布上的“可见标注”）

- **class `_HandleItem`**：矩形角点上的“调整把手” —— 选中矩形时出现在四个角的小圆点，
  - `__init__()`：参数：
  - `mousePressEvent()`：内部方法；结合源码段落注释阅读
  - `mouseMoveEvent()`：拖动把手中：把屏幕位置换算成矩形局部坐标，让父图元调整大小。
  - `mouseReleaseEvent()`：内部方法；结合源码段落注释阅读
- **class `ShapeItemMixin`**：混入类：两种标注图元共用的逻辑。
  - `_init_shape_item()`：公共初始化：存引用、开交互开关、画样式、加标签。
  - `itemChange()`：图元状态变化时 Qt 会调用这个方法。
  - `set_selected_style()`：切换选中/未选中的外观（由画布的选中变化信号驱动）。
  - `update_label()`：修改这个标注的类别显示（文字 + 颜色）。
  - `_scene_points()`：返回当前形状在【场景坐标】下的顶点列表（含拖动位移）。
  - `_make_label()`：在形状左上角外侧加一个类别标签（如 “person”）。
  - `_apply_style()`：根据是否选中设置边框和填充。
  - `_sync_back_to_model()`：把图元当前的位置写回 Annotation，并通知主窗口“形状变了”。
- **class `ShapeRectItem`**：矩形标注的图元，选中时四角出现把手，可拖动调整大小。
  - `__init__()`：参数：
  - `_scene_points()`：矩形的场景顶点：左上角 + 右下角。mapToScene 自动含拖动位移。
  - `_make_handles()`：在四个角创建把手（默认隐藏，选中时才显示）。
  - `set_selected_style()`：重写：除了换样式，还要显示/隐藏角点把手。
  - `resize_corner()`：把某个角拖到 local_pos（矩形局部坐标），对角保持不动。
  - `_layout_parts()`：根据当前矩形摆放标签和四个把手（局部坐标）。
- **class `ShapePolygonItem`**：多边形标注的图元（暂不支持顶点编辑，整体可拖动）。
  - `__init__()`：参数：
  - `_scene_points()`：多边形的场景顶点：全部顶点。mapToScene 自动含拖动位移。
