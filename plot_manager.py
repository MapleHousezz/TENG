# plot_manager.py
#
# 文件功能说明:
# 该文件包含 PlotManager 类，负责管理 PyQtGraph 图表的实时数据更新、
# 触摸点检测、测试数据生成、数据导出以及图表视图的同步和重置。
# 它处理从数据源（如串口）接收到的数据，更新图表线条、电压标签、
# 像素地图和数字矩阵显示。
#

import pyqtgraph as pg
import time
import random
import math
import csv
import os
from PyQt5.QtCore import QTimer, QObject, pyqtSignal # 导入 QTimer, QObject, pyqtSignal
from PyQt5.QtWidgets import QMessageBox, QFileDialog # 导入 QMessageBox, QFileDialog

class PlotManager(QObject): # 继承自 QObject 以使用信号/槽
    # 定义信号
    update_pixel_map_signal = pyqtSignal(int, int) # 发送触摸像素的行和列的信号
    update_digital_matrix_signal = pyqtSignal(int, int, float) # 发送行、列和时间的信号

    def __init__(self, main_window, plot_widgets, data_lines, voltage_labels, sample_interval_s, test_data_button, status_bar, test_data_timer, pixel_labels, frequency_spinbox, points_spinbox, digital_matrix_labels): # 添加 main_window 和 digital_matrix_labels 参数
        super().__init__() # 调用 QObject 构造函数
        self.main_window = main_window # 保存 MainWindow 引用
        self.plot_widgets = plot_widgets
        self.data_lines = data_lines
        # 使用双缓存数据存储
        self.display_data = [[] for _ in range(8)]  # 用于显示的数据
        self.full_data = [[] for _ in range(8)]     # 完整历史数据
        self.voltage_labels = voltage_labels
        self.sample_interval_s = sample_interval_s
        # self.max_data_points = max_data_points # 移除 max_data_points
        self.test_data_button = test_data_button
        self.status_bar = status_bar
        self.test_data_timer = test_data_timer
        self.pixel_labels = pixel_labels # 存储 pixel_labels 引用
        self.frequency_spinbox = frequency_spinbox # 存储 frequency spinbox 引用
        self.points_spinbox = points_spinbox # 存储 points spinbox 引用
        self.digital_matrix_labels = digital_matrix_labels # 存储 digital matrix labels 引用

        self.is_synchronizing_x = False # 标志，防止 X 轴递归同步



        # 测试数据生成控制变量
        self.is_generating_test_data = False
        self.test_data_total_points = 0
        self.test_data_frequency_hz = 1 # 默认频率 (Hz)
        self.test_data_points = 4 # 默认点数

        # 需要 MainWindow 中的标志/对象引用来检查数据源状态
        self.serial_thread_running = False # 需要从 MainWindow 更新此标志

        # 定义检测触摸信号的阈值
        self.touch_threshold = 0.5 # 此阈值可能需要根据传感器特性进行调整

        self.data_acquisition_start_time = None # 存储数据采集的开始时间

    def update_plots(self, data):
        """更新图表数据，优化性能"""
        # 检查数据有效性
        if not data or len(data) < 2:
            return
            
        values = data[0]
        current_time_s = data[1]
        
        try:
            # 限制数据处理频率
            if hasattr(self, '_last_update_time') and time.time() - self._last_update_time < 0.05:  # 20Hz更新频率
                return
                
            # 初始化开始时间
            if self.data_acquisition_start_time is None:
                self.data_acquisition_start_time = current_time_s

            # CH1-CH4 是行信号，CH5-CH8 是列信号
            row_signals = values[:4] # CH1-CH4
            col_signals = values[4:] # CH5-CH8

            # 批量处理数据更新
            for i in range(8):
                voltage = values[i]
                # 更新完整数据
                self.full_data[i].append((voltage, current_time_s))
                
                # 更新数据线条
                if i < len(self.data_lines):
                    if not hasattr(self, '_last_data') or self._last_data != self.full_data[i][-1]:
                        self.data_lines[i].setData(
                            [item[1] for item in self.full_data[i]],
                            [item[0] for item in self.full_data[i]]
                        )
                        self._last_data = self.full_data[i][-1]
                    
                # 更新电压标签
                if self.is_generating_test_data or self.serial_thread_running:
                    self.voltage_labels[i].setText(f"CH{i+1}: {voltage:.3f} V")

            # 触摸点检测和像素地图更新
            activated_rows = [i for i, signal in enumerate(row_signals) if signal > self.touch_threshold]
            activated_cols = [i for i, signal in enumerate(col_signals) if signal > self.touch_threshold]

            if len(activated_rows) == 1 and len(activated_cols) == 1:
                touched_row = activated_rows[0]
                touched_col = activated_cols[0]
                self.update_pixel_map_signal.emit(touched_row, touched_col)
                if self.display_data[0]:
                    touch_time = self.display_data[0][-1][1]
                    self.update_digital_matrix_signal.emit(touched_row, touched_col, touch_time)

            # 记录最后更新时间
            self._last_update_time = time.time()
            
        except Exception as e:
            print(f"图表更新错误: {e}")
            
            # 初始化开始时间
            if self.data_acquisition_start_time is None:
                self.data_acquisition_start_time = current_time_s

            # 批量处理数据更新
            row_signals = values[:4]
            col_signals = values[4:]
            
            # 使用局部变量减少属性访问
            plot_widgets = self.plot_widgets
            data_lines = self.data_lines
            voltage_labels = self.voltage_labels
            
            for i in range(8):
                voltage = values[i]
                # 更新完整数据
                self.full_data[i].append((voltage, current_time_s))
                
                # 仅当需要显示时才提取数据
                if i < len(data_lines):
                    plot_data = self.full_data[i] # 使用 full_data 进行绘制
                    data_lines[i].setData(
                        [item[1] for item in plot_data],
                        [item[0] for item in plot_data]
                    )
                    
                # 更新电压标签
                if self.is_generating_test_data or self.serial_thread_running:
                    voltage_labels[i].setText(f"CH{i+1}: {voltage:.3f} V")

            # 记录最后更新时间
            self._last_update_time = time.time()

        # 如果需要，自动调整所有图表的 X 轴范围
        if self.full_data and self.full_data[0]: # Use full_data here
            start_time = self.full_data[0][0][1] # Use full_data here
            end_time = self.full_data[0][-1][1] # Use full_data here

            # // 仅当新数据超出当前视图时调整 X 轴范围
            current_view_range = self.plot_widgets[0].getViewBox().viewRange()[0]

            # // 此自动调整仅在新数据到达时发生
            # // 且当前视图不包含新数据。
            # // 手动缩放/平移由 _synchronize_x_ranges 处理。
            new_end_time = end_time
            new_start_time = start_time # For full data, start time is the first data point's time

            # // 将新范围应用于所有图表
            for plot_widget in self.plot_widgets:
                plot_widget.getViewBox().setXRange(new_start_time, new_end_time, padding=0.01)

        # // 触摸点检测和像素地图更新
        touched_row = -1
        touched_col = -1

        # 查找激活的行
        activated_rows = [i for i, signal in enumerate(row_signals) if signal > self.touch_threshold]
        # 查找激活的列
        activated_cols = [i for i, signal in enumerate(col_signals) if signal > self.touch_threshold]

        # 根据激活的行和列确定触摸点
        if len(activated_rows) == 1 and len(activated_cols) == 1:
            touched_row = activated_rows[0]
            touched_col = activated_cols[0]
            # 发出信号更新像素地图
            self.update_pixel_map_signal.emit(touched_row, touched_col)
            # 发出信号更新数字矩阵，包含最后一个数据点的时间
            if self.display_data[0]: # 使用第一个通道的时间作为参考
                 touch_time = self.display_data[0][-1][1]
                 self.update_digital_matrix_signal.emit(touched_row, touched_col, touch_time)

        # 没有触摸或多点触摸 - 不在此处清除像素地图或数字矩阵
        # 清除由清除按钮和停止测试数据生成时处理


    def _generate_single_test_data_point(self):
        import random
        import math
        import time

        # 生成一组模拟数据
        test_values = []

        # 模拟一个触摸点用于测试
        simulated_touch_row = random.randint(0, 3)
        simulated_touch_col = random.randint(0, 3)

        for i in range(8):
            if i < 4: # 行信号 (CH1-CH4)
                if i == simulated_touch_row:
                    # 模拟触摸行的峰值
                    value = 2.5 + random.uniform(-0.2, 0.2) # 信号高于阈值
                else:
                    # 模拟其他行的背景噪声
                    value = random.uniform(0.1, 0.3) # 信号低于阈值
            else: # 列信号 (CH5-CH8)
                if (i - 4) == simulated_touch_col:
                     # 模拟触摸列的峰值
                    value = 2.5 + random.uniform(-0.2, 0.2) # 信号高于阈值
                else:
                    # 模拟其他列的背景噪声
                    value = random.uniform(0.1, 0.3) # 信号低于阈值

            # 确保值在 0-3.3V 范围内
            value = max(0, min(3.3, value))
            test_values.append(value)

        # 更新图表和像素映射，传递模拟数据和相对时间
        current_time = time.time()
        if self.data_acquisition_start_time is None:
            self.data_acquisition_start_time = current_time
            # 开始新的数据采集时重置图表视图
            self._reset_plot_views()
        relative_time = current_time - self.data_acquisition_start_time
        self.update_plots([test_values, relative_time])

        # 增加生成的总点数
        self.test_data_total_points += 1

        # 在更新图表后检查是否达到目标点数
        if self.test_data_total_points >= self.test_data_points:
            self.test_data_timer.stop()
            self.is_generating_test_data = False
            self.test_data_button.setText("生成测试数据")
            self.status_bar.showMessage(f"测试数据采集完成 ({self.test_data_points} 点)")
            # 最后一个点的像素地图和数字矩阵更新由 update_plots 处理


    def toggle_test_data_generation(self):
        if not self.is_generating_test_data:
            # 从微调框获取频率 (Hz) 和点数
            frequency_hz = self.frequency_spinbox.value()
            self.test_data_points = self.points_spinbox.value()

            # 从频率 (Hz) 计算定时器间隔 (ms)
            if frequency_hz > 0:
                timer_interval_ms = int(1000 / frequency_hz)
            else:
                timer_interval_ms = 1000 # 如果频率小于等于 0，默认为 1 Hz

            # 重置总点数计数器
            self.test_data_total_points = 0

            # 设置测试数据采样间隔 (基于定时器间隔)
            # 不再需要，因为我们使用实时时间
            # self.sample_interval_s = timer_interval_ms / 1000.0

            # 开始生成数据
            self.is_generating_test_data = True # 更新 PlotManager 中的标志
            # 在连接之前断开任何先前的连接
            try:
                self.test_data_timer.timeout.disconnect(self._generate_single_test_data_point)
            except TypeError:
                pass # 如果未连接则忽略
            self.test_data_timer.timeout.connect(self._generate_single_test_data_point)
            self.test_data_timer.start(timer_interval_ms) # 使用计算出的间隔

            self.test_data_button.setText("停止生成")
            self.status_bar.showMessage(f"测试数据采集中 ({frequency_hz} Hz, 共 {self.test_data_points} 点)...")
        else:
            # 手动停止生成数据
            self.test_data_timer.stop()
            try:
                self.test_data_timer.timeout.disconnect(self._generate_single_test_data_point)
            except TypeError:
                pass # 如果未连接则忽略
            self.is_generating_test_data = False # 更新 PlotManager 中的标志
            self.test_data_button.setText("生成测试数据")
            self.status_bar.showMessage("测试数据采集已停止")
            # 不要在此处清除像素地图或数字矩阵。它们应该保留直到用户清除。


    def export_data_to_csv(self):
        """导出完整历史数据到CSV文件"""
        if not any(self.full_data):
            QMessageBox.information(None, "导出数据", "没有数据可导出。")
            return

        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        file_path, _ = QFileDialog.getSaveFileName(None, "保存数据", "", "CSV 文件 (*.csv);;所有文件 (*)", options=options)

        if file_path:
            if not file_path.lower().endswith('.csv'):
                file_path += '.csv'

            try:
                with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                    csv_writer = csv.writer(csvfile)

                    # 准备表头
                    header = ['Sample Index', 'Time (s)']
                    for i in range(8):
                        header.append(f'Channel {i+1} Voltage (V)')
                    csv_writer.writerow(header)

                    # 使用完整历史数据
                    max_samples = max(len(channel) for channel in self.full_data)
                    
                    # 写入数据行
                    for sample_idx in range(max_samples):
                        row_data = [sample_idx + 1]  # 样本索引从1开始
                        
                        # 获取时间戳（使用第一个通道的时间）
                        if sample_idx < len(self.full_data[0]):
                            current_sample_time = self.full_data[0][sample_idx][1]
                        else:
                            current_sample_time = sample_idx * self.sample_interval_s
                            
                        row_data.append(f"{current_sample_time:.3f}")

                        # 添加各通道电压值
                        for i in range(8):
                            if sample_idx < len(self.full_data[i]):
                                row_data.append(f"{self.full_data[i][sample_idx][0]:.3f}")
                            else:
                                row_data.append('')
                        csv_writer.writerow(row_data)

                self.status_bar.showMessage(f"数据已导出到 {os.path.basename(file_path)}")
            except Exception as e:
                QMessageBox.critical(None, "导出错误", f"无法保存文件: {e}") # 使用 None 作为父级
                self.status_bar.showMessage(f"导出失败: {e}")

    def _mouse_moved_on_plot(self, pos, plot_widget, plot_index):
        vb = plot_widget.getViewBox()
        if plot_widget.sceneBoundingRect().contains(pos):
            mouse_point = vb.mapSceneToView(pos)
            mouse_x = mouse_point.x() # 获取鼠标在视图坐标中的 x 坐标

            # 根据鼠标的 x 坐标更新所有通道的电压标签
            voltage_strings = ["--- V"] * 8
            for ch_idx in range(8):
                ch_x_data = self.data_lines[ch_idx].xData
                ch_y_data = self.data_lines[ch_idx].yData

                if ch_x_data is not None and len(ch_x_data) > 0:
                    first_x = ch_x_data[0]
                    last_x = ch_x_data[-1]

                    if mouse_x < first_x:
                        # 鼠标在第一个数据点之前，使用第一个点的电压
                        interpolated_voltage = ch_y_data[0]
                    elif mouse_x > last_x:
                        # 鼠标在最后一个数据点之后，使用最后一个点的电压
                        interpolated_voltage = ch_y_data[-1]
                    else:
                        # 鼠标在数据范围内，找到最近的两个点并进行插值
                        # 查找恰好在 mouse_x 之前或在 mouse_x 处的点的索引
                        idx1 = 0
                        for i in range(len(ch_x_data) - 1):
                            if ch_x_data[i+1] > mouse_x:
                                idx1 = i
                                break
                            idx1 = i + 1 # 以防 mouse_x 恰好在数据点上或倒数第二个点之后

                        # idx1 现在是小于等于 mouse_x 的点的索引
                        # idx2 是大于等于 mouse_x 的点的索引
                        idx2 = idx1
                        if ch_x_data[idx1] < mouse_x and idx1 < len(ch_x_data) - 1:
                             idx2 = idx1 + 1

                        x1, y1 = ch_x_data[idx1], ch_y_data[idx1]
                        x2, y2 = ch_x_data[idx2], ch_y_data[idx2]

                        interpolated_voltage = self.linear_interpolate(mouse_x, x1, y1, x2, y2)

                    voltage_strings[ch_idx] = f"{interpolated_voltage:.3f} V"
                else:
                    # 此通道没有数据
                    voltage_strings[ch_idx] = "--- V"


            # 计算所有通道的电压后更新所有电压标签
            for ch_idx in range(8):
                 self.voltage_labels[ch_idx].setText(f"CH{ch_idx+1}: {voltage_strings[ch_idx]}")

            # 移除图表上的悬停文本显示 (如果有)
            # 原始代码有 hover_text_item，但它不用于在图表上显示文本。
            # 保留此行以防在其他地方使用或打算将来使用。
            if hasattr(plot_widget, 'hover_text_item') and plot_widget.hover_text_item:
                 plot_widget.hover_text_item.hide()

        else:
            # 鼠标离开图表区域，隐藏任何潜在的悬停文本
            if hasattr(plot_widget, 'hover_text_item') and plot_widget.hover_text_item:
                 plot_widget.hover_text_item.hide()
            # 可选地，当鼠标离开图表区域时重置电压标签
            # for ch_idx in range(8):
            #      self.voltage_labels[ch_idx].setText(f"CH{ch_idx+1}: --- V")

    def _reset_all_x_ranges_to_data_range(self, changed_vb):
        if hasattr(self, 'is_synchronizing_x') and self.is_synchronizing_x: # 防止在正在进行的同步期间出现问题
            return
        self.is_synchronizing_x = True # 在手动重置期间防止同步信号

        # 根据显示数据确定当前时间范围
        # 如果数据为空，则重置为默认初始视图。
        current_min_time = 0.0
        current_max_time = 5.0 # 如果没有数据，默认最大时间为5秒

        # 尝试从显示数据中查找实际时间范围
        if self.display_data and self.display_data[0]:
            times = [item[1] for item in self.display_data[0]]
            current_min_time = times[0]
            current_max_time = times[-1]
            # 如果数据较少，确保范围至少覆盖一个较小的默认窗口，例如5秒
            if (current_max_time - current_min_time) < 5.0:
                current_max_time = current_min_time + 5.0

        for pw in self.plot_widgets:
            pw.getViewBox().setXRange(current_min_time, current_max_time, padding=0)
            # Y 轴已固定且不可交互，因此此处无需重置 Y 轴
            # 如果需要，可以添加：pw.getViewBox().setYRange(0, 3.3, padding=0)

        self.is_synchronizing_x = False

    def _clear_plot_data(self):
        for i in range(8):
            self.display_data[i].clear()
            self.full_data[i].clear()
            self.data_lines[i].setData([], [])
            self.voltage_labels[i].setText(f"CH{i+1}: 0.000 V")
        # 重置数据采集开始时间
        self.data_acquisition_start_time = None
        # 重置 MainWindow 中的时间偏移量
        if self.main_window:
            self.main_window.last_time_offset = 0.0
        # 可选：重置图表 X 轴，或保持原样
        # 可以调用此方法重置缩放/平移
        # self._reset_plot_views()
        # 状态栏更新需要在 MainWindow 中处理
        # self.status_bar.showMessage("图表数据已清除")
        # 清除数据时清除像素地图和数字矩阵
        self.update_pixel_map_signal.emit(-1, -1)


    def _reset_plot_views(self):
        if hasattr(self, 'is_synchronizing_x') and self.is_synchronizing_x: # 防止在正在进行的同步期间出现问题
            return
        self.is_synchronizing_x = True # 在手动重置期间防止同步信号

        # 根据显示数据确定当前时间范围
        current_min_time = 0.0
        current_max_time = 5.0 # 默认初始显示 5 秒

        # 尝试从显示数据中查找实际时间范围
        if self.display_data and self.display_data[0]:
            times = [item[1] for item in self.display_data[0]]
            current_min_time = times[0]
            current_max_time = times[-1]
            # 确保至少显示 1 秒的数据
            if (current_max_time - current_min_time) < 1.0:
                current_max_time = current_min_time + 1.0

        for pw in self.plot_widgets:
            pw.getViewBox().setXRange(current_min_time, current_max_time, padding=0.1)
            # Y 轴已固定且不可交互，因此此处无需重置 Y 轴

        self.is_synchronizing_x = False

    def linear_interpolate(self, x, x1, y1, x2, y2):
        """执行线性插值。"""
        if x1 == x2:
            return y1
        return y1 + (x - x1) * (y2 - y1) / (x2 - x1)
    def synchronize_x_ranges(self, changed_vb, new_x_range):
        """Synchronizes the X-axis range of all plot widgets."""
        if hasattr(self, 'is_synchronizing_x') and self.is_synchronizing_x:
            return
        self.is_synchronizing_x = True

        for plot_widget in self.plot_widgets:
            vb = plot_widget.getViewBox()
            if vb is not changed_vb:
                vb.setXRange(new_x_range[0], new_x_range[1], padding=0)

        self.is_synchronizing_x = False
# 其他与图表相关的函数或类的占位符