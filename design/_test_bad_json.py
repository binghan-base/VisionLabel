"""容错测试：各种“坏 json”不应导致翻页崩溃。"""
import sys
sys.path.insert(0, r"D:\Users\12947\Desktop\VisionLabel")

from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPixmap
from PySide6.QtWidgets import QApplication

d = Path(r"D:\Users\12947\Desktop\VisionLabel\design\_test_images3")
d.mkdir(exist_ok=True)
for i in range(1, 4):
    pm = QPixmap(400, 300)
    pm.fill(QColor("#8fb0c9"))
    pm.save(str(d / f"img_{i}.png"))

# 1号图：根节点是列表的 json（别的软件写的）
(d / "img_1.json").write_text('[{"label": "x"}]', encoding="utf-8")
# 2号图：GBK 编码的中文 json（Windows 记事本另存为 ANSI 的产物）
(d / "img_2.json").write_bytes(
    '{"shapes": [{"label": "人", "shape_type": "rect", "points": [[1,2],[30,40]]}]}'
    .encode("gbk"))
# 3号图：坐标是字符串的损坏 json
(d / "img_3.json").write_text(
    '{"shapes": [{"label": "a", "shape_type": "rect", "points": [["x","y"],[3,4]]}]}',
    encoding="utf-8")

app = QApplication([])
app.styleHints().setColorScheme(Qt.ColorScheme.Light)
app.setFont(QFont("Microsoft YaHei", 9))

from visionlabel.main_window import MainWindow
w = MainWindow()
w.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
w.show()
assert w.open_folder(d)
w._next_image()
w._next_image()
w._prev_image()
w._prev_image()
print("bad-json tolerance OK, labels:", w._labels)
