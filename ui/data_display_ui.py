# ui/data_display_ui.py
#
# 文件功能说明:
# 该文件包含用于创建数据显示区域（包括图表）用户界面的函数。
#

from PyQt5.QtWidgets import QWidget, QGridLayout, QVBoxLayout
from PyQt5.QtCore import Qt
import pyqtgraph as pg

def create_data_display_area(parent):
    """创建数据显示区域，包含图表。"""
    data_display_area = QWidget() # 数据显示区域
    data_display_layout = QGridLayout(data_display_area) # 数据显示网格布局

    plot_widgets = [] # 图表控件列表
    data_lines = [] # 数据线条列表
    hover_texts = [] # 悬停文本列表

    for i in range(8): # 创建 8 个图表
        if i < 4:
            row = i
            col = 0
        else:
            row = i - 4
            col = 1

        plot_widget_container = QWidget() # 图表容器
        plot_layout = QVBoxLayout(plot_widget_container) # 图表容器布局
        plot_layout.setContentsMargins(10,10,10,10) # 设置边距

        plot_widget = pg.PlotWidget() # 创建 PlotWidget
        plot_widget.setBackground('w') # 设置背景颜色
        plot_widget.setTitle(f"CH{i+1}" if i < 4 else f"CH{i+1}") # 设置图表标题
        plot_widget.setLabel('left', '电压 (V)', color='#000000', size='12pt') # 设置左轴标签
        plot_widget.setLabel('bottom', '时间 (s)', color='#000000', size='12pt') # 设置底轴标签
        plot_widget.showGrid(x=False, y=False) # 显示网格
        plot_widget.setYRange(0, 3.3) # 设置 Y 轴范围
        plot_widget.getViewBox().setMouseEnabled(y=False) # 禁用 Y 轴鼠标交互
        plot_widget.getViewBox().setLimits(yMin=0, yMax=3.3, xMin=0) # 设置轴限制

        plot_widget.getAxis('left').setPen(color='#000000') # 设置左轴笔颜色
        plot_widget.getAxis('bottom').setPen(color='#000000') # 设置底轴笔颜色
        plot_widget.getAxis('left').setTextPen(color='#000000') # 设置左轴文本笔颜色
        plot_widget.getAxis('bottom').setTextPen(color='#000000') # 设置底轴文本笔颜色

        if (i < 3) or (i > 3 and i < 7):
            plot_widget.getAxis('bottom').setStyle(showValues=False) # 隐藏底轴值
            plot_widget.getAxis('bottom').setLabel('') # 清空底轴标签

        plot_widgets.append(plot_widget) # 添加图表到列表
        plot_layout.addWidget(plot_widget) # 添加图表到布局

        hover_text = pg.TextItem(anchor=(0,1)) # 创建悬停文本项
        plot_widget.addItem(hover_text) # 添加悬停文本项到图表
        hover_text.hide() # 默认隐藏
        plot_widget.hover_text_item = hover_text # 存储悬停文本项引用
        hover_texts.append(hover_text) # 添加悬停文本项到列表

        data_display_layout.addWidget(plot_widget_container, row, col) # 添加图表容器到数据显示布局

        # 将所有图表链接到第一个图表的 X 轴并连接信号
        if i > 0:
            plot_widget.setXLink(plot_widgets[0]) # 链接 X 轴
            # 连接视图范围改变信号以同步所有图表
            plot_widget.getViewBox().sigXRangeChanged.connect(
                lambda vb, rng, idx=i: parent.plot_manager.synchronize_x_ranges(vb, rng))

        data_line = plot_widget.plot([], [], pen=pg.mkPen(color=(i*30 % 255, i*50 % 255, i*70 % 255), width=2)) # 创建数据线条
        data_lines.append(data_line) # 添加数据线条到列表

    return {
        'data_display_area': data_display_area,
        'plot_widgets': plot_widgets,
        'data_lines': data_lines,
        'hover_texts': hover_texts
    }