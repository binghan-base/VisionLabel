"""
panels：右侧停靠面板
===================

四个面板都只负责“展示 + 发出用户选择信号”，不直接修改 Annotation：

- ``class_panel.py``    当前任务可用类别
- ``object_panel.py``   当前图片的 Annotation 实例列表
- ``property_panel.py`` 当前选中 Annotation 的属性摘要
- ``file_panel.py``     图片列表及 TODO/DONE/EMPTY/DIRTY/ERROR 状态

主窗口把它们放入 QDockWidget，因此用户可以拖动、关闭，并从“视图”菜单恢复。
"""
