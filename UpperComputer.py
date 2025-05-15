import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton, QComboBox, QStatusBar, QMenuBar, QMenu, QAction, QMessageBox, QFileDialog
from PyQt5.QtCore import QTimer, QThread, pyqtSignal
import serial
import serial.tools.list_ports
import pyqtgraph as pg
import struct
import time
import csv
import os # For path joining in export

class SerialThread(QThread):
    data_received = pyqtSignal(list)
    status_changed = pyqtSignal(str)

    def __init__(self, port, baudrate, stopbits, databits, parity, flowcontrol):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.stopbits = stopbits
        self.databits = databits
        self.parity = parity
        self.flowcontrol = flowcontrol # Store flow control, though pyserial might not directly use it in Serial() init for all types
        self.serial_port = None
        self.running = False
        self.data_frame_tail = bytes([0x00, 0x00, 0x80, 0x7f])
        self.buffer = bytearray()

    def run(self):
        try:
            self.serial_port = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=self.databits, # Changed from stopbits to bytesize
                parity=self.parity,
                stopbits=self.stopbits,
                timeout=1,
                rtscts=self.flowcontrol == 'RTS/CTS',
                xonxoff=self.flowcontrol == 'XON/XOFF'
            )
            self.running = True
            self.status_changed.emit(f"已连接到 {self.port} @ {self.baudrate}")
            print(f"Serial port {self.port} opened successfully.")

            while self.running:
                if self.serial_port.in_waiting > 0:
                    data_byte = self.serial_port.read(self.serial_port.in_waiting)
                    self.buffer.extend(data_byte)
                    self.process_buffer()
                time.sleep(0.001) # 避免CPU占用过高

        except serial.SerialException as e:
            self.status_changed.emit(f"串口错误: {e}")
            print(f"Serial error: {e}")
        finally:
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close()
            self.status_changed.emit("串口已断开")
            print("Serial port closed.")

    def process_buffer(self):
        # 数据帧长度：8个浮点数 * 4字节/浮点数 + 4字节帧尾 = 32 + 4 = 36字节
        frame_length = 36 
        while len(self.buffer) >= frame_length:
            # 寻找帧尾
            try:
                tail_index = self.buffer.index(self.data_frame_tail)
                # 确保帧尾之前有足够的数据构成一个完整的数据帧 (8 * 4 = 32 bytes)
                if tail_index >= 32:
                    frame_data_start_index = tail_index - 32
                    frame_data = self.buffer[frame_data_start_index:tail_index]
                    
                    # 解析8个浮点数
                    values = []
                    for i in range(8):
                        # 假设数据是大端字节序，如果不是，需要调整
                        value_bytes = frame_data[i*4 : (i+1)*4]
                        value = struct.unpack('>f', value_bytes)[0] # '>' for big-endian
                        values.append(value)
                    
                    self.data_received.emit(values)
                    # 移除已处理的数据（包括帧尾）
                    self.buffer = self.buffer[tail_index + len(self.data_frame_tail):]
                else:
                    # 帧尾位置不正确，可能数据损坏或未对齐，丢弃帧尾之前的数据
                    self.buffer = self.buffer[tail_index + len(self.data_frame_tail):]
            except ValueError:
                # 未找到帧尾，保留缓冲区等待更多数据，但要防止缓冲区无限增长
                if len(self.buffer) > frame_length * 10: # 缓冲区过大，可能帧同步丢失
                    self.buffer = self.buffer[len(self.buffer) - frame_length:] # 保留最后一部分
                break # 等待更多数据

    def stop(self):
        self.running = False

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TENG阵列多通道信号检测系统")
        self.setGeometry(0, 0, 1920, 1080)

        self.serial_thread = None
        self.plot_widgets = []
        # self.voltage_labels = [] # 不再需要电压标签
        self.data_lines = []
        self.data_queues = [[] for _ in range(8)] # 每个通道一个数据队列 (voltage, time_s)
        self.max_data_points = 200 # 图表上显示的最大数据点数
        self.hover_texts = [] # 用于存储每个图表的悬停文本对象
        self.is_synchronizing_x = False # Flag to prevent recursive X-axis sync
        self.sample_interval_s = 0.001 # 采样间隔，秒 (对应1ms)

        self.test_data_timer = QTimer(self) # 新增测试数据定时器
        self.is_generating_test_data = False # 新增测试数据生成状态标志

        self._init_ui()
        self._populate_serial_ports()

    def _init_ui(self):
        # --- Central Widget and Layout --- #
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # --- Left Control Panel --- #
        control_panel = QWidget()
        control_layout = QVBoxLayout(control_panel)
        control_panel.setFixedWidth(400) # 稍微加宽
        control_layout.setSpacing(15) # 增加控件间的垂直间距
        control_layout.setContentsMargins(15, 15, 15, 15) # 增加边距

        # --- 字体定义 ---
        label_font = self.font()
        label_font.setPointSize(14)
        button_font = self.font()
        button_font.setPointSize(14)

        # --- 实时电压显示区域 ---
        voltage_display_group = QWidget() # 使用 QGroupBox 增加边框和标题
        voltage_display_group_layout = QVBoxLayout(voltage_display_group)
        # voltage_display_group.setTitle("实时电压") # QGroupBox 方式
        # voltage_display_group.setFont(label_font)

        voltage_title = QLabel("实时电压值")
        title_font = self.font()
        title_font.setPointSize(18)
        title_font.setBold(True)
        voltage_title.setFont(title_font)
        voltage_display_group_layout.addWidget(voltage_title)

        self.voltage_labels = []
        for i in range(8):
            label = QLabel(f"CH{i+1}: 0.000 V") # 更改标签格式
            color = f"color: rgb({i*30 % 255}, {i*50 % 255}, {i*70 % 255})"
            label.setStyleSheet(f"font-family: Consolas, Courier New, monospace; font-size: 14pt; {color}")
            voltage_display_group_layout.addWidget(label)
            self.voltage_labels.append(label)
        voltage_display_group_layout.addStretch()
        control_layout.addWidget(voltage_display_group)

        # --- 协议与连接 --- #
        protocol_connection_label = QLabel("协议与连接")
        protocol_connection_font = self.font()
        protocol_connection_font.setPointSize(18)
        protocol_connection_font.setBold(True)
        protocol_connection_label.setFont(protocol_connection_font)
        control_layout.addWidget(protocol_connection_label)

        # --- 数据引擎 --- #
        data_engine_layout = QHBoxLayout()
        data_engine_label = QLabel("数据引擎")
        data_engine_label.setFont(label_font)
        # Add a question mark label if needed, for now, just the text
        # help_label = QLabel("?") 
        # help_label.setFont(label_font)
        self.data_engine_combo = QComboBox()
        self.data_engine_combo.addItems(["JustFloat"]) # Add other options if any
        self.data_engine_combo.setCurrentText("JustFloat")
        self.data_engine_combo.setFont(label_font)
        self.data_engine_combo.setMinimumHeight(40)
        data_engine_layout.addWidget(data_engine_label)
        # data_engine_layout.addWidget(help_label) # If question mark is separate
        data_engine_layout.addStretch()
        data_engine_layout.addWidget(self.data_engine_combo)
        control_layout.addLayout(data_engine_layout)


        # --- 数据接口 --- #
        data_interface_layout = QHBoxLayout()
        data_interface_label = QLabel("数据接口")
        data_interface_label.setFont(label_font)
        self.data_interface_combo = QComboBox()
        self.data_interface_combo.addItems(["串口"]) # Add other options if any
        self.data_interface_combo.setCurrentText("串口")
        self.data_interface_combo.setFont(label_font)
        self.data_interface_combo.setMinimumHeight(40)
        data_interface_layout.addWidget(data_interface_label)
        data_interface_layout.addStretch()
        data_interface_layout.addWidget(self.data_interface_combo)
        control_layout.addLayout(data_interface_layout)


        # --- 串口参数配置 --- #
        serial_params_label = QLabel("串口参数配置")
        serial_params_font = self.font()
        serial_params_font.setPointSize(16) # Slightly smaller than main title
        serial_params_font.setBold(True)
        serial_params_label.setFont(serial_params_font)
        serial_params_label.setStyleSheet("color: #1E90FF;") # DodgerBlue color
        control_layout.addWidget(serial_params_label)

        serial_group = QWidget() # Keep the group for serial params
        serial_layout = QGridLayout(serial_group) # Use QGridLayout for better alignment
        serial_layout.setSpacing(8) # Reduce spacing for compact look

        port_label = QLabel("端口号")
        port_label.setFont(label_font)
        serial_layout.addWidget(port_label, 0, 0)
        self.port_combo = QComboBox()
        self.port_combo.setFont(label_font)
        self.port_combo.setMinimumHeight(40)
        serial_layout.addWidget(self.port_combo, 0, 1)


        baud_label = QLabel("波特率")
        baud_label.setFont(label_font)
        serial_layout.addWidget(baud_label, 2, 0)
        self.baud_combo = QComboBox()
        self.baud_combo.addItems(["9600", "19200", "38400", "57600", "115200"])
        self.baud_combo.setCurrentText("115200")
        self.baud_combo.setFont(label_font)
        self.baud_combo.setMinimumHeight(40)
        serial_layout.addWidget(self.baud_combo, 2, 1)

        flow_control_label = QLabel("数据流控")
        flow_control_label.setFont(label_font)
        serial_layout.addWidget(flow_control_label, 3, 0)
        self.flow_control_combo = QComboBox()
        self.flow_control_combo.addItems(["None", "RTS/CTS", "XON/XOFF"]) # Common options
        self.flow_control_combo.setCurrentText("None")
        self.flow_control_combo.setFont(label_font)
        self.flow_control_combo.setMinimumHeight(40)
        serial_layout.addWidget(self.flow_control_combo, 3, 1)

        parity_label = QLabel("校验位")
        parity_label.setFont(label_font)
        serial_layout.addWidget(parity_label, 4, 0)
        self.parity_combo = QComboBox()
        self.parity_combo.addItems(["None", "Even", "Odd", "Mark", "Space"]) # Common options
        self.parity_combo.setCurrentText("None")
        self.parity_combo.setFont(label_font)
        self.parity_combo.setMinimumHeight(40)
        serial_layout.addWidget(self.parity_combo, 4, 1)

        databits_label = QLabel("数据位数")
        databits_label.setFont(label_font)
        serial_layout.addWidget(databits_label, 5, 0)
        self.databits_combo = QComboBox()
        self.databits_combo.addItems(["5", "6", "7", "8"])
        self.databits_combo.setCurrentText("8")
        self.databits_combo.setFont(label_font)
        self.databits_combo.setMinimumHeight(40)
        serial_layout.addWidget(self.databits_combo, 5, 1)

        stopbits_label = QLabel("停止位数") # Changed from "停止位"
        stopbits_label.setFont(label_font)
        serial_layout.addWidget(stopbits_label, 6, 0)
        self.stopbits_combo = QComboBox()
        self.stopbits_combo.addItems(["1", "1.5", "2"])
        self.stopbits_combo.setCurrentText("1")
        self.stopbits_combo.setFont(label_font)
        self.stopbits_combo.setMinimumHeight(40)
        serial_layout.addWidget(self.stopbits_combo, 6, 1)
        
        control_layout.addWidget(serial_group)

        # --- 操作按钮区域 ---
        action_buttons_layout = QGridLayout() # 使用网格布局让按钮更规整

        self.connect_button = QPushButton("连接")
        self.connect_button.setFont(button_font)
        self.connect_button.setMinimumHeight(48)
        self.connect_button.clicked.connect(self.connect_serial)
        action_buttons_layout.addWidget(self.connect_button, 0, 0)

        self.disconnect_button = QPushButton("断开")
        self.disconnect_button.setFont(button_font)
        self.disconnect_button.setMinimumHeight(48)
        self.disconnect_button.clicked.connect(self.disconnect_serial)
        self.disconnect_button.setEnabled(False)
        action_buttons_layout.addWidget(self.disconnect_button, 0, 1)

        self.test_data_button = QPushButton("生成测试数据")
        self.test_data_button.setFont(button_font)
        self.test_data_button.setMinimumHeight(48)
        self.test_data_button.clicked.connect(self.toggle_test_data_generation)
        action_buttons_layout.addWidget(self.test_data_button, 1, 0, 1, 2) # 跨两列

        self.reset_view_button = QPushButton("复位图表")
        self.reset_view_button.setFont(button_font)
        self.reset_view_button.setMinimumHeight(48)
        self.reset_view_button.clicked.connect(self._reset_plot_views)
        action_buttons_layout.addWidget(self.reset_view_button, 2, 0)

        self.clear_data_button = QPushButton("清空数据") # 新增清空数据按钮
        self.clear_data_button.setFont(button_font)
        self.clear_data_button.setMinimumHeight(48)
        self.clear_data_button.clicked.connect(self._clear_plot_data) # 连接到新方法
        action_buttons_layout.addWidget(self.clear_data_button, 2, 1)

        self.export_data_button = QPushButton("导出数据")
        self.export_data_button.setFont(button_font)
        self.export_data_button.setMinimumHeight(48)
        self.export_data_button.clicked.connect(self.export_data_to_csv)
        action_buttons_layout.addWidget(self.export_data_button, 3, 0, 1, 2) # 跨两列
        
        control_layout.addLayout(action_buttons_layout)
        control_layout.addStretch()
        main_layout.addWidget(control_panel)

        # --- Right Data Display Area --- #
        data_display_area = QWidget()
        data_display_layout = QGridLayout(data_display_area)
        main_layout.addWidget(data_display_area, 1) # Give more stretch factor to data area

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
            if (i < 3) or (i > 3 and i < 7):  # 隐藏中间图表的X轴
                plot_widget.getAxis('bottom').setStyle(showValues=False)
                plot_widget.getAxis('bottom').setLabel('')
            
            self.plot_widgets.append(plot_widget)
            plot_layout.addWidget(plot_widget)

            # Connect sigXRangeChanged for synchronization
            plot_widget.getViewBox().sigXRangeChanged.connect(self._synchronize_x_ranges)

            # 创建用于显示悬停信息的TextItem
            hover_text = pg.TextItem(anchor=(0,1))
            plot_widget.addItem(hover_text)
            hover_text.hide()
            # 将hover_text与plot_widget关联，方便后续查找
            plot_widget.hover_text_item = hover_text 

            # 连接鼠标移动事件
            plot_widget.scene().sigMouseMoved.connect(lambda pos, pw=plot_widget, idx=i: self._mouse_moved_on_plot(pos, pw, idx))

            data_display_layout.addWidget(plot_widget_container, row, col)
            
            # 初始化数据线
            data_line = plot_widget.plot([], [], pen=pg.mkPen(color=(i*30 % 255, i*50 % 255, i*70 % 255), width=2))
            self.data_lines.append(data_line)

        # --- Menu Bar --- #
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("文件")
        # settings_menu = menu_bar.addMenu("设置") # Removed
        # help_menu = menu_bar.addMenu("帮助") # Removed

        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # TODO: Add serial config to settings menu if needed

        # about_action = QAction("关于", self) # Removed as help menu is removed
        # about_action.triggered.connect(self.show_about_dialog)
        # help_menu.addAction(about_action)

        # --- Status Bar --- #
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("准备就绪")

    def _populate_serial_ports(self):
        ports = serial.tools.list_ports.comports()
        self.port_combo.clear()
        for port in ports:
            self.port_combo.addItem(port.device)
        if not ports:
            self.port_combo.addItem("无可用串口")
            self.connect_button.setEnabled(False)

    def connect_serial(self):
        port = self.port_combo.currentText()
        if port == "无可用串口":
            QMessageBox.warning(self, "连接错误", "没有选择有效的串口。")
            return
            
        baudrate = int(self.baud_combo.currentText())

        stopbits_str = self.stopbits_combo.currentText()
        if stopbits_str == "1":
            stopbits = serial.STOPBITS_ONE
        elif stopbits_str == "1.5":
            stopbits = serial.STOPBITS_ONE_POINT_FIVE
        else: # "2"
            stopbits = serial.STOPBITS_TWO

        databits_str = self.databits_combo.currentText()
        if databits_str == "5":
            databits = serial.FIVEBITS
        elif databits_str == "6":
            databits = serial.SIXBITS
        elif databits_str == "7":
            databits = serial.SEVENBITS
        else: # "8"
            databits = serial.EIGHTBITS

        parity_str = self.parity_combo.currentText()
        if parity_str == "None":
            parity = serial.PARITY_NONE
        elif parity_str == "Even":
            parity = serial.PARITY_EVEN
        elif parity_str == "Odd":
            parity = serial.PARITY_ODD
        elif parity_str == "Mark":
            parity = serial.PARITY_MARK
        else: # "Space"
            parity = serial.PARITY_SPACE
        
        flowcontrol = self.flow_control_combo.currentText()

        self.serial_thread = SerialThread(port, baudrate, stopbits, databits, parity, flowcontrol)
        self.serial_thread.data_received.connect(self.update_plots)
        self.serial_thread.status_changed.connect(self.update_status_bar)
        self.serial_thread.start()

        self.connect_button.setEnabled(False)
        self.disconnect_button.setEnabled(True)
        self.port_combo.setEnabled(False)
        self.baud_combo.setEnabled(False)
        self.stopbits_combo.setEnabled(False)
        self.databits_combo.setEnabled(False)
        self.parity_combo.setEnabled(False)
        self.flow_control_combo.setEnabled(False)
        self.data_engine_combo.setEnabled(False)
        self.data_interface_combo.setEnabled(False)

    def disconnect_serial(self):
        if self.serial_thread and self.serial_thread.isRunning():
            self.serial_thread.stop()
            self.serial_thread.wait() # 等待线程结束
        
        self.connect_button.setEnabled(True)
        self.disconnect_button.setEnabled(False)
        self.port_combo.setEnabled(True)
        self.baud_combo.setEnabled(True)
        self.stopbits_combo.setEnabled(True)
        self.databits_combo.setEnabled(True)
        self.parity_combo.setEnabled(True)
        self.flow_control_combo.setEnabled(True)
        self.data_engine_combo.setEnabled(True)
        self.data_interface_combo.setEnabled(True)
        self.status_bar.showMessage("串口已断开")

    def update_plots(self, values):
        # values 是一个包含8个浮点数的列表
        for i in range(8):
            # 将原始浮点数转换为0-3.3V电压值 (根据文档，假设原始数据已经是电压值或需要转换)
            # 这里假设接收到的已经是电压值，如果不是，需要添加转换逻辑
            voltage = values[i]
            # 确保电压在0-3.3V范围内显示，实际数据可能超出，但图表Y轴已限制
            # voltage = max(0, min(3.3, voltage)) 

            # Determine the time for the current data point
            if not self.data_queues[i]:
                current_time_s = 0.0
            else:
                # Get the time of the last point and add interval
                last_time_s = self.data_queues[i][-1][1] 
                current_time_s = last_time_s + self.sample_interval_s

            self.data_queues[i].append((voltage, current_time_s))
            if len(self.data_queues[i]) > self.max_data_points:
                self.data_queues[i].pop(0) # 移除最老的数据点
            
            # Extract x (time) and y (voltage) data for plotting
            plot_times = [item[1] for item in self.data_queues[i]]
            plot_voltages = [item[0] for item in self.data_queues[i]]
            self.data_lines[i].setData(plot_times, plot_voltages)
            # Update voltage labels if data is actively being generated
            if self.is_generating_test_data or (self.serial_thread and self.serial_thread.isRunning()):
                self.voltage_labels[i].setText(f"CH{i+1}: {voltage:.3f} V")
            # self.voltage_labels[i].setText(f"当前电压: {voltage:.3f} V") # 移除电压标签更新

    def update_status_bar(self, message):
        self.status_bar.showMessage(message)

    def _mouse_moved_on_plot(self, pos, plot_widget, plot_index):
        vb = plot_widget.getViewBox()
        if plot_widget.sceneBoundingRect().contains(pos):
            mouse_point = vb.mapSceneToView(pos)
            # xData now contains time values (floats)
            # yData contains voltage values (floats)
            x_data = self.data_lines[plot_index].xData 
            y_data = self.data_lines[plot_index].yData

            if x_data is not None and len(x_data) > 0:
                # Find the index of the data point closest to the mouse's x-coordinate
                # This is a simple way, for large datasets, numpy.argmin(numpy.abs(x_data - mouse_point.x())) would be more efficient
                min_dist = float('inf')
                closest_index = -1
                for idx, x_val in enumerate(x_data):
                    dist = abs(x_val - mouse_point.x())
                    if dist < min_dist:
                        min_dist = dist
                        closest_index = idx
                
                # Check if the mouse is reasonably close to a data point on the x-axis
                # This threshold can be adjusted. For example, half the sample interval.
                if closest_index != -1 and min_dist < (self.sample_interval_s * 5): # Allow a bit of leeway
                    actual_x_time = x_data[closest_index]
                    actual_y_voltage = y_data[closest_index] # Voltage of the hovered plot at that point

                    # If data generation is stopped, update all voltage labels based on hovered time
                    if not self.is_generating_test_data and not (self.serial_thread and self.serial_thread.isRunning()):
                        for ch_idx in range(8):
                            ch_x_data = self.data_lines[ch_idx].xData
                            ch_y_data = self.data_lines[ch_idx].yData
                            voltage_at_hover_time_str = "--- V"
                            if ch_x_data is not None and len(ch_x_data) > 0:
                                # Find closest data point in this channel to actual_x_time
                                ch_closest_idx = -1
                                ch_min_dist = float('inf')
                                for idx_in_ch, x_val_in_ch in enumerate(ch_x_data):
                                    dist_in_ch = abs(x_val_in_ch - actual_x_time)
                                    if dist_in_ch < ch_min_dist:
                                        ch_min_dist = dist_in_ch
                                        ch_closest_idx = idx_in_ch
                                
                                # Check if the found point is reasonably close (e.g., within a sample interval)
                                if ch_closest_idx != -1 and ch_min_dist < self.sample_interval_s * 1.5: # Allow small tolerance
                                    voltage_at_hover_time_str = f"{ch_y_data[ch_closest_idx]:.3f} V"
                            self.voltage_labels[ch_idx].setText(f"CH{ch_idx+1}: {voltage_at_hover_time_str}")
                    # elif self.is_generating_test_data or (self.serial_thread and self.serial_thread.isRunning()):
                        # If data is generating, update only the hovered plot's label (or rely on update_plots)
                        # self.voltage_labels[plot_index].setText(f"CH{plot_index+1}: {actual_y_voltage:.3f} V")
                        # The update_plots method already handles this for active data generation.
                        pass # Voltage labels are updated by update_plots during active data generation

                    # Remove on-plot hover text display
                    plot_widget.hover_text_item.hide()
                else:
                    plot_widget.hover_text_item.hide()
            else:
                plot_widget.hover_text_item.hide()
        else:
            plot_widget.hover_text_item.hide()

    def show_about_dialog(self):
        QMessageBox.about(self, "关于", "PyQt 上位机软件\n版本 1.0\n作者: Trae AI")

    def _generate_single_test_data_point(self):
        import random
        import math
        import time

        # 生成一组模拟数据
        test_values = []
        current_time = time.time() # Use current time for dynamic data
        for i in range(8):
            # 生成一个0-3.3V范围内的正弦波形数据
            value = 1.65 + 1.65 * math.sin(current_time + i * math.pi / 4 + (current_time * 2)) # Add current_time to make it dynamic
            # 添加一些随机噪声
            value += random.uniform(-0.1, 0.1)
            # 确保值在0-3.3V范围内
            value = max(0, min(3.3, value))
            test_values.append(value)

        # 更新图表
        self.update_plots(test_values)
        # self.status_bar.showMessage("已生成测试数据") # Status bar update can be handled by toggle function

    def toggle_test_data_generation(self):
        if not self.is_generating_test_data:
            # 保存原始采样间隔
            self.original_sample_interval_s = self.sample_interval_s 
            # 设置测试数据采样间隔 (10Hz -> 0.1s)
            self.sample_interval_s = 0.1
            # 开始生成数据
            self.test_data_timer.timeout.connect(self._generate_single_test_data_point)
            self.test_data_timer.start(100) # 10Hz = 100ms interval
            self.is_generating_test_data = True
            self.test_data_button.setText("停止生成")
            self.status_bar.showMessage("测试数据采集中 (10Hz)...")
        else:
            # 停止生成数据
            self.test_data_timer.stop()
            self.test_data_timer.timeout.disconnect(self._generate_single_test_data_point) # Disconnect to avoid multiple connections if started again
            self.is_generating_test_data = False
            self.test_data_button.setText("生成测试数据")
            # 恢复原始采样间隔
            if hasattr(self, 'original_sample_interval_s'):
                self.sample_interval_s = self.original_sample_interval_s
            self.status_bar.showMessage("测试数据采集已停止")

    def _synchronize_x_ranges(self, changed_vb):
        if self.is_synchronizing_x:
            return
        self.is_synchronizing_x = True
        
        new_x_range = changed_vb.viewRange()[0] # Get the new x-range from the source ViewBox
        
        for pw in self.plot_widgets:
            if pw.getViewBox() is not changed_vb: # Don't update the ViewBox that triggered the signal
                pw.getViewBox().setXRange(new_x_range[0], new_x_range[1], padding=0)
                
        self.is_synchronizing_x = False

    def _clear_plot_data(self):
        for i in range(8):
            self.data_queues[i].clear()
            self.data_lines[i].setData([], [])
            self.voltage_labels[i].setText(f"CH{i+1}: 0.000 V")
        # Optionally, reset X-axis of plots if desired, or leave as is
        # self._reset_plot_views() # Could call this to reset zoom/pan
        self.status_bar.showMessage("图表数据已清空")

    def _reset_plot_views(self):
        if self.is_synchronizing_x: # Prevent issues if called during an ongoing sync
            return
        self.is_synchronizing_x = True # Prevent sync signals during manual reset
        
        # Determine the current time range based on the first non-empty data queue
        # If all queues are empty, reset to a default initial view.
        current_min_time = 0.0
        current_max_time = self.max_data_points * self.sample_interval_s # Default max time if no data

        # Try to find the actual time range from data
        found_data_range = False
        for queue in self.data_queues:
            if queue:
                times = [item[1] for item in queue]
                current_min_time = times[0]
                current_max_time = times[-1]
                # Ensure the range covers at least the max_data_points window if data is less
                if (current_max_time - current_min_time) < (self.max_data_points * self.sample_interval_s):
                    current_max_time = current_min_time + (self.max_data_points * self.sample_interval_s)
                found_data_range = True
                break
        
        if not found_data_range and self.data_queues[0]: # Fallback if first queue has data but loop didn't catch
             if self.data_queues[0]:
                times = [item[1] for item in self.data_queues[0]]
                current_min_time = times[0]
                current_max_time = times[-1]
                if (current_max_time - current_min_time) < (self.max_data_points * self.sample_interval_s):
                    current_max_time = current_min_time + (self.max_data_points * self.sample_interval_s)

        for pw in self.plot_widgets:
            pw.getViewBox().setXRange(current_min_time, current_max_time, padding=0)
            # Y-axis is already fixed and non-interactive, so no Y-reset needed here
            # If it were, you'd add: pw.getViewBox().setYRange(0, 3.3, padding=0) 
        
        self.is_synchronizing_x = False

    def export_data_to_csv(self):
        if not any(self.data_queues):
            QMessageBox.information(self, "导出数据", "没有数据可导出。")
            return

        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        file_path, _ = QFileDialog.getSaveFileName(self, "保存数据", "", "CSV 文件 (*.csv);;所有文件 (*)", options=options)

        if file_path:
            try:
                with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                    csv_writer = csv.writer(csvfile)
                    
                    # Prepare header
                    header = ['Sample Index', 'Time (s)']
                    for i in range(8):
                        header.append(f'Channel {i+1} Voltage (V)')
                    csv_writer.writerow(header)

                    # Determine the maximum number of samples across all channels for consistent rows
                    max_samples = 0
                    for i in range(8):
                        if self.data_queues[i]:
                           max_samples = max(max_samples, len(self.data_queues[i]))
                    
                    if max_samples == 0 and self.data_queues[0]: # Check if only first channel has data
                        max_samples = len(self.data_queues[0])

                    # Write data rows
                    for sample_idx in range(max_samples):
                        row_data = [sample_idx]
                        # Time for this sample index - assumes first channel's time or calculate if needed
                        # For simplicity, we'll use the time from the first channel that has this sample
                        # or derive it if all channels are synchronized by sample count.
                        # A more robust way would be to ensure all data_queues[i][sample_idx] have same time or handle discrepancies.
                        
                        # Get time from the first available channel for this sample_idx
                        current_sample_time = None
                        for i in range(8):
                            if sample_idx < len(self.data_queues[i]):
                                current_sample_time = self.data_queues[i][sample_idx][1] # (voltage, time_s)
                                break
                        if current_sample_time is None: # Should not happen if max_samples is correct
                            # Fallback: calculate time based on sample_idx and interval if no direct time found
                            current_sample_time = sample_idx * self.sample_interval_s 

                        row_data.append(f"{current_sample_time:.3f}")

                        for i in range(8):
                            if sample_idx < len(self.data_queues[i]):
                                voltage = self.data_queues[i][sample_idx][0]
                                row_data.append(f"{voltage:.3f}")
                            else:
                                row_data.append('') # Empty if no data for this channel at this sample index
                        csv_writer.writerow(row_data)
                
                self.status_bar.showMessage(f"数据已导出到 {os.path.basename(file_path)}")
            except Exception as e:
                QMessageBox.critical(self, "导出错误", f"无法保存文件: {e}")
                self.status_bar.showMessage(f"导出失败: {e}")

    def closeEvent(self, event):
        self.disconnect_serial() #确保关闭时断开串口
        super().closeEvent(event)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_win = MainWindow()
    main_win.show()
    sys.exit(app.exec_())