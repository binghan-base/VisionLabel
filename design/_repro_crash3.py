"""更接近真实使用：连续画多个框 + 快捷键翻页 + 快速连续翻页。"""
import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import sys
sys.path.insert(0, r"D:\Users\12947\Desktop\VisionLabel")

from pathlib import Path
from PySide6.QtCore import QPoint, Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLineEdit
from visionlabel.main_window import MainWindow

IMG_DIR = Path(r"D:\Users\12947\Desktop\VisionLabel\design\_test_images2")
IMG_DIR.mkdir(exist_ok=True)

app = QApplication([])
app.setFont(QFont("Microsoft YaHei", 9))

# 造 4 张干净的测试图（避免旧 json 干扰）
from PySide6.QtGui import QColor, QPainter, QPixmap
for i in range(1, 5):
    pm = QPixmap(800, 600)
    pm.fill(QColor("#8fb0c9"))
    pm.save(str(IMG_DIR / f"img_{i}.png"))
    j = IMG_DIR / f"img_{i}.json"
    if j.exists():
        j.unlink()


def answer_dialog(text=None):
    def handler():
        w = QApplication.activeModalWidget()
        if w is not None:
            if text is not None:
                w.findChild(QLineEdit).setText(text)
            w.accept()
    QTimer.singleShot(120, handler)


def draw(canvas, vp, sx, sy, ex, ey):
    p1 = canvas.mapFromScene(QPoint(sx, sy))
    p2 = canvas.mapFromScene(QPoint(ex, ey))
    QTest.mousePress(vp, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, p1)
    QTest.mouseMove(vp, p2)
    QTest.mouseRelease(vp, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, p2)
    app.processEvents()


window = MainWindow()
window.show()
window.open_folder(IMG_DIR)
canvas = window.canvas
vp = canvas.viewport()

# 连续画 3 个框（模拟真实标注节奏）
canvas.set_mode("rect")
for i, (x1, y1, x2, y2) in enumerate([(-300, -200, -100, 0),
                                       (0, -100, 200, 100),
                                       (-200, 100, 0, 250)]):
    answer_dialog(f"label{i}")
    draw(canvas, vp, x1, y1, x2, y2)
print("drawn:", len(window._current_shapes), window._labels)

# 按 D 键翻页（画布持有焦点，模拟快捷键）
print("-> press D")
QTest.keyClick(vp, Qt.Key.Key_D)
app.processEvents()
print("now at:", window._current_index)

# 再画一个框，然后快速连点“下一张”
canvas.set_mode("rect")
answer_dialog("labelX")
draw(canvas, vp, -250, -250, -50, -50)
print("-> rapid next x3")
for _ in range(3):
    window.canvas_bar.btn_next.click()
    app.processEvents()
print("now at:", window._current_index)

# 再按 A 回退两次
QTest.keyClick(vp, Qt.Key.Key_A)
QTest.keyClick(vp, Qt.Key.Key_A)
app.processEvents()
print("now at:", window._current_index)
print("OK, no crash")
