"""
tools：标注工具层
================

“工具”负责用户【如何创建】一种标注，例如：
- RectTool：按下 -> 拖动 -> 松开；
- PolygonTool：连续点击顶点 -> 闭合。

它们不负责：类别持久化、JSON 保存、文件切换、右侧面板。
这些职责分别属于 MainWindow / services / widgets。

新增一种几何标注类型的完整接入通常需要：
1. ``models/annotation.py`` 注册数据规则；
2. ``tools/`` 新增 BaseTool 子类，定义鼠标交互；
3. ``widgets/shape_item.py`` 增加对应可视化图元；
4. ``widgets/canvas_view.py`` 的工具表和 add_shape_item() 接入；
5. ``config.py`` 的 MODES 加入口；
6. 按需扩展 Validation / YOLO / COCO 等服务。

因此“新增工具只改 config.py”是不完整的说法；本版文档已修正这一点。
"""
