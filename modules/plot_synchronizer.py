# modules/plot_synchronizer.py
#
# 图表同步模块
# 负责管理多个图表的视图同步、范围设置和交互
#

from PyQt5.QtCore import QObject, pyqtSignal

class PlotSynchronizer(QObject):
    """图表同步器，负责同步多个图表的视图范围和交互"""
    
    # 定义信号
    range_changed = pyqtSignal(float, float)  # 范围改变信号
    
    def __init__(self, plot_widgets=None):
        super().__init__()
        self.plot_widgets = plot_widgets or []
        self.is_synchronizing = False  # 防止递归同步
        
    def set_plot_widgets(self, plot_widgets):
        """设置要同步的图表控件列表"""
        self.plot_widgets = plot_widgets
        
    def add_plot_widget(self, plot_widget):
        """添加图表控件到同步列表"""
        if plot_widget not in self.plot_widgets:
            self.plot_widgets.append(plot_widget)
            
    def remove_plot_widget(self, plot_widget):
        """从同步列表中移除图表控件"""
        if plot_widget in self.plot_widgets:
            self.plot_widgets.remove(plot_widget)
            
    def synchronize_x_ranges(self, changed_vb, new_x_range):
        """同步所有图表的X轴范围
        
        Args:
            changed_vb: 发生变化的ViewBox
            new_x_range: 新的X轴范围 (min, max)
        """
        if self.is_synchronizing:
            return
            
        self.is_synchronizing = True
        
        try:
            for plot_widget in self.plot_widgets:
                vb = plot_widget.getViewBox()
                if vb is not changed_vb:
                    vb.setXRange(new_x_range[0], new_x_range[1], padding=0)
                    
            # 发出范围改变信号
            self.range_changed.emit(new_x_range[0], new_x_range[1])
            
        finally:
            self.is_synchronizing = False
            
    def set_all_x_ranges(self, min_time, max_time, padding=0.01):
        """设置所有图表的X轴范围
        
        Args:
            min_time: 最小时间
            max_time: 最大时间
            padding: 边距比例
        """
        if self.is_synchronizing:
            return
            
        self.is_synchronizing = True
        
        try:
            for plot_widget in self.plot_widgets:
                vb = plot_widget.getViewBox()
                vb.setXRange(min_time, max_time, padding=padding)
                
        finally:
            self.is_synchronizing = False
            
    def set_all_y_ranges(self, min_voltage, max_voltage, padding=0.01):
        """设置所有图表的Y轴范围
        
        Args:
            min_voltage: 最小电压
            max_voltage: 最大电压
            padding: 边距比例
        """
        for plot_widget in self.plot_widgets:
            vb = plot_widget.getViewBox()
            vb.setYRange(min_voltage, max_voltage, padding=padding)
            
    def reset_all_ranges_to_data(self, data_manager):
        """根据数据重置所有图表的范围
        
        Args:
            data_manager: 数据管理器实例
        """
        if self.is_synchronizing:
            return
            
        self.is_synchronizing = True
        
        try:
            # 获取数据时间范围
            start_time, end_time = data_manager.get_time_range()
            
            # 如果数据范围太小，设置最小显示窗口
            if (end_time - start_time) < 5.0:
                end_time = start_time + 5.0
                
            # 设置所有图表的范围
            for plot_widget in self.plot_widgets:
                vb = plot_widget.getViewBox()
                vb.setXRange(start_time, end_time, padding=0.01)
                # Y轴通常固定在0-3.3V范围
                vb.setYRange(0, 3.3, padding=0.01)
                
        finally:
            self.is_synchronizing = False
            
    def reset_to_default_view(self):
        """重置到默认视图"""
        if self.is_synchronizing:
            return
            
        self.is_synchronizing = True
        
        try:
            for plot_widget in self.plot_widgets:
                vb = plot_widget.getViewBox()
                vb.setXRange(0.0, 5.0, padding=0.01)  # 默认显示5秒
                vb.setYRange(0, 3.3, padding=0.01)    # 电压范围0-3.3V
                
        finally:
            self.is_synchronizing = False
            
    def auto_range_all(self):
        """自动调整所有图表的范围"""
        for plot_widget in self.plot_widgets:
            vb = plot_widget.getViewBox()
            vb.autoRange()
            
    def enable_auto_range(self, enable=True):
        """启用或禁用自动范围调整
        
        Args:
            enable: 是否启用自动范围
        """
        for plot_widget in self.plot_widgets:
            vb = plot_widget.getViewBox()
            vb.enableAutoRange(enable=enable)
            
    def set_mouse_enabled(self, x=True, y=True):
        """设置鼠标交互是否启用
        
        Args:
            x: 是否启用X轴鼠标交互
            y: 是否启用Y轴鼠标交互
        """
        for plot_widget in self.plot_widgets:
            vb = plot_widget.getViewBox()
            vb.setMouseEnabled(x=x, y=y)
            
    def get_current_x_range(self):
        """获取当前X轴范围
        
        Returns:
            tuple: (min_time, max_time) 如果有图表的话
        """
        if self.plot_widgets:
            vb = self.plot_widgets[0].getViewBox()
            x_range = vb.viewRange()[0]
            return x_range[0], x_range[1]
        return 0.0, 5.0
        
    def get_current_y_range(self):
        """获取当前Y轴范围
        
        Returns:
            tuple: (min_voltage, max_voltage) 如果有图表的话
        """
        if self.plot_widgets:
            vb = self.plot_widgets[0].getViewBox()
            y_range = vb.viewRange()[1]
            return y_range[0], y_range[1]
        return 0.0, 3.3
        
    def zoom_to_time_range(self, start_time, end_time):
        """缩放到指定的时间范围
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
        """
        self.set_all_x_ranges(start_time, end_time)
        
    def pan_by_time(self, time_delta):
        """按时间增量平移视图
        
        Args:
            time_delta: 时间增量（正数向右，负数向左）
        """
        if not self.plot_widgets:
            return
            
        current_min, current_max = self.get_current_x_range()
        new_min = current_min + time_delta
        new_max = current_max + time_delta
        
        self.set_all_x_ranges(new_min, new_max)
        
    def zoom_by_factor(self, factor, center_time=None):
        """按比例缩放视图
        
        Args:
            factor: 缩放因子（>1放大，<1缩小）
            center_time: 缩放中心时间（None表示使用当前视图中心）
        """
        if not self.plot_widgets:
            return
            
        current_min, current_max = self.get_current_x_range()
        current_range = current_max - current_min
        
        if center_time is None:
            center_time = (current_min + current_max) / 2
            
        new_range = current_range / factor
        new_min = center_time - new_range / 2
        new_max = center_time + new_range / 2
        
        self.set_all_x_ranges(new_min, new_max)