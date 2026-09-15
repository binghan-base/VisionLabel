"""
Step27 Heap-Fix：选中标注后反复切图压力测试
================================================

运行：
    python design/_test_scene_switch_stress.py

测试目标：
- 反复创建并选中 Rectangle，使四角 Handle 出现；
- 连续在多张图片之间切换 Scene；
- 验证不再出现 Windows ``0xC0000374`` heap corruption。

为什么普通 assert 测不到这个 Bug？
--------------------------------
该问题发生在 PySide6 背后的 Qt/C++ 对象生命周期：旧版本在输入事件尚未完全
结束时 ``scene.clear()`` 同步销毁被选中的 item。C++ 层内存破坏可能直接终止
进程，甚至没有 Python traceback。因此这里必须真实创建 QApplication、Scene、
GraphicsItem，并让 Qt 事件循环 ``processEvents()`` 实际运行。
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import QApplication

# 允许直接从项目根目录运行 design 脚本。
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from visionlabel.main_window import MainWindow
from visionlabel.models.annotation import Annotation


# 如果外部环境已经创建 QApplication 就复用，否则新建。
app = QApplication.instance() or QApplication([])

# tempfile 会在测试结束后自动删除测试图片和项目文件。
with tempfile.TemporaryDirectory(prefix="visionlabel_scene_stress_") as tmp:
    folder = Path(tmp)

    # 创建 3 张真实 PNG，颜色略有不同，确保 QPixmap 可以正常加载。
    for i in range(3):
        pm = QPixmap(800, 600)
        pm.fill(QColor(120 + i * 20, 150, 180))
        pm.save(str(folder / f"img_{i}.png"))

    win = MainWindow()

    # WA_DontShowOnScreen：窗口对象仍真实创建，只是不需要在测试时弹到屏幕前面。
    win.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    win.show()
    assert win.open_folder(folder)
    app.processEvents()

    # 每一轮：当前图放一个 Rectangle -> 选中 -> 让 Handle 出现 -> 切图。
    # 不标 dirty，避免自动保存逻辑干扰；这里专门隔离验证 Scene 生命周期。
    for i in range(200):
        shape = Annotation(
            label="stress",
            shape_type="rect",
            points=[(100.0, 100.0), (300.0, 260.0)],
        )

        win._current_shapes = [shape]
        win.canvas.clear_shapes()
        item = win.canvas.add_shape_item(shape, "#ff0000")
        item.setSelected(True)
        app.processEvents()

        # 到末尾就往回切，否则往下一张切，让 200 轮里持续创建/释放 Scene。
        if win._current_index < len(win._image_files) - 1:
            win.canvas_bar.btn_next.click()
        else:
            win.canvas_bar.btn_prev.click()
        app.processEvents()

    print("PASS: selected-item scene switch stress x200")

    # 正常关闭并再处理一轮事件，让 deleteLater() 有机会执行。
    win.close()
    app.processEvents()
