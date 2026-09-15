"""
通用标注数据模型
================

本模块只回答两个问题：

1. “一条标注数据长什么样？” —— Annotation
2. “一种标注类型对数据有什么基本要求？” —— AnnotationTypeSpec

它不负责鼠标怎么画，也不负责 Qt 怎么显示。
这样新增标注类型时，数据层、绘制工具层、显示层可以分别维护，
避免所有逻辑都堆在 MainWindow 或 CanvasView 里。

当前 JSON 仍沿用 shape_type / points 字段，保证旧标注文件兼容。
代码层新增 annotation_type 属性作为更通用的称呼。
"""

from __future__ import annotations

import copy
import math
from dataclasses import dataclass, field
from typing import Any


Point = tuple[float, float]


@dataclass(frozen=True)
class AnnotationTypeSpec:
    """
    一种标注类型在“数据层”的声明。

    参数：
        key          JSON 中的内部标识，例如 rect / polygon。
        display_name 给人看的中文名。
        min_points   最少需要多少个点。
        max_points   最多允许多少个点；None 表示不限。
        uses_points  这种标注是否使用几何点。

    注意：这里故意不放 Qt 图元、鼠标事件等 UI 信息。
    数据模型不应该依赖界面框架。
    """

    key: str
    display_name: str
    min_points: int = 0
    max_points: int | None = None
    uses_points: bool = True

    def validate_point_count(self, count: int) -> None:
        """检查点数量是否满足当前标注类型的约束。"""
        if not self.uses_points:
            if count != 0:
                raise ValueError(
                    f"{self.display_name}（{self.key}）不应该包含 points"
                )
            return

        if count < self.min_points:
            raise ValueError(
                f"{self.display_name}（{self.key}）至少需要 {self.min_points} 个点"
            )

        if self.max_points is not None and count > self.max_points:
            if self.min_points == self.max_points:
                raise ValueError(
                    f"{self.display_name}（{self.key}）必须正好包含 "
                    f"{self.max_points} 个点"
                )
            raise ValueError(
                f"{self.display_name}（{self.key}）最多允许 {self.max_points} 个点"
            )


# ----------------------------------------------------------------------
# 标注类型注册表
# ----------------------------------------------------------------------

_ANNOTATION_TYPE_REGISTRY: dict[str, AnnotationTypeSpec] = {}


def register_annotation_type(spec: AnnotationTypeSpec, *, replace: bool = False) -> None:
    """
    注册一种新的标注数据类型。

    以后新增 Point / Line / RotatedBBox 等类型时，数据层不需要再去
    Annotation.from_dict() 里增加 if/elif，只需要注册一条规则。

    replace=False 是保护措施：同名类型重复注册时默认报错，避免某个模块
    悄悄覆盖已有规则。确实需要替换时显式传 replace=True。
    """
    key = spec.key.strip()
    if not key:
        raise ValueError("标注类型 key 不能为空")

    if key in _ANNOTATION_TYPE_REGISTRY and not replace:
        raise ValueError(f"标注类型已经注册：{key}")

    _ANNOTATION_TYPE_REGISTRY[key] = spec


def get_annotation_type_spec(annotation_type: str) -> AnnotationTypeSpec:
    """取得某种标注类型的规则；尚未注册时给出明确错误。"""
    try:
        return _ANNOTATION_TYPE_REGISTRY[annotation_type]
    except KeyError as error:
        raise ValueError(f"不支持的 shape_type：{annotation_type!r}") from error


def registered_annotation_types() -> tuple[AnnotationTypeSpec, ...]:
    """返回当前已经注册的标注类型（只读快照）。"""
    return tuple(_ANNOTATION_TYPE_REGISTRY.values())


# 当前已经真正实现“数据 + 绘制 + 显示”的类型。
# Point 等类型等对应 Tool / CanvasItem 做好后再注册，避免 JSON 能加载
# 但界面无法显示的“半支持”状态。
register_annotation_type(
    AnnotationTypeSpec(
        key="rect",
        display_name="矩形框",
        min_points=2,
        max_points=2,
    )
)
register_annotation_type(
    AnnotationTypeSpec(
        key="polygon",
        display_name="多边形",
        min_points=3,
        max_points=None,
    )
)


# ----------------------------------------------------------------------
# 通用 Annotation
# ----------------------------------------------------------------------

