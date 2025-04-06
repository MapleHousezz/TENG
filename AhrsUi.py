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
from tkinter import messagebox
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import matplotlib.animation as animation
from collections import deque
import random
import time

class AhrsUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("IMU Data Viewer")
        self.root.minsize(800, 600)
        
        # 设置采样率
        self.sample_rate = 500  # 500Hz
        self.interval = 1000 / self.sample_rate
        
        # 创建主框架
        self.frame = tk.Frame(self.root)
        self.frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建控制面板框架
        self.control_frame = tk.Frame(self.root)
        self.control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 创建数据选择框架
        self.data_select_frame = tk.Frame(self.control_frame)
        self.data_select_frame.pack(side=tk.LEFT, padx=5)
        
        # 数据显示控制
        self.show_pitch = tk.BooleanVar(value=True)
        self.show_roll = tk.BooleanVar(value=True)
        self.show_yaw = tk.BooleanVar(value=True)
        
        tk.Checkbutton(self.data_select_frame, text="Pitch", variable=self.show_pitch, 
                      command=self.update_line_visibility).pack(side=tk.LEFT)
        tk.Checkbutton(self.data_select_frame, text="Roll", variable=self.show_roll,
                      command=self.update_line_visibility).pack(side=tk.LEFT)
        tk.Checkbutton(self.data_select_frame, text="Yaw", variable=self.show_yaw,
                      command=self.update_line_visibility).pack(side=tk.LEFT)
        
        # 创建按钮框架
        self.button_frame = tk.Frame(self.control_frame)
        self.button_frame.pack(side=tk.LEFT, padx=5)
        
        # 暂停/继续按钮
        self.is_paused = False
        self.pause_button = tk.Button(self.button_frame, text="暂停", command=self.toggle_pause)
        self.pause_button.pack(side=tk.LEFT, padx=2)
        
        # 导出按钮
        self.export_button = tk.Button(self.button_frame, text="导出数据", command=self.export_data)
        self.export_button.pack(side=tk.LEFT, padx=2)
        
        # 缩放重置按钮
        self.reset_zoom_button = tk.Button(self.button_frame, text="重置缩放", command=self.reset_zoom)
        self.reset_zoom_button.pack(side=tk.LEFT, padx=2)
        
        # 创建图表
        self.fig = plt.Figure(figsize=(8, 6), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.frame)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(fill=tk.BOTH, expand=True)
        
        # 启用缩放平移功能
        self.toolbar = NavigationToolbar2Tk(self.canvas, self.frame)
        self.toolbar.update()
        
        # 初始化数据
        self.max_points = 500000  # 可存储1000秒的数据
        self.pitch_data = deque(maxlen=self.max_points)
        self.roll_data = deque(maxlen=self.max_points)
        self.yaw_data = deque(maxlen=self.max_points)
        self.time_data = deque(maxlen=self.max_points)
        
        # 创建线条并设置样式
        self.lines = []
        self.lines.append(self.ax.plot([], [], label='Pitch', linewidth=1.5, color='red')[0])
        self.lines.append(self.ax.plot([], [], label='Roll', linewidth=1.5, color='green')[0])
        self.lines.append(self.ax.plot([], [], label='Yaw', linewidth=1.5, color='blue')[0])
        
        # 设置图表属性
        self.ax.grid(True, linestyle='--', alpha=0.7)
        self.ax.legend(loc='upper left')
        self.ax.set_title('IMU Data (500Hz)')
        self.ax.set_xlabel('Time (s)')
        self.ax.set_ylabel('Angle (degrees)')
        
        # 初始化时间和采样率监测
        self.start_time = time.time()
        self.last_update_time = self.start_time
        self.sample_count = 0
        self.last_rate_check = self.start_time
        
        # 创建动画
        self.ani = animation.FuncAnimation(
            self.fig, 
            self.update_plot, 
            interval=self.interval,
            blit=False
        )
        
        # 绑定鼠标事件
        self.canvas.mpl_connect('scroll_event', self.on_scroll)
        self.canvas.mpl_connect('button_press_event', self.on_press)
        self.canvas.mpl_connect('button_release_event', self.on_release)
        self.canvas.mpl_connect('motion_notify_event', self.on_motion)
        
        self.is_panning = False
        self.pan_start = None

    def generate_random_data(self):
        pitch = random.uniform(-1, 1)
        roll = random.uniform(-1, 1)
        yaw = random.uniform(-1, 1)
        
        last_pitch = self.pitch_data[-1] if self.pitch_data else 0
        last_roll = self.roll_data[-1] if self.roll_data else 0
        last_yaw = self.yaw_data[-1] if self.yaw_data else 0
        
        new_pitch = np.clip(last_pitch + pitch, -180, 180)
        new_roll = np.clip(last_roll + roll, -180, 180)
        new_yaw = np.clip(last_yaw + yaw, -180, 180)
        
        return new_pitch, new_roll, new_yaw

    def toggle_pause(self):
        """切换暂停/继续状态"""
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.pause_button.config(text="继续")
        else:
            self.pause_button.config(text="暂停")
    
    def export_data(self):
        """导出数据到文件"""
        try:
            with open('1.txt', 'w') as f:
                f.write("Time(s)\tPitch(deg)\tRoll(deg)\tYaw(deg)\n")
                for t, p, r, y in zip(self.time_data, self.pitch_data, self.roll_data, self.yaw_data):
                    f.write(f"{t:.3f}\t{p:.3f}\t{r:.3f}\t{y:.3f}\n")
            tk.messagebox.showinfo("成功", "数据已成功导出到1.txt")
        except Exception as e:
            tk.messagebox.showerror("错误", f"导出数据时发生错误：{str(e)}")

    def update_line_visibility(self):
        """更新数据线的可见性"""
        self.lines[0].set_visible(self.show_pitch.get())
        self.lines[1].set_visible(self.show_roll.get())
        self.lines[2].set_visible(self.show_yaw.get())
        self.canvas.draw()
    
    def reset_zoom(self):
        """重置缩放和平移"""
        self.ax.set_xlim(0, max(30, time.time() - self.start_time))
        self.ax.relim()
        self.ax.autoscale_view()
        self.canvas.draw()
    
    def on_scroll(self, event):
        """处理鼠标滚轮缩放"""
        if event.inaxes != self.ax:
            return
        
        cur_xlim = self.ax.get_xlim()
        cur_ylim = self.ax.get_ylim()
        xdata = event.xdata
        
        base_scale = 1.5
        
        if event.button == 'up':
            scale_factor = 1/base_scale
        else:
            scale_factor = base_scale
        
        new_width = (cur_xlim[1] - cur_xlim[0]) * scale_factor
        new_height = (cur_ylim[1] - cur_ylim[0]) * scale_factor
        
        relx = (cur_xlim[1] - xdata)/(cur_xlim[1] - cur_xlim[0])
        
        self.ax.set_xlim([xdata - new_width * (1-relx), xdata + new_width * relx])
        self.ax.set_ylim([cur_ylim[0], cur_ylim[0] + new_height])
        
        self.canvas.draw()
    
    def on_press(self, event):
        """处理鼠标按下事件"""
        if event.inaxes != self.ax:
            return
        self.is_panning = True
        self.pan_start = (event.xdata, event.ydata)
    
    def on_release(self, event):
        """处理鼠标释放事件"""
        self.is_panning = False
    
    def on_motion(self, event):
        """处理鼠标移动事件"""
        if not self.is_panning or event.inaxes != self.ax:
            return
            
        dx = event.xdata - self.pan_start[0]
        self.ax.set_xlim(self.ax.get_xlim() - dx)
        self.canvas.draw()
        
        self.pan_start = (event.xdata, event.ydata)

    def update_plot(self, frame):
        if self.is_paused:
            return self.lines
            
        current_time = time.time()
        if current_time - self.last_update_time < self.interval/1000:
            return self.lines
            
        # 更新采样率统计
        self.sample_count += 1
        if current_time - self.last_rate_check >= 1.0:
            actual_rate = self.sample_count / (current_time - self.last_rate_check)
            print(f"实际采样率: {actual_rate:.1f} Hz")
            self.sample_count = 0
            self.last_rate_check = current_time
        
        self.last_update_time = current_time
        elapsed_time = current_time - self.start_time
        
        pitch, roll, yaw = self.generate_random_data()
        
        self.time_data.append(elapsed_time)
        self.pitch_data.append(pitch)
        self.roll_data.append(roll)
        self.yaw_data.append(yaw)
        
        # 更新数据线
        for line, data in zip(self.lines, [self.pitch_data, self.roll_data, self.yaw_data]):
            if line.get_visible():
                line.set_data(self.time_data, data)
        
        # 自动滚动显示最新数据
        if not self.is_panning:
            self.ax.set_xlim(max(0, elapsed_time - 30), max(30, elapsed_time))
        
        self.ax.relim()
        self.ax.autoscale_view(scalex=False)
        
        return self.lines

    def on_window_resize(self, event):
        """处理窗口调整大小事件"""
        # 只处理主窗口的调整事件
        if event.widget == self.root:
            if self.resize_timer:
                self.root.after_cancel(self.resize_timer)
            
            self.resize_timer = self.root.after(200, self.perform_resize)

    def perform_resize(self):
        """执行实际的调整操作"""
        try:
            # 获取当前窗口大小
            width = self.frame.winfo_width()
            height = self.frame.winfo_height()
            
            # 确保最小尺寸
            width = max(width, 400)
            height = max(height, 300)
            
            # 计算合适的图表尺寸
            fig_width = width / 100
            fig_height = height / 100
            
            # 更新图表尺寸
            self.fig.set_size_inches(fig_width, fig_height, forward=True)
            
            # 更新布局
            self.fig.tight_layout()
            
            # 重绘画布
            self.canvas.draw()
            
        except Exception as e:
            print(f"Resize error: {e}")
        finally:
            self.resize_timer = None

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = AhrsUI()
    app.run()  # 这行现在正确缩进了
