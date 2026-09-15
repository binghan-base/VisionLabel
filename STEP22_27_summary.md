# VisionLabel 第22-27步完成说明

## 第22步：通用 Undo/Redo
新增 `visionlabel/services/history.py`，主窗口不再直接管理两个栈。历史记录保存的是 `Annotation` 快照，因此与 rect/polygon/未来 point/keypoint 无关。

## 第23步：检测框编辑完善
沿用并整理现有 `ShapeRectItem`：矩形可选中、整体拖动、四角拉伸，修改会写回 Annotation，并接入统一历史服务。

## 第24步：快捷键与效率
保留并统一：Ctrl+Z/Ctrl+Y、Delete、Ctrl+D、A/D、V/R/P、Ctrl+H、F、Ctrl+0、数字1-9。Ctrl+S 仍按既定规则作为“主动确认保存”，空图会生成空 JSON。

## 第25步：项目配置与多任务类别
新增 `visionlabel/services/project_service.py`，项目根目录保存 `.visionlabel_project.json`。检测、分割、分类类别分开持久化；rect 自动对应 detection，polygon 自动对应 segmentation。

## 第26步：数据合法性检查
新增 `visionlabel/services/validation_service.py`。检查损坏 JSON、图片尺寸、越界坐标、0面积矩形、退化多边形。工具栏“校验”按钮接入该服务。

## 第27步：YOLO / COCO 导入导出
新增 `visionlabel/services/export_service.py`：
- YOLO detection：导入/导出矩形框；
- COCO：导入/导出 rect 与 polygon；
- 不伪装支持尚未实现的 mask/keypoint。

## 自验
```bash
python -m compileall -q .
python design/_test_annotation_model.py
python design/_test_steps22_27.py
```
