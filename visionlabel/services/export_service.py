"""
标注格式导入 / 导出服务
=======================

本模块负责 VisionLabel 内部 Annotation 与外部常见数据格式之间的转换。
当前稳定版明确支持：

1. YOLO Detection
   - 仅 rect；
   - 仅为存在同名标注 JSON 的图片生成 .txt；
   - 每行为：class_id cx cy w h，坐标均归一化到 0~1。

2. COCO
   - rect -> bbox；
   - polygon -> segmentation；
   - 使用一个 JSON 文件保存 images / annotations / categories。

设计原则：
- 这里只处理“数据转换”，不弹 Qt 对话框；
- 图片尺寸通过 size_reader 函数传进来，避免 service 依赖 QPixmap；
- 只导出当前真正支持的类型，不把未实现的 Mask / Keypoint 假装成已支持。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from .. import shapes as shapes_io
from ..models.annotation import Annotation


# 类型别名写在注释里理解即可：
# size_reader(path) -> (width, height)
# Callable[[Path], tuple[int, int]] 正是这个“函数形状”的类型注解。


def _rect_xyxy(annotation: Annotation) -> tuple[float, float, float, float]:
    """
    把内部 rect 的 (x, y, width, height) 转成 (x1, y1, x2, y2)。

    当前模块暂未直接调用它，但保留作为几何转换辅助函数，
    后续若加入 Pascal VOC 等使用 xyxy 的格式可以复用。
    """
    x, y, w, h = annotation.rect()
    return x, y, x + w, y + h


def export_yolo_detection(
    image_files: list[Path],
    output_dir: Path,
    classes: list[str],
    size_reader: Callable[[Path], tuple[int, int]],
) -> int:
    """
    把 VisionLabel 的矩形标注导出为 YOLO Detection 格式。

    仅导出存在对应 JSON 的图片；空 JSON 标注仍导出空 TXT，表示负样本。

    返回值：实际导出的矩形标注总数。

    关键转换：
        内部：x, y, w, h（像素；x/y 是左上角）
        YOLO：cx, cy, w, h（相对图片宽高归一化）
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # 保存类别顺序。YOLO txt 里只存 class_id，必须有 classes.txt 才知道
    # 0/1/2 分别对应什么类别。
    (output_dir / "classes.txt").write_text("\n".join(classes), encoding="utf-8")

    # 字典推导式：类别名 -> 数字 id，例如 {"screw": 0, "wrench": 1}。
    class_to_id = {name: i for i, name in enumerate(classes)}
    count = 0

    for image_path in image_files:
        # 没有 JSON 表示尚未标注，不能当作已确认无目标的负样本导出。
        if not shapes_io.json_path_for(image_path).exists():
            continue

        width, height = size_reader(image_path)
        if width <= 0 or height <= 0:
            # 图片损坏时跳过。更严格的检查可先运行 validation_service。
            continue

        lines: list[str] = []

        for ann in shapes_io.load_shapes(image_path):
            # YOLO detection 只支持矩形；未知类别也不导出，避免生成无效 id。
            if ann.shape_type != "rect" or ann.label not in class_to_id:
                continue

            x, y, w, h = ann.rect()

            # YOLO 使用框中心坐标，并除以图片尺寸归一化。
            cx = (x + w / 2) / width
            cy = (y + h / 2) / height
            nw = w / width
            nh = h / height

            # 保留 6 位小数是常见 YOLO 文本精度，足以覆盖高分辨率图片。
            lines.append(
                f"{class_to_id[ann.label]} "
                f"{cx:.6f} {cy:.6f} {nw:.6f} {nh:.6f}"
            )

        # 已有 JSON 但没有可导出的矩形时，保留空 txt 的负样本语义。
        (output_dir / f"{image_path.stem}.txt").write_text(
            "\n".join(lines),
            encoding="utf-8",
        )
        count += len(lines)

    return count


def import_yolo_detection(
    image_files: list[Path],
    input_dir: Path,
    classes: list[str],
    size_reader: Callable[[Path], tuple[int, int]],
) -> int:
    """
    导入 YOLO Detection 标签，并写回 VisionLabel 同名 JSON。

    该函数是“有覆盖行为”的：某张图片存在 YOLO txt 时，会根据 txt
    重新生成该图片的 VisionLabel Annotation 列表并保存。

    返回值：成功导入的矩形标注总数。
    """
    imported = 0

    for image_path in image_files:
        txt_path = input_dir / f"{image_path.stem}.txt"
        if not txt_path.exists():
            # 没有对应 txt 就完全不碰原 JSON。
            continue

        width, height = size_reader(image_path)
        if width <= 0 or height <= 0:
            continue

        annotations: list[Annotation] = []

        for line_no, raw in enumerate(
            txt_path.read_text(encoding="utf-8").splitlines(),
            start=1,
        ):
            raw = raw.strip()
            if not raw:
                continue

            parts = raw.split()
            if len(parts) != 5:
                raise ValueError(
                    f"{txt_path.name}:{line_no} 不是 YOLO detection 的 5 列格式"
                )

            class_id = int(parts[0])
            if not 0 <= class_id < len(classes):
                raise ValueError(
                    f"{txt_path.name}:{line_no} 类别编号 {class_id} 越界"
                )

            # map(float, ...) 把四个字符串一次转换成浮点数。
            cx, cy, nw, nh = map(float, parts[1:])

            # 归一化尺寸还原成像素尺寸。
            w, h = nw * width, nh * height
            x1, y1 = cx * width - w / 2, cy * height - h / 2

            # VisionLabel 的 rect 用两个对角点保存。
            annotations.append(
                Annotation(
                    classes[class_id],
                    "rect",
                    [(x1, y1), (x1 + w, y1 + h)],
                )
            )

        # save_empty=True：YOLO 的空 txt 也是有语义的——表示这张图明确没有目标。
        shapes_io.save_shapes(
            image_path,
            width,
            height,
            annotations,
            save_empty=True,
        )
        imported += len(annotations)

    return imported


