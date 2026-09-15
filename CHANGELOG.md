# CHANGELOG

## Step 27 Heap-Fix · 详细注释学习版

本次不改变稳定版业务逻辑，主要进行维护性更新：

- 补充 models / services / tools / widgets / MainWindow 的教学型注释；
- 重写并更新 README，使其与当前真实功能一致；
- 新增工程架构、代码阅读、测试、新增标注类型、Python 工程知识文档；
- 补充 design 测试脚本用途说明；
- 清理 Python `__pycache__` / `.pyc`；
- 更新 `.gitignore`，避免日志、缓存、构建产物进入版本控制；
- 保留 Step 27 Heap-Fix 的 Scene 生命周期修复逻辑不变。

## Step 27 Heap-Fix

- 修复选中 Rectangle 后切图可能触发 Windows `0xC0000374` heap corruption；
- `CanvasView.load_image()` 不再在切图事件链中对旧 Scene 调 `clear()`；
- 改为创建新 `QGraphicsScene`、切换 View、旧 Scene `deleteLater()`；
- Handle 不再额外强引用父 Rectangle，使用 Qt `parentItem()` 所有权关系；
- 新增 `design/_test_scene_switch_stress.py`，200 次选中+切图压力测试。

## Step 22-27

- 通用 Undo / Redo；
- Rectangle 拖动与四角缩放；
- 快捷键体系；
- `.visionlabel_project.json` 多任务类别配置；
- 数据校验服务；
- YOLO Detection / COCO bbox+polygon 基础导入导出。

## Step 20-21

- TODO / DONE / EMPTY / DIRTY / ERROR 统一状态；
- Shape 数据模型升级为通用 Annotation 接口；
- 标注类型注册表；
- 保留 Shape / copy_shapes 兼容别名。
