"""
图标加载器
==========

图标文件是外部 SVG（存放在 resources/icons/，来自 Lucide 图标库，
详见该目录的 NOTICE.md）。为什么用外部 SVG 而不是代码手绘？

1. 专业图标库的设计水准远高于手绘，软件颜值立刻提升；
2. SVG 是矢量格式，在任何分辨率（包括 4K 高分屏）下都清晰；
3. 新增图标 = 往 resources/icons/ 里放一个 .svg 文件，零代码。

本模块负责两件事：
- ``make_icon()``  按名字加载 SVG，可选地“染”成指定颜色
- ``color_swatch()`` 生成纯色小方块（类别列表的颜色标识）
"""

from pathlib import Path

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

# resources/icons/ 目录的位置（相对于本文件推算，项目搬动也不怕）
ICON_DIR = Path(__file__).parent / "resources" / "icons"

# 图标加载后的默认渲染边长（像素）。
# SVG 是矢量的，加载时指定多大就是多大；32 在常用尺寸下都够清晰。
ICON_SIZE = 32


def make_icon(kind: str, color: str | None = None) -> QIcon:
    """
    按名字加载一个 SVG 图标，可指定颜色。

    参数：
        kind  图标名，对应 resources/icons/<kind>.svg 文件名
              （如 "rect" -> resources/icons/rect.svg）
        color 可选。传入颜色（如 "#ff4d4f"）时，把图标整体染成该颜色；
              不传则使用 SVG 文件里自带的颜色（深灰 #444444）。

    返回：
        QIcon，可以直接用在按钮、菜单、列表项上。
    """
    path = ICON_DIR / f"{kind}.svg"
    if not path.exists():
        # 图标文件缺失时不要崩溃，返回一个空图标并在控制台提醒
        print(f"[警告] 图标文件不存在: {path}")
        return QIcon()

    pixmap = _render_svg(path, ICON_SIZE)

    if color is not None:
        pixmap = _tint(pixmap, color)

    return QIcon(pixmap)


def _render_svg(path: Path, size: int) -> QPixmap:
    """
    把一个 SVG 文件渲染成指定大小的位图（QPixmap）。

    为什么不用 QPixmap(path) 直接加载？
        QPixmap 加载 SVG 依赖一个可选的 Qt 插件（qsvg），
        有的 PySide6 安装里没带它，会导致图标一片空白。
        而 QSvgRenderer 是 QtSvg 模块自带的功能，不依赖该插件，
        用它渲染更保险 —— 这也是很多 Qt 项目的做法。
    """
    renderer = QSvgRenderer(str(path))

    # 准备一块透明画布
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    # 把 SVG 画到画布上（保持宽高比，居中）
    painter = QPainter(pixmap)
    renderer.setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)
    renderer.render(painter)
    painter.end()
    return pixmap


def _tint(pixmap: QPixmap, color: str) -> QPixmap:
    """
    把一张图“染”成指定颜色（保留透明度）。

    原理：新建一块透明画布，先把原图画上去；
    然后用 SourceIn 混合模式涂目标颜色 ——
    这个模式的含义是“颜色只留在原图不透明的地方”，
    于是原图的形状就整体变成了目标颜色。
    """
    tinted = QPixmap(pixmap.size())
    tinted.fill(Qt.GlobalColor.transparent)

    painter = QPainter(tinted)
    painter.drawPixmap(0, 0, pixmap)  # 先画原图
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    painter.fillRect(tinted.rect(), QColor(color))  # 再染色
    painter.end()
    return tinted


def color_swatch(color: str, size: int = 14) -> QPixmap:
    """
    生成一个纯色小方块（圆角），用于类别列表里的“颜色标识”。

    参数：
        color 填充颜色
        size  方块边长（像素）
    """
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)          # 不要边框
    painter.setBrush(QColor(color))            # 只要填充
    painter.drawRoundedRect(QRectF(0, 0, size, size), 3, 3)
    painter.end()
    return pixmap
