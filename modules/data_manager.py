# modules/data_manager.py
#
# 数据管理模块
# 负责管理图表数据的存储、更新和缓存
#

import time
from PyQt5.QtCore import QObject, pyqtSignal

class DataManager(QObject):
    """数据管理器，负责处理双缓存数据存储和更新"""
    
    # 定义信号
    data_updated = pyqtSignal(list, float)  # 数据更新信号
    
    def __init__(self):
        super().__init__()
        # 使用双缓存数据存储
        self.display_data = [[] for _ in range(8)]  # 用于显示的数据
        self.full_data = [[] for _ in range(8)]     # 完整历史数据
        self.data_acquisition_start_time = None    # 数据采集开始时间
        self._last_update_time = 0                 # 上次更新时间
        
    def add_data_point(self, values, current_time_s):
        """添加新的数据点"""
        # 限制数据处理频率 (20Hz)
        if time.time() - self._last_update_time < 0.05:
            return False
            
        # 初始化开始时间
        if self.data_acquisition_start_time is None:
            self.data_acquisition_start_time = current_time_s
            
        # 添加数据到完整数据集
        for i in range(8):
            if i < len(values):
                voltage = values[i]
                self.full_data[i].append((voltage, current_time_s))
                
        # 记录最后更新时间
        self._last_update_time = time.time()
        
        # 发出数据更新信号
        self.data_updated.emit(values, current_time_s)
        return True
        
    def get_channel_data(self, channel_index):
        """获取指定通道的数据"""
        if 0 <= channel_index < 8:
            return self.full_data[channel_index]
        return []
        
    def get_all_data(self):
        """获取所有通道的数据"""
        return self.full_data
        
    def get_time_range(self):
        """获取数据的时间范围"""
        if self.full_data and self.full_data[0]:
            start_time = self.full_data[0][0][1]
            end_time = self.full_data[0][-1][1]
            return start_time, end_time
        return 0.0, 5.0
        
    def clear_data(self):
        """清除所有数据"""
        for i in range(8):
            self.display_data[i].clear()
            self.full_data[i].clear()
        self.data_acquisition_start_time = None
        
    def has_data(self):
        """检查是否有数据"""
        return any(len(channel) > 0 for channel in self.full_data)
        
    def get_latest_values(self):
        """获取最新的电压值"""
        latest_values = []
        for i in range(8):
            if self.full_data[i]:
                latest_values.append(self.full_data[i][-1][0])
            else:
                latest_values.append(0.0)
        return latest_values
        
    def interpolate_voltage_at_time(self, channel_index, target_time):
        """在指定时间点插值电压值"""
        if not (0 <= channel_index < 8) or not self.full_data[channel_index]:
            return 0.0
            
        data = self.full_data[channel_index]
        
        # 如果目标时间在数据范围之外
        if target_time <= data[0][1]:
            return data[0][0]
        if target_time >= data[-1][1]:
            return data[-1][0]
            
        # 查找插值点
        for i in range(len(data) - 1):
            if data[i][1] <= target_time <= data[i+1][1]:
                # 线性插值
                t1, v1 = data[i][1], data[i][0]
                t2, v2 = data[i+1][1], data[i+1][0]
                if t2 == t1:
                    return v1
                return v1 + (target_time - t1) * (v2 - v1) / (t2 - t1)
                
        return 0.0