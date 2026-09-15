"""
VisionLabel 程序入口
"""
import faulthandler
import sys
import traceback
from datetime import datetime
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QMessageBox
from visionlabel.main_window import MainWindow

# 崩溃日志的位置（和 main.py 同目录）
CRASH_LOG = Path(__file__).parent / "crash.log"


def _install_crash_logging() -> None:
    """
    安装“黑匣子”：程序万一崩溃，把错误详情写进 crash.log 文件。

    为什么需要它：
        Qt 6 / PySide6 里，事件回调（点击按钮、按键等）中【未捕获的
        Python 异常】会导致程序直接终止 —— 用户看到的就是“闪退”，
        如果是双击启动的，连错误信息都看不到。
        装上这个钩子后，任何未捕获的异常都会：①写入 crash.log；
        ②弹出错误对话框。出了问题把 crash.log 发来即可定位。

    它由两部分组成：
    - sys.excepthook：接住所有“没被 try 捕获”的 Python 异常
    - faulthandler：  连更底层的崩溃（段错误等）也能留下记录
    """
    # faulthandler：把底层崩溃（C++ 层面的段错误等）也写进日志。
    # 以追加模式打开文件，多次崩溃的记录会累积
    log_file = open(CRASH_LOG, "a", encoding="utf-8")
    faulthandler.enable(log_file)

    def excepthook(exc_type, exc_value, exc_tb):
        """替换 Python 默认的异常处理：写日志 + 弹窗提示。"""
        text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        header = f"\n===== {datetime.now():%Y-%m-%d %H:%M:%S} 未捕获的异常 =====\n"
        try:
            with open(CRASH_LOG, "a", encoding="utf-8") as f:
                f.write(header + text)
        except OSError:
            pass  # 日志写不进去就算了，别在错误处理里再出错
        print(header + text, file=sys.stderr)  # 终端启动时也能看到

        # 弹窗告诉用户“出错了”，而不是无声闪退。
        # 注意：此时程序状态可能不稳定，弹窗用最小依赖的方式创建
        try:
            QMessageBox.critical(
                None, "程序遇到错误",
                "程序遇到了一个未处理的错误，详情已写入 crash.log。\n\n"
                f"{exc_type.__name__}: {exc_value}\n\n"
                "请把 crash.log 的内容发给开发者。",
            )
        except Exception:
            pass

    sys.excepthook = excepthook


def main() -> int:
    """创建应用、显示主窗口、进入事件循环，返回程序退出码。"""
    # QApplication 是 Qt 程序的“大管家”，负责管理事件循环、剪贴板、
    # 全局样式等。必须在创建任何窗口部件之前创建它。
    # sys.argv 是命令行参数，Qt 支持一些标准命令行选项，所以传给它。
    app = QApplication(sys.argv)

    # 装“黑匣子”要在创建窗口之前，这样启动期的异常也能被记录
    _install_crash_logging()

    # 应用元信息（会用在任务栏、系统“关于”等地方）
    app.setApplicationName("VisionLabel")
    app.setOrganizationName("VisionLabel")

    # 使用 Fusion 风格：Qt 自带的跨平台统一外观，
    # 保证软件在 Windows / macOS / Linux 上看起来基本一致。
    app.setStyle("Fusion")

    # 锁定浅色配色：Qt 6.5+ 默认会跟随操作系统的深/浅色模式，
    # 但我们的界面（深色画布 + 浅色面板）是按浅色系统设计稿来的，
    # 所以这里明确指定浅色，保证在任何系统设置下外观一致。
    # setColorScheme 是 Qt 6.8 新增的接口，低版本没有，做个兼容处理。
    try:
        app.styleHints().setColorScheme(Qt.ColorScheme.Light)
    except AttributeError:
        pass  # Qt 版本低于 6.8 时不支持，忽略即可

    # 显式指定中文字体：不指定时 Qt 会猜测系统默认字体，
    # 在某些环境下中文字符会显示成方块（豆腐块），指定后可避免。
    # 微软雅黑是 Windows 自带字体；本软件主要运行在 Windows 上。
    app.setFont(QFont("Microsoft YaHei", 9))

    # 创建主窗口并显示。窗口内部如何组装，见 visionlabel/main_window.py
    window = MainWindow()
    window.show()

    # app.exec() 启动“事件循环”：程序会一直停在这里，
    # 不断响应用户的点击、键盘输入等操作，直到窗口全部关闭才返回。
    return app.exec()


if __name__ == "__main__":
    # Python 惯用写法：只有“直接运行本文件”时才执行 main()；
    # 如果本文件被其他代码 import，则不会自动启动程序。
    sys.exit(main())
