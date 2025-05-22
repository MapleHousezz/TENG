# ui/status_bar_ui.py
#
# 文件功能说明:
# 该文件包含用于创建状态栏用户界面的函数。
#

from PyQt5.QtWidgets import QStatusBar

def create_status_bar(parent):
    """创建状态栏。"""
    status_bar = QStatusBar() # 创建状态栏
    parent.setStatusBar(status_bar) # 设置主窗口的状态栏
    status_bar.showMessage("准备就绪") # 显示初始消息
    return status_bar # 返回状态栏控件