def export_coco(
    image_files: list[Path],
    output_file: Path,
    classes: list[str],
    size_reader: Callable[[Path], tuple[int, int]],
) -> int:
    """
    导出基础 COCO JSON。

    当前映射：
        Annotation(rect)    -> COCO bbox
        Annotation(polygon) -> COCO segmentation + bbox

    返回值：写入 annotations 数组的条目数。
    """
    # COCO category id 通常从 1 开始；这里保持这一习惯。
    categories = [
        {"id": i + 1, "name": name}
        for i, name in enumerate(classes)
    ]
    class_to_id = {name: i + 1 for i, name in enumerate(classes)}

    images = []
    annotations = []
    ann_id = 1

    for image_id, image_path in enumerate(image_files, start=1):
        width, height = size_reader(image_path)

        # COCO 的 images 数组保存图片元信息；标注通过 image_id 关联到这里。
        images.append({
            "id": image_id,
            "file_name": image_path.name,
            "width": width,
            "height": height,
        })

        for ann in shapes_io.load_shapes(image_path):
            if ann.label not in class_to_id:
                continue

            if ann.shape_type == "rect":
                x, y, w, h = ann.rect()
                segmentation = []
                bbox = [x, y, w, h]
                area = w * h

            elif ann.shape_type == "polygon":
                # Polygon 的外接矩形作为 COCO bbox。
                xs = [p[0] for p in ann.points]
                ys = [p[1] for p in ann.points]
                x, y = min(xs), min(ys)
                w, h = max(xs) - x, max(ys) - y
                bbox = [x, y, w, h]

                # COCO polygon segmentation 是一维坐标数组：
                # [(x1,y1), (x2,y2)] -> [x1,y1,x2,y2]
                segmentation = [[coord for point in ann.points for coord in point]]

                # 鞋带公式（Shoelace formula）计算多边形面积。
                area = 0.5 * abs(sum(
                    ann.points[i][0] * ann.points[(i + 1) % len(ann.points)][1]
                    - ann.points[(i + 1) % len(ann.points)][0] * ann.points[i][1]
                    for i in range(len(ann.points))
                ))

            else:
                # 当前 COCO 导出尚未实现 Point / Keypoint / Mask 等类型。
                continue

            annotations.append({
                "id": ann_id,
                "image_id": image_id,
                "category_id": class_to_id[ann.label],
                "bbox": [round(v, 2) for v in bbox],
                "area": round(area, 2),
                "iscrowd": 0,
                "segmentation": [
                    [round(v, 2) for v in seg]
                    for seg in segmentation
                ],
            })
            ann_id += 1

    data = {
        "images": images,
        "annotations": annotations,
        "categories": categories,
    }

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return len(annotations)


def import_coco(
    image_files: list[Path],
    coco_file: Path,
) -> tuple[int, list[str]]:
    """
    导入基础 COCO bbox / polygon segmentation。

    返回：
        (导入的标注数量, COCO 中出现的类别名称列表)

    当前策略：
        - 如果 segmentation 是可识别的 polygon，则优先导入 polygon；
        - 否则退回 bbox，导入 rect；
        - COCO 文件中找不到对应本地图片名的记录会被忽略。
    """
    data = json.loads(coco_file.read_text(encoding="utf-8"))

    # 把列表转换为字典，后续通过 id 查找时是 O(1)，不必每次遍历整个列表。
    categories = {
        int(x["id"]): str(x["name"])
        for x in data.get("categories", [])
    }
    images = {
        int(x["id"]): x
        for x in data.get("images", [])
    }

    # 本地图片按文件名建立索引，用 COCO file_name 查找对应 Path。
    by_name = {p.name: p for p in image_files}

    # 先把 annotations 按 image_id 分组，后面处理一张图时无需扫描全部标注。
    grouped: dict[int, list[dict]] = {}
    for ann in data.get("annotations", []):
        grouped.setdefault(int(ann["image_id"]), []).append(ann)

    imported = 0

    for image_id, image_info in images.items():
        image_path = by_name.get(str(image_info.get("file_name", "")))
        if image_path is None:
            continue

        width = int(image_info.get("width", 0))
        height = int(image_info.get("height", 0))
        annotations: list[Annotation] = []

        for raw in grouped.get(image_id, []):
            label = categories.get(int(raw.get("category_id", -1)))
            if not label:
                continue

            segmentation = raw.get("segmentation") or []

            # 当前只支持最常见的 polygon segmentation：[[x1,y1,x2,y2,...]]。
            if (
                segmentation
                and isinstance(segmentation, list)
                and isinstance(segmentation[0], list)
                and len(segmentation[0]) >= 6
            ):
                flat = segmentation[0]
                points = [
                    (float(flat[i]), float(flat[i + 1]))
                    for i in range(0, len(flat) - 1, 2)
                ]
                annotations.append(Annotation(label, "polygon", points))

            else:
                # 没有可用 polygon 时使用 bbox。
                x, y, w, h = map(float, raw["bbox"])
                annotations.append(
                    Annotation(label, "rect", [(x, y), (x + w, y + h)])
                )

        # COCO 中出现了这张图片，就把导入结果明确保存；即使 annotations 为空，
        # save_empty=True 也会保留“已确认无目标”的语义。
        shapes_io.save_shapes(
            image_path,
            width,
            height,
            annotations,
            save_empty=True,
        )
        imported += len(annotations)

    return imported, list(categories.values())