@dataclass
class Annotation:
    """
    一条通用标注数据。

    公共字段：
        label       类别名，例如 screw / scratch。
        shape_type  为兼容现有 JSON 保留的类型字段，例如 rect / polygon。
        points      图片坐标中的几何点；非几何标注未来可以为空。
        attributes  可扩展属性，供以后保存 difficult、occluded、track_id
                    或工业项目自定义字段等信息。

    重要原则：
        Annotation 只保存数据，不知道鼠标怎么画，也不知道 Qt 怎么显示。
    """

    label: str
    shape_type: str
    points: list[Point] = field(default_factory=list)
    attributes: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """直接创建 Annotation 时也执行一次基础规范化与校验。"""
        self.label = self._normalise_label(self.label)
        self.shape_type = self._normalise_type(self.shape_type)
        self.points = self._normalise_points(self.points)

        if not isinstance(self.attributes, dict):
            raise ValueError("attributes 必须是字典")
        # 做深拷贝，避免调用方后续修改原字典时连标注一起被改。
        self.attributes = copy.deepcopy(self.attributes)

        self.validate()

    @property
    def annotation_type(self) -> str:
        """
        shape_type 的通用语义别名。

        JSON 继续使用 shape_type 保持兼容；新代码讨论“标注类型”时可以
        使用 annotation_type，避免把所有 Annotation 都误解为几何 Shape。
        """
        return self.shape_type

    def validate(self) -> None:
        """根据注册表检查当前标注的数据是否满足对应类型的约束。"""
        spec = get_annotation_type_spec(self.shape_type)
        spec.validate_point_count(len(self.points))

    def clone(self) -> Annotation:
        """深拷贝当前标注，撤销/重做快照使用它。"""
        return Annotation(
            label=self.label,
            shape_type=self.shape_type,
            points=list(self.points),
            attributes=copy.deepcopy(self.attributes),
        )

    def translated_copy(self, dx: float, dy: float) -> Annotation:
        """
        返回一份整体平移后的副本。

        对当前 rect / polygon 都适用；未来非几何 Annotation 的 points
        为空，因此平移后仍然为空，不需要为每种类型写复制逻辑。
        """
        return Annotation(
            label=self.label,
            shape_type=self.shape_type,
            points=[(x + dx, y + dy) for x, y in self.points],
            attributes=copy.deepcopy(self.attributes),
        )

    def move_by(self, dx: float, dy: float) -> None:
        """把当前几何点整体平移 dx、dy 个图片像素。"""
        self.points = [(x + dx, y + dy) for x, y in self.points]

    def rect(self) -> tuple[float, float, float, float]:
        """
        矩形兼容辅助方法：返回 (x, y, width, height)。

        这是旧 Shape API 的兼容接口。新类型不应依赖它。
        """
        if self.shape_type != "rect":
            raise ValueError("rect() 只能用于 rect 类型标注")
        (x1, y1), (x2, y2) = self.points[0], self.points[1]
        x, y = min(x1, x2), min(y1, y2)
        return x, y, abs(x2 - x1), abs(y2 - y1)

    def to_dict(self) -> dict[str, Any]:
        """转换成可直接写入 JSON 的普通字典。"""
        data: dict[str, Any] = {
            "label": self.label,
            "shape_type": self.shape_type,
            # 统一保留 1 位小数；如需调整精度，只改这里即可。
            "points": [[round(x, 1), round(y, 1)] for x, y in self.points],
        }
        if self.attributes:
            data["attributes"] = copy.deepcopy(self.attributes)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Annotation:
        """检查 JSON 字典并创建 Annotation。"""
        if not isinstance(data, dict):
            raise ValueError("单条标注必须是字典")

        label = data.get("label")
        shape_type = data.get("shape_type")
        raw_points = data.get("points", [])
        attributes = data.get("attributes", {})

        if not isinstance(raw_points, list):
            raise ValueError("points 必须是列表")

        return cls(
            label=label,
            shape_type=shape_type,
            points=raw_points,
            attributes=attributes,
        )

    @staticmethod
    def _normalise_label(label: object) -> str:
        if not isinstance(label, str) or not label.strip():
            raise ValueError("label 必须是非空字符串")
        return label.strip()

    @staticmethod
    def _normalise_type(shape_type: object) -> str:
        if not isinstance(shape_type, str) or not shape_type.strip():
            raise ValueError("shape_type 必须是非空字符串")
        shape_type = shape_type.strip()
        # 在这里查注册表，未知类型立即失败，而不是等到界面绘制时才出问题。
        get_annotation_type_spec(shape_type)
        return shape_type

    @staticmethod
    def _normalise_points(raw_points: object) -> list[Point]:
        if not isinstance(raw_points, (list, tuple)):
            raise ValueError("points 必须是列表")

        points: list[Point] = []
        for point in raw_points:
            if not isinstance(point, (list, tuple)) or len(point) != 2:
                raise ValueError("每个坐标点必须包含 x、y 两个数值")

            x, y = point
            if (
                isinstance(x, bool)
                or isinstance(y, bool)
                or not isinstance(x, (int, float))
                or not isinstance(y, (int, float))
            ):
                raise ValueError("坐标必须是数字")

            x = float(x)
            y = float(y)
            if not math.isfinite(x) or not math.isfinite(y):
                raise ValueError("坐标不能是 NaN 或无穷大")

            points.append((x, y))
        return points


def copy_annotations(annotations: list[Annotation]) -> list[Annotation]:
    """深拷贝一组标注，主要用于撤销/重做快照。"""
    return [annotation.clone() for annotation in annotations]


# ----------------------------------------------------------------------
# 兼容旧代码
# ----------------------------------------------------------------------
# 旧模块和用户已有代码可能还在使用 Shape / copy_shapes。
# 暂时保留别名，避免第21步为了“改名字”造成大面积无意义改动。
# 新代码应优先使用 Annotation / copy_annotations。
Shape = Annotation
copy_shapes = copy_annotations
