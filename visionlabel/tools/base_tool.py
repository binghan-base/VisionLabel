"""
标注工具基类（插件接口）
========================

这个文件定义了所有标注工具必须遵守的“合同”。

设计思想（面向对象里的“抽象基类”）：
    画布（CanvasView）不关心每种标注具体怎么画，
    它只负责把鼠标事件转发给“当前工具”，工具自己决定做什么。
    只要新工具实现了这里定义的方法，画布就能直接使用它 ——
    这就是“可插拔”：新增标注类型时不用改动画布的代码。

事件流向（以矩形框为例）：

    用户按下鼠标
      -> Qt 调用 CanvasView.mousePressEvent()
      -> 画布发现当前处于标注模式，把事件转交给 RectTool.on_mouse_press()
      -> RectTool 记录起点、创建预览框
    用户拖动鼠标
      -> ... -> RectTool.on_mouse_move() 更新预览框
    用户松开鼠标
      -> ... -> RectTool.on_mouse_release() 完成绘制，通知画布
"""

from abc import ABC, abstractmethod


class BaseTool(ABC):
    """
    所有标注工具的抽象基类。

    ABC 表示“抽象基类”：它不能被直接实例化，只能被继承；
    子类必须实现所有 @abstractmethod 标注的方法，否则 Python
    会在创建子类对象时报错 —— 这保证了“合同”被遵守。

    每个事件方法都会收到两个参数：
        canvas  画布对象（CanvasView），工具可以通过它操作场景
                （添加预览图形、查询图片尺寸等）
        pos     鼠标位置，【场景坐标】（QPointF）。
                注意：场景坐标不是图片坐标！图片居中放在场景原点，
                需要换算时调用 canvas 提供的换算方法，
                工具自己不用记换算规则。
    """

    # ---- 工具的基本信息（子类用类属性覆盖即可）----
    key: str = ""       # 内部标识，与 config.MODES 中的 key 对应
    name: str = ""      # 显示名称
    shortcut: str = ""  # 切换快捷键

    @abstractmethod
    def on_mouse_press(self, canvas, pos) -> None:
        """鼠标左键按下（比如：记录矩形起点 / 添加多边形顶点）。"""

    @abstractmethod
    def on_mouse_move(self, canvas, pos) -> None:
        """鼠标移动（比如：实时更新正在绘制的预览图形）。"""

    @abstractmethod
    def on_mouse_release(self, canvas, pos) -> None:
        """鼠标左键松开（比如：完成矩形绘制）。"""

    def cancel(self, canvas) -> None:
        """
        用户按 Esc 或切换到别的工具时调用，用于清理现场
        （比如删除画了一半的预览图形）。子类按需覆盖，可以不实现。
        """
