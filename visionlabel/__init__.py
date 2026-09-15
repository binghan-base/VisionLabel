"""
VisionLabel 主 Python 包
======================

Python 工程知识：什么是“包”？
----------------------------
只要一个目录能够作为 Python package 使用，其他模块就可以通过：

    from visionlabel.models.annotation import Annotation

这样的方式导入它。``__init__.py`` 通常用于：
- 给包写总体说明；
- 暴露版本号；
- 必要时统一导出少量公共 API。

当前项目按职责分层：

- ``config.py``        全局常量、标注模式声明、类别颜色盘
- ``icons.py``         SVG 图标加载与运行时换色
- ``main_window.py``   主窗口 / 应用流程编排（Controller / Coordinator）
- ``models/``          与 Qt 无关的数据模型：Annotation、状态等
- ``services/``        与 UI 解耦的业务逻辑：历史、项目、校验、导入导出
- ``tools/``           鼠标标注工具：矩形、多边形等
- ``widgets/``         Qt 界面组件：画布、工具条、面板
- ``resources/``       SVG 等静态资源

阅读建议：先看 docs/代码阅读路线.md，再按 models -> services -> tools -> widgets
-> main_window.py 的顺序阅读，会比直接从主窗口 1400 行代码开始容易得多。
"""

# 当前版本号仍保持稳定版原值。本次“详细注释版”只更新注释/文档，
# 不改变标注格式和运行逻辑，因此不单独提升运行时版本。
__version__ = "0.1.0"
