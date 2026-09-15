"""
标注状态模型
============

这一模块只描述“一张图片现在处于什么标注状态”，完全不关心具体标注类型。
因此 Rectangle、Polygon、Point、Keypoint 等都可以共用同一套状态机。

为什么要单独定义 Enum？
----------------------
早期如果到处直接写 "done" / "empty" / "todo" 字符串，容易出现：
- 拼写错误直到运行时才发现；
- 不同模块对同一个状态使用不同名字；
- 状态含义分散在很多 if/else 里。

Enum 把允许出现的状态集中声明，IDE 也能自动补全。
"""

from enum import Enum


class AnnotationStatus(str, Enum):
    """
    一张图片在文件列表中的统一状态。

    继承顺序 ``str, Enum`` 的效果是：成员既是枚举，又拥有字符串值。
    例如 ``AnnotationStatus.DONE.value == "done"``。
    """

    TODO = "todo"      # 没有标注 JSON：尚未明确完成
    DONE = "done"      # JSON 存在，并且至少有一个 Annotation
    EMPTY = "empty"    # JSON 存在，但 shapes=[]：人工确认“无目标”
    DIRTY = "dirty"    # 内存内容已修改，但尚未保存到磁盘
    ERROR = "error"    # JSON 存在，但读取 / 解析失败


def resolve_annotation_status(
    *,
    annotation_count: int,
    annotation_file_exists: bool,
    dirty: bool = False,
    error: bool = False,
) -> AnnotationStatus:
    """
    根据几个与具体标注类型无关的事实计算最终状态。

    ``*`` 的含义：后面的参数必须用关键字传入，例如：

        resolve_annotation_status(
            annotation_count=2,
            annotation_file_exists=True,
            dirty=False,
        )

    这样调用处读起来更清楚，也不容易把两个 bool 参数位置写反。

    状态优先级：
        ERROR > DIRTY > DONE / EMPTY / TODO

    为什么 ERROR 和 DIRTY 优先？
        ERROR 是磁盘数据异常，必须优先提示；DIRTY 表示用户当前有未保存修改，
        也比“磁盘上原来是什么状态”更重要。
    """
    if error:
        return AnnotationStatus.ERROR

    if dirty:
        return AnnotationStatus.DIRTY

    if annotation_count > 0:
        return AnnotationStatus.DONE

    if annotation_file_exists:
        # 0 个标注 + JSON 存在，说明用户主动确认过“没有目标”。
        return AnnotationStatus.EMPTY

    # 0 个标注 + 没有 JSON，说明还没有完成标注。
    return AnnotationStatus.TODO
