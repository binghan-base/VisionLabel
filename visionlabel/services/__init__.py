"""
services：业务服务层
==================

Service 层负责“怎么处理数据”，但尽量不知道具体 Qt 控件。
这样业务逻辑就可以被自动化测试直接调用。

当前服务：
- history.py            Annotation 撤销 / 重做历史
- project_service.py    项目配置与多任务类别持久化
- validation_service.py 数据合法性检查
- export_service.py     YOLO / COCO 导入导出

这里仅重导出最常用的项目/历史类；其余服务建议从各自模块显式导入，
这样调用处能一眼看出功能来源。
"""

from .history import AnnotationHistory
from .project_service import ProjectConfig, load_project, save_project

__all__ = [
    "AnnotationHistory",
    "ProjectConfig",
    "load_project",
    "save_project",
]
