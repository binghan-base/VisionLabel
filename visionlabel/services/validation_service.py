"""
数据校验服务
============

本模块负责“发现数据问题”，不负责弹窗，也不负责自动修复。
这是典型的业务逻辑与 UI 解耦：

    MainWindow 点击“校验”
        ↓
    validate_dataset() 返回一组 ValidationIssue
        ↓
    MainWindow 再决定用 QMessageBox 怎样展示

这样做的优点：
- 校验逻辑可以在没有 Qt 界面的自动化测试中运行；
- 以后可以把校验结果导出成 CSV/报告，而无需重写规则；
- 自动修复如果加入，也可以单独做成另一个 service。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .. import shapes as shapes_io
from ..models.annotation import Annotation


@dataclass(frozen=True)
class ValidationIssue:
    """
    一条数据问题记录。

    frozen=True 表示对象创建后字段不能再被重新赋值，适合“检查结果”这种只读值。

    level   问题级别，例如 ERROR / WARNING。
    image   出问题的图片文件名。
    message 面向用户的具体描述。
    """

    level: str
    image: str
    message: str


def validate_annotation(annotation: Annotation, width: int, height: int) -> list[str]:
    """
    校验【单条 Annotation】，返回问题文字列表。

    当前规则分三层：
    1. Annotation 自身结构是否合法；
    2. 几何点是否落在图片范围内；
    3. 针对当前已支持类型做额外几何检查。

    返回 list[str] 而不是抛异常，是因为一条标注可能同时有多个问题，
    调用方希望一次性把所有问题汇总给用户。
    """
    messages: list[str] = []

    # 第一层：复用数据模型自己的约束，例如 polygon 至少 3 个点。
    try:
        annotation.validate()
    except ValueError as error:
        messages.append(str(error))
        # 基础结构都不合法时，后面的几何检查可能没有意义，直接返回。
        return messages

    # 第二层：检查每个点是否越过图片边界。
    # 一条标注只报告一次越界即可，避免同一个框产生很多重复信息。
    for x, y in annotation.points:
        if x < 0 or y < 0 or x > width or y > height:
            messages.append(
                f"存在越界坐标 ({x:.2f}, {y:.2f})，图像范围为 {width}×{height}"
            )
            break

    # 第三层：类型特有检查。
    if annotation.shape_type == "rect":
        _, _, w, h = annotation.rect()
        if w <= 0 or h <= 0:
            messages.append("矩形框宽或高为 0")

    elif annotation.shape_type == "polygon":
        # set(annotation.points) 会把完全相同的重复点合并；
        # 少于三个不同顶点无法构成有效多边形。
        if len(set(annotation.points)) < 3:
            messages.append("多边形有效顶点不足 3 个")

    return messages


def validate_dataset(image_files: list[Path], image_size_reader) -> list[ValidationIssue]:
    """
    校验整个图片集合，并汇总所有 ValidationIssue。

    参数 image_size_reader 是一个“函数依赖”：
        image_size_reader(path) -> (width, height)

    为什么不在这里直接 import QPixmap？
        ValidationService 不应该依赖 Qt。MainWindow 可以传 QPixmap 版本，
        自动化测试可以传一个普通 Python 函数，这叫“依赖注入”。
    """
    issues: list[ValidationIssue] = []

    for image_path in image_files:
        json_path = shapes_io.json_path_for(image_path)

        # 没有 JSON 代表“尚未标注”，不是数据损坏，因此跳过。
        if not json_path.exists():
            continue

        # 先检查 JSON 能否正常解析成 Annotation。
        try:
            annotations = shapes_io.load_shapes(image_path)
        except Exception as error:
            issues.append(
                ValidationIssue(
                    "ERROR",
                    image_path.name,
                    f"JSON 读取失败：{error}",
                )
            )
            continue

        # 再验证图片本身是否能读取出有效尺寸。
        width, height = image_size_reader(image_path)
        if width <= 0 or height <= 0:
            issues.append(
                ValidationIssue("ERROR", image_path.name, "图片无法读取或尺寸非法")
            )
            continue

        # enumerate(..., start=1) 让用户看到“标注 #1、#2...”，
        # 而不是 Python 内部使用的 0 起始下标。
        for index, annotation in enumerate(annotations, start=1):
            for message in validate_annotation(annotation, width, height):
                issues.append(
                    ValidationIssue(
                        "WARNING",
                        image_path.name,
                        f"标注 #{index}: {message}",
                    )
                )

    return issues
