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

    def __init__(self, plot_widgets, data_lines, data_queues, voltage_labels, sample_interval_s, test_data_button, status_bar, test_data_timer, pixel_labels, frequency_spinbox, points_spinbox, digital_matrix_labels): # 添加 digital_matrix_labels 参数
        super().__init__() # 调用 QObject 构造函数
        self.plot_widgets = plot_widgets
        self.data_lines = data_lines
        # 将数据队列更改为普通列表
        self.data_queues = [[] for _ in range(8)] # 修改为普通列表
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
        # data 是一个列表，包含 [values, current_time]
        values = data[0] # values 是一个包含8个浮点数的列表 (CH1-CH8)
        current_time_s = data[1] # current_time 是接收到数据时的真实时间戳

        # 如果是第一个数据点，初始化开始时间
        if self.data_acquisition_start_time is None:
            self.data_acquisition_start_time = current_time_s

        # 计算相对时间
        relative_time_s = current_time_s - self.data_acquisition_start_time

        # CH1-CH4 是行信号，CH5-CH8 是列信号
        row_signals = values[:4] # CH1-CH4
        col_signals = values[4:] # CH5-CH8

        # 更新图表数据和电压标签
        for i in range(8):
            voltage = values[i]

            # 将新数据点添加到 deque 中，deque 会自动处理 maxlen
            self.data_queues[i].append((voltage, current_time_s))

            # 提取用于绘图的 x (时间) 和 y (电压) 数据
            plot_times = [item[1] for item in self.data_queues[i]]
            plot_voltages = [item[0] for item in self.data_queues[i]]

            # 更新数据线条
            self.data_lines[i].setData(plot_times, plot_voltages)

            # 如果数据正在主动生成，更新电压标签
            if self.is_generating_test_data or self.serial_thread_running: # 需要从 MainWindow 更新 serial_thread_running 标志
                self.voltage_labels[i].setText(f"CH{i+1}: {voltage:.3f} V")

        # 如果需要，自动调整所有图表的 X 轴范围
        if self.data_queues and self.data_queues[0]:
            start_time = self.data_queues[0][0][1]
            end_time = self.data_queues[0][-1][1]

            # 仅当新数据超出当前视图时调整 X 轴范围
            current_view_range = self.plot_widgets[0].getViewBox().viewRange()[0]
            view_duration = current_view_range[1] - current_view_range[0]

            # 此自动调整仅在新数据到达时发生
            # 且当前视图不包含新数据。
            # 手动缩放/平移由 _synchronize_x_ranges 处理。
            current_view_range = self.plot_widgets[0].getViewBox().viewRange()[0]
            if end_time > current_view_range[1] or start_time < current_view_range[0]:
                 # 根据最后一个数据点计算所需的新范围
                 # 保持与当前视图范围相同的持续时间
                 view_duration = current_view_range[1] - current_view_range[0]
                 new_end_time = end_time
                 new_start_time = max(start_time, new_end_time - view_duration)

                 # 将新范围应用于所有图表
                 for plot_widget in self.plot_widgets:
                     plot_widget.getViewBox().setXRange(new_start_time, new_end_time, padding=0.01)

        # --- 触摸点检测和像素地图更新 ---
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
            if self.data_queues[0]: # 使用第一个通道的时间作为参考
                 touch_time = self.data_queues[0][-1][1]
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
        if not any(self.data_queues):
            QMessageBox.information(None, "导出数据", "没有数据可导出。") # 使用 None 作为父级
            return

        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        file_path, _ = QFileDialog.getSaveFileName(None, "保存数据", "", "CSV 文件 (*.csv);;所有文件 (*)", options=options) # 使用 None 作为父级

        if file_path:
            # 确保文件路径以 .csv 结尾
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

                    # 确定所有通道的最大样本数以保持行一致
                    max_samples = 0
                    for i in range(8):
                        if self.data_queues[i]:
                           max_samples = max(max_samples, len(self.data_queues[i]))

                    if max_samples == 0 and self.data_queues[0]: # 如果第一个队列有数据但循环未捕获，则回退
                         if self.data_queues[0]:
                            max_samples = len(self.data_queues[0])


                    # 写入数据行
                    for sample_idx in range(max_samples):
                        row_data = [sample_idx]
                        # 此样本索引的时间 - 假设是第一个通道的时间或根据需要计算
                        # 为简单起见，我们将使用具有此样本的第一个通道的时间
                        # 或者如果所有通道按样本数同步，则推导它。

                        current_sample_time = None
                        # 查找在 sample_idx 处具有数据的第一个通道的时间
                        for i in range(8):
                            if sample_idx < len(self.data_queues[i]):
                                current_sample_time = self.data_queues[i][sample_idx][1] # (电压, 时间_s)
                                break

                        if current_sample_time is None: # 如果 max_samples 正确，则不应发生
                            # 回退：如果未找到直接时间，则根据 sample_idx 和间隔计算时间
                            current_sample_time = sample_idx * self.sample_interval_s


                        row_data.append(f"{current_sample_time:.3f}")

                        for i in range(8):
                            if sample_idx < len(self.data_queues[i]):
                                voltage = self.data_queues[i][sample_idx][0]
                                row_data.append(f"{voltage:.3f}")
                            else:
                                row_data.append('') # 如果此样本索引处此通道没有数据，则为空
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

        # 根据第一个非空数据队列确定当前时间范围
        # 如果所有队列都为空，则重置为默认初始视图。
        current_min_time = 0.0
        current_max_time = 5.0 # 如果没有数据，默认最大时间为5秒

        # 尝试从数据中查找实际时间范围
        found_data_range = False
        for queue in self.data_queues:
            if queue:
                times = [item[1] for item in queue]
                current_min_time = times[0]
                current_max_time = times[-1]
                # 如果数据较少，确保范围至少覆盖一个较小的默认窗口，例如5秒
                if (current_max_time - current_min_time) < 5.0:
                    current_max_time = current_min_time + 5.0
                found_data_range = True
                break

        if not found_data_range and self.data_queues[0]: # 如果第一个队列有数据但循环未捕获，则回退
             if self.data_queues[0]:
                times = [item[1] for item in self.data_queues[0]]
                current_min_time = times[0]
                current_max_time = times[-1]
                if (current_max_time - current_min_time) < 5.0:
                    current_max_time = current_min_time + 5.0

        for pw in self.plot_widgets:
            pw.getViewBox().setXRange(current_min_time, current_max_time, padding=0)
            # Y 轴已固定且不可交互，因此此处无需重置 Y 轴
            # 如果需要，可以添加：pw.getViewBox().setYRange(0, 3.3, padding=0)

        self.is_synchronizing_x = False

    def _clear_plot_data(self):
        for i in range(8):
            self.data_queues[i].clear()
            self.data_lines[i].setData([], [])
            self.voltage_labels[i].setText(f"CH{i+1}: 0.000 V")
        # 重置数据采集开始时间
        self.data_acquisition_start_time = None
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

        # 根据第一个非空数据队列确定当前时间范围
        # 如果所有队列都为空，则重置为默认初始视图。
        current_min_time = 0.0
        current_max_time = 5.0 # 默认初始显示 5 秒

        # 尝试从数据中查找实际时间范围
        found_data_range = False
        for queue in self.data_queues:
            if queue:
                times = [item[1] for item in queue]
                current_min_time = times[0]
                current_max_time = times[-1]
                # 确保至少显示 1 秒的数据
                if (current_max_time - current_min_time) < 1.0:
                    current_max_time = current_min_time + 1.0
                found_data_range = True
                break

        if not found_data_range and self.data_queues[0]: # 如果第一个队列有数据但循环未捕获，则回退
             if self.data_queues[0]:
                times = [item[1] for item in self.data_queues[0]]
                current_min_time = times[0]
                current_max_time = times[-1]
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