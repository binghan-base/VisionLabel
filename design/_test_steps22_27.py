"""
第22-27步核心逻辑 smoke test
===========================

运行：
    python design/_test_steps22_27.py

本脚本刻意不创建 GUI，验证可以从 Qt 中独立出来的业务层：
- Step22 History Undo/Redo；
- Step25 ProjectConfig 持久化；
- Step26 Validation；
- Step27 YOLO / COCO 导入导出 round-trip。

TemporaryDirectory 会自动创建并清理临时目录，因此测试不会污染真实项目数据。
"""

from pathlib import Path
from tempfile import TemporaryDirectory
import sys

# 让脚本无论从哪个工作目录启动，都能找到项目根目录的 visionlabel 包。
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from visionlabel import shapes
from visionlabel.models.annotation import Annotation
from visionlabel.services.history import AnnotationHistory
from visionlabel.services.project_service import ProjectConfig, save_project, load_project
from visionlabel.services.export_service import (
    export_yolo_detection,
    import_yolo_detection,
    export_coco,
    import_coco,
)
from visionlabel.services.validation_service import validate_annotation


def main() -> None:
    """顺序执行第22-27步的最小关键路径验证。"""

    # ------------------------------------------------------------------
    # Step22：History
    # ------------------------------------------------------------------
    current = [Annotation("a", "rect", [(0, 0), (10, 20)])]
    history = AnnotationHistory()

    # 修改前先 record；随后模拟新增一个 polygon。
    history.record(current)
    current.append(Annotation("b", "polygon", [(0, 0), (5, 0), (2, 3)]))

    # undo 应恢复到“只有一个 rect”的旧状态。
    assert len(history.undo(current)) == 1

    # redo 应重新得到两个 Annotation。
    assert len(history.redo([Annotation("a", "rect", [(0, 0), (10, 20)])])) == 2

    # ------------------------------------------------------------------
    # Step26：Validation
    # ------------------------------------------------------------------
    # 正常框无问题；含负坐标的框应至少报告一条问题。
    assert validate_annotation(
        Annotation("a", "rect", [(0, 0), (10, 20)]), 100, 100
    ) == []
    assert validate_annotation(
        Annotation("a", "rect", [(-1, 0), (10, 20)]), 100, 100
    )

    # 以下项目持久化和格式 round-trip 全部放进临时目录。
    with TemporaryDirectory() as td:
        root = Path(td)
        image = root / "x.jpg"

        # ExportService 只需要文件路径和尺寸函数；这里不需要真正可解码的 JPEG。
        image.write_bytes(b"test-placeholder")

        # --------------------------------------------------------------
        # Step25：ProjectConfig persistence
        # --------------------------------------------------------------
        project = ProjectConfig()
        project.add_class("screw", "detection")
        project.add_class("scratch", "segmentation")
        save_project(root, project)

        loaded = load_project(root)
        assert loaded.classes_for("detection") == ["screw"]
        assert loaded.classes_for("segmentation") == ["scratch"]

        # 依赖注入：测试不使用 QPixmap，直接提供一个固定尺寸读取函数。
        def size_reader(_):
            return 100, 100

        # --------------------------------------------------------------
        # Step27：YOLO round-trip
        # --------------------------------------------------------------
        shapes.save_shapes(
            image,
            100,
            100,
            [Annotation("screw", "rect", [(10, 20), (50, 60)])],
            save_empty=True,
        )
        yolo_dir = root / "yolo"
        assert export_yolo_detection([image], yolo_dir, ["screw"], size_reader) == 1

        # 删除 VisionLabel JSON，再从刚导出的 YOLO txt 重新导入。
        shapes.save_shapes(image, 100, 100, [], save_empty=False)
        assert import_yolo_detection([image], yolo_dir, ["screw"], size_reader) == 1

        # --------------------------------------------------------------
        # Step27：COCO rect + polygon round-trip
        # --------------------------------------------------------------
        shapes.save_shapes(image, 100, 100, [
            Annotation("screw", "rect", [(10, 20), (50, 60)]),
            Annotation("scratch", "polygon", [(1, 1), (5, 1), (3, 4)]),
        ], save_empty=True)

        coco = root / "coco.json"
        assert export_coco([image], coco, ["screw", "scratch"], size_reader) == 2

        # 再次删除内部 JSON，确认 COCO 能重建两条 Annotation。
        shapes.save_shapes(image, 100, 100, [], save_empty=False)
        count, labels = import_coco([image], coco)
        assert count == 2
        assert set(labels) == {"screw", "scratch"}

    print("STEP22-27 smoke tests: PASS")


if __name__ == "__main__":
    main()
