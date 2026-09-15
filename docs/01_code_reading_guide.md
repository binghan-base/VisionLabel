# VisionLabel 代码阅读路线

这份文档解决一个问题：**面对几十个 Python 文件，应该按什么顺序读，才能真正理解而不是只看懂单行语法。**

## 第一层：程序如何启动

先看 `main.py`。

重点理解：

- `if __name__ == "__main__"`；
- `QApplication` 为什么必须先创建；
- `app.exec()` 为什么让程序一直运行；
- `sys.excepthook` 与 `faulthandler` 的区别；
- 为什么 C++ heap corruption 不一定能被 Python traceback 捕获。

## 第二层：数据是什么

读 `visionlabel/models/annotation.py`。

你要回答：

1. 一条 Annotation 有哪些字段？
2. Rectangle 为什么用两个 points？
3. Polygon 为什么是任意数量 points？
4. `@dataclass` 帮我们自动生成了什么？
5. `field(default_factory=list)` 为什么不能直接写 `=[]`？
6. `__post_init__()` 在什么时候执行？
7. 注册表为什么比在 `from_dict()` 里不断加 `if/elif` 更适合扩展？
8. 为什么 Undo 要 `clone()` 深拷贝？

然后看 `annotation_status.py`，理解“数据内容”和“标注流程状态”是两件不同的事。

## 第三层：磁盘怎么保存

看 `visionlabel/shapes.py`。

重点：

```text
图片 001.jpg
    ↕
标注 001.json
```

理解：

- `Path.with_suffix()`；
- `json.dumps()` / `json.loads()`；
- `ensure_ascii=False`；
- 临时文件 + `replace()` 的原子式保存思路；
- `save_empty=False` 与 `save_empty=True` 的语义区别；
- 为什么“没有 JSON”和“shapes=[] 的 JSON”不能混为一谈。

## 第四层：业务逻辑为什么单独放 Service

按顺序读：

1. `services/history.py`
2. `services/project_service.py`
3. `services/validation_service.py`
4. `services/export_service.py`

理解“纯 Python 业务逻辑”应尽量不依赖 QWidget/QMessageBox。

## 第五层：鼠标怎么变成 Annotation

看：

```text
tools/base_tool.py
    ↓
rect_tool.py
    ↓
polygon_tool.py
```

理解抽象基类、继承、多态。

Canvas 不需要知道 Rectangle 怎么画，只知道“把鼠标事件交给当前 Tool”。

## 第六层：Annotation 如何显示成 Qt 图元

先读 `widgets/shape_item.py`，再读 `widgets/canvas_view.py`。

必须理解三个对象：

```text
Annotation        Python 数据
QGraphicsItem     场景里的一个可交互图元
QGraphicsScene    管理所有图元
QGraphicsView     用户看到 Scene 的窗口
```

特别关注 Heap-Fix：切图时为什么不能简单认为 `scene.clear()` 永远安全。

## 第七层：小组件

读：

- `canvas_bar.py`
- `mode_strip.py`
- `label_dialog.py`
- `panels/*.py`

这些文件适合学习 Qt Signal/Slot 和“小组件只做一件事”的思想。

## 第八层：最后读 MainWindow

最后读 `main_window.py`。

此时你应该能把它理解为“编排器”：

```text
用户动作
  ↓ Signal
MainWindow
  ↓ 调用 Model / Service / Canvas
更新数据
  ↓
刷新多个 Widget
```

不要把 MainWindow 理解成“所有功能的实现文件”。长期维护时，MainWindow 越只负责协调越好。
