# ui/control_panel_ui.py
#
# 文件功能说明:
# 该文件包含用于创建控制面板用户界面的函数。
#

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton, QComboBox, QSpinBox
from ui.utils import get_font

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