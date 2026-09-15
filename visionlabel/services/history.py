"""
撤销 / 重做历史服务
====================

这个模块专门负责 Annotation 数据的“时间线”，不负责界面。

为什么要单独做成 service？
-------------------------
如果把撤销逻辑写在 MainWindow 里，随着 Rectangle、Polygon、Point、
Keypoint 等类型越来越多，主窗口会同时承担 UI、业务状态和历史管理，
代码会迅速变得难以维护。

这里采用最容易理解的“快照式 Undo/Redo”：

    修改前状态 A
       ↓ record(A)
    当前状态 B
       ↓ undo(B)
    恢复 A，同时把 B 放进 redo 栈
       ↓ redo(A)
    恢复 B

栈结构：
    _undo：保存“可以退回去”的历史快照
    _redo：保存“撤销以后可以重新前进”的快照

注意：栈里保存的是 Annotation 的【深拷贝】，而不是原对象引用。
否则用户继续移动当前框时，历史快照也会一起改变，撤销就失去意义。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..models.annotation import Annotation, copy_annotations


@dataclass
class AnnotationHistory:
    """
    与具体标注类型无关的撤销/重做历史管理器。

    参数：
        max_steps：最多保存多少步撤销记录。默认 100。
                   这是为了限制内存使用；快照式历史会复制整张图的标注列表。

    设计要点：
        - 不依赖 Qt，因此可以单独测试；
        - 不关心 rect / polygon，任何 Annotation 都能进入历史；
        - 对外只返回“恢复后的数据快照”，UI 如何刷新由 MainWindow 决定。
    """

    max_steps: int = 100

    # field(default_factory=list) 很重要：
    # 不要写 _undo: list = []，否则多个 AnnotationHistory 实例会共享同一个列表。
    _undo: list[list[Annotation]] = field(default_factory=list)
    _redo: list[list[Annotation]] = field(default_factory=list)

    @property
    def can_undo(self) -> bool:
        """是否至少存在一步可撤销操作。用于控制“撤销”按钮是否可用。"""
        return bool(self._undo)

    @property
    def can_redo(self) -> bool:
        """是否至少存在一步可重做操作。用于控制“重做”按钮是否可用。"""
        return bool(self._redo)

    def clear(self) -> None:
        """
        清空当前图片的全部历史。

        VisionLabel 每张图片的历史相互独立，因此切图时 MainWindow 会调用它。
        """
        self._undo.clear()
        self._redo.clear()

    def record(self, annotations: list[Annotation]) -> None:
        """
        把当前 Annotation 列表作为“一步历史”记录到 undo 栈。

        典型调用时机：
            新建 / 删除 / 改类别之前，先 record(当前状态)，再执行修改。

        一旦发生新的修改，旧的 redo 路径必须失效，这与文本编辑器行为一致：
            撤销 -> 做了一个全新的修改 -> 已经不能再重做到原来的未来状态。
        """
        self._undo.append(copy_annotations(annotations))

        # 控制历史长度。del list[0] 删除最老的一步，只保留最近 max_steps 步。
        if len(self._undo) > self.max_steps:
            del self._undo[0]

        # 新操作产生后，旧 redo 栈失效。
        self._redo.clear()

    def record_snapshot(self, snapshot: list[Annotation]) -> None:
        """
        记录调用方事先保存好的快照。

        这个接口主要用于拖动 / 拉伸：用户按下鼠标时先保存“拖动前”的快照，
        真正发生位移后再把这份旧快照压入历史。这样一次连续拖动只算一步。
        """
        self._undo.append(copy_annotations(snapshot))
        if len(self._undo) > self.max_steps:
            del self._undo[0]
        self._redo.clear()

    def undo(self, current: list[Annotation]) -> list[Annotation] | None:
        """
        撤销一步，并返回应该恢复的 Annotation 列表。

        参数 current 是“撤销前的当前状态”，它要先进入 redo 栈，
        否则用户之后按 Ctrl+Y 时没有办法恢复回来。

        没有历史时返回 None，由调用方决定是否提示用户。
        """
        if not self._undo:
            return None

        # 当前状态成为“可以重做回来的未来状态”。
        self._redo.append(copy_annotations(current))

        # pop() 取出并删除 undo 栈最后一项（LIFO：后进先出）。
        return copy_annotations(self._undo.pop())

    def redo(self, current: list[Annotation]) -> list[Annotation] | None:
        """
        重做一步，并返回应该恢复的 Annotation 列表。

        与 undo 完全对称：当前状态先回到 undo 栈，再从 redo 栈取出下一状态。
        """
        if not self._redo:
            return None

        self._undo.append(copy_annotations(current))
        return copy_annotations(self._redo.pop())
