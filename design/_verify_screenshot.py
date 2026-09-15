"""开发自验脚本：模拟完整的“画框 -> 弹窗选标签”流程并截图验证。

覆盖的需求点：
1. 画完框弹出标签对话框
2. 输入新标签名 = 创建新标签
3. 弹窗默认值 = 上一个标注的标签（直接回车即可）
4. 取消弹窗 = 放弃这个标注
5. 标签不内置：保存后重新打开文件夹，标签从 .json 里恢复
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, r"D:\Users\12947\Desktop\VisionLabel")

from PySide6.QtCore import Qt, QPointF, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QLineEdit
from visionlabel.main_window import MainWindow

OUT_DIR = Path(r"D:\Users\12947\Desktop\VisionLabel\design")
IMG_DIR = OUT_DIR / "_test_images"
IMG_DIR.mkdir(exist_ok=True)

app = QApplication([])
app.setStyle("Fusion")
app.styleHints().setColorScheme(Qt.ColorScheme.Light)
app.setFont(QFont("Microsoft YaHei", 9))

# ---- 造 3 张测试图片（顺便清掉旧的标注文件，保证测试从干净状态开始）----
colors = ["#7ba7c9", "#8fbf7f", "#c98f7b"]
for i, c in enumerate(colors, start=1):
    pm = QPixmap(960, 640)
    pm.fill(QColor(c))
    p = QPainter(pm)
    p.setPen(QColor("white"))
    f = QFont("Arial", 120)
    f.setBold(True)
    p.setFont(f)
    p.drawText(pm.rect(), Qt.AlignmentFlag.AlignCenter, f"IMG {i}")
    p.end()
    pm.save(str(IMG_DIR / f"test_{i:03d}.png"))
    old_json = IMG_DIR / f"test_{i:03d}.json"
    if old_json.exists():
        old_json.unlink()


def answer_dialog(text=None, accept=True):
    """排期一个“自动应答”：弹窗出现后填入文字并点确定（或取消）。

    exec() 弹窗会开启一个内层事件循环，所以 QTimer 到点仍会触发，
    借此模拟用户操作弹窗。
    """
    def handler():
        w = QApplication.activeModalWidget()  # 当前正在显示的模态弹窗
        if w is not None:
            if text is not None:
                w.findChild(QLineEdit).setText(text)
            w.accept() if accept else w.reject()
    QTimer.singleShot(80, handler)


def draw_rect(sx, sy, ex, ey):
    """模拟一次完整的“按下-拖动-松开”画框操作。"""
    tool = window.canvas._tool
    tool.on_mouse_press(window.canvas, QPointF(sx, sy))
    tool.on_mouse_move(window.canvas, QPointF(ex, ey))
    tool.on_mouse_release(window.canvas, QPointF(ex, ey))
    app.processEvents()


# ================= 第 1 个窗口：标注 + 保存 =================
window = MainWindow()
window.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
window.show()
assert window.open_folder(IMG_DIR), "打开文件夹失败"
assert window._labels == [], "初始应该没有任何内置标签"

window.canvas.set_mode("rect")

# 需求2：输入新标签名，创建新标签
answer_dialog("person")
draw_rect(-400, -250, -150, 50)
assert window._labels == ["person"], f"应创建标签 person，实际 {window._labels}"

# 需求3：默认值 = 上一个标签（不输入直接确定）
answer_dialog(None)  # 不改文字，直接接受默认值
draw_rect(50, -100, 380, 220)
assert window._current_shapes[-1].label == "person", "默认标签应是上一个 person"

# 需求2：再创建一个新标签 car
answer_dialog("car")
draw_rect(-100, 80, 250, 280)
assert window._labels == ["person", "car"], f"实际 {window._labels}"
assert window._label_colors["person"] != window._label_colors["car"]

# 需求4：取消弹窗 = 放弃标注
answer_dialog(accept=False)
draw_rect(0, 0, 100, 100)
assert len(window._current_shapes) == 3, "取消后不应新增标注"


# ---- 多边形工具：逐点点击 + 点回起点闭合 ----
def draw_polygon(points, close_on_first=True):
    """模拟多边形绘制：依次点击各顶点，最后点回起点闭合。"""
    tool = window.canvas._tool
    for px, py in points:
        tool.on_mouse_press(window.canvas, QPointF(px, py))
    if close_on_first:
        fx, fy = points[0]
        tool.on_mouse_press(window.canvas, QPointF(fx + 1, fy + 1))  # 起点附近
    app.processEvents()


window.canvas.set_mode("polygon")
assert window.canvas._tool is not None, "多边形工具应已注册"
answer_dialog(None)  # 弹窗直接接受默认标签（上一个 = car）
draw_polygon([(-350, 180), (-250, 60), (-80, 100), (-120, 260)])  # 四边形
assert window._current_shapes[-1].shape_type == "polygon"
assert len(window._current_shapes[-1].points) == 4, "多边形应有 4 个顶点"

# Esc 取消：画了 2 个点后取消，不应产生标注
tool = window.canvas._tool
tool.on_mouse_press(window.canvas, QPointF(300, -200))
tool.on_mouse_press(window.canvas, QPointF(380, -150))
tool.cancel(window.canvas)
app.processEvents()
assert len(window._current_shapes) == 4, "Esc 取消后不应新增标注"

app.processEvents()
window.grab().save(str(OUT_DIR / "ui-screenshot.png"))
print("shot 1: 3 shapes,", window._labels)

window._save_current()
data = json.loads((IMG_DIR / "test_001.json").read_text(encoding="utf-8"))
assert [s["label"] for s in data["shapes"]] == ["person", "person", "car", "car"]
assert data["shapes"][3]["shape_type"] == "polygon"
assert len(data["shapes"][3]["points"]) == 4, "json 里多边形应有 4 个顶点"
print("json ok:", [(s["label"], s["shape_type"]) for s in data["shapes"]])

# ================= 第 2 个窗口：重新打开，标签和标注从 .json 恢复 =================
window2 = MainWindow()
window2.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
window2.show()
window2.open_folder(IMG_DIR)
# 需求5：标签不内置，从已有标注文件里读出来
assert window2._labels == ["person", "car"], f"应从json恢复标签，实际 {window2._labels}"
assert len(window2._current_shapes) == 4, "应恢复 4 个标注（含多边形）"
assert window2._current_shapes[3].shape_type == "polygon"
app.processEvents()
window2.grab().save(str(OUT_DIR / "ui-screenshot-2.png"))
print("shot 2: reopened, labels restored:", window2._labels)

# ================= 打磨项验证（都在 window2 上做，初始 4 个标注）=================
canvas2 = window2.canvas

# ---- 1. 拖动：脏标记 + 撤销/重做 ----
item0 = canvas2._shape_items[0]
before = list(window2._current_shapes[0].points)
canvas2.shape_drag_started.emit(item0)   # 模拟“按住了这个标注”
item0.setPos(20, 20)                      # 模拟拖动（触发 itemChange 回写）
app.processEvents()
assert window2._dirty, "拖动后应标记为未保存"
moved = window2._current_shapes[0].points
assert moved[0][0] - before[0][0] == 20 and moved[0][1] - before[0][1] == 20, \
    f"拖动 20px 后数据应同步，实际 {before} -> {moved}"
assert len(window2._undo_stack) == 1, "一次拖动应只记一条撤销"
window2._undo()
assert window2._current_shapes[0].points == before, "撤销后应回到拖动前"
window2._redo()
assert window2._current_shapes[0].points == moved, "重做后应回到拖动后"
print("undo/redo drag ok")

# ---- 2. 角点拉伸矩形 ----
rect_item = canvas2._shape_items[0]
old_rect = rect_item.rect()
canvas2.shape_drag_started.emit(rect_item)
rect_item.resize_corner(2, old_rect.bottomRight() + QPointF(30, 15))  # 拉右下角
app.processEvents()
new_pts = window2._current_shapes[0].points
new_w = new_pts[1][0] - new_pts[0][0]
assert abs(new_w - (old_rect.width() + 30)) < 1, f"拉角点后宽应 +30，实际 {new_w}"
window2._undo()  # 撤销拉伸，回到拖动后的状态，方便后续断言
print("resize corner ok")

# ---- 3. 复制标注 ----
canvas2._shape_items[0].setSelected(True)
window2._duplicate_selected()
assert len(window2._current_shapes) == 5, "复制后应有 5 个标注"
dup = window2._current_shapes[-1]
orig = window2._current_shapes[0]
assert dup.label == orig.label
assert dup.points[0][0] - orig.points[0][0] == 12, "复制体应偏移 12px"
window2._undo()
assert len(window2._current_shapes) == 4, "撤销复制后应回到 4 个"
print("duplicate ok")

# ---- 4. 双击对象面板改标签 ----
answer_dialog("cat")  # 弹窗出现后输入 cat 并确定
window2.object_panel.edit_requested.emit(0)
assert window2._current_shapes[0].label == "cat", "双击改标签应生效"
assert "cat" in window2._labels, "新标签 cat 应被注册"
assert canvas2._shape_items[0]._label_item.text() == "cat", "画布标签文字应同步"
print("rename ok")

# ---- 5. 显隐标注 ----
canvas2.set_shapes_visible(False)
assert not canvas2._shape_items[0].isVisible(), "隐藏后图元不可见"
canvas2.set_shapes_visible(True)
assert canvas2._shape_items[0].isVisible(), "恢复后图元可见"
print("visibility ok")

# ---- 6. 缩放范围限制 ----
for _ in range(60):
    canvas2.zoom_out()
assert canvas2.transform().m11() >= canvas2.ZOOM_MIN - 1e-9, "缩小不应低于下限"
for _ in range(300):
    canvas2.zoom_in()
assert canvas2.transform().m11() <= canvas2.ZOOM_MAX + 1e-9, "放大不应高于上限"
canvas2.fit()
print("zoom clamp ok")

app.processEvents()
window2.grab().save(str(OUT_DIR / "ui-screenshot-3.png"))
print("shot 3: polish features verified")
print("ALL CHECKS PASSED")
