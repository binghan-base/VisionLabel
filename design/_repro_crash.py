"""复现“标注完点下一张闪退”：穷举各种操作后再翻页。"""
import sys
sys.path.insert(0, r"D:\Users\12947\Desktop\VisionLabel")

from pathlib import Path
from PySide6.QtCore import Qt, QPointF, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QLineEdit
from visionlabel.main_window import MainWindow

IMG_DIR = Path(r"D:\Users\12947\Desktop\VisionLabel\design\_test_images")

app = QApplication([])
app.setStyle("Fusion")
app.styleHints().setColorScheme(Qt.ColorScheme.Light)
app.setFont(QFont("Microsoft YaHei", 9))


def answer_dialog(text=None, accept=True):
    def handler():
        w = QApplication.activeModalWidget()
        if w is not None:
            if text is not None:
                w.findChild(QLineEdit).setText(text)
            w.accept() if accept else w.reject()
    QTimer.singleShot(80, handler)


def draw_rect(win, sx, sy, ex, ey):
    tool = win.canvas._tool
    tool.on_mouse_press(win.canvas, QPointF(sx, sy))
    tool.on_mouse_move(win.canvas, QPointF(ex, ey))
    tool.on_mouse_release(win.canvas, QPointF(ex, ey))
    app.processEvents()


def fresh_window():
    win = MainWindow()
    win.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    win.show()
    win.open_folder(IMG_DIR)
    return win


def scenario(name, ops):
    """每个场景用全新窗口：画一个矩形，执行 ops，然后翻页。"""
    win = fresh_window()
    win.canvas.set_mode("rect")
    answer_dialog("person")
    draw_rect(win, -300, -200, -100, 0)
    ops(win)
    app.processEvents()
    win._next_image()
    app.processEvents()
    win._prev_image()
    app.processEvents()
    print(f"[ok] {name}")
    win.close()
    win.deleteLater()
    app.processEvents()


# 场景1：选中标注（角点把手显示出来）再翻页
def op_select(win):
    win.canvas._shape_items[0].setSelected(True)
scenario("选中后翻页", op_select)

# 场景2：拖动标注后再翻页
def op_drag(win):
    item = win.canvas._shape_items[0]
    win.canvas.shape_drag_started.emit(item)
    item.setPos(30, 30)
scenario("拖动后翻页", op_drag)

# 场景3：拉伸角点后再翻页
def op_resize(win):
    item = win.canvas._shape_items[0]
    win.canvas.shape_drag_started.emit(item)
    item.resize_corner(2, item.rect().bottomRight() + QPointF(40, 40))
scenario("拉伸后翻页", op_resize)

# 场景4：撤销、重做后再翻页
def op_undo(win):
    win._undo()
    win._redo()
scenario("撤销重做后翻页", op_undo)

# 场景5：删除标注后再翻页
def op_delete(win):
    win.canvas._shape_items[0].setSelected(True)
    win._delete_selected()
scenario("删除后翻页", op_delete)

# 场景6：复制标注后再翻页
def op_dup(win):
    win.canvas._shape_items[0].setSelected(True)
    win._duplicate_selected()
scenario("复制后翻页", op_dup)

# 场景7：多边形 + 选中 + 翻页
def op_polygon(win):
    win.canvas.set_mode("polygon")
    answer_dialog(None)
    tool = win.canvas._tool
    for p in [(-350, 180), (-250, 60), (-80, 100)]:
        tool.on_mouse_press(win.canvas, QPointF(*p))
    tool.on_mouse_press(win.canvas, QPointF(-349, 181))  # 点回起点闭合
    app.processEvents()
    win.canvas._shape_items[-1].setSelected(True)
scenario("多边形选中后翻页", op_polygon)

# 场景8：改标签后翻页
def op_rename(win):
    answer_dialog("cat")
    win.object_panel.edit_requested.emit(0)
scenario("改标签后翻页", op_rename)

print("ALL SCENARIOS SURVIVED")
