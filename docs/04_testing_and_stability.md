# VisionLabel 测试与稳定性

## 1. 测试分层

### A. 静态语法检查

```bash
python -m compileall -q .
```

用于发现 SyntaxError、缩进错误、导入阶段语法问题。

### B. 纯 Python 数据/服务自验

```bash
python design/_test_annotation_model.py
python design/_test_steps22_27.py
```

覆盖 Annotation、注册表、History、ProjectConfig、Validation、YOLO/COCO round-trip。

### C. Qt 生命周期压力测试

```bash
python design/_test_scene_switch_stress.py
```

200 次“选中矩形 + 切换 Scene”，针对曾出现的 Windows `0xC0000374`。

### D. 人工 GUI 回归

必须继续覆盖：

- 新建 rect / polygon；
- 移动 / resize / delete / duplicate；
- Undo / Redo；
- Ctrl+S 空标注；
- 普通空图切换不生成 JSON；
- 重启后 DONE / EMPTY / TODO 恢复；
- 损坏 JSON 恢复；
- YOLO / COCO 真数据导入导出。

## 2. 为什么 compileall 不是“测试通过”

`compileall` 只能证明代码能被 Python 解析，不能证明业务逻辑正确，也不能发现很多 Qt C++ 生命周期问题。

因此稳定性必须是：

```text
语法检查 + 纯逻辑测试 + GUI 压力测试 + 真实人工使用
```

## 3. crash.log

`main.py` 通过 `sys.excepthook` 和 `faulthandler` 尽量留下错误信息。

但像 Windows heap corruption 这种 C++ 层崩溃可能直接结束进程，所以日志不是绝对保证。复现步骤和压力测试仍然很重要。

## 4. 当前稳定版结论

用户已经实际验证 `VisionLabel_step27_heapfix`：选中标注框后切图不再闪退。当前状态应记为：

**已修复并通过当前压力测试，后续真实使用继续观察。**
