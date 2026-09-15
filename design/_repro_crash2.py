"""用 QTest 真实鼠标事件复现“标注完点下一张闪退”。

QT_QPA_PLATFORM=offscreen：窗口真实创建和显示，但不弹到屏幕上，
QTest 的鼠标点击/拖动事件走 Qt 完整的事件分发链路，
和真实用户操作几乎一致。
"""
import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import sys
sys.path.insert(0, r"D:\Users\12947\Desktop\VisionLabel")

from pathlib import Path
from PySide6.QtCore import Qt, QPoint, QTimer
from PySide6.QtGui import QFont
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLineEdit
from visionlabel.main_window import MainWindow

IMG_DIR = Path(r"D:\Users\12947\Desktop\VisionLabel\design\_test_images")

app = QApplication([])
app.setFont(QFont("Microsoft YaHei", 9))


def answer_dialog(text=None, accept=True):
    def handler():
        w = QApplication.activeModalWidget()
        if w is not None:
            if text is not None:
                w.findChild(QLineEdit).setText(text)
            w.accept() if accept else w.reject()
    QTimer.singleShot(150, handler)


def view_point(canvas, scene_x, scene_y):
    """场景坐标 -> 视口像素坐标（QTest 点击用）。"""
    return canvas.mapFromScene(QPoint(scene_x, scene_y)).toPointF().toPoint()


window = MainWindow()
window.show()
window.open_folder(IMG_DIR)
app.processEvents()
canvas = window.canvas
vp = canvas.viewport()

# ---- 真实鼠标画一个矩形 ----
window.canvas.set_mode("rect")
answer_dialog("person")
p1 = view_point(canvas, -300, -200)
p2 = view_point(canvas, -100, 0)
QTest.mousePress(vp, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, p1)
QTest.mouseMove(vp, p2)
QTest.mouseRelease(vp, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, p2)
app.processEvents()
print("drawn shapes:", len(window._current_shapes))

# ---- 切到选择模式，真实鼠标点击选中这个矩形 ----
window.canvas.set_mode("select")
center = view_point(canvas, -200, -100)
QTest.mouseClick(vp, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, center)
app.processEvents()
print("selected:", window._current_shapes[0].label if window._current_shapes else None)

# ---- 真实鼠标拖动这个矩形 ----
QTest.mousePress(vp, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, center)
dest = QPoint(center.x() + 30, center.y() + 30)
QTest.mouseMove(vp, dest)
QTest.mouseRelease(vp, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, dest)
app.processEvents()
print("dragged, dirty =", window._dirty)

# ---- 真实鼠标点击“下一张”按钮 ----
print("-> clicking next button")
window.canvas_bar.btn_next.click()
app.processEvents()
print("survived next:", window._current_index)

QTest.qWait(200)
print("OK, no crash")
