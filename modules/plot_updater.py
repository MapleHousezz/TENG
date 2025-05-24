# modules/plot_updater.py
#
# 图表更新模块
# 负责处理图表的实时数据更新、线条绘制和标签更新
#

import time
from PyQt5.QtCore import QObject, pyqtSignal

class PlotUpdater(QObject):
    """图表更新器，负责实时更新图表显示"""
    
    # 定义信号
    voltage_updated = pyqtSignal(int, float)  # 电压更新信号 (channel, voltage)
    plot_updated = pyqtSignal()               # 图表更新完成信号
    
    def __init__(self, plot_widgets=None, data_lines=None, voltage_labels=None):
        super().__init__()
        self.plot_widgets = plot_widgets or []
        self.data_lines = data_lines or []
        self.voltage_labels = voltage_labels or []
        
        # 性能优化参数
        self._last_update_time = 0
        self._update_frequency_limit = 0.05  # 20Hz更新频率限制
        self._last_data_cache = {}
        
    def set_components(self, plot_widgets, data_lines, voltage_labels):
        """设置图表组件
        
        Args:
            plot_widgets: 图表控件列表
            data_lines: 数据线条列表
            voltage_labels: 电压标签列表
        """
        self.plot_widgets = plot_widgets
        self.data_lines = data_lines
        self.voltage_labels = voltage_labels
        
    def update_plots_from_data(self, data_manager, force_update=False):
        """从数据管理器更新图表
        
        Args:
            data_manager: 数据管理器实例
            force_update: 是否强制更新（忽略频率限制）
            
        Returns:
            bool: 是否执行了更新
        """
        # 频率限制检查
        current_time = time.time()
        if not force_update and (current_time - self._last_update_time) < self._update_frequency_limit:
            return False
            
        try:
            # 更新所有通道的数据线条
            for i in range(min(8, len(self.data_lines))):
                channel_data = data_manager.get_channel_data(i)
                if channel_data:
                    # 检查数据是否有变化
                    data_hash = hash(str(channel_data[-5:]))  # 使用最后5个数据点的哈希
                    if force_update or self._last_data_cache.get(i) != data_hash:
                        times = [item[1] for item in channel_data]
                        voltages = [item[0] for item in channel_data]
                        self.data_lines[i].setData(times, voltages)
                        self._last_data_cache[i] = data_hash
                        
            # 更新时间轴范围
            if data_manager.has_data():
                start_time, end_time = data_manager.get_time_range()
                self._update_x_axis_range(start_time, end_time)
                
            self._last_update_time = current_time
            self.plot_updated.emit()
            return True
            
        except Exception as e:
            print(f"图表更新错误: {e}")
            return False
            
    def update_voltage_labels(self, values, is_active=True):
        """更新电压标签显示
        
        Args:
            values: 8个通道的电压值列表
            is_active: 是否为活跃状态（影响显示格式）
        """
        for i in range(min(8, len(self.voltage_labels), len(values))):
            voltage = values[i]
            if is_active:
                self.voltage_labels[i].setText(f"CH{i+1}: {voltage:.3f} V")
            else:
                self.voltage_labels[i].setText(f"CH{i+1}: {voltage:.3f} V")
            
            # 发出电压更新信号
            self.voltage_updated.emit(i, voltage)
            
    def update_voltage_labels_from_mouse(self, mouse_x, data_manager):
        """根据鼠标位置更新电压标签（显示插值电压）
        
        Args:
            mouse_x: 鼠标X坐标（时间）
            data_manager: 数据管理器实例
        """
        voltage_strings = ["--- V"] * 8
        
        for ch_idx in range(8):
            if ch_idx < len(self.data_lines):
                # 从数据管理器获取插值电压
                interpolated_voltage = data_manager.interpolate_voltage_at_time(ch_idx, mouse_x)
                voltage_strings[ch_idx] = f"{interpolated_voltage:.3f} V"
            else:
                voltage_strings[ch_idx] = "--- V"
                
        # 更新所有电压标签
        for ch_idx in range(min(8, len(self.voltage_labels))):
            self.voltage_labels[ch_idx].setText(f"CH{ch_idx+1}: {voltage_strings[ch_idx]}")
            
    def reset_voltage_labels(self):
        """重置电压标签为默认值"""
        for i in range(min(8, len(self.voltage_labels))):
            self.voltage_labels[i].setText(f"CH{i+1}: 0.000 V")
            
    def clear_all_plots(self):
        """清除所有图表数据"""
        for i in range(len(self.data_lines)):
            self.data_lines[i].setData([], [])
        self.reset_voltage_labels()
        self._last_data_cache.clear()
        
    def _update_x_axis_range(self, start_time, end_time):
        """更新X轴范围（仅在数据超出当前视图时）
        
        Args:
            start_time: 数据开始时间
            end_time: 数据结束时间
        """
        if not self.plot_widgets:
            return
            
        # 获取当前视图范围
        current_view_range = self.plot_widgets[0].getViewBox().viewRange()[0]
        current_min, current_max = current_view_range
        
        # 检查是否需要调整范围
        need_update = False
        new_min, new_max = current_min, current_max
        
        # 如果新数据超出当前视图右边界，扩展视图
        if end_time > current_max:
            new_max = end_time
            new_min = start_time  # 显示所有数据
            need_update = True
            
        if need_update:
            for plot_widget in self.plot_widgets:
                plot_widget.getViewBox().setXRange(new_min, new_max, padding=0.01)
                
    def set_update_frequency_limit(self, frequency_hz):
        """设置更新频率限制
        
        Args:
            frequency_hz: 最大更新频率（Hz）
        """
        if frequency_hz > 0:
            self._update_frequency_limit = 1.0 / frequency_hz
        else:
            self._update_frequency_limit = 0
            
    def get_plot_performance_stats(self):
        """获取图表性能统计信息
        
        Returns:
            dict: 性能统计信息
        """
        current_time = time.time()
        time_since_last_update = current_time - self._last_update_time
        
        return {
            'last_update_time': self._last_update_time,
            'time_since_last_update': time_since_last_update,
            'update_frequency_limit': self._update_frequency_limit,
            'cached_channels': len(self._last_data_cache),
            'plot_widgets_count': len(self.plot_widgets),
            'data_lines_count': len(self.data_lines)
        }
        
    def force_refresh_all(self, data_manager):
        """强制刷新所有图表
        
        Args:
            data_manager: 数据管理器实例
        """
        # 清除缓存以强制更新
        self._last_data_cache.clear()
        
        # 强制更新
        self.update_plots_from_data(data_manager, force_update=True)
        
    def set_line_properties(self, channel, **kwargs):
        """设置指定通道线条的属性
        
        Args:
            channel: 通道索引 (0-7)
            **kwargs: 线条属性（如color, width等）
        """
        if 0 <= channel < len(self.data_lines):
            line = self.data_lines[channel]
            if 'color' in kwargs:
                line.setPen(color=kwargs['color'])
            if 'width' in kwargs:
                pen = line.opts['pen']
                pen.setWidth(kwargs['width'])
                line.setPen(pen)
                
    def highlight_channel(self, channel, highlight=True):
        """高亮显示指定通道
        
        Args:
            channel: 通道索引 (0-7)
            highlight: 是否高亮
        """
        if 0 <= channel < len(self.data_lines):
            line = self.data_lines[channel]
            if highlight:
                # 增加线条宽度和亮度
                pen = line.opts['pen']
                pen.setWidth(3)
                line.setPen(pen)
            else:
                # 恢复正常线条
                pen = line.opts['pen']
                pen.setWidth(1)
                line.setPen(pen)