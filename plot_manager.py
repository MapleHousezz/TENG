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
    # Define signals
    update_pixel_map_signal = pyqtSignal(int, int) # Signal to send row and column of the touched pixel
    update_digital_matrix_signal = pyqtSignal(int, int, float) # Signal to send row, col, and time

    def __init__(self, plot_widgets, data_lines, data_queues, voltage_labels, sample_interval_s, max_data_points, test_data_button, status_bar, test_data_timer, pixel_labels, frequency_spinbox, points_spinbox, digital_matrix_labels): # Add digital_matrix_labels parameter
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
        self.pixel_labels = pixel_labels # Store the pixel_labels reference
        self.frequency_spinbox = frequency_spinbox # Store frequency spinbox reference
        self.points_spinbox = points_spinbox # Store points spinbox reference
        self.digital_matrix_labels = digital_matrix_labels # Store digital matrix labels reference

        self.is_synchronizing_x = False # Flag to prevent recursive X-axis sync
        


        # Test data generation control variables
        self.is_generating_test_data = False
        self.test_data_total_points = 0
        self.test_data_frequency_hz = 1 # Default frequency in Hz
        self.test_data_points = 4 # Default number of points

        # Need references to flags/objects from MainWindow to check data source status
        self.serial_thread_running = False # This will need to be updated from MainWindow

        # Define a threshold for detecting a touch signal
        self.touch_threshold = 0.5 # This threshold may need to be adjusted based on sensor characteristics

        self.data_acquisition_start_time = None # Store the start time of data acquisition

    def update_plots(self, data):
        # data 是一个列表，包含 [values, current_time]
        values = data[0] # values 是一个包含8个浮点数的列表 (CH1-CH8)
        current_time_s = data[1] # current_time 是接收到数据时的真实时间戳

        # Initialize start time if it's the first data point
        if self.data_acquisition_start_time is None:
            self.data_acquisition_start_time = current_time_s

        # Calculate relative time
        relative_time_s = current_time_s - self.data_acquisition_start_time

        # CH1-CH4 are row signals, CH5-CH8 are column signals
        row_signals = values[:4] # CH1-CH4
        col_signals = values[4:] # CH5-CH8

        # Update plot data and voltage labels
        for i in range(8):
            voltage = values[i]

            # 使用计算出的相对时间
            self.data_queues[i].append((voltage, current_time_s))
            if len(self.data_queues[i]) > self.max_data_points:
                self.data_queues[i].pop(0) # 移除最老的数据点

            # Extract x (time) and y (voltage) data for plotting
            plot_times = [item[1] for item in self.data_queues[i]]
            plot_voltages = [item[0] for item in self.data_queues[i]]
            self.data_lines[i].setData(plot_times, plot_voltages)
            # Update voltage labels if data is actively being generated
            if self.is_generating_test_data or self.serial_thread_running: # Need to update serial_thread_running flag from MainWindow
                self.voltage_labels[i].setText(f"CH{i+1}: {voltage:.3f} V")

        # Automatically adjust X-axis range for all plots if needed
        if plot_times:
            start_time = plot_times[0]
            end_time = plot_times[-1]
            
            # Adjust X-axis range only if new data is outside current view
            current_view_range = self.plot_widgets[0].getViewBox().viewRange()[0]
            view_duration = current_view_range[1] - current_view_range[0]
            
            # Automatically adjust X-axis range for all plots if needed
            # This automatic adjustment should only happen when new data arrives
            # and the current view does not encompass the new data.
            # Manual zooming/panning is handled by _synchronize_x_ranges.
            current_view_range = self.plot_widgets[0].getViewBox().viewRange()[0]
            if end_time > current_view_range[1] or start_time < current_view_range[0]:
                 # Calculate the desired new range based on the last data point
                 # Keep the same duration as the current view range
                 view_duration = current_view_range[1] - current_view_range[0]
                 new_end_time = end_time
                 new_start_time = max(plot_times[0], new_end_time - view_duration)

                 # Apply the new range to all plots
                 for plot_widget in self.plot_widgets:
                     plot_widget.getViewBox().setXRange(new_start_time, new_end_time, padding=0.01)
                    
        # --- Touch Point Detection and Pixel Map Update ---
        touched_row = -1
        touched_col = -1

        # Find activated row
        activated_rows = [i for i, signal in enumerate(row_signals) if signal > self.touch_threshold]
        # Find activated column
        activated_cols = [i for i, signal in enumerate(col_signals) if signal > self.touch_threshold]

        # Determine touch point based on activated row and column
        if len(activated_rows) == 1 and len(activated_cols) == 1:
            touched_row = activated_rows[0]
            touched_col = activated_cols[0]
            # Emit signal to update pixel map
            self.update_pixel_map_signal.emit(touched_row, touched_col)
            # Emit signal to update digital matrix with the time of the last data point
            if self.data_queues[0]: # Use time from the first channel as a reference
                 touch_time = self.data_queues[0][-1][1]
                 self.update_digital_matrix_signal.emit(touched_row, touched_col, touch_time)

        # No touch or multiple touches - do not clear pixel map or digital matrix here
        # Clearing is handled by the clear button and when stopping test data generation


    def _generate_single_test_data_point(self):
        import random
        import math
        import time

        # 生成一组模拟数据
        test_values = []

        # Simulate a single touch point for testing
        simulated_touch_row = random.randint(0, 3)
        simulated_touch_col = random.randint(0, 3)

        for i in range(8):
            if i < 4: # Row signals (CH1-CH4)
                if i == simulated_touch_row:
                    # Simulate a peak for the touched row
                    value = 2.5 + random.uniform(-0.2, 0.2) # Signal above threshold
                else:
                    # Simulate background noise for other rows
                    value = random.uniform(0.1, 0.3) # Signal below threshold
            else: # Column signals (CH5-CH8)
                if (i - 4) == simulated_touch_col:
                     # Simulate a peak for the touched column
                    value = 2.5 + random.uniform(-0.2, 0.2) # Signal above threshold
                else:
                    # Simulate background noise for other columns
                    value = random.uniform(0.1, 0.3) # Signal below threshold

            # Ensure value is within 0-3.3V range
            value = max(0, min(3.3, value))
            test_values.append(value)

        # 更新图表和像素映射，传递模拟数据和相对时间
        current_time = time.time()
        if self.data_acquisition_start_time is None:
            self.data_acquisition_start_time = current_time
            # Reset plot views when starting new data acquisition
            self._reset_plot_views()
        relative_time = current_time - self.data_acquisition_start_time
        self.update_plots([test_values, relative_time])

        # Increment the total generated points
        self.test_data_total_points += 1

        # Check if the target number of points has been reached AFTER updating plots
        if self.test_data_total_points >= self.test_data_points:
            self.test_data_timer.stop()
            self.is_generating_test_data = False
            self.test_data_button.setText("生成测试数据")
            self.status_bar.showMessage(f"测试数据采集完成 ({self.test_data_points} 点)")
            # The last point's pixel map and digital matrix updates are handled by update_plots




    def toggle_test_data_generation(self):
        if not self.is_generating_test_data:
            # Get frequency in Hz and points from spinboxes
            frequency_hz = self.frequency_spinbox.value()
            self.test_data_points = self.points_spinbox.value()

            # Calculate timer interval in ms from frequency in Hz
            if frequency_hz > 0:
                timer_interval_ms = int(1000 / frequency_hz)
            else:
                timer_interval_ms = 1000 # Default to 1 Hz if frequency is 0 or less

            # Reset total points counter
            self.test_data_total_points = 0

            # Set test data sample interval (based on timer interval)
            # self.sample_interval_s = timer_interval_ms / 1000.0 # This is no longer needed as we use real time

            # Start generating data
            self.is_generating_test_data = True # Update flag in PlotManager
            # Disconnect any previous connections before connecting
            try:
                self.test_data_timer.timeout.disconnect(self._generate_single_test_data_point)
            except TypeError:
                pass # Ignore if not connected
            self.test_data_timer.timeout.connect(self._generate_single_test_data_point)
            self.test_data_timer.start(timer_interval_ms) # Use calculated interval

            self.test_data_button.setText("停止生成")
            self.status_bar.showMessage(f"测试数据采集中 ({frequency_hz} Hz, 共 {self.test_data_points} 点)...")
        else:
            # Stop generating data manually
            self.test_data_timer.stop()
            try:
                self.test_data_timer.timeout.disconnect(self._generate_single_test_data_point)
            except TypeError:
                pass # Ignore if not connected
            self.is_generating_test_data = False # Update flag in PlotManager
            self.test_data_button.setText("生成测试数据")
            self.status_bar.showMessage("测试数据采集已停止")
            # Do NOT clear the pixel map or digital matrix here. They should persist until cleared by the user.


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

                    if max_samples == 0 and self.data_queues[0]: # Fallback if first queue has data but loop didn't catch
                         if self.data_queues[0]:
                            max_samples = len(self.data_queues[0])


                    # Write data rows
                    for sample_idx in range(max_samples):
                        row_data = [sample_idx]
                        # Time for this sample index - assumes first channel's time or calculate if needed
                        # For simplicity, we'll use the time from the first channel that has this sample
                        # or derive it if all channels are synchronized by sample count.

                        current_sample_time = None
                        # Find the time from the first channel that has data at this sample_idx
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
            mouse_x = mouse_point.x() # Get the mouse's x-coordinate in view coordinates

            # Update voltage labels for all channels based on the mouse's x-coordinate
            voltage_strings = ["--- V"] * 8
            for ch_idx in range(8):
                ch_x_data = self.data_lines[ch_idx].xData
                ch_y_data = self.data_lines[ch_idx].yData

                if ch_x_data is not None and len(ch_x_data) > 0:
                    first_x = ch_x_data[0]
                    last_x = ch_x_data[-1]

                    if mouse_x < first_x:
                        # Mouse is before the first data point, use the first point's voltage
                        interpolated_voltage = ch_y_data[0]
                    elif mouse_x > last_x:
                        # Mouse is after the last data point, use the last point's voltage
                        interpolated_voltage = ch_y_data[-1]
                    else:
                        # Mouse is within the data range, find the two closest points and interpolate
                        # Find the index of the point just before or at mouse_x
                        idx1 = 0
                        for i in range(len(ch_x_data) - 1):
                            if ch_x_data[i+1] > mouse_x:
                                idx1 = i
                                break
                            idx1 = i + 1 # In case mouse_x is exactly on a data point or after the second to last

                        # idx1 is now the index of the point <= mouse_x
                        # idx2 is the index of the point >= mouse_x
                        idx2 = idx1
                        if ch_x_data[idx1] < mouse_x and idx1 < len(ch_x_data) - 1:
                             idx2 = idx1 + 1

                        x1, y1 = ch_x_data[idx1], ch_y_data[idx1]
                        x2, y2 = ch_x_data[idx2], ch_y_data[idx2]

                        interpolated_voltage = self.linear_interpolate(mouse_x, x1, y1, x2, y2)

                    voltage_strings[ch_idx] = f"{interpolated_voltage:.3f} V"
                else:
                    # No data in this channel
                    voltage_strings[ch_idx] = "--- V"


            # Update all voltage labels after calculating voltages for all channels
            for ch_idx in range(8):
                 self.voltage_labels[ch_idx].setText(f"CH{ch_idx+1}: {voltage_strings[ch_idx]}")

            # Remove on-plot hover text display (if any)
            # The original code had hover_text_item, but it's not used for displaying text on the plot.
            # Keeping this line for safety if it's used elsewhere or intended for future use.
            if hasattr(plot_widget, 'hover_text_item') and plot_widget.hover_text_item:
                 plot_widget.hover_text_item.hide()

        else:
            # Mouse left the plot area, hide any potential hover text
            if hasattr(plot_widget, 'hover_text_item') and plot_widget.hover_text_item:
                 plot_widget.hover_text_item.hide()
            # Optionally, reset voltage labels when mouse leaves the plot area
            # for ch_idx in range(8):
            #      self.voltage_labels[ch_idx].setText(f"CH{ch_idx+1}: --- V")

    def _reset_all_x_ranges_to_data_range(self, changed_vb):
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

    def _clear_plot_data(self):
        for i in range(8):
            self.data_queues[i].clear()
            self.data_lines[i].setData([], [])
            self.voltage_labels[i].setText(f"CH{i+1}: 0.000 V")
        # Reset the data acquisition start time
        self.data_acquisition_start_time = None
        # Optional: reset plot X-axis, or keep as is
        # self._reset_plot_views() # Can call this method to reset zoom/pan
        # Status bar update needs to be handled in MainWindow
        # self.status_bar.showMessage("Plot data cleared")
        # Clear the pixel map and digital matrix when clearing data
        self.update_pixel_map_signal.emit(-1, -1)


    def _reset_plot_views(self):
        if hasattr(self, 'is_synchronizing_x') and self.is_synchronizing_x: # Prevent issues if called during an ongoing sync
            return
        self.is_synchronizing_x = True # Prevent sync signals during manual reset

        # Determine the current time range based on the first non-empty data queue
        # If all queues are empty, reset to a default initial view.
        current_min_time = 0.0
        current_max_time = 5.0 # Default to show 5 seconds initially

        # Try to find the actual time range from data
        found_data_range = False
        for queue in self.data_queues:
            if queue:
                times = [item[1] for item in queue]
                current_min_time = times[0]
                current_max_time = times[-1]
                # Ensure we show at least 1 second of data
                if (current_max_time - current_min_time) < 1.0:
                    current_max_time = current_min_time + 1.0
                found_data_range = True
                break

        if not found_data_range and self.data_queues[0]: # Fallback if first queue has data but loop didn't catch
             if self.data_queues[0]:
                times = [item[1] for item in self.data_queues[0]]
                current_min_time = times[0]
                current_max_time = times[-1]
                if (current_max_time - current_min_time) < 1.0:
                    current_max_time = current_min_time + 1.0

        for pw in self.plot_widgets:
            pw.getViewBox().setXRange(current_min_time, current_max_time, padding=0.1)
            # Y-axis is already fixed and non-interactive, so no Y-reset needed here

        self.is_synchronizing_x = False

    def linear_interpolate(self, x, x1, y1, x2, y2):
        """Performs linear interpolation."""
        if x1 == x2:
            return y1
        return y1 + (x - x1) * (y2 - y1) / (x2 - x1)

# 其他与图表相关的函数或类的占位符