# ui/pixel_map_ui.py
#
# 文件功能说明:
# 该文件包含用于创建像素映射和数字矩阵显示区域用户界面的函数。
#

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QLabel, QPushButton, QSizePolicy, QMessageBox, QFileDialog
from PyQt5.QtCore import Qt
from ui.utils import get_font
from PIL import Image
import datetime

def export_binary_image(pixel_labels, parent):
    """导出像素映射为二值 BMP 图像。"""
    binary_image = Image.new('1', (4, 4)) # 创建 4x4 二值图像
    pixels = binary_image.load() # 获取像素访问对象

    for row in range(4):
        for col in range(4):
            # 检查背景颜色以确定像素是否高亮
            color = pixel_labels[row][col].palette().color(pixel_labels[row][col].backgroundRole())
            # 假设 lightblue 是高亮颜色，检查其 RGB 值
            if color.red() == 173 and color.green() == 216 and color.blue() == 230: # lightblue 的 RGB
                 pixels[col, row] = 0 # 高亮显示为黑色
            else:
                 pixels[col, row] = 1 # 未高亮显示为白色


    # 生成带当前日期和时间的文件名
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S") # 获取时间戳
    filename = f'binary_image_{timestamp}.bmp' # 生成文件名
    binary_image.save(filename) # 保存图像
    QMessageBox.information(parent, "导出成功", f"二值图已导出为 {filename}") # 显示成功消息


def create_pixel_map_area(parent):
    """创建像素映射和数字矩阵显示区域。"""
    pixel_map_widget = QWidget() # 像素映射区域控件
    # 使用 QVBoxLayout 堆叠标题和网格
    main_pixel_layout = QVBoxLayout(pixel_map_widget) # 主垂直布局
    main_pixel_layout.setSpacing(5) # 设置间距
    main_pixel_layout.setContentsMargins(10, 10, 10, 10) # 设置边距

    # 添加像素映射标题
    pixel_map_title = QLabel("像素映射") # 像素映射标题
    pixel_map_title.setFont(get_font(18, bold=True)) # 设置字体
    pixel_map_title.setAlignment(Qt.AlignCenter) # 居中对齐
    main_pixel_layout.addWidget(pixel_map_title) # 添加标题

    # 创建像素网格布局
    pixel_map_layout = QGridLayout() # 网格布局
    pixel_map_layout.setSpacing(1) # 减小像素间距
    pixel_map_layout.setContentsMargins(0, 0, 0, 0) # 移除边距

    pixel_labels = [] # 像素标签列表
    for row in range(4):
        row_labels = []
        for col in range(4):
            label = QLabel() # 创建标签
            label.setStyleSheet("background-color: lightgray; border: none;") # 设置默认样式
            label.setAlignment(Qt.AlignCenter) # 居中对齐
            label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding) # 设置大小策略为扩展
            pixel_map_layout.addWidget(label, row, col) # 添加标签到布局
            row_labels.append(label) # 添加标签到行列表
        pixel_labels.append(row_labels) # 添加行列表到像素标签列表

    # 为行和列设置相等的伸展因子
    for i in range(4):
        pixel_map_layout.setRowStretch(i, 1)
        pixel_map_layout.setColumnStretch(i, 1)

    # 将像素网格布局添加到主 QVBoxLayout
    main_pixel_layout.addLayout(pixel_map_layout) # 添加布局

    # --- 数字矩阵显示 ---
    digital_matrix_title = QLabel("触摸时间 (s)") # 触摸时间标题
    digital_matrix_title.setFont(get_font(18, bold=True)) # 设置字体
    digital_matrix_title.setAlignment(Qt.AlignCenter) # 居中对齐
    main_pixel_layout.addWidget(digital_matrix_title) # 添加标题

    digital_matrix_layout = QGridLayout() # 数字矩阵网格布局
    digital_matrix_layout.setSpacing(5) # 设置间距
    digital_matrix_layout.setContentsMargins(0, 0, 0, 0) # 移除边距

    digital_matrix_labels = [] # 数字矩阵标签列表
    for row in range(4):
        row_labels = []
        for col in range(4):
            label = QLabel("0.000") # 默认文本
            label.setFixedSize(60, 30) # 根据需要调整大小
            label.setAlignment(Qt.AlignCenter) # 居中对齐
            label.setStyleSheet("border: 1px solid black;") # 添加边框以便可见
            label.setFont(get_font(10)) # 较小的字体用于数字
            row_labels.append(label) # 添加标签到行列表
            digital_matrix_layout.addWidget(label, row, col) # 添加标签到布局
        digital_matrix_labels.append(row_labels) # 添加行列表到数字矩阵标签列表

    main_pixel_layout.addLayout(digital_matrix_layout) # 添加数字矩阵布局

    # 添加导出按钮
    export_button = QPushButton("导出二值图") # 导出二值图按钮
    export_button.setFont(get_font(14)) # 设置字体
    export_button.setMinimumHeight(48) # 设置最小高度
    export_button.clicked.connect(lambda: export_binary_image(pixel_labels, parent)) # 连接点击信号，传递 parent

    clear_map_button = QPushButton("清空映射") # 清空映射按钮
    clear_map_button.setFont(get_font(14)) # 设置字体
    clear_map_button.setMinimumHeight(48) # 设置最小高度
    clear_map_button.clicked.connect(lambda: parent.clear_pixel_map()) # 连接点击信号

    main_pixel_layout.addWidget(export_button) # 添加导出按钮
    main_pixel_layout.addWidget(clear_map_button) # 添加清空按钮
    main_pixel_layout.addStretch() # 添加伸展空间将网格推到顶部

    pixel_map_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)  # 允许根据布局空间调整大小
    return {'pixel_map_widget': pixel_map_widget, 'pixel_labels': pixel_labels, 'export_button': export_button, 'clear_map_button': clear_map_button, 'digital_matrix_labels': digital_matrix_labels} # 返回相关控件和标签