from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton, QComboBox, QStatusBar, QMenuBar, QMenu, QAction, QMessageBox, QFileDialog
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
import pyqtgraph as pg
import serial.tools.list_ports # Needed for populate_serial_ports

# Helper function to get font
def get_font(point_size, bold=False):
    font = QFont()
    font.setPointSize(point_size)
    font.setBold(bold)
    return font

def create_control_panel(parent):
    control_panel = QWidget()
    control_layout = QVBoxLayout(control_panel)
    control_panel.setFixedWidth(400)
    control_layout.setSpacing(15)
    control_layout.setContentsMargins(15, 15, 15, 15)

    label_font = get_font(14)
    button_font = get_font(14)

    # --- 实时电压显示区域 ---
    voltage_display_group = QWidget()
    voltage_display_group_layout = QVBoxLayout(voltage_display_group)

    voltage_title = QLabel("实时电压值")
    voltage_title.setFont(get_font(18, bold=True))
    voltage_display_group_layout.addWidget(voltage_title)

    voltage_labels = []
    for i in range(8):
        label = QLabel(f"CH{i+1}: 0.000 V")
        color = f"color: rgb({i*30 % 255}, {i*50 % 255}, {i*70 % 255})"
        label.setStyleSheet(f"font-family: Consolas, Courier New, monospace; font-size: 14pt; {color}")
        voltage_display_group_layout.addWidget(label)
        voltage_labels.append(label)
    voltage_display_group_layout.addStretch()
    control_layout.addWidget(voltage_display_group)

    # --- 协议与连接 ---
    protocol_connection_label = QLabel("协议与连接")
    protocol_connection_label.setFont(get_font(18, bold=True))
    control_layout.addWidget(protocol_connection_label)

    # --- 数据引擎 ---
    data_engine_layout = QHBoxLayout()
    data_engine_label = QLabel("数据引擎")
    data_engine_label.setFont(label_font)
    data_engine_combo = QComboBox()
    data_engine_combo.addItems(["JustFloat"])
    data_engine_combo.setCurrentText("JustFloat")
    data_engine_combo.setFont(label_font)
    data_engine_combo.setMinimumHeight(40)
    data_engine_layout.addWidget(data_engine_label)
    data_engine_layout.addStretch()
    data_engine_layout.addWidget(data_engine_combo)
    control_layout.addLayout(data_engine_layout)

    # --- 数据接口 ---
    data_interface_layout = QHBoxLayout()
    data_interface_label = QLabel("数据接口")
    data_interface_label.setFont(label_font)
    data_interface_combo = QComboBox()
    data_interface_combo.addItems(["串口"])
    data_interface_combo.setCurrentText("串口")
    data_interface_combo.setFont(label_font)
    data_interface_combo.setMinimumHeight(40)
    data_interface_layout.addWidget(data_interface_label)
    data_interface_layout.addStretch()
    data_interface_layout.addWidget(data_interface_combo)
    control_layout.addLayout(data_interface_layout)

    # --- 串口参数配置 ---
    serial_params_label = QLabel("串口参数配置")
    serial_params_label.setFont(get_font(16, bold=True))
    serial_params_label.setStyleSheet("color: #1E90FF;")
    control_layout.addWidget(serial_params_label)

    serial_group = QWidget()
    serial_layout = QGridLayout(serial_group)
    serial_layout.setSpacing(8)

    port_label = QLabel("端口号")
    port_label.setFont(label_font)
    serial_layout.addWidget(port_label, 0, 0)
    port_combo = QComboBox()
    port_combo.setFont(label_font)
    port_combo.setMinimumHeight(40)
    serial_layout.addWidget(port_combo, 0, 1)

    baud_label = QLabel("波特率")
    baud_label.setFont(label_font)
    serial_layout.addWidget(baud_label, 2, 0)
    baud_combo = QComboBox()
    baud_combo.addItems(["9600", "19200", "38400", "57600", "115200"])
    baud_combo.setCurrentText("115200")
    baud_combo.setFont(label_font)
    baud_combo.setMinimumHeight(40)
    serial_layout.addWidget(baud_combo, 2, 1)

    flow_control_label = QLabel("数据流控")
    flow_control_label.setFont(label_font)
    serial_layout.addWidget(flow_control_label, 3, 0)
    flow_control_combo = QComboBox()
    flow_control_combo.addItems(["None", "RTS/CTS", "XON/XOFF"])
    flow_control_combo.setCurrentText("None")
    flow_control_combo.setFont(label_font)
    flow_control_combo.setMinimumHeight(40)
    serial_layout.addWidget(flow_control_combo, 3, 1)

    parity_label = QLabel("校验位")
    parity_label.setFont(label_font)
    serial_layout.addWidget(parity_label, 4, 0)
    parity_combo = QComboBox()
    parity_combo.addItems(["None", "Even", "Odd", "Mark", "Space"])
    parity_combo.setCurrentText("None")
    parity_combo.setFont(label_font)
    parity_combo.setMinimumHeight(40)
    serial_layout.addWidget(parity_combo, 4, 1)

    databits_label = QLabel("数据位数")
    databits_label.setFont(label_font)
    serial_layout.addWidget(databits_label, 5, 0)
    databits_combo = QComboBox()
    databits_combo.addItems(["5", "6", "7", "8"])
    databits_combo.setCurrentText("8")
    databits_combo.setFont(label_font)
    databits_combo.setMinimumHeight(40)
    serial_layout.addWidget(databits_combo, 5, 1)

    stopbits_label = QLabel("停止位数")
    stopbits_label.setFont(label_font)
    serial_layout.addWidget(stopbits_label, 6, 0)
    stopbits_combo = QComboBox()
    stopbits_combo.addItems(["1", "1.5", "2"])
    stopbits_combo.setCurrentText("1")
    stopbits_combo.setFont(label_font)
    stopbits_combo.setMinimumHeight(40)
    serial_layout.addWidget(stopbits_combo, 6, 1)

    control_layout.addWidget(serial_group)

    # --- 操作按钮区域 ---
    action_buttons_layout = QGridLayout()

    connect_button = QPushButton("连接")
    connect_button.setFont(button_font)
    connect_button.setMinimumHeight(48)
    action_buttons_layout.addWidget(connect_button, 0, 0)

    disconnect_button = QPushButton("断开")
    disconnect_button.setFont(button_font)
    disconnect_button.setMinimumHeight(48)
    disconnect_button.setEnabled(False)
    action_buttons_layout.addWidget(disconnect_button, 0, 1)

    test_data_button = QPushButton("生成测试数据")
    test_data_button.setFont(button_font)
    test_data_button.setMinimumHeight(48)
    action_buttons_layout.addWidget(test_data_button, 1, 0, 1, 2)

    reset_view_button = QPushButton("复位图表")
    reset_view_button.setFont(button_font)
    reset_view_button.setMinimumHeight(48)
    action_buttons_layout.addWidget(reset_view_button, 2, 0)

    clear_data_button = QPushButton("清空数据")
    clear_data_button.setFont(button_font)
    clear_data_button.setMinimumHeight(48)
    action_buttons_layout.addWidget(clear_data_button, 2, 1)

    export_data_button = QPushButton("导出数据")
    export_data_button.setFont(button_font)
    export_data_button.setMinimumHeight(48)
    action_buttons_layout.addWidget(export_data_button, 3, 0, 1, 2)

    control_layout.addLayout(action_buttons_layout)
    control_layout.addStretch()

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
        'export_data_button': export_data_button
    }

