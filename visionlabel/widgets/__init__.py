"""
widgets：Qt 界面组件层
====================

这里存放可独立理解和复用的 Qt Widget / Graphics Item：

- ``canvas_view.py``  中央画布：图片、缩放、平移、工具调度、Scene 生命周期
- ``shape_item.py``   Annotation 在 QGraphicsScene 中的可视化/编辑图元
- ``canvas_bar.py``   翻页和缩放控制条
- ``mode_strip.py``   左侧标注模式条
- ``label_dialog.py`` 类别选择 / 新建对话框
- ``panels/``         类别、对象、属性、文件列表四个右侧面板

组件之间尽量通过 Qt Signal 通信，而不是相互持有并直接修改内部状态。
MainWindow 负责把这些信号连接起来。
"""
