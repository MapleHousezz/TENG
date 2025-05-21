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

    def __init__(self, port, baudrate, stopbits, databits, parity, flowcontrol, start_time_with_offset=None):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.stopbits = stopbits
        self.databits = databits
        self.parity = parity
        self.flowcontrol = flowcontrol
        self.serial_port = None
        self.running = False
        self.data_frame_tail = bytes([0x00, 0x00, 0x80, 0x7f])
        self.buffer = bytearray()
        self.start_time = time.time() # 线程启动时的实际时间
        # 计算初始时间偏移量
        self.time_offset = 0.0
        if start_time_with_offset is not None:
             self.time_offset = self.start_time - start_time_with_offset

    def run(self):
        """线程主循环，处理串口连接和数据读取"""
        try:
            # 设置连接超时为2秒
            self.serial_port = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=self.databits,
                parity=self.parity,
                stopbits=self.stopbits,
                timeout=1,      # 读取超时时间
                write_timeout=2, # 写入超时时间
                rtscts=self.flowcontrol == 'RTS/CTS',
                xonxoff=self.flowcontrol == 'XON/XOFF'
            )
            
            # 测试串口是否真正可用
            try:
                self.serial_port.write(b'\n')  # 发送测试字节
                self.serial_port.flush()
            except serial.SerialTimeoutException:
                raise serial.SerialException("串口连接超时，请检查设备")
                
            self.running = True
            # 如果已有时间基准则使用，否则初始化
            if self.start_time is None:
                self.start_time = time.time()
                self.time_offset = 0.0
            self.status_changed.emit(f"已连接到 {self.port} @ {self.baudrate}")
            print(f"Serial port {self.port} opened successfully.")

            # 主循环
            while self.running:
                try:
                    # 非阻塞读取
                    if self.serial_port.in_waiting > 0:
                        data_byte = self.serial_port.read(self.serial_port.in_waiting)
                        if data_byte:  # 确保有数据
                            self.buffer.extend(data_byte)
                            self.process_buffer()
                    
                    # 更合理的休眠时间
                    time.sleep(0.01)  # 10ms休眠
                    
                except serial.SerialException as e:
                    self.status_changed.emit(f"串口读取错误: {e}")
                    break

        except serial.SerialException as e:
            self.status_changed.emit(f"串口错误: {e}") # 发出串口错误信号
            print(f"Serial error: {e}") # 打印串口错误信息
        finally:
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close() # 关闭串口
            self.status_changed.emit("串口已断开") # 发出串口断开信号
            print("Serial port closed.") # 打印串口关闭信息

    def process_buffer(self):
        """处理接收缓冲区中的数据，提取有效数据帧"""
        frame_length = 36  # 完整数据帧长度(32字节数据+4字节帧尾)
        max_buffer_size = frame_length * 10  # 最大缓冲区大小
        
        try:
            while len(self.buffer) >= frame_length:
                # 查找帧尾
                try:
                    tail_index = self.buffer.index(self.data_frame_tail)
                except ValueError:
                    # 没有找到帧尾，检查缓冲区是否过大
                    if len(self.buffer) > max_buffer_size:
                        self.buffer = self.buffer[-frame_length:]  # 保留最后可能的部分帧
                    break
                
                # 检查帧尾位置是否合理
                if tail_index < 32:
                    # 帧尾位置不正确，丢弃错误数据
                    self.buffer = self.buffer[tail_index + len(self.data_frame_tail):]
                    continue
                
                # 提取有效数据帧
                frame_start = tail_index - 32
                frame_data = self.buffer[frame_start:tail_index]
                
                # 解析8个浮点数值
                values = []
                try:
                    for i in range(8):
                        value_bytes = frame_data[i*4:(i+1)*4]
                        value = struct.unpack('<f', value_bytes)[0]
                        values.append(value)
                except struct.error:
                    # 数据解析错误，丢弃该帧
                    self.buffer = self.buffer[tail_index + len(self.data_frame_tail):]
                    continue
                
                # 计算相对时间，加上偏移量
                current_time = time.time()
                relative_time = (current_time - self.start_time) + self.time_offset

                # 发送有效数据
                self.data_received.emit([values, relative_time])
                
                # 移除已处理的数据
                self.buffer = self.buffer[tail_index + len(self.data_frame_tail):]
                
        except Exception as e:
            # 捕获所有处理异常，防止线程崩溃
            print(f"Buffer processing error: {e}")
            self.buffer = bytearray()  # 清空缓冲区

    def stop(self):
        """停止线程运行"""
        self.running = False
        
        # 保存当前时间偏移量
        if self.start_time is not None:
            self.time_offset = time.time() - self.start_time
            
        # 安全关闭串口
        if self.serial_port and self.serial_port.is_open:
            try:
                # 先取消读取操作
                self.serial_port.cancel_read()
                # 设置超时关闭
                self.serial_port.timeout = 0.1
                self.serial_port.write_timeout = 0.1
                # 尝试关闭串口
                self.serial_port.close()
            except Exception as e:
                print(f"关闭串口时出错: {e}")
            finally:
                # 确保串口被关闭
                if hasattr(self.serial_port, '_port_handle'):
                    try:
                        self.serial_port._port_handle = None
                    except:
                        pass
                    
        # 等待线程结束，但设置超时
        self.wait(2000)  # 最多等待2秒

def list_available_ports():
    """列出系统中所有可用的串口。"""
    ports = serial.tools.list_ports.comports() # 获取可用串口列表
    return [port.device for port in ports] # 返回串口设备名称列表