# modules/data_exporter.py
#
# 数据导出模块
# 负责将采集的数据导出为各种格式的文件
#

import csv
import os
import json
from datetime import datetime
from PyQt5.QtWidgets import QMessageBox, QFileDialog
from PyQt5.QtCore import QObject, pyqtSignal

class DataExporter(QObject):
    """数据导出器，负责将数据导出为不同格式的文件"""
    
    # 定义信号
    export_completed = pyqtSignal(str)  # 导出完成信号
    export_failed = pyqtSignal(str)     # 导出失败信号
    
    def __init__(self, parent=None):
        super().__init__()
        self.parent = parent
        
    def export_to_csv(self, data_manager, sample_interval_s=0.1):
        """导出数据到CSV文件
        
        Args:
            data_manager: 数据管理器实例
            sample_interval_s: 采样间隔（秒）
            
        Returns:
            bool: 导出是否成功
        """
        if not data_manager.has_data():
            QMessageBox.information(self.parent, "导出数据", "没有数据可导出。")
            return False
            
        # 选择保存文件路径
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        file_path, _ = QFileDialog.getSaveFileName(
            self.parent, 
            "保存数据", 
            f"sensor_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV 文件 (*.csv);;所有文件 (*)", 
            options=options
        )
        
        if not file_path:
            return False
            
        if not file_path.lower().endswith('.csv'):
            file_path += '.csv'
            
        try:
            self._write_csv_file(file_path, data_manager, sample_interval_s)
            self.export_completed.emit(os.path.basename(file_path))
            return True
        except Exception as e:
            error_msg = f"无法保存文件: {e}"
            QMessageBox.critical(self.parent, "导出错误", error_msg)
            self.export_failed.emit(error_msg)
            return False
            
    def _write_csv_file(self, file_path, data_manager, sample_interval_s):
        """写入CSV文件"""
        full_data = data_manager.get_all_data()
        
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            csv_writer = csv.writer(csvfile)
            
            # 写入表头
            header = ['Sample Index', 'Time (s)']
            for i in range(8):
                header.append(f'Channel {i+1} Voltage (V)')
            csv_writer.writerow(header)
            
            # 获取最大样本数
            max_samples = max(len(channel) for channel in full_data) if full_data else 0
            
            # 写入数据行
            for sample_idx in range(max_samples):
                row_data = [sample_idx + 1]  # 样本索引从1开始
                
                # 获取时间戳（使用第一个通道的时间）
                if sample_idx < len(full_data[0]):
                    current_sample_time = full_data[0][sample_idx][1]
                else:
                    current_sample_time = sample_idx * sample_interval_s
                    
                row_data.append(f"{current_sample_time:.3f}")
                
                # 添加各通道电压值
                for i in range(8):
                    if sample_idx < len(full_data[i]):
                        row_data.append(f"{full_data[i][sample_idx][0]:.3f}")
                    else:
                        row_data.append('')
                        
                csv_writer.writerow(row_data)
                
    def export_to_json(self, data_manager, metadata=None):
        """导出数据到JSON文件
        
        Args:
            data_manager: 数据管理器实例
            metadata: 附加的元数据字典
            
        Returns:
            bool: 导出是否成功
        """
        if not data_manager.has_data():
            QMessageBox.information(self.parent, "导出数据", "没有数据可导出。")
            return False
            
        # 选择保存文件路径
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        file_path, _ = QFileDialog.getSaveFileName(
            self.parent,
            "保存数据",
            f"sensor_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "JSON 文件 (*.json);;所有文件 (*)",
            options=options
        )
        
        if not file_path:
            return False
            
        if not file_path.lower().endswith('.json'):
            file_path += '.json'
            
        try:
            self._write_json_file(file_path, data_manager, metadata)
            self.export_completed.emit(os.path.basename(file_path))
            return True
        except Exception as e:
            error_msg = f"无法保存文件: {e}"
            QMessageBox.critical(self.parent, "导出错误", error_msg)
            self.export_failed.emit(error_msg)
            return False
            
    def _write_json_file(self, file_path, data_manager, metadata):
        """写入JSON文件"""
        full_data = data_manager.get_all_data()
        
        # 构建JSON数据结构
        export_data = {
            'metadata': {
                'export_time': datetime.now().isoformat(),
                'channels': 8,
                'data_points': len(full_data[0]) if full_data else 0,
                'time_range': data_manager.get_time_range()
            },
            'channels': {}
        }
        
        # 添加用户提供的元数据
        if metadata:
            export_data['metadata'].update(metadata)
            
        # 添加通道数据
        for i in range(8):
            channel_data = []
            for voltage, timestamp in full_data[i]:
                channel_data.append({
                    'time': timestamp,
                    'voltage': voltage
                })
            export_data['channels'][f'CH{i+1}'] = channel_data
            
        # 写入文件
        with open(file_path, 'w', encoding='utf-8') as jsonfile:
            json.dump(export_data, jsonfile, indent=2, ensure_ascii=False)
            
    def export_summary_report(self, data_manager, touch_events=None):
        """导出数据摘要报告
        
        Args:
            data_manager: 数据管理器实例
            touch_events: 触摸事件列表
            
        Returns:
            bool: 导出是否成功
        """
        if not data_manager.has_data():
            QMessageBox.information(self.parent, "导出报告", "没有数据可导出。")
            return False
            
        # 选择保存文件路径
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        file_path, _ = QFileDialog.getSaveFileName(
            self.parent,
            "保存摘要报告",
            f"summary_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "文本文件 (*.txt);;所有文件 (*)",
            options=options
        )
        
        if not file_path:
            return False
            
        try:
            self._write_summary_report(file_path, data_manager, touch_events)
            self.export_completed.emit(os.path.basename(file_path))
            return True
        except Exception as e:
            error_msg = f"无法保存文件: {e}"
            QMessageBox.critical(self.parent, "导出错误", error_msg)
            self.export_failed.emit(error_msg)
            return False
            
    def _write_summary_report(self, file_path, data_manager, touch_events):
        """写入摘要报告"""
        full_data = data_manager.get_all_data()
        start_time, end_time = data_manager.get_time_range()
        
        with open(file_path, 'w', encoding='utf-8') as report_file:
            report_file.write("传感器数据摘要报告\n")
            report_file.write("=" * 50 + "\n\n")
            
            # 基本信息
            report_file.write(f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            report_file.write(f"数据采集时间范围: {start_time:.3f}s - {end_time:.3f}s\n")
            report_file.write(f"总采集时长: {end_time - start_time:.3f}s\n")
            report_file.write(f"通道数量: 8\n")
            report_file.write(f"数据点数量: {len(full_data[0]) if full_data else 0}\n\n")
            
            # 各通道统计信息
            report_file.write("各通道统计信息:\n")
            report_file.write("-" * 30 + "\n")
            
            for i in range(8):
                if full_data[i]:
                    voltages = [point[0] for point in full_data[i]]
                    min_v = min(voltages)
                    max_v = max(voltages)
                    avg_v = sum(voltages) / len(voltages)
                    
                    report_file.write(f"CH{i+1}: 最小值={min_v:.3f}V, 最大值={max_v:.3f}V, 平均值={avg_v:.3f}V\n")
                else:
                    report_file.write(f"CH{i+1}: 无数据\n")
                    
            # 触摸事件统计
            if touch_events:
                report_file.write(f"\n触摸事件统计:\n")
                report_file.write("-" * 30 + "\n")
                report_file.write(f"总触摸事件数: {len(touch_events)}\n")
                
                # 按位置统计触摸次数
                touch_count = {}
                for event in touch_events:
                    pos = (event.get('row', -1), event.get('col', -1))
                    touch_count[pos] = touch_count.get(pos, 0) + 1
                    
                report_file.write("\n各位置触摸次数:\n")
                for (row, col), count in sorted(touch_count.items()):
                    if row >= 0 and col >= 0:
                        report_file.write(f"位置({row}, {col}): {count}次\n")