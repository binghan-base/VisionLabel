# 新增标注类型指南

以后不要采用“到处加 if shape_type == xxx”的方式扩展 VisionLabel。

以下以 `rotated_rect` 为例。

## 1. 数据层

在 `models/annotation.py` 注册：

```python
register_annotation_type(
    AnnotationTypeSpec(
        key="rotated_rect",
        display_name="旋转框",
        min_points=..., 
        max_points=...,
    )
)
```

首先明确“怎样的数据才能唯一表示这种标注”。

## 2. Tool 层

新增：

```text
visionlabel/tools/rotated_rect_tool.py
```

继承 `BaseTool`，实现鼠标 press/move/release。

Tool 只负责产生几何结果，不应该在这里写 JSON。

## 3. ShapeItem 层

在 `widgets/shape_item.py` 增加对应 QGraphicsItem。

职责：

- 怎么画；
- 怎么被选择；
- 怎么编辑；
- 编辑后如何同步回 Annotation。

## 4. Canvas 注册

`canvas_view.py` 至少检查：

- `_build_tools()` 是否注册 Tool；
- `add_shape_item()` 是否能把 Annotation 转成正确 Item；
- 完成绘制后是否有 Signal 把图片坐标交给 MainWindow。

## 5. 配置入口

在 `config.MODES` 增加模式按钮，确认 `enabled=True` 之前 Tool 和 Item 都已真实实现。

## 6. 任务类别

在 MainWindow 的 `_task_for_shape_type()` 决定它属于 detection、segmentation 或新的任务。

## 7. Validation

增加该类型的：

- 点数是否合法；
- 是否越界；
- 是否退化；
- 特有几何约束。

## 8. Import / Export

不要默认所有格式都支持新类型。

例如 rotated bbox 不能直接无损导出普通 YOLO Detection。需要明确：

- 是否拒绝；
- 是否转外接矩形；
- 是否使用 YOLO OBB；
- 是否会造成信息损失。

## 9. Undo / Redo

如果新类型仍由 Annotation 表示，通用快照历史通常无需修改。

这就是当前架构把 History 放在 Annotation 层的价值。
