# 创建一个UI界面，解析串口数据
# 串口数据为16进制数据，的样本如下：
# 55 AA DC 4A B1 07 00 6A 00 00 F2 7D 19 
# 55 AA DC 8A B1 07 00 6A 00 00 F2 7D D9 
# 55 AA DC CA B1 07 00 6A 00 00 F2 7D 99 
# 55 AA DC 0A B1 07 00 6A 00 00 F2 7D 59 
# 55 AA DC 4A B1 07 00 6A 00 00 F2 7D 19 

# 帧头：55 AA DC

# 需要解析的数据（大端字节序）是第7-8个字节(角度Pitch)，即：00 6A；第9-10个字节(角度Roll)，即：00 00；第11-12个字节（角度Yaw），即：F2 7D

import struct
import serial
import serial.tools.list_ports
import tkinter as tk
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.animation as animation
from collections import deque

class AhrsUI:
    def __init__(self):
        # 创建主窗口
        self.root = tk.Tk()
        self.root.title("IMU Data Viewer")
        
        # 设置窗口最小尺寸
        self.root.minsize(600, 400)
        
        # 创建框架来容纳图表
        self.frame = tk.Frame(self.root)
        self.frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建图形
        self.fig, self.ax = plt.subplots(figsize=(6, 4))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # 配置图表自适应布局
        self.fig.tight_layout()
        
        # 绑定窗口调整大小事件
        self.frame.bind('<Configure>', self.on_resize)
        
        # 使用deque存储数据，限制最大长度
        max_points = 200
        self.pitch_data = deque(maxlen=max_points)
        self.roll_data = deque(maxlen=max_points)
        self.yaw_data = deque(maxlen=max_points)
        
        # 初始化图表线条
        self.x_data = np.arange(max_points)
        self.lines = []
        self.lines.append(self.ax.plot([], [], label='Pitch')[0])
        self.lines.append(self.ax.plot([], [], label='Roll')[0])
        self.lines.append(self.ax.plot([], [], label='Yaw')[0])
        
        # 设置图表
        self.ax.set_xlim(0, max_points)
        self.ax.set_ylim(-180, 180)
        self.ax.legend(loc='upper left')
        self.ax.set_title('IMU Data')
        self.ax.grid(True)
        
        # 尝试打开串口
        self.setup_serial()
        
        # 设置动画，降低更新频率
        self.ani = animation.FuncAnimation(
            self.fig, self.update_plot, interval=50,  # 增加间隔到50ms
            blit=True)  # 使用blitting提高性能

    def setup_serial(self):
        ports = serial.tools.list_ports.comports()
        if not ports:
            print("没有找到可用的串口!")
            return
        
        print("可用串口:")
        for port in ports:
            print(f"- {port.device}")
        
        try:
            self.ser = serial.Serial(ports[0].device, 115200, timeout=0.1)
            print(f"成功打开串口: {ports[0].device}")
        except serial.SerialException as e:
            print(f"打开串口失败: {e}")
            self.ser = None

    def parse_data(self, data):
        pitch = struct.unpack('>h', data[6:8])[0] * (360.0 / 65536.0)
        roll = struct.unpack('>h', data[8:10])[0] * (360.0 / 65536.0)
        yaw = struct.unpack('>h', data[10:12])[0] * (360.0 / 65536.0)
        return pitch, roll, yaw

    def update_plot(self, frame):
        if not hasattr(self, 'ser') or self.ser is None:
            return self.lines
        
        try:
            # 读取所有可用数据
            while self.ser.in_waiting:
                data = self.ser.read(1)
                if data == b'\x55':
                    data += self.ser.read(2)
                    if data == b'\x55\xAA\xDC':
                        data += self.ser.read(11)
                        if len(data) == 14:
                            pitch, roll, yaw = self.parse_data(data)
                            
                            # 更新数据
                            self.pitch_data.append(pitch)
                            self.roll_data.append(roll)
                            self.yaw_data.append(yaw)
                            
                            # 更新线条数据
                            y_datas = [self.pitch_data, self.roll_data, self.yaw_data]
                            for line, y_data in zip(self.lines, y_datas):
                                line.set_data(range(len(y_data)), y_data)
        
        except serial.SerialException as e:
            print(f"串口读取错误: {e}")
            self.ser = None
        
        return self.lines

    def run(self):
        self.root.mainloop()

    def cleanup(self):
        if hasattr(self, 'ser') and self.ser is not None:
            self.ser.close()

    def on_resize(self, event):
        # 当窗口大小改变时调整图表大小
        width = event.width / 100  # 将像素转换为英寸（近似值）
        height = event.height / 100
        self.fig.set_size_inches(width, height)
        # 更新布局
        self.fig.tight_layout()
        self.canvas.draw()

if __name__ == "__main__":
    app = AhrsUI()
    try:
        app.run()
    finally:
        app.cleanup()
