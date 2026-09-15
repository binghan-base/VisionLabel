"""
项目配置服务
============

本模块负责保存“项目级、跨图片”的信息，目前主要是：

- 当前任务（detection / segmentation / classification）
- 每种任务自己的类别列表

配置文件名固定为：.visionlabel_project.json
它放在用户打开的图片文件夹根目录中。

为什么类别要放在项目配置里，而不是某一张图片的 JSON？
-------------------------------------------------------
图片 JSON 描述的是“这一张图有什么标注”；类别集合属于整个数据集/项目。
如果把类别只藏在单张图片中，就无法区分：
    - 当前项目允许哪些类别；
    - 某一张图恰好出现了哪些类别。

为什么 detection / segmentation / classification 分开？
-------------------------------------------------------
用户已经明确要求不同任务不要共用标签。例如 detection 里的 "scratch"
不应该自动成为 classification 的类别。task_classes 就是为此设计的。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

# 项目配置文件使用“点文件”命名，Windows 仍然可以正常读写。
PROJECT_FILENAME = ".visionlabel_project.json"

# 当前项目层已经预留三种任务。以后增加 keypoint 等任务时，
# 应同时评估 UI、Annotation、Tool、导出格式是否真正支持，而不是只加字符串。
SUPPORTED_TASKS = ("detection", "segmentation", "classification")


@dataclass
class ProjectConfig:
    """
    VisionLabel 的项目级配置数据模型。

    字段：
        version      配置格式版本。以后格式升级时可据此做迁移。
        active_task  当前激活的任务类型。
        task_classes 每个任务各自拥有的类别列表。

    dataclass 会自动生成 __init__ / __repr__ 等样板代码，让“纯数据对象”更简洁。
    """

    version: int = 1
    active_task: str = "detection"

    # default_factory 使用 lambda，每创建一个 ProjectConfig 都会得到新的 dict。
    # 这避免多个项目对象共享同一个可变字典。
    task_classes: dict[str, list[str]] = field(default_factory=lambda: {
        "detection": [],
        "segmentation": [],
        "classification": [],
    })

    def __post_init__(self) -> None:
        """
        dataclass 完成 __init__ 后自动调用，用来做数据清洗和兼容保护。

        即使项目 JSON 被手工修改过，也尽量把它整理成程序期望的结构。
        """
        # 未知任务回退到 detection，避免后续代码访问不存在的任务。
        if self.active_task not in SUPPORTED_TASKS:
            self.active_task = "detection"

        for task in SUPPORTED_TASKS:
            # setdefault：若 task 不存在就插入 []，存在则直接返回原值。
            values = self.task_classes.setdefault(task, [])

            # 这一行同时完成三个动作：
            # 1. str(v).strip()：统一转成去除首尾空白的字符串；
            # 2. if ...：丢弃空字符串；
            # 3. dict.fromkeys(...)：利用字典 key 唯一性去重，并保持原顺序。
            self.task_classes[task] = list(
                dict.fromkeys(str(v).strip() for v in values if str(v).strip())
            )

    def classes_for(self, task: str | None = None) -> list[str]:
        """
        返回某个任务的类别列表。

        task=None 时使用 active_task。返回的是内部列表本身，因此调用方可以读取；
        新增类别建议使用 add_class()，这样能统一完成去空白和去重。
        """
        return self.task_classes.setdefault(task or self.active_task, [])

    def add_class(self, label: str, task: str | None = None) -> None:
        """向指定任务添加类别；空类别和重复类别都会被忽略。"""
        label = label.strip()
        if not label:
            return

        classes = self.classes_for(task)
        if label not in classes:
            classes.append(label)

    def to_dict(self) -> dict:
        """转换成 json.dumps() 可以直接序列化的普通字典。"""
        return {
            "version": self.version,
            "active_task": self.active_task,
            "task_classes": self.task_classes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ProjectConfig":
        """
        从 JSON 字典恢复 ProjectConfig。

        @classmethod 的第一个参数是 cls（类本身），因此可以写 cls(...) 创建对象。
        与写死 ProjectConfig(...) 相比，它对子类继承更友好。
        """
        if not isinstance(data, dict):
            raise ValueError("项目配置根节点必须是字典")

        return cls(
            version=int(data.get("version", 1)),
            active_task=str(data.get("active_task", "detection")),
            task_classes=dict(data.get("task_classes", {})),
        )


def project_path(folder: Path) -> Path:
    """根据项目图片文件夹计算配置文件的完整路径。"""
    return Path(folder) / PROJECT_FILENAME


def load_project(folder: Path) -> ProjectConfig:
    """
    从项目文件夹读取配置。

    配置文件不存在不是错误：说明这是第一次打开该目录，直接返回默认配置。
    JSON 语法错误等异常不在这里吞掉，交给 MainWindow 决定如何提示用户。
    """
    path = project_path(folder)
    if not path.exists():
        return ProjectConfig()

    data = json.loads(path.read_text(encoding="utf-8"))
    return ProjectConfig.from_dict(data)


def save_project(folder: Path, project: ProjectConfig) -> Path:
    """
    把项目配置安全写入磁盘，并返回最终配置路径。

    采用“临时文件 -> replace 正式文件”的方式：
        1. 先把完整 JSON 写到 .tmp；
        2. 写成功后一次性替换正式配置。

    这样比直接覆盖正式文件更安全：写到一半程序异常时，旧文件仍然完整。
    """
    path = project_path(folder)
    temp = path.with_suffix(path.suffix + ".tmp")

    # ensure_ascii=False：中文类别直接保存为中文，而不是 Unicode 转义；
    # indent=2：两空格缩进，方便人直接检查配置文件。
    temp.write_text(
        json.dumps(project.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temp.replace(path)
    return path
