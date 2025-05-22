# ui/utils.py
#
# 文件功能说明:
# 该文件包含用于 UI 组件的辅助函数。
#

from PyQt5.QtGui import QFont

# 获取字体的辅助函数
def get_font(point_size, bold=False):
    font = QFont()
    font.setPointSize(point_size)
    font.setBold(bold)
    return font