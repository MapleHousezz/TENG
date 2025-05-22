# ui/serial_utils.py
#
# 文件功能说明:
# 该文件包含用于处理串口相关的辅助函数。
#

from PyQt5.QtWidgets import QComboBox
import serial.tools.list_ports

# 填充可用串口到下拉框的辅助函数
def populate_serial_ports(port_combo):
    """填充可用串口到下拉框。"""
    ports = serial.tools.list_ports.comports() # 获取可用串口列表
    port_combo.clear() # 清空下拉框
    for port in ports:
        port_combo.addItem(port.device) # 添加串口设备名称
    if not ports:
        port_combo.addItem("无可用串口") # 如果没有可用串口，显示提示
        port_combo.setEnabled(False) # 禁用下拉框
    else:
        port_combo.setEnabled(True) # 启用下拉框