# VisionLabel 工程架构说明

## 1. 当前分层

```text
             ┌──────────────────┐
             │    MainWindow    │  流程协调
             └───────┬──────────┘
                     │
      ┌──────────────┼──────────────┐
      ↓              ↓              ↓
   Widgets          Tools         Services
  显示/交互      创建标注交互      业务处理
      │              │              │
      └──────────────┼──────────────┘
                     ↓
                  Models
                  纯数据
                     │
                     ↓
                 JSON / 外部格式
```

## 2. Models：数据是什么

`Annotation` 是核心业务对象。它不 import PySide6，这一点非常重要。

如果未来把 GUI 换成 Web、命令行，Annotation 仍然可以复用。

## 3. Tools：用户怎么创建数据

Tool 是“交互策略”。Rectangle 和 Polygon 的鼠标行为完全不同，因此把它们做成独立类。

这是 Strategy / Plugin 思路的简单实现。

## 4. Widgets：数据怎么显示

Qt 控件只负责视觉和交互。比如 FilePanel 不应该直接删除 JSON；它只发出“用户点击第 N 行”的 Signal。

## 5. Services：数据怎么处理

History、Project、Validation、Export 都是业务逻辑。把它们从 MainWindow 拆出来后：

- 可独立测试；
- 依赖更清晰；
- MainWindow 不会无限膨胀；
- 后续增加命令行批量转换工具更容易。

## 6. MainWindow：协调者

MainWindow 当前仍然较大，但它的主要职责已经明确：

- 创建 QAction、菜单、Toolbar、Dock；
- 连接 Signal/Slot；
- 维护“当前项目 / 当前图片”的应用状态；
- 协调 Canvas、Panel、Service；
- 弹用户确认框。

未来若继续大型化，可以再拆 `ProjectController` / `AnnotationController`，但当前阶段不需要为了“架构漂亮”提前过度设计。

## 7. 数据流示例：画一个 Rectangle

```text
RectTool.on_mouse_release()
        ↓
CanvasView.finish_new_rect()
        ↓ rect_drawn Signal
MainWindow._on_rect_drawn()
        ↓
MainWindow._create_shape()
        ↓
Annotation(...)
        ↓
_current_shapes.append()
        ↓
CanvasView.add_shape_item()
        ↓
ObjectPanel 刷新
        ↓
_mark_dirty(True)
```

## 8. 数据流示例：保存

```text
Ctrl+S / 保存按钮
        ↓
MainWindow._save_current()
        ↓
shapes.save_shapes()
        ↓
Annotation.to_dict()
        ↓
json.dumps()
        ↓
.tmp 文件
        ↓ replace()
正式 JSON
```

## 9. 为什么 Heap-Fix 属于架构问题而不只是一个 Bug

PySide6 同时存在：

- Python 对象生命周期；
- Qt/C++ 对象所有权；
- 事件循环中尚未处理完的事件。

旧 Scene 中被选中的 Rectangle 及其 Handle 可能仍处于 Qt 当前事件链。立即 `scene.clear()` 会同步删除 C++ item；如果事件链之后仍访问旧 item，就可能发生 C++ 层内存破坏。

稳定版改为：

```text
断开旧 Scene Signal
→ 新建 Scene
→ View 切换到新 Scene
→ old_scene.deleteLater()
```

本质是把“对象销毁”推迟到 Qt 认为安全的事件循环时机。
