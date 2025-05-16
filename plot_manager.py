# plot_manager.py

import pyqtgraph as pg
import struct
import time
import random
import math
import csv
import os
from PyQt5.QtCore import QTimer, QObject, pyqtSignal # Import QTimer, QObject, pyqtSignal
from PyQt5.QtWidgets import QMessageBox, QFileDialog # Import QMessageBox, QFileDialog

class PlotManager(QObject): # Inherit from QObject to use signals/slots
    def __init__(self, plot_widgets, data_lines, data_queues, voltage_labels, sample_interval_s, max_data_points, test_data_button, status_bar, test_data_timer):
        super().__init__() # Call QObject constructor
        self.plot_widgets = plot_widgets
        self.data_lines = data_lines
        self.data_queues = data_queues
        self.voltage_labels = voltage_labels
        self.sample_interval_s = sample_interval_s
        self.max_data_points = max_data_points
        self.test_data_button = test_data_button
        self.status_bar = status_bar
        self.test_data_timer = test_data_timer
        # Need references to flags/objects from MainWindow to check data source status
        self.is_generating_test_data = False # This will need to be updated from MainWindow
        self.serial_thread_running = False # This will need to be updated from MainWindow

    def update_plots(self, values):
        # values 是一个包含8个浮点数的列表
        for i in range(8):
            voltage = values[i]

            # Determine the time for the current data point
            if not self.data_queues[i]:
                current_time_s = 0.0
            else:
                last_time_s = self.data_queues[i][-1][1]
                current_time_s = last_time_s + self.sample_interval_s

            self.data_queues[i].append((voltage, current_time_s))
            if len(self.data_queues[i]) > self.max_data_points:
                self.data_queues[i].pop(0) # 移除最老的数据点

            # Extract x (time) and y (voltage) data for plotting
            plot_times = [item[1] for item in self.data_queues[i]]
            plot_voltages = [item[0] for item in self.data_queues[i]]
            self.data_lines[i].setData(plot_times, plot_voltages)
            # Update voltage labels if data is actively being generated
            if self.is_generating_test_data or self.serial_thread_running:
                self.voltage_labels[i].setText(f"CH{i+1}: {voltage:.3f} V")

     # 其他与图表相关的方法将稍后移至此处


    def _generate_single_test_data_point(self):
        import random
        import math
        import time

        # 生成一组模拟数据
        test_values = []
        current_time = time.time() # Use current time for dynamic data
        for i in range(8):
            # 生成一个0-3.3V范围内的正弦波形数据
            value = 1.65 + 1.65 * math.sin(current_time + i * math.pi / 4 + (current_time * 2)) # Add current_time to make it dynamic
            # 添加一些随机噪声
            value += random.uniform(-0.1, 0.1)
            # 确保值在0-3.3V范围内
            value = max(0, min(3.3, value))
            test_values.append(value)

        # 更新图表
        self.update_plots(test_values)
        # self.status_bar.showMessage("已生成测试数据") # 状态栏更新可在切换函数中处理

    def toggle_test_data_generation(self):
        if not self.is_generating_test_data:
            # 保存原始采样间隔
            self.original_sample_interval_s = self.sample_interval_s
            # 设置测试数据采样间隔 (10Hz -> 0.1s)
            self.sample_interval_s = 0.1
            # 开始生成数据
            self.is_generating_test_data = True # Update flag in PlotManager
            self.test_data_timer.timeout.connect(self._generate_single_test_data_point)
            self.test_data_timer.start(100) # 10Hz = 100ms interval
            self.test_data_button.setText("停止生成")
            self.status_bar.showMessage("测试数据采集中 (10Hz)...")
        else:
            # 停止生成数据
            self.test_data_timer.stop()
            self.test_data_timer.timeout.disconnect(self._generate_single_test_data_point) # 断开连接以避免再次启动时重复连接
            self.is_generating_test_data = False # Update flag in PlotManager
            self.test_data_button.setText("生成测试数据")
            # 恢复原始采样间隔
            if hasattr(self, 'original_sample_interval_s'):
                self.sample_interval_s = self.original_sample_interval_s
            self.status_bar.showMessage("测试数据采集已停止")




    def export_data_to_csv(self):
        if not any(self.data_queues):
            QMessageBox.information(None, "导出数据", "没有数据可导出。") # Use None as parent
            return

        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        file_path, _ = QFileDialog.getSaveFileName(None, "保存数据", "", "CSV 文件 (*.csv);;所有文件 (*)", options=options) # Use None as parent

        if file_path:
            # Ensure the file path ends with .csv
            if not file_path.lower().endswith('.csv'):
                file_path += '.csv'

            try:
                with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                    csv_writer = csv.writer(csvfile)

                    # Prepare header
                    header = ['Sample Index', 'Time (s)']
                    for i in range(8):
                        header.append(f'Channel {i+1} Voltage (V)')
                    csv_writer.writerow(header)

                    # Determine the maximum number of samples across all channels for consistent rows
                    max_samples = 0
                    for i in range(8):
                        if self.data_queues[i]:
                           max_samples = max(max_samples, len(self.data_queues[i]))

                    if max_samples == 0 and self.data_queues[0]: # Check if only first channel has data
                        max_samples = len(self.data_queues[0])

                    # Write data rows
                    for sample_idx in range(max_samples):
                        row_data = [sample_idx]
                        # Time for this sample index - assumes first channel's time or calculate if needed
                        # For simplicity, we'll use the time from the first channel that has this sample
                        # or derive it if all channels are synchronized by sample count.

                        # Get time from the first available channel for this sample_idx
                        current_sample_time = None
                        for i in range(8):
                            if sample_idx < len(self.data_queues[i]):
                                current_sample_time = self.data_queues[i][sample_idx][1] # (voltage, time_s)
                                break
                        if current_sample_time is None: # Should not happen if max_samples is correct
                            # Fallback: calculate time based on sample_idx and interval if no direct time found
                            current_sample_time = sample_idx * self.sample_interval_s

                        row_data.append(f"{current_sample_time:.3f}")

                        for i in range(8):
                            if sample_idx < len(self.data_queues[i]):
                                voltage = self.data_queues[i][sample_idx][0]
                                row_data.append(f"{voltage:.3f}")
                            else:
                                row_data.append('') # Empty if no data for this channel at this sample index
                        csv_writer.writerow(row_data)

                self.status_bar.showMessage(f"数据已导出到 {os.path.basename(file_path)}")
            except Exception as e:
                QMessageBox.critical(None, "导出错误", f"无法保存文件: {e}") # Use None as parent
                self.status_bar.showMessage(f"导出失败: {e}")

    def _mouse_moved_on_plot(self, pos, plot_widget, plot_index):
        vb = plot_widget.getViewBox()
        if plot_widget.sceneBoundingRect().contains(pos):
            mouse_point = vb.mapSceneToView(pos)
            # xData now contains time values (floats)
            # yData contains voltage values (floats)
            x_data = self.data_lines[plot_index].xData
            y_data = self.data_lines[plot_index].yData

            if x_data is not None and len(x_data) > 0:
                # Find the index of the data point closest to the mouse's x-coordinate
                # This is a simple way, for large datasets, numpy.argmin(numpy.abs(x_data - mouse_point.x())) would be more efficient
                min_dist = float('inf')
                closest_index = -1
                for idx, x_val in enumerate(x_data):
                    dist = abs(x_val - mouse_point.x())
                    if dist < min_dist:
                        min_dist = dist
                        closest_index = idx

                # Check if the mouse is reasonably close to a data point on the x-axis
                # This threshold can be adjusted. For example, half the sample interval.
                if closest_index != -1 and min_dist < (self.sample_interval_s * 5): # Allow a bit of leeway
                    actual_x_time = x_data[closest_index]
                    actual_y_voltage = y_data[closest_index] # Voltage of the hovered plot at that point

                    # If data generation is stopped, update all voltage labels based on hovered time
                    # Need to access MainWindow's state for this
                    if not self.is_generating_test_data and not self.serial_thread_running:
                        # Store voltage strings for each channel
                        voltage_strings = ["--- V"] * 8
                        for ch_idx in range(8):
                            ch_x_data = self.data_lines[ch_idx].xData
                            ch_y_data = self.data_lines[ch_idx].yData
                            
                            if ch_x_data is not None and len(ch_x_data) > 0:
                                # Find closest data point in this channel to actual_x_time
                                ch_min_dist = float('inf')
                                ch_closest_idx = -1
                                for idx_in_ch, x_val_in_ch in enumerate(ch_x_data):
                                    dist_in_ch = abs(x_val_in_ch - actual_x_time)
                                    if dist_in_ch < ch_min_dist:
                                        ch_min_dist = dist_in_ch
                                        ch_closest_idx = idx_in_ch
 
                                # Check if the found point is reasonably close (e.g., within a sample interval)
                                if ch_closest_idx != -1 and ch_min_dist < self.sample_interval_s * 1.5: # Allow small tolerance
                                    voltage_strings[ch_idx] = f"{ch_y_data[ch_closest_idx]:.3f} V"
 
                        # Update all voltage labels after finding closest points for all channels
                        for ch_idx in range(8):
                             self.voltage_labels[ch_idx].setText(f"CH{ch_idx+1}: {voltage_strings[ch_idx]}")
                    # elif self.is_generating_test_data or self.serial_thread_running:
                        # If data is generating, update only the hovered plot's label (or rely on update_plots)
                        # self.voltage_labels[plot_index].setText(f"CH{plot_index+1}: {actual_y_voltage:.3f} V")
                        # The update_plots method already handles this for active data generation.
                        pass # Voltage labels are updated by update_plots during active data generation
 
                    # Remove on-plot hover text display
                    plot_widget.hover_text_item.hide()
                else:
                    plot_widget.hover_text_item.hide()
            else:
                plot_widget.hover_text_item.hide()
        else:
            plot_widget.hover_text_item.hide()

    def _synchronize_x_ranges(self, changed_vb):
        if hasattr(self, 'is_synchronizing_x') and self.is_synchronizing_x:
            return
        self.is_synchronizing_x = True

        new_x_range = changed_vb.viewRange()[0] # Get the new x-range from the source ViewBox

        for pw in self.plot_widgets:
            if pw.getViewBox() is not changed_vb: # Don't update the ViewBox that triggered the signal
                pw.getViewBox().setXRange(new_x_range[0], new_x_range[1], padding=0)

        self.is_synchronizing_x = False

    def _clear_plot_data(self):
        for i in range(8):
            self.data_queues[i].clear()
            self.data_lines[i].setData([], [])
            self.voltage_labels[i].setText(f"CH{i+1}: 0.000 V")
        # 可选：如果需要，重置图表X轴，或保持原样
        # self._reset_plot_views() # 可调用此方法重置缩放/平移
        # 状态栏更新需要在MainWindow中处理
        # self.status_bar.showMessage("图表数据已清空")

    def _reset_plot_views(self):
        if hasattr(self, 'is_synchronizing_x') and self.is_synchronizing_x: # Prevent issues if called during an ongoing sync
            return
        self.is_synchronizing_x = True # Prevent sync signals during manual reset

        # Determine the current time range based on the first non-empty data queue
        # If all queues are empty, reset to a default initial view.
        current_min_time = 0.0
        current_max_time = self.max_data_points * self.sample_interval_s # Default max time if no data

        # Try to find the actual time range from data
        found_data_range = False
        for queue in self.data_queues:
            if queue:
                times = [item[1] for item in queue]
                current_min_time = times[0]
                current_max_time = times[-1]
                # Ensure the range covers at least the max_data_points window if data is less
                if (current_max_time - current_min_time) < (self.max_data_points * self.sample_interval_s):
                    current_max_time = current_min_time + (self.max_data_points * self.sample_interval_s)
                found_data_range = True
                break

        if not found_data_range and self.data_queues[0]: # Fallback if first queue has data but loop didn't catch
             if self.data_queues[0]:
                times = [item[1] for item in self.data_queues[0]]
                current_min_time = times[0]
                current_max_time = times[-1]
                if (current_max_time - current_min_time) < (self.max_data_points * self.sample_interval_s):
                    current_max_time = current_min_time + (self.max_data_points * self.sample_interval_s)

        for pw in self.plot_widgets:
            pw.getViewBox().setXRange(current_min_time, current_max_time, padding=0)
            # Y-axis is already fixed and non-interactive, so no Y-reset needed here
            # 如果需要，可以添加：pw.getViewBox().setYRange(0, 3.3, padding=0)

        self.is_synchronizing_x = False

# 其他与图表相关的函数或类的占位符