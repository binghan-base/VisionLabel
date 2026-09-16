# VisionLabel

VisionLabel 是一个基于 **Python 3.10+** 与 **PySide6（Qt for Python）** 开发的轻量级、可扩展图像标注工具。

目前支持目标检测矩形框标注与多边形分割标注，并提供项目级类别管理、标注状态管理、撤销/重做、数据校验以及 YOLO / COCO 数据导入导出功能。

项目采用模块化标注架构设计，便于后续扩展关键点、旋转框、Mask、自定义工业标注类型等更多标注方式。

---

## 功能特性

### 图片管理

* 打开并扫描图片文件夹
* 上一张 / 下一张图片切换
* 跳转到指定图片
* 图片适应窗口
* 原始尺寸显示
* 画布缩放与平移

### 目标检测标注

* 创建矩形检测框
* 选择已有标注
* 拖动矩形框
* 通过四角控制点调整矩形大小
* 删除标注
* 复制标注
* 动态创建和选择类别
* 不同类别使用不同颜色显示

### 多边形分割标注

* 创建 Polygon 多边形标注
* 闭合并保存多边形
* 加载已有多边形标注
* 删除多边形标注
* 独立维护分割任务类别

### 标注状态管理

VisionLabel 对图片标注状态进行明确区分：

* `TODO`：图片尚未标注
* `DONE`：图片存在有效标注
* `EMPTY`：用户已经明确确认该图片不存在需要标注的目标
* `DIRTY`：当前标注已经修改但尚未保存
* `ERROR`：标注数据无法正常读取

其中，**空标注**与**未标注**属于两种不同状态。

### 撤销 / 重做

VisionLabel 使用通用 Annotation 历史记录系统管理标注操作。

当前支持：

* 新建标注撤销
* 删除标注撤销
* 矩形框移动撤销
* 矩形框缩放撤销
* Undo
* Redo

### 项目配置

VisionLabel 支持按任务独立管理类别。

Detection、Segmentation 和 Classification 使用不同的类别集合，例如：

```text
Detection
├── screw
├── wrench
└── tape

Segmentation
├── scratch
└── crack
```

项目级配置默认保存在：

```text
.visionlabel_project.json
```

### 数据校验

内置数据校验功能目前可以检测：

* 标注 JSON 损坏
* 图片无法正常读取
* 坐标越界
* 退化矩形框
* 零面积矩形框
* 非法多边形数据

### 导入与导出

#### YOLO

当前支持：

```text
VisionLabel Rectangle
        ↕
YOLO Detection
```

YOLO 导出使用归一化矩形框坐标，并生成：

```text
classes.txt
```

用于记录类别顺序。

#### COCO

当前支持：

```text
Rectangle → bbox
Polygon   → segmentation
```

导入导出的 COCO 数据采用标准结构：

```text
images
annotations
categories
```

---

## 安装

### 环境要求

* Python 3.10+
* PySide6
* Pillow

克隆项目：

```bash
git clone https://github.com/binghan-base/VisionLabel.git
cd VisionLabel
```

建议使用 Conda 或 Python 虚拟环境管理依赖。

### 使用 Conda

```bash
conda create -n visionlabel python=3.10
conda activate visionlabel
pip install -r requirements.txt
```

---

## 运行

在项目根目录执行：

```bash
python main.py
```

即可启动 VisionLabel。

---

## 快捷键

| 功能        | 快捷键      |
| --------- | -------- |
| 打开图片文件夹   | `Ctrl+O` |
| 保存当前标注    | `Ctrl+S` |
| 撤销        | `Ctrl+Z` |
| 重做        | `Ctrl+Y` |
| 删除选中标注    | `Delete` |
| 复制选中标注    | `Ctrl+D` |
| 上一张图片     | `A`      |
| 下一张图片     | `D`      |
| 选择工具      | `V`      |
| 矩形框工具     | `R`      |
| 多边形工具     | `P`      |
| 显示 / 隐藏标注 | `Ctrl+H` |
| 适应窗口      | `F`      |
| 原始尺寸      | `Ctrl+0` |
| 快速选择类别    | `1`–`9`  |

### 空标注

如果当前图片确认不存在需要标注的目标，可以使用：

```text
Ctrl+S
```

主动确认该图片为空标注。

VisionLabel 同时提供独立的“保存空标签”操作。

如果只是打开一张空图片后直接切换到下一张，而没有执行主动保存操作，则不会自动生成空标注文件。

---

## 项目结构

```text
VisionLabel/
├── main.py
├── requirements.txt
├── README.md
├── CHANGELOG.md
│
├── visionlabel/
│   ├── __init__.py
│   ├── config.py
│   ├── icons.py
│   ├── main_window.py
│   ├── shapes.py
│   │
│   ├── models/
│   │   ├── annotation.py
│   │   └── annotation_status.py
│   │
│   ├── services/
│   │   ├── history.py
│   │   ├── project_service.py
│   │   ├── validation_service.py
│   │   └── export_service.py
│   │
│   ├── tools/
│   │   ├── base_tool.py
│   │   ├── rect_tool.py
│   │   └── polygon_tool.py
│   │
│   ├── widgets/
│   │   ├── canvas_view.py
│   │   ├── shape_item.py
│   │   ├── canvas_bar.py
│   │   ├── label_dialog.py
│   │   ├── mode_strip.py
│   │   └── panels/
│   │
│   └── resources/
│       └── icons/
│
├── design/
└── docs/
```

