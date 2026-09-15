"""
models：纯数据模型层
===================

这里尽量不 import PySide6。原因是“数据是什么”不应该依赖“界面怎么画”。
这样模型可以被：GUI、自动化测试、导入导出脚本、未来命令行工具共同复用。

本包对外暴露的主要对象：
- Annotation / AnnotationTypeSpec：通用标注数据与类型规则；
- AnnotationStatus：文件列表中的统一标注状态；
- 注册表相关函数：支持新增标注类型。
"""

from .annotation import (
    Annotation,
    AnnotationTypeSpec,
    copy_annotations,
    get_annotation_type_spec,
    register_annotation_type,
    registered_annotation_types,
)
from .annotation_status import AnnotationStatus, resolve_annotation_status

# __all__ 明确“from visionlabel.models import *”时哪些名字属于公共 API。
# 即使平时很少使用 import *，它也能作为一份清晰的模块出口声明。
__all__ = [
    "Annotation",
    "AnnotationTypeSpec",
    "copy_annotations",
    "get_annotation_type_spec",
    "register_annotation_type",
    "registered_annotation_types",
    "AnnotationStatus",
    "resolve_annotation_status",
]
