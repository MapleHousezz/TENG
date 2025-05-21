# ui_components.py
#
# 文件功能说明:
# 该文件包含用于构建主窗口用户界面的各种组件函数。
# 它定义了创建控制面板、数据显示区域（包括图表）、菜单栏、状态栏和像素映射区域的函数。
# 这些函数返回创建的 Qt 控件和布局，供主窗口类使用。
#

from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton, QComboBox, QSpinBox, QStatusBar, QMenuBar, QMenu, QAction, QMessageBox, QFileDialog, QSizePolicy
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
import pyqtgraph as pg
import serial.tools.list_ports # populate_serial_ports 函数需要
import datetime # 导入 datetime

# 获取字体的辅助函数
def get_font(point_size, bold=False):
    font = QFont()
    font.setPointSize(point_size)
    font.setBold(bold)
    return font

def create_control_panel(parent):
    """创建控制面板区域。"""
    control_panel = QWidget()
    control_layout = QVBoxLayout(control_panel)
    control_panel.setFixedWidth(400) # 设置固定宽度
    control_layout.setSpacing(15) # 设置控件间距
    control_layout.setContentsMargins(15, 15, 15, 15) # 设置边距

    label_font = get_font(14) # 标签字体
    button_font = get_font(14) # 按钮字体

    # --- 实时电压显示区域 ---
    voltage_display_group = QWidget()
    voltage_display_group_layout = QVBoxLayout(voltage_display_group)

    voltage_title = QLabel("实时电压值") # 实时电压值标题
    voltage_title.setFont(get_font(18, bold=True)) # 设置标题字体
    voltage_display_group_layout.addWidget(voltage_title) # 添加标题

    voltage_labels = [] # 电压标签列表
    for i in range(8):
        label = QLabel(f"CH{i+1}: 0.000 V") # 创建通道标签
        color = f"color: rgb({i*30 % 255}, {i*50 % 255}, {i*70 % 255})" # 根据通道索引设置颜色
        label.setStyleSheet(f"font-family: Consolas, Courier New, monospace; font-size: 14pt; {color}") # 设置样式
        voltage_display_group_layout.addWidget(label) # 添加标签
        voltage_labels.append(label) # 将标签添加到列表
    voltage_display_group_layout.addStretch() # 添加伸展空间
    control_layout.addWidget(voltage_display_group) # 添加电压显示组

    # --- 协议与连接 ---
    protocol_connection_label = QLabel("协议与连接") # 协议与连接标签
    protocol_connection_label.setFont(get_font(18, bold=True)) # 设置字体
    test_data_control_label = QLabel("测试数据控制") # 测试数据控制标签
    test_data_control_label.setFont(get_font(18, bold=True)) # 设置字体
    control_layout.addWidget(test_data_control_label) # 添加测试数据控制标签

    frequency_label = QLabel("频率 (Hz)") # 频率标签
    frequency_label.setFont(label_font) # 设置字体
    frequency_spinbox = QSpinBox() # 频率微调框
    frequency_spinbox.setRange(1, 1000) # 设置范围
    frequency_spinbox.setValue(1) # 设置默认值
    frequency_spinbox.setFont(label_font) # 设置字体
    frequency_spinbox.setMinimumHeight(40) # 设置最小高度
    control_layout.addWidget(frequency_label) # 添加频率标签
    control_layout.addWidget(frequency_spinbox) # 添加频率微调框

    # --- 测试数据持续时间 --- #
    duration_label = QLabel("持续时间 (秒)") # 持续时间标签
    duration_label.setFont(label_font) # 设置字体
    duration_spinbox = QSpinBox() # 持续时间微调框
    duration_spinbox.setRange(1, 3600) # 设置范围 (1秒到1小时)
    duration_spinbox.setValue(10) # 设置默认值
    duration_spinbox.setFont(label_font) # 设置字体
    duration_spinbox.setMinimumHeight(40) # 设置最小高度
    control_layout.addWidget(duration_label) # 添加持续时间标签
    control_layout.addWidget(duration_spinbox) # 添加持续时间微调框

    control_layout.addWidget(protocol_connection_label) # 添加协议与连接标签

    # --- 数据引擎 ---
    data_engine_layout = QHBoxLayout() # 数据引擎水平布局
    data_engine_label = QLabel("数据引擎") # 数据引擎标签
    data_engine_label.setFont(label_font) # 设置字体
    data_engine_combo = QComboBox() # 数据引擎下拉框
    data_engine_combo.addItems(["JustFloat"]) # 添加选项
    data_engine_combo.setCurrentText("JustFloat") # 设置当前文本
    data_engine_combo.setFont(label_font) # 设置字体

    data_engine_combo.setMinimumHeight(40) # 设置最小高度
    data_engine_layout.addWidget(data_engine_label) # 添加标签
    data_engine_layout.addStretch() # 添加伸展空间
    data_engine_layout.addWidget(data_engine_combo) # 添加下拉框
    control_layout.addLayout(data_engine_layout) # 添加布局

    # --- 数据接口 ---
    data_interface_layout = QHBoxLayout() # 数据接口水平布局
    data_interface_label = QLabel("数据接口") # 数据接口标签
    data_interface_label.setFont(label_font) # 设置字体
    data_interface_combo = QComboBox() # 数据接口下拉框
    data_interface_combo.addItems(["串口"]) # 添加选项
    data_interface_combo.setCurrentText("串口") # 设置当前文本
    data_interface_combo.setFont(label_font) # 设置字体
    data_interface_combo.setMinimumHeight(40) # 设置最小高度
    data_interface_layout.addWidget(data_interface_label) # 添加标签
    data_interface_layout.addStretch() # 添加伸展空间
    data_interface_layout.addWidget(data_interface_combo) # 添加下拉框
    control_layout.addLayout(data_interface_layout) # 添加布局

    # --- 串口参数配置 ---
    serial_params_label = QLabel("串口参数配置") # 串口参数配置标签
    serial_params_label.setFont(get_font(16, bold=True)) # 设置字体
    serial_params_label.setStyleSheet("color: #1E90FF;") # 设置样式
    control_layout.addWidget(serial_params_label) # 添加标签


    serial_group = QWidget() # 串口参数分组
    serial_layout = QGridLayout(serial_group) # 串口参数网格布局
    serial_layout.setSpacing(8) # 设置间距

    port_label = QLabel("端口号") # 端口号标签
    port_label.setFont(label_font) # 设置字体
    serial_layout.addWidget(port_label, 0, 0) # 添加标签到布局
    port_combo = QComboBox() # 端口号下拉框
    port_combo.setFont(label_font) # 设置字体
    port_combo.setMinimumHeight(40) # 设置最小高度
    serial_layout.addWidget(port_combo, 0, 1) # 添加下拉框到布局

    baud_label = QLabel("波特率") # 波特率标签
    baud_label.setFont(label_font) # 设置字体
    serial_layout.addWidget(baud_label, 2, 0) # 添加标签到布局
    baud_combo = QComboBox() # 波特率下拉框
    baud_combo.addItems(["9600", "19200", "38400", "57600", "115200"]) # 添加选项
    baud_combo.setCurrentText("115200") # 设置当前文本
    baud_combo.setFont(label_font) # 设置字体
    baud_combo.setMinimumHeight(40) # 设置最小高度
    serial_layout.addWidget(baud_combo, 2, 1) # 添加下拉框到布局

    flow_control_label = QLabel("数据流控") # 数据流控标签
    flow_control_label.setFont(label_font) # 设置字体
    serial_layout.addWidget(flow_control_label, 3, 0) # 添加标签到布局
    flow_control_combo = QComboBox() # 数据流控下拉框
    flow_control_combo.addItems(["None", "RTS/CTS", "XON/XOFF"]) # 添加选项

    flow_control_combo.setCurrentText("None") # 设置当前文本
    flow_control_combo.setFont(label_font) # 设置字体
    flow_control_combo.setMinimumHeight(40) # 设置最小高度
    serial_layout.addWidget(flow_control_combo, 3, 1) # 添加下拉框到布局

    parity_label = QLabel("校验位") # 校验位标签
    parity_label.setFont(label_font) # 设置字体
    serial_layout.addWidget(parity_label, 4, 0) # 添加标签到布局
    parity_combo = QComboBox() # 校验位下拉框
    parity_combo.addItems(["None", "Even", "Odd", "Mark", "Space"]) # 添加选项
    parity_combo.setCurrentText("None") # 设置当前文本
    parity_combo.setFont(label_font) # 设置字体
    parity_combo.setMinimumHeight(40) # 设置最小高度
    serial_layout.addWidget(parity_combo, 4, 1) # 添加下拉框到布局

    databits_label = QLabel("数据位数") # 数据位数标签
    databits_label.setFont(label_font) # 设置字体
    serial_layout.addWidget(databits_label, 5, 0) # 添加标签到布局
    databits_combo = QComboBox() # 数据位数下拉框
    databits_combo.addItems(["5", "6", "7", "8"]) # 添加选项
    databits_combo.setCurrentText("8") # 设置当前文本
    databits_combo.setFont(label_font) # 设置字体
    databits_combo.setMinimumHeight(40) # 设置最小高度
    serial_layout.addWidget(databits_combo, 5, 1) # 添加下拉框到布局

    stopbits_label = QLabel("停止位数") # 停止位数标签

    stopbits_label.setFont(label_font) # 设置字体
    serial_layout.addWidget(stopbits_label, 6, 0) # 添加标签到布局
    stopbits_combo = QComboBox() # 停止位数下拉框
    stopbits_combo.addItems(["1", "1.5", "2"]) # 添加选项
    stopbits_combo.setCurrentText("1") # 设置当前文本
    stopbits_combo.setFont(label_font) # 设置字体
    stopbits_combo.setMinimumHeight(40) # 设置最小高度
    serial_layout.addWidget(stopbits_combo, 6, 1) # 添加下拉框到布局

    control_layout.addWidget(serial_group) # 添加串口参数分组

    # --- 操作按钮区域 ---
    action_buttons_layout = QGridLayout() # 操作按钮网格布局

    connect_button = QPushButton("连接") # 连接按钮
    connect_button.setFont(button_font) # 设置字体
    connect_button.setMinimumHeight(48) # 设置最小高度
    action_buttons_layout.addWidget(connect_button, 0, 0) # 添加按钮到布局

    disconnect_button = QPushButton("断开") # 断开按钮
    disconnect_button.setFont(button_font) # 设置字体
    disconnect_button.setMinimumHeight(48) # 设置最小高度
    disconnect_button.setEnabled(False) # 默认禁用
    action_buttons_layout.addWidget(disconnect_button, 0, 1) # 添加按钮到布局

    test_data_button = QPushButton("生成测试数据") # 生成测试数据按钮
    test_data_button.setFont(button_font) # 设置字体
    test_data_button.setMinimumHeight(48) # 设置最小高度

    action_buttons_layout.addWidget(test_data_button, 1, 0, 1, 2) # 添加按钮到布局，跨两列

    reset_view_button = QPushButton("复位图表") # 复位图表按钮
    reset_view_button.setFont(button_font) # 设置字体
    reset_view_button.setMinimumHeight(48) # 设置最小高度
    action_buttons_layout.addWidget(reset_view_button, 2, 0) # 添加按钮到布局

    clear_data_button = QPushButton("清空数据") # 清空数据按钮
    clear_data_button.setFont(button_font) # 设置字体
    clear_data_button.setMinimumHeight(48) # 设置最小高度
    action_buttons_layout.addWidget(clear_data_button, 2, 1) # 添加按钮到布局

    export_data_button = QPushButton("导出数据") # 导出数据按钮
    export_data_button.setFont(button_font) # 设置字体
    export_data_button.setMinimumHeight(48) # 设置最小高度
    action_buttons_layout.addWidget(export_data_button, 3, 0, 1, 2) # 添加按钮到布局，跨两列

    control_layout.addLayout(action_buttons_layout) # 添加操作按钮布局
    control_layout.addStretch() # 添加伸展空间

    return {
        'control_panel': control_panel,
        'voltage_labels': voltage_labels,
        'data_engine_combo': data_engine_combo,
        'data_interface_combo': data_interface_combo,
        'port_combo': port_combo,
        'baud_combo': baud_combo,
        'flow_control_combo': flow_control_combo,
        'parity_combo': parity_combo,
        'databits_combo': databits_combo,
        'stopbits_combo': stopbits_combo,
        'connect_button': connect_button,
        'disconnect_button': disconnect_button,
        'test_data_button': test_data_button,
        'reset_view_button': reset_view_button,
        'clear_data_button': clear_data_button,
        'export_data_button': export_data_button,
        'frequency_spinbox': frequency_spinbox, # 添加频率微调框
        'duration_spinbox': duration_spinbox, # 添加持续时间微调框
    }

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

