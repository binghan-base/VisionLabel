"""
标注 JSON 读写
=============

从第21步开始，真正的标注数据模型已经移动到：
    visionlabel/models/annotation.py

这个模块只负责“一张图片的标注如何保存 / 加载”，尽量不再承担
具体标注类型的业务规则。这样未来增加 Point、Line、Keypoint、
RotatedBBox 等类型时，JSON I/O 不需要跟着写大量 if/elif。

兼容说明：
    为了不一次性破坏旧代码，本模块仍重新导出 Shape 和 copy_shapes。
    它们分别是 Annotation 和 copy_annotations 的兼容别名。
"""

from __future__ import annotations

import json
from pathlib import Path

from . import __version__
from .models.annotation import (
    Annotation,
    Shape,
    copy_annotations,
    copy_shapes,
)


class AnnotationLoadError(Exception):
    """标注文件存在，但内容无法被 VisionLabel 安全读取。"""


# ----------------------------------------------------------------------
# 整张图片标注的保存 / 加载
# ----------------------------------------------------------------------

def json_path_for(image_path: Path) -> Path:
    """
    计算一张图片对应的标注文件路径。

    例：/data/test_001.png -> /data/test_001.json
    """
    return image_path.with_suffix(".json")


def save_shapes(
    image_path: Path,
    width: int,
    height: int,
    shapes: list[Annotation],
    save_empty: bool = False,
) -> None:
    """
    保存当前图片的标注。

    save_empty=False：空标注不生成 JSON；如果已有旧 JSON，则删除。
    save_empty=True ：即使没有标注，也生成 shapes=[] 的 JSON，表示用户
                      已人工确认当前图片没有目标。

    注意：函数名暂时保留 save_shapes，是为了兼容现有主窗口代码和旧项目；
    参数实际已经是通用 Annotation 列表。
    """
    path = json_path_for(image_path)

    if not shapes and not save_empty:
        path.unlink(missing_ok=True)
        return

    data = {
        "version": __version__,
        "imagePath": image_path.name,
        "imageWidth": width,
        "imageHeight": height,
        "shapes": [annotation.to_dict() for annotation in shapes],
    }

    text = json.dumps(
        data,
        ensure_ascii=False,
        indent=2,
    )

    temporary_path = path.with_suffix(path.suffix + ".tmp")

    try:
        # 原子式保存：先写完整临时文件，成功后再替换正式 JSON。
        temporary_path.write_text(text, encoding="utf-8")
        temporary_path.replace(path)
    except OSError:
        try:
            temporary_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def load_shapes(image_path: Path) -> list[Annotation]:
    """
    读取一张图片的标注文件。

    JSON 不存在表示尚未标注，返回空列表；
    JSON 存在但损坏或含未注册的标注类型，则抛出 AnnotationLoadError。
    """
    path = json_path_for(image_path)

    if not path.exists():
        return []

    try:
        data = json.loads(path.read_text(encoding="utf-8"))

        if not isinstance(data, dict):
            raise ValueError("JSON 根节点必须是字典")

        raw_shapes = data.get("shapes", [])
        if not isinstance(raw_shapes, list):
            raise ValueError("shapes 必须是列表")

        return [Annotation.from_dict(item) for item in raw_shapes]

    except (
        OSError,
        UnicodeError,
        TypeError,
        ValueError,
    ) as error:
        raise AnnotationLoadError(
            f"标注文件读取失败：{path}\n"
            f"原因：{error}"
        ) from error


# 新名字给后续代码使用；旧名字继续有效。
save_annotations = save_shapes
load_annotations = load_shapes

__all__ = [
    "Annotation",
    "Shape",
    "AnnotationLoadError",
    "copy_annotations",
    "copy_shapes",
    "json_path_for",
    "save_shapes",
    "load_shapes",
    "save_annotations",
    "load_annotations",
]
