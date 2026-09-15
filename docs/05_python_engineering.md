# 从 VisionLabel 学 Python 工程构建

## 1. 模块与包

一个 `.py` 文件通常是一个 module；带 `__init__.py` 的目录可以组织成 package。

VisionLabel 不把所有功能塞进 `main.py`，而是按职责拆包，这是从脚本走向工程的第一步。

## 2. 类型注解

例如：

```python
self._image_files: list[Path] = []
```

它不会强制 Python 运行时只能放 Path，但能给 IDE、静态检查、人类阅读提供明确契约。

`Path | None` 表示这个变量可以是 Path，也可以暂时没有值（None）。

## 3. dataclass

`Annotation`、`ProjectConfig`、`ValidationIssue` 都适合 dataclass，因为它们首先是“数据”。

它减少手写 `__init__` 等样板代码。

## 4. 可变默认值与 default_factory

错误习惯：

```python
items: list = []
```

多个实例可能共享同一个默认列表。

正确方式：

```python
items: list = field(default_factory=list)
```

## 5. Enum

状态集合使用 Enum，而不是散落的字符串：

```python
AnnotationStatus.DIRTY
```

比到处写 `"dirty"` 更安全。

## 6. 深拷贝与对象身份

Undo 历史必须保存深拷贝，因为 Annotation 是可修改对象。

主窗口查找选中对象时使用 `is` 而不是 `==`：两个坐标完全一样的框也可能是两个不同实例。

## 7. Signal / Slot

Qt 推荐组件之间通过信号通信：

```python
self.canvas.rect_drawn.connect(self._on_rect_drawn)
```

Canvas 不需要知道 MainWindow 后续怎么存 JSON；它只广播“矩形完成了”。

这是解耦。

## 8. 依赖注入

Validation / Export Service 不直接 import QPixmap，而接收：

```python
size_reader(path) -> (width, height)
```

GUI 可以传 Qt 实现，测试可以传普通函数。相同业务逻辑更容易测试。

## 9. 原子式写文件

直接覆盖 JSON 时，如果程序中途退出，正式文件可能只写了一半。

VisionLabel 使用：

```text
写 temp
→ 完整成功
→ replace 正式文件
```

这是非常常见的工程可靠性思路。

## 10. 单一职责

判断一个函数是否应该拆分，可以问：

> “这个函数现在有几个不同原因会发生变化？”

例如 YOLO 格式变化不应该迫使 FilePanel 修改；界面样式变化也不应该迫使 Annotation 修改。

## 11. 不要过度设计

可扩展不等于一开始建立几十层抽象。

当前 VisionLabel 的原则是：

- 已经出现重复/耦合的问题才抽象；
- 新类型真正实现时再开放对应接口；
- 不为尚未实现的 Mask/Keypoint 提前写大量空架构。

这是比“设计得很复杂”更重要的工程能力。
