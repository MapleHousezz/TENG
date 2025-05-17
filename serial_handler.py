# serial_handler.py
#
# 文件功能说明:
# 该文件包含 SerialThread 类，负责在单独的线程中处理串口通信。
# 它负责连接到指定的串口，以设定的波特率和其他参数接收数据，
# 解析接收到的数据帧，并发出信号通知主线程数据已接收。
# 它还提供列出可用串口的功能。
#

import serial
import serial.tools.list_ports
from PyQt5.QtCore import QThread, pyqtSignal
import struct
import time

class SerialThread(QThread):
    data_received = pyqtSignal(list) # 接收到数据时发出的信号
    status_changed = pyqtSignal(str) # 串口状态改变时发出的信号

    def __init__(self, port, baudrate, stopbits, databits, parity, flowcontrol):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.stopbits = stopbits
        self.databits = databits
        self.parity = parity
        self.flowcontrol = flowcontrol
        self.serial_port = None
        self.running = False
        self.data_frame_tail = bytes([0x00, 0x00, 0x80, 0x7f]) # 数据帧尾部标识
        self.buffer = bytearray() # 接收缓冲区
        self.start_time = None # 添加 start_time 属性，记录数据采集开始时间

    def run(self):
        try:
            self.serial_port = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=self.databits,
                parity=self.parity,
                stopbits=self.stopbits,
                timeout=1, # 读取超时时间
                rtscts=self.flowcontrol == 'RTS/CTS', # RTS/CTS 流控制
                xonxoff=self.flowcontrol == 'XON/XOFF' # XON/XOFF 流控制
            )
            self.running = True
            self.start_time = time.time() # 连接成功时记录开始时间
            self.status_changed.emit(f"已连接到 {self.port} @ {self.baudrate}")
            print(f"Serial port {self.port} opened successfully.") # 打印串口打开成功信息

            while self.running:
                if self.serial_port.in_waiting > 0:
                    data_byte = self.serial_port.read(self.serial_port.in_waiting) # 读取可用数据
                    self.buffer.extend(data_byte) # 将数据添加到缓冲区
                    self.process_buffer() # 处理缓冲区数据
                time.sleep(0.001) # 短暂休眠，避免占用过多 CPU

        except serial.SerialException as e:
            self.status_changed.emit(f"串口错误: {e}") # 发出串口错误信号
            print(f"Serial error: {e}") # 打印串口错误信息
        finally:
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close() # 关闭串口
            self.status_changed.emit("串口已断开") # 发出串口断开信号
            print("Serial port closed.") # 打印串口关闭信息

    def process_buffer(self):
        frame_length = 36 # 数据帧长度
        while len(self.buffer) >= frame_length:
            try:
                tail_index = self.buffer.index(self.data_frame_tail) # 查找帧尾
                if tail_index >= 32: # 确保帧尾前面有足够的数据
                    frame_data_start_index = tail_index - 32 # 计算帧数据开始索引
                    frame_data = self.buffer[frame_data_start_index:tail_index] # 提取帧数据

                    values = []
                    for i in range(8): # 解析 8 个浮点数
                        value_bytes = frame_data[i*4 : (i+1)*4] # 提取每个浮点数的字节
                        value = struct.unpack('>f', value_bytes)[0] # 按大端浮点数解析
                        values.append(value) # 添加到值列表

                    current_time = time.time() # 获取当前时间
                    if self.start_time is None:
                        self.start_time = current_time # 如果是第一个数据点，记录开始时间
                    relative_time = current_time - self.start_time # 计算相对时间
                    self.data_received.emit([values, relative_time]) # 发出数据接收信号，包含值和相对时间
                    self.buffer = self.buffer[tail_index + len(self.data_frame_tail):] # 移除已处理的数据帧及帧尾
                else:
                    # 如果帧尾前面数据不足，移除帧尾并继续查找
                    self.buffer = self.buffer[tail_index + len(self.data_frame_tail):]
            except ValueError:
                # 如果缓冲区中没有找到帧尾
                if len(self.buffer) > frame_length * 10:
                    # 如果缓冲区过大，可能存在错误数据，保留最后一部分
                    self.buffer = self.buffer[len(self.buffer) - frame_length:]
                break # 退出循环，等待更多数据

    def stop(self):
        self.running = False # 设置运行标志为 False，停止线程循环

def list_available_ports():
    """列出系统中所有可用的串口。"""
    ports = serial.tools.list_ports.comports() # 获取可用串口列表
    return [port.device for port in ports] # 返回串口设备名称列表