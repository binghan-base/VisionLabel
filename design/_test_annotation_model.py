"""
第21步 Annotation 数据模型轻量自验
==================================

运行：
    python design/_test_annotation_model.py

这个脚本不创建 QApplication，不依赖 GUI，适合快速验证最底层的数据模型：
- Rectangle 的坐标解释；
- Polygon 类型；
- 深拷贝快照；
- translated_copy；
- dict -> Annotation -> dict 的基础兼容；
- 注册一个新类型时不需要修改 Annotation.from_dict()。

Python 测试知识：
    ``assert 条件`` 在条件为 False 时抛出 AssertionError。
    这种脚本属于 smoke test（冒烟测试）：覆盖关键路径，但不是完整单元测试体系。
"""

from pathlib import Path
import sys

# 直接运行 design/*.py 时，Python 默认把 design/ 而不是项目根目录放进 sys.path。
# 下面把项目根目录插到最前面，因此可以正常 import visionlabel。
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from visionlabel.models.annotation import (
    Annotation,
    AnnotationTypeSpec,
    copy_annotations,
    register_annotation_type,
)

# 1) Rectangle：两个对角点应被 rect() 解释为 x/y/w/h。
rect = Annotation("box", "rect", [(10, 20), (30, 50)])
assert rect.rect() == (10.0, 20.0, 20.0, 30.0)

# 2) Polygon：annotation_type 是 shape_type 的通用别名。
polygon = Annotation("scratch", "polygon", [(0, 0), (10, 0), (5, 8)])
assert polygon.annotation_type == "polygon"

# 3) copy_annotations 必须深拷贝：修改原 rect 后，snapshot 不能一起变化。
snapshot = copy_annotations([rect, polygon])
rect.move_by(100, 100)
assert snapshot[0].points == [(10.0, 20.0), (30.0, 50.0)]

# 4) translated_copy 返回新对象，并整体平移全部几何点。
duplicate = polygon.translated_copy(12, 12)
assert duplicate.points == [(12.0, 12.0), (22.0, 12.0), (17.0, 20.0)]

# 5) JSON 字典 round-trip 的基础检查。
round_trip = Annotation.from_dict(rect.to_dict())
assert round_trip.shape_type == "rect"

print("STEP21 Annotation model smoke test: PASS")

# 6) 验证注册表设计的核心目标：新增数据类型不修改 from_dict()。
register_annotation_type(
    AnnotationTypeSpec(
        key="point_demo",
        display_name="测试关键点",
        min_points=1,
        max_points=1,
    )
)
point = Annotation.from_dict({
    "label": "center",
    "shape_type": "point_demo",
    "points": [[3, 4]],
})
assert point.points == [(3.0, 4.0)]
print("STEP21 registry extension smoke test: PASS")
