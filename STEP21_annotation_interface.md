# 第21步：通用 Annotation 数据接口

本步目标不是增加一种新标注功能，而是把“标注数据模型”从具体的 Shape 概念中抽离出来，为后续 Point、Line、Keypoint、RotatedBBox、Classification 等类型预留稳定接口。

## 新增

- `visionlabel/models/annotation.py`
  - `Annotation`：通用标注数据对象。
  - `AnnotationTypeSpec`：一种标注类型在数据层的约束。
  - `register_annotation_type()`：注册新标注类型。
  - `copy_annotations()`：通用深拷贝，供 Undo/Redo 使用。

## 修改

- `visionlabel/shapes.py`
  - 现在主要负责 JSON 保存/加载。
  - 标注类型校验移交给 `models/annotation.py`。
  - 继续保留 `Shape = Annotation`、`copy_shapes = copy_annotations` 兼容旧代码。
- `visionlabel/main_window.py`
  - 核心业务代码开始使用 `Annotation`。
  - 复制标注改用 `translated_copy()`，不再手写构造器。
- `canvas_view.py`、`shape_item.py`、对象/属性面板
  - 类型提示改为 `Annotation`，行为不变。

## 为什么不一次性重命名所有 `_current_shapes`

`_current_shapes`、JSON 的 `shapes` 等名称已经贯穿现有工程和旧标注文件。第21步的目标是建立扩展接口而不是做大面积无功能收益的改名，因此保留这些兼容名称。后续如果需要，可以单独做一次纯重构。

## 新增类型的最低数据层步骤

例如未来要增加关键点：

```python
register_annotation_type(
    AnnotationTypeSpec(
        key="point",
        display_name="关键点",
        min_points=1,
        max_points=1,
    )
)
```

这之后 `Annotation.from_dict()` 不需要再增加 `if shape_type == "point"`。
真正可在 GUI 中使用，还需要对应 `PointTool` 和显示图元，这是刻意分层的。

## 附带一致性修正

`config.py` 中 `point` 原来显示为 enabled=True，但当前并没有 `PointTool` 和对应显示图元。本步将它临时改为 `False`，避免出现“按钮能点但实际上没有关键点工具”的半实现状态。等 Point 类型真正实现时再启用。
