import time
# serial_manager.py
#
# 文件功能说明:
# 该文件包含 SerialManager 类，负责管理串口连接和配置。
# 它处理 UI 控件（如下拉框和按钮）与 SerialThread 之间的交互，
# 允许用户选择串口参数、连接和断开串口，并接收来自 SerialThread 的数据和状态更新。
#

import serial
import serial.tools.list_ports
from PyQt5.QtWidgets import QComboBox, QPushButton, QMessageBox, QStatusBar
from PyQt5.QtCore import pyqtSignal, QObject
from serial_handler import SerialThread # 假设 SerialThread 在 serial_handler.py 中

class SerialManager(QObject):
    # 定义将连接到 MainWindow 的信号
    status_changed = pyqtSignal(str) # 串口状态改变时发出的信号
    data_received = pyqtSignal(list) # 假设数据以值列表的形式接收

    def __init__(self, port_combo, baud_combo, flow_control_combo, parity_combo, databits_combo, stopbits_combo, connect_button, disconnect_button, status_bar, main_window=None):
        super().__init__()
        self.port_combo = port_combo
        self.baud_combo = baud_combo
        self.flow_control_combo = flow_control_combo
        self.parity_combo = parity_combo
        self.databits_combo = databits_combo
        self.stopbits_combo = stopbits_combo
        self.connect_button = connect_button
        self.disconnect_button = disconnect_button
        self.status_bar = status_bar
        self.main_window = main_window  # 保存MainWindow引用
        self.serial_thread = None

    def populate_serial_ports(self):
        """填充可用串口到下拉框。"""
        ports = serial.tools.list_ports.comports() # 获取可用串口列表
        self.port_combo.clear() # 清空下拉框
        for port in ports:
            self.port_combo.addItem(port.device) # 添加串口设备名称
        if not ports:
            self.port_combo.addItem("无可用串口") # 如果没有可用串口，显示提示
            self.connect_button.setEnabled(False) # 禁用连接按钮

    def connect_serial(self):
        """连接到选定的串口。"""
        port = self.port_combo.currentText() # 获取选定的串口名称
        if port == "无可用串口":
            QMessageBox.warning(None, "连接错误", "没有选择有效的串口。") # 使用 None 作为 QMessageBox 的父级
            return

        baudrate = int(self.baud_combo.currentText()) # 获取选定的波特率

        stopbits_str = self.stopbits_combo.currentText() # 获取选定的停止位字符串
        if stopbits_str == "1":
            stopbits = serial.STOPBITS_ONE
        elif stopbits_str == "1.5":
            stopbits = serial.STOPBITS_ONE_POINT_FIVE
        else: # "2"
            stopbits = serial.STOPBITS_TWO

        databits_str = self.databits_combo.currentText() # 获取选定的数据位字符串
        if databits_str == "5":
            databits = serial.FIVEBITS
        elif databits_str == "6":
            databits = serial.SIXBITS
        elif databits_str == "7":
            databits = serial.SEVENBITS
        else: # "8"
            databits = serial.EIGHTBITS

        parity_str = self.parity_combo.currentText() # 获取选定的奇偶校验字符串
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

        flowcontrol = self.flow_control_combo.currentText() # 获取选定的流控制方式

        # 获取并应用上次断开的时间偏移
        current_time = time.time()
        start_time_with_offset = current_time - self.main_window.last_time_offset if self.main_window else current_time

        # 创建并启动串口处理线程
        self.serial_thread = SerialThread(
            port,
            baudrate,
            stopbits,
            databits,
            parity,
            flowcontrol,
            start_time_with_offset  # 传递带有偏移的时间基准
        )
        self.serial_thread.data_received.connect(self.data_received.emit) # 连接数据接收信号
        self.serial_thread.status_changed.connect(self.status_changed.emit) # 连接状态改变信号
        self.serial_thread.start() # 启动线程

        # 更新 UI 控件状态
        self.connect_button.setEnabled(False)
        self.disconnect_button.setEnabled(True)
        self.port_combo.setEnabled(False)
        self.baud_combo.setEnabled(False)
        self.stopbits_combo.setEnabled(False)
        self.databits_combo.setEnabled(False)
        self.parity_combo.setEnabled(False)
        self.flow_control_combo.setEnabled(False)
        # 数据引擎和接口下拉框由 MainWindow 处理
        # self.data_engine_combo.setEnabled(False)
        # self.data_interface_combo.setEnabled(False)

    def disconnect_serial(self):
        """断开当前串口连接。"""
        if self.serial_thread and self.serial_thread.isRunning():
            try:
                # 在停止线程前保存当前时间偏移量
                if self.main_window and hasattr(self.serial_thread, 'time_offset'):
                    self.main_window.last_time_offset = self.serial_thread.time_offset
                
                # 停止线程并设置超时
                self.serial_thread.stop()
                
                # 使用超时等待线程结束
                if not self.serial_thread.wait(2000):  # 最多等待2秒
                    self.serial_thread.terminate()  # 强制终止线程
                    self.status_changed.emit("警告：串口线程强制终止") # 发出警告信号
                
                # 确保串口已关闭
                if hasattr(self.serial_thread, 'serial_port') and self.serial_thread.serial_port:
                    if self.serial_thread.serial_port.is_open:
                        try:
                            self.serial_thread.serial_port.close()
                        except Exception as e:
                            print(f"关闭串口时出错: {e}")
            
            except Exception as e:
                print(f"断开串口时出错: {e}")
                self.status_changed.emit(f"断开串口时出错: {e}")

        # 更新 UI 控件状态
        self.connect_button.setEnabled(True)
        self.disconnect_button.setEnabled(False)
        self.port_combo.setEnabled(True)
        self.baud_combo.setEnabled(True)
        self.stopbits_combo.setEnabled(True)
        self.databits_combo.setEnabled(True)
        self.parity_combo.setEnabled(True)
        self.flow_control_combo.setEnabled(True)
        self.status_changed.emit("串口已断开") # 发出状态改变信号

    def is_connected(self):
        """检查串口是否已连接。"""
        return self.serial_thread is not None and self.serial_thread.isRunning() # 返回连接状态