# design 目录说明

这个目录不是生产运行代码，主要保存 UI 设计资产、回归测试和历史崩溃复现脚本。

## 当前推荐执行的自验

- `_test_annotation_model.py`：Annotation、深拷贝、类型注册；
- `_test_steps22_27.py`：History、Project、Validation、YOLO/COCO；
- `_test_scene_switch_stress.py`：Step27 Heap-Fix 的 200 次 Qt Scene 压力测试。

## 容错 / 历史复现

- `_test_bad_json.py`：坏 JSON 场景；
- `_repro_crash.py`：早期“操作后翻页闪退”的多场景复现；
- `_repro_crash2.py`：使用 QTest 注入更真实的鼠标事件；
- `_repro_crash3.py`：连续画框 + 快速翻页压力复现。

这些 `_repro_*` 脚本属于调试资产，不代表正式测试 API；其中部分脚本保留了开发机路径，正常开发时优先使用三个 `_test_*` 稳定自验脚本。

## UI 资产

- `ui-mockup.html`：早期 UI 设计稿；
- `ui-screenshot*.png`：界面验证截图；
- `_verify_screenshot.py`：用于生成/核对界面截图的辅助脚本。
