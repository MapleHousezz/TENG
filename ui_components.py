from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton, QComboBox, QSpinBox, QStatusBar, QMenuBar, QMenu, QAction, QMessageBox, QFileDialog, QSizePolicy
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
import pyqtgraph as pg
import serial.tools.list_ports # Needed for populate_serial_ports
import datetime # Import datetime

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
    test_data_control_label = QLabel("测试数据控制")
    test_data_control_label.setFont(get_font(18, bold=True))
    control_layout.addWidget(test_data_control_label)

    frequency_label = QLabel("频率 (Hz)") # Change label to Hz
    frequency_label.setFont(label_font)
    frequency_spinbox = QSpinBox()
    frequency_spinbox.setRange(1, 1000) # Keep range for now, assuming up to 1000Hz is possible
    frequency_spinbox.setValue(1) # Default to 1 Hz
    frequency_spinbox.setFont(label_font)
    frequency_spinbox.setMinimumHeight(40)
    control_layout.addWidget(frequency_label)
    control_layout.addWidget(frequency_spinbox)

    points_label = QLabel("点数")
    points_label.setFont(label_font)
    points_spinbox = QSpinBox()
    points_spinbox.setRange(1, 100)
    points_spinbox.setValue(10)
    points_spinbox.setFont(label_font)
    points_spinbox.setMinimumHeight(40)
    control_layout.addWidget(points_label)
    control_layout.addWidget(points_spinbox)

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
        'export_data_button': export_data_button,
        'frequency_spinbox': frequency_spinbox, # Add frequency spinbox
        'points_spinbox': points_spinbox # Add points spinbox
    }

def create_data_display_area(parent):
    data_display_area = QWidget()
    data_display_layout = QGridLayout(data_display_area)

    plot_widgets = []
    data_lines = []
    hover_texts = []

    for i in range(8):
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
        plot_widget.setLabel('bottom', '时间 (s)', color='#000000', size='12pt')
        plot_widget.showGrid(x=False, y=False)
        plot_widget.setYRange(0, 3.3)
        plot_widget.getViewBox().setMouseEnabled(y=False)
        plot_widget.getViewBox().setLimits(yMin=0, yMax=3.3, xMin=0)

        plot_widget.getAxis('left').setPen(color='#000000')
        plot_widget.getAxis('bottom').setPen(color='#000000')
        plot_widget.getAxis('left').setTextPen(color='#000000')
        plot_widget.getAxis('bottom').setTextPen(color='#000000')

        if (i < 3) or (i > 3 and i < 7):
            plot_widget.getAxis('bottom').setStyle(showValues=False)
            plot_widget.getAxis('bottom').setLabel('')

        plot_widgets.append(plot_widget)
        plot_layout.addWidget(plot_widget)

        hover_text = pg.TextItem(anchor=(0,1))
        plot_widget.addItem(hover_text)
        hover_text.hide()
        plot_widget.hover_text_item = hover_text
        hover_texts.append(hover_text)

        data_display_layout.addWidget(plot_widget_container, row, col)

        # Link all plots to first plot's X axis and connect signals
        if i > 0:
            plot_widget.setXLink(plot_widgets[0])
            # Connect view range changed signal to synchronize all plots
            plot_widget.getViewBox().sigXRangeChanged.connect(
                lambda vb, rng, idx=i: parent.plot_manager._synchronize_x_ranges(vb, rng))

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

    about_action = QAction("关于", parent)
    file_menu.addAction(about_action)

    return {'exit_action': exit_action, 'about_action': about_action}
def create_status_bar(parent):
    status_bar = QStatusBar()
    parent.setStatusBar(status_bar)
    status_bar.showMessage("准备就绪")
    return status_bar