---

## 架构设计

VisionLabel 将标注数据、交互工具、界面显示以及业务逻辑进行分层管理。

```text
Models
  │
  ├── Annotation 数据
  └── Annotation 状态
        │
        ▼
Services
  │
  ├── 历史记录
  ├── 项目配置
  ├── 数据校验
  └── 导入 / 导出
        │
        ▼
Tools
  │
  ├── Rectangle Tool
  └── Polygon Tool
        │
        ▼
Widgets
  │
  ├── Canvas
  ├── Graphics Items
  └── Panels
        │
        ▼
MainWindow
```

### Annotation 数据模型

Annotation 数据模型与 Qt 图形对象相互独立。

例如矩形框和多边形可以使用统一的 Annotation 数据结构，但分别遵循不同的几何规则和交互方式。

通过这种方式，数据存储逻辑不会与 Qt 界面绘制逻辑紧密耦合，从而降低后续新增标注类型时的修改范围。

### 标注类型注册机制

VisionLabel 通过统一的标注类型注册机制管理不同 Annotation 类型，而不是在项目各个模块中重复硬编码类型判断。

该设计可以为后续扩展以下标注方式提供基础：

* Point
* Line
* Keypoint
* Rotated Bounding Box
* Mask
* 自定义领域标注类型

---

## 标注数据格式

VisionLabel 使用 JSON 保存标注数据。

矩形框示例：

```json
{
    "label": "screw",
    "shape_type": "rect",
    "points": [
        [120.25, 80.50],
        [360.75, 240.25]
    ]
}
```

多边形示例：

```json
{
    "label": "scratch",
    "shape_type": "polygon",
    "points": [
        [120.30, 80.20],
        [180.50, 95.60],
        [210.40, 160.80],
        [140.20, 175.10]
    ]
}
```

标注坐标统一使用原始图片坐标系。

---

## 测试

执行基础 Python 语法检查：

```bash
python -m compileall -q .
```

执行 Annotation 数据模型测试：

```bash
python design/_test_annotation_model.py
```

执行 Service 与导入导出测试：

```bash
python design/_test_steps22_27.py
```

执行 Qt Scene 切换压力测试：

```bash
python design/_test_scene_switch_stress.py
```

Scene 切换测试会重复执行：

```text
创建矩形
→ 选中矩形
→ 显示四角控制点
→ 切换图片
```

用于验证连续切换图片过程中 Qt 图元生命周期管理是否稳定。

---

## 当前限制

以下功能目前尚未完成或仍在完善：

* Point 标注
* Keypoint 标注
* Line 标注
* 旋转框标注
* Mask / Brush 标注
* Polygon 顶点级编辑
* COCO RLE Mask
* COCO Keypoints
* AI 辅助标注

---

## 开发计划

后续计划包括：

* 完善 Polygon 编辑功能
* 增加 Point / Keypoint 标注
* 增加旋转框标注
* 增加 Mask 分割标注
* 支持更多数据集格式
* 完善项目管理
* 支持自定义快捷键
* 增加标注统计功能
* 完善自动化测试
* 增加 AI 辅助预标注

---

## 参与贡献

欢迎提交 Issue、Bug Report、Feature Request 或 Pull Request。

对于较大的功能修改，建议先创建 Issue，讨论功能需求与实现方式。

推荐使用独立分支开发：

```bash
git checkout -b feature/your-feature
```

完成修改和测试后提交：

```bash
git add .
git commit -m "Add your feature"
```

推送分支：

```bash
git push origin feature/your-feature
```

然后在 GitHub 上创建 Pull Request。

---

## Bug 反馈

提交 Bug 时，建议提供以下信息：

* 操作系统
* Python 版本
* PySide6 版本
* Bug 复现步骤
* 预期行为
* 实际行为
* Python Traceback
* Windows 进程退出代码（如果存在）

如果 GUI 发生崩溃但没有产生 Python Traceback，请尽可能提供 Windows 退出代码以及崩溃前的具体操作步骤。

---

## License

本项目基于 MIT License 开源。

你可以自由使用、复制、修改、合并、发布、分发以及用于商业用途，但需要保留原始版权声明和许可证声明。

---

## 致谢

VisionLabel 基于以下开源项目和技术构建：

* [Python](https://www.python.org/)
* [Qt for Python / PySide6](https://doc.qt.io/qtforpython/)
* [Pillow](https://python-pillow.org/)

---

## 项目状态

VisionLabel 当前仍处于持续开发阶段。

现有版本已经提供目标检测矩形标注、多边形分割标注、项目配置、标注历史管理、数据校验以及 YOLO / COCO 数据互操作等基础能力，并将继续围绕多类型标注、工程稳定性和标注效率进行扩展。
