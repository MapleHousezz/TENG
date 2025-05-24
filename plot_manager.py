# plot_manager_new.py
#
# 重构后的图表管理器
# 使用模块化设计，将原来的大文件拆分为多个专门的模块
#

import time
from PyQt5.QtCore import QTimer, QObject, pyqtSignal
from PyQt5.QtWidgets import QMessageBox

# 导入自定义模块
from modules.data_manager import DataManager
from modules.touch_detector import TouchDetector
from modules.test_data_generator import TestDataGenerator
from modules.data_exporter import DataExporter
from modules.plot_synchronizer import PlotSynchronizer
from modules.plot_updater import PlotUpdater

class PlotManager(QObject):
    """重构后的图表管理器
    
    使用模块化设计，将功能分散到不同的专门模块中：
    - DataManager: 数据存储和管理
    - TouchDetector: 触摸点检测
    - TestDataGenerator: 测试数据生成
    - DataExporter: 数据导出
    - PlotSynchronizer: 图表同步
    - PlotUpdater: 图表更新
    """
    
    # 定义信号
    update_pixel_map_signal = pyqtSignal(int, int)  # 发送触摸像素的行和列的信号
    update_digital_matrix_signal = pyqtSignal(int, int, float)  # 发送行、列和时间的信号
    
    def __init__(self, main_window, plot_widgets, data_lines, voltage_labels, 
                 sample_interval_s, test_data_button, status_bar, test_data_timer, 
                 pixel_labels, frequency_spinbox, digital_matrix_labels):
        super().__init__()
        
        # 保存主要组件引用
        self.main_window = main_window
        self.plot_widgets = plot_widgets
        self.data_lines = data_lines
        self.voltage_labels = voltage_labels
        self.sample_interval_s = sample_interval_s
        self.test_data_button = test_data_button
        self.status_bar = status_bar
        self.test_data_timer = test_data_timer
        self.pixel_labels = pixel_labels
        self.frequency_spinbox = frequency_spinbox
        self.digital_matrix_labels = digital_matrix_labels
        self.duration_spinbox = None
        
        # 初始化各个功能模块
        self._init_modules()
        
        # 连接信号
        self._connect_signals()
        
        # 状态变量
        self.is_generating_test_data = False
        self.serial_thread_running = False
        
    def _init_modules(self):
        """初始化各个功能模块"""
        # 数据管理模块
        self.data_manager = DataManager()
        
        # 触摸检测模块
        self.touch_detector = TouchDetector(touch_threshold=0.5)
        
        # 测试数据生成模块
        self.test_data_generator = TestDataGenerator()
        
        # 数据导出模块
        self.data_exporter = DataExporter(parent=self.main_window)
        
        # 图表同步模块
        self.plot_synchronizer = PlotSynchronizer(self.plot_widgets)
        
        # 图表更新模块
        self.plot_updater = PlotUpdater(self.plot_widgets, self.data_lines, self.voltage_labels)
        
    def _connect_signals(self):
        """连接各模块之间的信号"""
        # 数据管理器信号
        self.data_manager.data_updated.connect(self._on_data_updated)
        
        # 触摸检测器信号
        self.touch_detector.touch_detected.connect(self.update_pixel_map_signal.emit)
        self.touch_detector.touch_with_time.connect(self.update_digital_matrix_signal.emit)
        
        # 测试数据生成器信号
        self.test_data_generator.data_generated.connect(self._on_test_data_generated)
        self.test_data_generator.generation_finished.connect(self._on_test_generation_finished)
        
        # 数据导出器信号
        self.data_exporter.export_completed.connect(self._on_export_completed)
        self.data_exporter.export_failed.connect(self._on_export_failed)
        
    def update_plots(self, data):
        """更新图表数据（主要入口点）
        
        Args:
            data: [values, current_time_s] 格式的数据
        """
        # 检查数据有效性
        if not data or len(data) < 2:
            return
            
        values = data[0]
        current_time_s = data[1]
        
        # 检查数据格式
        if not values or len(values) < 8:
            return
            
        try:
            # 添加数据到数据管理器
            if self.data_manager.add_data_point(values, current_time_s):
                # 更新图表显示
                self.plot_updater.update_plots_from_data(self.data_manager)
                
                # 更新电压标签（如果正在采集数据）
                if self._is_data_acquisition_active():
                    self.plot_updater.update_voltage_labels(values, is_active=True)
                    
                # 触摸检测
                self.touch_detector.detect_touch(values, current_time_s)
                
        except Exception as e:
            print(f"图表更新错误: {e}")
            
    def _on_data_updated(self, values, current_time_s):
        """数据更新回调"""
        # 这里可以添加额外的数据更新处理逻辑
        pass
        
    def _on_test_data_generated(self, values, timestamp):
        """测试数据生成回调"""
        # 将生成的测试数据传递给更新函数
        self.update_plots([values, timestamp])
        
    def _on_test_generation_finished(self):
        """测试数据生成完成回调"""
        self._stop_test_data_generation()
        duration = self.test_data_generator.duration_seconds
        self.status_bar.showMessage(f"测试数据采集已完成 (持续时间: {duration} 秒)")
        
    def _on_export_completed(self, filename):
        """数据导出完成回调"""
        self.status_bar.showMessage(f"数据已导出到 {filename}")
        
    def _on_export_failed(self, error_msg):
        """数据导出失败回调"""
        self.status_bar.showMessage(f"导出失败: {error_msg}")
        
    def toggle_test_data_generation(self):
        """切换测试数据生成状态"""
        if not self.is_generating_test_data:
            self._start_test_data_generation()
        else:
            self._stop_test_data_generation()
            
    def _start_test_data_generation(self):
        """开始生成测试数据"""
        # 获取参数
        frequency_hz = self.frequency_spinbox.value()
        
        # 获取持续时间
        self.duration_spinbox = getattr(self.main_window, 'duration_spinbox', None)
        duration_seconds = self.duration_spinbox.value() if self.duration_spinbox else 10
        
        # 开始生成
        if self.test_data_generator.start_generation(frequency_hz, duration_seconds):
            self.is_generating_test_data = True
            self.test_data_button.setText("停止生成")
            self.status_bar.showMessage(f"测试数据采集中 ({frequency_hz} Hz, {duration_seconds} 秒)...")
        
    def _stop_test_data_generation(self):
        """停止生成测试数据"""
        self.test_data_generator.stop_generation()
        self.is_generating_test_data = False
        self.test_data_button.setText("生成测试数据")
        self.status_bar.showMessage("测试数据采集已停止")
        
    def export_data_to_csv(self):
        """导出数据到CSV文件"""
        return self.data_exporter.export_to_csv(self.data_manager, self.sample_interval_s)
        
    def export_data_to_json(self, metadata=None):
        """导出数据到JSON文件"""
        return self.data_exporter.export_to_json(self.data_manager, metadata)
        
    def export_summary_report(self, touch_events=None):
        """导出摘要报告"""
        return self.data_exporter.export_summary_report(self.data_manager, touch_events)
        
    def _mouse_moved_on_plot(self, pos, plot_widget, plot_index):
        """鼠标在图表上移动的处理"""
        vb = plot_widget.getViewBox()
        if plot_widget.sceneBoundingRect().contains(pos):
            mouse_point = vb.mapSceneToView(pos)
            mouse_x = mouse_point.x()
            
            # 更新电压标签显示鼠标位置的插值电压
            self.plot_updater.update_voltage_labels_from_mouse(mouse_x, self.data_manager)
            
    def synchronize_x_ranges(self, changed_vb, new_x_range):
        """同步X轴范围"""
        self.plot_synchronizer.synchronize_x_ranges(changed_vb, new_x_range)
        
    def _reset_all_x_ranges_to_data_range(self, changed_vb):
        """重置所有X轴范围到数据范围"""
        self.plot_synchronizer.reset_all_ranges_to_data(self.data_manager)
        
    def _clear_plot_data(self):
        """清除图表数据"""
        # 清除数据管理器中的数据
        self.data_manager.clear_data()
        
        # 清除图表显示
        self.plot_updater.clear_all_plots()
        
        # 重置主窗口的时间偏移量
        if hasattr(self.main_window, 'last_time_offset'):
            self.main_window.last_time_offset = 0.0
            
        # 清除像素地图
        self.update_pixel_map_signal.emit(-1, -1)
        
    def _reset_plot_views(self):
        """重置图表视图"""
        if self.data_manager.has_data():
            self.plot_synchronizer.reset_all_ranges_to_data(self.data_manager)
        else:
            self.plot_synchronizer.reset_to_default_view()
            
    def linear_interpolate(self, x, x1, y1, x2, y2):
        """线性插值（保持向后兼容）"""
        if x1 == x2:
            return y1
        return y1 + (x - x1) * (y2 - y1) / (x2 - x1)
        
    def _is_data_acquisition_active(self):
        """检查数据采集是否活跃"""
        return (self.is_generating_test_data or 
                (self.main_window and 
                 getattr(self.main_window, 'serial_manager', None) and 
                 getattr(self.main_window.serial_manager, 'serial_thread', None) is not None))
                 
    # 公共接口方法
    def get_data_manager(self):
        """获取数据管理器实例"""
        return self.data_manager
        
    def get_touch_detector(self):
        """获取触摸检测器实例"""
        return self.touch_detector
        
    def get_test_data_generator(self):
        """获取测试数据生成器实例"""
        return self.test_data_generator
        
    def get_data_exporter(self):
        """获取数据导出器实例"""
        return self.data_exporter
        
    def get_plot_synchronizer(self):
        """获取图表同步器实例"""
        return self.plot_synchronizer
        
    def get_plot_updater(self):
        """获取图表更新器实例"""
        return self.plot_updater
        
    def set_touch_threshold(self, threshold):
        """设置触摸检测阈值"""
        self.touch_detector.set_threshold(threshold)
        
    def get_current_data_stats(self):
        """获取当前数据统计信息"""
        if not self.data_manager.has_data():
            return None
            
        stats = {
            'has_data': True,
            'time_range': self.data_manager.get_time_range(),
            'latest_values': self.data_manager.get_latest_values(),
            'data_points': len(self.data_manager.get_channel_data(0)),
            'is_generating_test_data': self.is_generating_test_data,
            'is_serial_active': self.serial_thread_running
        }
        
        return stats