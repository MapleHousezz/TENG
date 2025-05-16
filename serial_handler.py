import serial
import serial.tools.list_ports
from PyQt5.QtCore import QThread, pyqtSignal
import struct
import time

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
        self.flowcontrol = flowcontrol
        self.serial_port = None
        self.running = False
        self.data_frame_tail = bytes([0x00, 0x00, 0x80, 0x7f])
        self.buffer = bytearray()

    def run(self):
        try:
            self.serial_port = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=self.databits,
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
                time.sleep(0.001)

        except serial.SerialException as e:
            self.status_changed.emit(f"串口错误: {e}")
            print(f"Serial error: {e}")
        finally:
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close()
            self.status_changed.emit("串口已断开")
            print("Serial port closed.")

    def process_buffer(self):
        frame_length = 36
        while len(self.buffer) >= frame_length:
            try:
                tail_index = self.buffer.index(self.data_frame_tail)
                if tail_index >= 32:
                    frame_data_start_index = tail_index - 32
                    frame_data = self.buffer[frame_data_start_index:tail_index]
                    
                    values = []
                    for i in range(8):
                        value_bytes = frame_data[i*4 : (i+1)*4]
                        value = struct.unpack('>f', value_bytes)[0]
                        values.append(value)
                    
                    self.data_received.emit(values)
                    self.buffer = self.buffer[tail_index + len(self.data_frame_tail):]
                else:
                    self.buffer = self.buffer[tail_index + len(self.data_frame_tail):]
            except ValueError:
                if len(self.buffer) > frame_length * 10:
                    self.buffer = self.buffer[len(self.buffer) - frame_length:]
                break

    def stop(self):
        self.running = False

def list_available_ports():
    ports = serial.tools.list_ports.comports()
    return [port.device for port in ports]