def create_pixel_map_area(parent):
    pixel_map_widget = QWidget()
    # Use QVBoxLayout to stack title and grid
    main_pixel_layout = QVBoxLayout(pixel_map_widget)
    main_pixel_layout.setSpacing(5)
    main_pixel_layout.setContentsMargins(10, 10, 10, 10)

    # Add title for the pixel map
    pixel_map_title = QLabel("像素映射")
    pixel_map_title.setFont(get_font(18, bold=True))
    pixel_map_title.setAlignment(Qt.AlignCenter)
    main_pixel_layout.addWidget(pixel_map_title)

    # Create the grid layout for pixels
    pixel_map_layout = QGridLayout() # <-- Changed
    pixel_map_layout.setSpacing(1) # Reduce spacing between pixels
    pixel_map_layout.setContentsMargins(0, 0, 0, 0) # Remove margins

    pixel_labels = []
    for row in range(4):
        row_labels = []
        for col in range(4):
            label = QLabel()
            label.setStyleSheet("background-color: lightgray; border: none;")
            label.setAlignment(Qt.AlignCenter)
            label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding) # Set size policy to expanding
            pixel_map_layout.addWidget(label, row, col)
            row_labels.append(label)
        pixel_labels.append(row_labels)

    # Set equal stretch factors for rows and columns
    for i in range(4):
        pixel_map_layout.setRowStretch(i, 1)
        pixel_map_layout.setColumnStretch(i, 1)

    # Add the pixel grid layout to the main QVBoxLayout
    main_pixel_layout.addLayout(pixel_map_layout) # <-- Added

    # --- Digital Matrix Display ---
    digital_matrix_title = QLabel("触摸时间 (s)")
    digital_matrix_title.setFont(get_font(18, bold=True))
    digital_matrix_title.setAlignment(Qt.AlignCenter)
    main_pixel_layout.addWidget(digital_matrix_title)

    digital_matrix_layout = QGridLayout()
    digital_matrix_layout.setSpacing(5)
    digital_matrix_layout.setContentsMargins(0, 0, 0, 0)

    digital_matrix_labels = []
    for row in range(4):
        row_labels = []
        for col in range(4):
            label = QLabel("0.000") # Default text
            label.setFixedSize(60, 30) # Adjust size as needed
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("border: 1px solid black;") # Add border for visibility
            label.setFont(get_font(10)) # Smaller font for numbers
            row_labels.append(label)
            digital_matrix_layout.addWidget(label, row, col)
        digital_matrix_labels.append(row_labels)

    main_pixel_layout.addLayout(digital_matrix_layout)


    # Add export button
    export_button = QPushButton("导出二值图")
    export_button.setFont(get_font(14))
    export_button.setMinimumHeight(48)
    export_button.clicked.connect(lambda: export_binary_image(pixel_labels))

    clear_map_button = QPushButton("清空映射")
    clear_map_button.setFont(get_font(14))
    clear_map_button.setMinimumHeight(48)
    clear_map_button.clicked.connect(lambda: parent.clear_pixel_map())

    main_pixel_layout.addWidget(export_button)
    main_pixel_layout.addWidget(clear_map_button)
    main_pixel_layout.addStretch() # Add stretch to push grid to top

    def export_binary_image(pixel_labels):
        from PIL import Image
        import datetime # Import datetime

        binary_image = Image.new('1', (4, 4))
        pixels = binary_image.load()

        for row in range(4):
            for col in range(4):
                # Check the background color to determine if the pixel is highlighted
                color = pixel_labels[row][col].palette().color(pixel_labels[row][col].backgroundRole())
                # Assuming lightblue is the highlighted color, check its RGB values
                if color.red() == 173 and color.green() == 216 and color.blue() == 230: # RGB for lightblue
                     pixels[col, row] = 0 # Black for highlighted
                else:
                     pixels[col, row] = 1 # White for not highlighted


        # Generate filename with current date and time
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f'binary_image_{timestamp}.bmp'
        binary_image.save(filename)
        QMessageBox.information(parent, "导出成功", f"二值图已导出为 {filename}")

    pixel_map_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)  # 允许根据布局空间调整大小
    return {'pixel_map_widget': pixel_map_widget, 'pixel_labels': pixel_labels, 'export_button': export_button, 'clear_map_button': clear_map_button, 'digital_matrix_labels': digital_matrix_labels} # Return clear button and digital matrix labels

def populate_serial_ports(port_combo):
    ports = serial.tools.list_ports.comports()
    port_combo.clear()
    for port in ports:
        port_combo.addItem(port.device)
    if not ports:
        port_combo.addItem("无可用串口")
        port_combo.setEnabled(False)
    else:
        port_combo.setEnabled(True)