def create_status_bar(parent):
    """创建状态栏。"""
    status_bar = QStatusBar() # 创建状态栏
    parent.setStatusBar(status_bar) # 设置主窗口的状态栏
    status_bar.showMessage("准备就绪") # 显示初始消息
    return status_bar # 返回状态栏控件

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
    export_button.clicked.connect(lambda: export_binary_image(pixel_labels)) # 连接点击信号

    clear_map_button = QPushButton("清空映射") # 清空映射按钮
    clear_map_button.setFont(get_font(14)) # 设置字体
    clear_map_button.setMinimumHeight(48) # 设置最小高度
    clear_map_button.clicked.connect(lambda: parent.clear_pixel_map()) # 连接点击信号

    main_pixel_layout.addWidget(export_button) # 添加导出按钮
    main_pixel_layout.addWidget(clear_map_button) # 添加清空按钮
    main_pixel_layout.addStretch() # 添加伸展空间将网格推到顶部

    def export_binary_image(pixel_labels):
        """导出像素映射为二值 BMP 图像。"""
        from PIL import Image
        import datetime # 导入 datetime

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

    pixel_map_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)  # 允许根据布局空间调整大小
    return {'pixel_map_widget': pixel_map_widget, 'pixel_labels': pixel_labels, 'export_button': export_button, 'clear_map_button': clear_map_button, 'digital_matrix_labels': digital_matrix_labels} # 返回相关控件和标签

def populate_serial_ports(port_combo):
    """填充可用串口到下拉框。"""
    ports = serial.tools.list_ports.comports() # 获取可用串口列表
    port_combo.clear() # 清空下拉框
    for port in ports:
        port_combo.addItem(port.device) # 添加串口设备名称
    if not ports:
        port_combo.addItem("无可用串口") # 如果没有可用串口，显示提示
        port_combo.setEnabled(False) # 禁用下拉框
    else:
        port_combo.setEnabled(True) # 启用下拉框