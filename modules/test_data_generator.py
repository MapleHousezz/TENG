# modules/test_data_generator.py
#
# 测试数据生成模块
# 负责生成模拟的触摸传感器数据用于测试
#

import random
import time
from PyQt5.QtCore import QObject, QTimer, pyqtSignal

class TestDataGenerator(QObject):
    """测试数据生成器，用于生成模拟的传感器数据"""
    
    # 定义信号
    data_generated = pyqtSignal(list, float)  # 生成数据信号 (values, timestamp)
    generation_finished = pyqtSignal()        # 生成完成信号
    
    def __init__(self):
        super().__init__()
        self.timer = QTimer()
        self.timer.timeout.connect(self._generate_data_point)
        
        # 生成参数
        self.is_generating = False
        self.frequency_hz = 1.0
        self.duration_seconds = 10.0
        self.start_time = None
        self.total_points = 0
        
        # 数据生成参数
        self.touch_threshold = 0.5
        self.signal_high = 2.5
        self.signal_low_range = (0.1, 0.3)
        self.noise_range = (-0.2, 0.2)
        self.voltage_range = (0.0, 3.3)
        
    def start_generation(self, frequency_hz=1.0, duration_seconds=10.0):
        """开始生成测试数据
        
        Args:
            frequency_hz: 生成频率 (Hz)
            duration_seconds: 持续时间 (秒)
        """
        if self.is_generating:
            return False
            
        self.frequency_hz = frequency_hz
        self.duration_seconds = duration_seconds
        self.start_time = time.time()
        self.total_points = 0
        self.is_generating = True
        
        # 计算定时器间隔
        if frequency_hz > 0:
            interval_ms = int(1000 / frequency_hz)
        else:
            interval_ms = 1000
            
        self.timer.start(interval_ms)
        return True
        
    def stop_generation(self):
        """停止生成测试数据"""
        if not self.is_generating:
            return False
            
        self.timer.stop()
        self.is_generating = False
        return True
        
    def _generate_data_point(self):
        """生成单个数据点"""
        # 检查是否超过持续时间
        if self.start_time and time.time() - self.start_time >= self.duration_seconds:
            self.stop_generation()
            self.generation_finished.emit()
            return
            
        # 生成模拟触摸点
        simulated_touch_row = random.randint(0, 3)
        simulated_touch_col = random.randint(0, 3)
        
        test_values = []
        
        # 生成8个通道的数据
        for i in range(8):
            if i < 4:  # 行信号 (CH1-CH4)
                if i == simulated_touch_row:
                    # 模拟触摸行的峰值
                    value = self.signal_high + random.uniform(*self.noise_range)
                else:
                    # 模拟其他行的背景噪声
                    value = random.uniform(*self.signal_low_range)
            else:  # 列信号 (CH5-CH8)
                if (i - 4) == simulated_touch_col:
                    # 模拟触摸列的峰值
                    value = self.signal_high + random.uniform(*self.noise_range)
                else:
                    # 模拟其他列的背景噪声
                    value = random.uniform(*self.signal_low_range)
                    
            # 确保值在有效范围内
            value = max(self.voltage_range[0], min(self.voltage_range[1], value))
            test_values.append(value)
            
        # 生成时间戳
        current_time = time.time()
        if self.start_time:
            relative_time = current_time - self.start_time
        else:
            relative_time = 0.0
            
        self.total_points += 1
        
        # 发出数据生成信号
        self.data_generated.emit(test_values, relative_time)
        
    def generate_single_point(self):
        """生成单个数据点（不使用定时器）
        
        Returns:
            tuple: (values, timestamp)
        """
        # 生成随机触摸点
        simulated_touch_row = random.randint(0, 3)
        simulated_touch_col = random.randint(0, 3)
        
        test_values = []
        
        for i in range(8):
            if i < 4:  # 行信号
                if i == simulated_touch_row:
                    value = self.signal_high + random.uniform(*self.noise_range)
                else:
                    value = random.uniform(*self.signal_low_range)
            else:  # 列信号
                if (i - 4) == simulated_touch_col:
                    value = self.signal_high + random.uniform(*self.noise_range)
                else:
                    value = random.uniform(*self.signal_low_range)
                    
            value = max(self.voltage_range[0], min(self.voltage_range[1], value))
            test_values.append(value)
            
        return test_values, time.time()
        
    def set_signal_parameters(self, signal_high=2.5, signal_low_range=(0.1, 0.3), 
                             noise_range=(-0.2, 0.2), voltage_range=(0.0, 3.3)):
        """设置信号生成参数
        
        Args:
            signal_high: 触摸信号的高电平
            signal_low_range: 背景噪声的范围
            noise_range: 信号噪声的范围
            voltage_range: 电压的有效范围
        """
        self.signal_high = signal_high
        self.signal_low_range = signal_low_range
        self.noise_range = noise_range
        self.voltage_range = voltage_range
        
    def get_generation_status(self):
        """获取生成状态信息
        
        Returns:
            dict: 包含生成状态的字典
        """
        elapsed_time = 0.0
        if self.start_time:
            elapsed_time = time.time() - self.start_time
            
        return {
            'is_generating': self.is_generating,
            'frequency_hz': self.frequency_hz,
            'duration_seconds': self.duration_seconds,
            'elapsed_time': elapsed_time,
            'total_points': self.total_points,
            'remaining_time': max(0, self.duration_seconds - elapsed_time)
        }