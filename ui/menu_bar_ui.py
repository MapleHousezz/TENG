# ui/menu_bar_ui.py
#
# 文件功能说明:
# 该文件包含用于创建菜单栏用户界面的函数。
#

from PyQt5.QtWidgets import QMenuBar, QMenu, QAction

def create_menu_bar(parent):
    """创建菜单栏。"""
    menu_bar = parent.menuBar() # 获取菜单栏
    file_menu = menu_bar.addMenu("文件") # 添加文件菜单

    exit_action = QAction("退出", parent) # 创建退出动作
    exit_action.triggered.connect(parent.close) # 连接退出信号
    file_menu.addAction(exit_action) # 添加退出动作到菜单

    about_action = QAction("关于", parent) # 创建关于动作
    file_menu.addAction(about_action) # 添加关于动作到菜单

    return {'exit_action': exit_action, 'about_action': about_action} # 返回动作字典