def create_data_display_area(parent):
    data_display_area = QWidget()
    data_display_layout = QGridLayout(data_display_area)

    plot_widgets = []
    data_lines = []
    hover_texts = []

    for i in range(8):
        # 4行2列布局：左边通道1-4 (i=0..3)，右边通道5-8 (i=4..7)
        if i < 4:
            row = i
            col = 0
        else:
            row = i - 4
            col = 1

        plot_widget_container = QWidget()
        plot_layout = QVBoxLayout(plot_widget_container)
        plot_layout.setContentsMargins(10,10,10,10)

        plot_widget = pg.PlotWidget()
        plot_widget.setBackground('w')
        plot_widget.setTitle(f"CH{i+1}" if i < 4 else f"CH{i+1}")
        plot_widget.setLabel('left', '电压 (V)', color='#000000', size='12pt')
        plot_widget.setLabel('bottom', '时间 (s)', color='#000000', size='12pt') # Changed label
        plot_widget.showGrid(x=False, y=False)  # 移除栅格线
        plot_widget.setYRange(0, 3.3) # 电压范围 0-3.3V
        plot_widget.getViewBox().setMouseEnabled(y=False) # 禁用Y轴缩放
        plot_widget.getViewBox().setLimits(yMin=0, yMax=3.3, xMin=0) # Added xMin=0 limit

        # 设置坐标轴刻度颜色
        plot_widget.getAxis('left').setPen(color='#000000')
        plot_widget.getAxis('bottom').setPen(color='#000000')
        plot_widget.getAxis('left').setTextPen(color='#000000')
        plot_widget.getAxis('bottom').setTextPen(color='#000000')

        # 只在底部图表显示X轴标签
        if (i < 3) or (i > 3 and i < 7):
            plot_widget.getAxis('bottom').setStyle(showValues=False)
            plot_widget.getAxis('bottom').setLabel('')

        plot_widgets.append(plot_widget)
        plot_layout.addWidget(plot_widget)

        # Connect sigXRangeChanged for synchronization (This connection needs to be in MainWindow)
        # plot_widget.getViewBox().sigXRangeChanged.connect(parent._synchronize_x_ranges)

        # 创建用于显示悬停信息的TextItem
        hover_text = pg.TextItem(anchor=(0,1))
        plot_widget.addItem(hover_text)
        hover_text.hide()
        # 将hover_text与plot_widget关联，方便后续查找
        plot_widget.hover_text_item = hover_text
        hover_texts.append(hover_text)

        # 连接鼠标移动事件 (This connection needs to be in MainWindow)
        # plot_widget.scene().sigMouseMoved.connect(lambda pos, pw=plot_widget, idx=i: parent._mouse_moved_on_plot(pos, pw, idx))

        data_display_layout.addWidget(plot_widget_container, row, col)

        # 初始化数据线
        data_line = plot_widget.plot([], [], pen=pg.mkPen(color=(i*30 % 255, i*50 % 255, i*70 % 255), width=2))
        data_lines.append(data_line)

    return {
        'data_display_area': data_display_area,
        'plot_widgets': plot_widgets,
        'data_lines': data_lines,
        'hover_texts': hover_texts
    }

def create_menu_bar(parent):
    menu_bar = parent.menuBar()
    file_menu = menu_bar.addMenu("文件")

    exit_action = QAction("退出", parent)
    exit_action.triggered.connect(parent.close)
    file_menu.addAction(exit_action)

    # Add About action
    about_action = QAction("关于", parent)
    file_menu.addAction(about_action)

    return {'exit_action': exit_action, 'about_action': about_action}

def create_status_bar(parent):
    status_bar = QStatusBar()
    parent.setStatusBar(status_bar)
    status_bar.showMessage("准备就绪")
    return status_bar

def populate_serial_ports(port_combo):
    ports = serial.tools.list_ports.comports()
    port_combo.clear()
    for port in ports:
        port_combo.addItem(port.device)
    if not ports:
        port_combo.addItem("无可用串口")
        port_combo.setEnabled(False) # Disable combo box if no ports
    else:
        port_combo.setEnabled(True) # Enable combo box if ports are found