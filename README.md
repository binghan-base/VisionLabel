# VisionLabel

VisionLabel 是一个使用 **Python 3.10+ / PySide6 (Qt for Python)** 构建的可扩展图像标注工具。当前稳定基线已经完成矩形检测标注、多边形分割标注、统一 Annotation 数据模型、Undo/Redo、多任务类别持久化、数据校验、YOLO/COCO 基础导入导出，并修复了选中图元后切图可能触发的 Qt Scene 生命周期崩溃问题。

> 当前基线：**Step 27 Heap-Fix 稳定版（详细注释学习版）**  
> 本注释版不改变已验证通过的运行逻辑，主要更新源码注释、工程文档和代码阅读说明。

## 1. 当前已实现功能

- 图片文件夹扫描、图片切换、页码跳转；
- 画布缩放、适应窗口、原始大小、空格拖动画布；
- Rectangle 创建、选择、移动、四角缩放、删除、复制；
- Polygon 创建、闭合、保存、加载、删除；
- 动态类别创建与颜色分配；
- Detection / Segmentation / Classification 类别分开持久化；
- TODO / DONE / EMPTY / DIRTY / ERROR 五种统一标注状态；
- Ctrl+S 主动空标注确认与独立“保存空标签”按钮；
- 通用 Annotation 快照式 Undo / Redo；
- 损坏 JSON 检测、备份与恢复入口；
- 数据合法性校验；
- YOLO Detection 导入 / 导出；
- COCO bbox / polygon 导入 / 导出；
- Qt Scene 安全切换：选中矩形后反复切图压力测试通过。

当前未完成或尚未完善：Point / Keypoint、Mask/Brush、Line、旋转框、Polygon 顶点级编辑、AI 预标注、COCO RLE/Keypoint 等。

## 2. 运行方法

推荐使用你当前的 Conda 环境：

```bash
conda activate visionlabel
python main.py
```

首次安装依赖：

```bash
pip install -r requirements.txt
```

## 3. 先做代码级自验

在项目根目录执行：

```bash
python -m compileall -q .
python design/_test_annotation_model.py
python design/_test_steps22_27.py
python design/_test_scene_switch_stress.py
```

最后一个测试需要可用的 PySide6 GUI 环境，目标是反复执行：

```text
创建矩形 -> 选中 -> 显示四角 Handle -> 切图
```

200 次不发生 Windows `0xC0000374` heap corruption。

## 4. 工程结构

```text
VisionLabel/
├── main.py                       # 程序入口、QApplication、崩溃日志
├── requirements.txt              # Python 第三方依赖
├── README.md                     # 当前工程总览
├── CHANGELOG.md                  # 阶段变更记录
├── docs/                         # 面向学习/维护的工程文档
├── design/                       # 自验、崩溃复现、UI 设计资产
└── visionlabel/
    ├── __init__.py               # 主包说明与版本号
    ├── config.py                 # 全局常量、模式定义、颜色盘
    ├── icons.py                  # SVG 图标加载和换色
    ├── main_window.py            # UI 编排 + 业务流程协调
    ├── shapes.py                 # VisionLabel JSON I/O
    ├── models/                   # “数据是什么”
    │   ├── annotation.py         # Annotation + 类型注册表
    │   └── annotation_status.py  # TODO/DONE/EMPTY/DIRTY/ERROR
    ├── services/                 # “数据怎么处理”
    │   ├── history.py            # Undo / Redo
    │   ├── project_service.py    # 项目配置/任务类别
    │   ├── validation_service.py # 数据校验
    │   └── export_service.py     # YOLO / COCO
    ├── tools/                    # “用户怎么创建标注”
    │   ├── base_tool.py
    │   ├── rect_tool.py
    │   └── polygon_tool.py
    ├── widgets/                  # “界面怎么显示和交互”
    │   ├── canvas_view.py
    │   ├── shape_item.py
    │   ├── canvas_bar.py
    │   ├── label_dialog.py
    │   ├── mode_strip.py
    │   └── panels/
    └── resources/icons/          # SVG 图标资源
```

## 5. 推荐阅读顺序

不要从 `main_window.py` 第一行开始硬读。建议：

```text
main.py
  ↓
models/annotation.py
  ↓
shapes.py + models/annotation_status.py
  ↓
services/
  ↓
tools/base_tool.py -> rect_tool.py -> polygon_tool.py
  ↓
widgets/shape_item.py -> canvas_view.py
  ↓
widgets/panels/
  ↓
main_window.py
```

详细解释见：[`docs/01_code_reading_guide.md`](docs/01_code_reading_guide.md)。

## 6. 关键设计原则

1. **Model 与 Qt 解耦**：Annotation 不知道 QGraphicsItem 怎么画。
2. **Tool 与保存解耦**：RectTool 只负责鼠标画框，不负责类别或 JSON。
3. **Service 与 UI 解耦**：校验、Undo、导出不直接弹 QMessageBox。
4. **MainWindow 做编排，不做所有事情**：它连接 Signal/Slot 并协调各层。
5. **状态不能由 `bool(shapes)` 推断**：空 JSON 是“人工确认无目标”，不同于“未标注”。
6. **Qt C++ 对象生命周期要谨慎**：切图使用新 Scene + `deleteLater()`，不在当前事件链中 `scene.clear()` 暴力销毁选中图元。

## 7. 快捷键

| 功能 | 快捷键 |
|---|---|
| 打开文件夹 | Ctrl+O |
| 主动保存（空图也可确认空标注） | Ctrl+S |
| 撤销 / 重做 | Ctrl+Z / Ctrl+Y |
| 删除 | Delete |
| 复制 | Ctrl+D |
| 上一张 / 下一张 | A / D |
| 选择 / 矩形 / 多边形 | V / R / P |
| 显示/隐藏标注 | Ctrl+H |
| 适应窗口 | F |
| 原始大小 | Ctrl+0 |
| 快速选择类别 | 1~9 |

## 8. 进一步学习文档

- `docs/01_code_reading_guide.md`：按学习顺序理解整个项目；
- `docs/02_architecture.md`：Model / Service / Tool / Widget / MainWindow 如何协作；
- `docs/03_add_annotation_type.md`：以后增加 Point、RotatedBBox 等应该改哪些层；
- `docs/04_testing_and_stability.md`：当前测试体系和稳定性验收；
- `docs/05_python_engineering.md`：结合本项目学习 dataclass、Enum、类型注解、Signal/Slot、依赖注入等；
- `design/README.md`：design 目录里的测试/复现脚本分别做什么。


## 9. 本压缩包文档命名说明

为了避免 Windows 解压工具对中文 ZIP 文件名处理不一致，本学习版的 `docs/` 文档统一使用 ASCII 文件名，正文仍为中文：

- `01_code_reading_guide.md`：代码阅读路线；
- `02_architecture.md`：工程架构说明；
- `03_add_annotation_type.md`：新增标注类型指南；
- `04_testing_and_stability.md`：测试与稳定性；
- `05_python_engineering.md`：Python 工程知识；
- `06_file_function_index.md`：文件与函数索引；
- `07_logic_equivalence_check.md`：稳定版逻辑一致性检查；
- `08_learning_guide.docx`：Word 学习说明。

项目根目录的 `CONTENTS.txt` 可用于核对压缩包是否完整。
