# serial_manager.py

import serial
import serial.tools.list_ports
from PyQt5.QtWidgets import QComboBox, QPushButton, QMessageBox, QStatusBar
from PyQt5.QtCore import pyqtSignal, QObject
from serial_handler import SerialThread # Assuming SerialThread is in serial_handler.py

class SerialManager(QObject):
    # Define signals that MainWindow will connect to
    status_changed = pyqtSignal(str)
    data_received = pyqtSignal(list) # Assuming data is received as a list of values

    def __init__(self, port_combo, baud_combo, flow_control_combo, parity_combo, databits_combo, stopbits_combo, connect_button, disconnect_button, status_bar):
        super().__init__()
        self.port_combo = port_combo
        self.baud_combo = baud_combo
        self.flow_control_combo = flow_control_combo
        self.parity_combo = parity_combo
        self.databits_combo = databits_combo
        self.stopbits_combo = stopbits_combo
        self.connect_button = connect_button
        self.disconnect_button = disconnect_button
        self.status_bar = status_bar # Need status bar reference to update messages

        self.serial_thread = None

    def populate_serial_ports(self):
        ports = serial.tools.list_ports.comports()
        self.port_combo.clear()
        for port in ports:
            self.port_combo.addItem(port.device)
        if not ports:
            self.port_combo.addItem("无可用串口")
            self.connect_button.setEnabled(False)

    def connect_serial(self):
        port = self.port_combo.currentText()
        if port == "无可用串口":
            QMessageBox.warning(None, "连接错误", "没有选择有效的串口。") # Use None as parent for QMessageBox
            return

        baudrate = int(self.baud_combo.currentText())

        stopbits_str = self.stopbits_combo.currentText()
        if stopbits_str == "1":
            stopbits = serial.STOPBITS_ONE
        elif stopbits_str == "1.5":
            stopbits = serial.STOPBITS_ONE_POINT_FIVE
        else: # "2"
            stopbits = serial.STOPBITS_TWO

        databits_str = self.databits_combo.currentText()
        if databits_str == "5":
            databits = serial.FIVEBITS
        elif databits_str == "6":
            databits = serial.SIXBITS
        elif databits_str == "7":
            databits = serial.SEVENBITS
        else: # "8"
            databits = serial.EIGHTBITS

        parity_str = self.parity_combo.currentText()
        if parity_str == "None":
            parity = serial.PARITY_NONE
        elif parity_str == "Even":
            parity = serial.PARITY_EVEN
        elif parity_str == "Odd":
            parity = serial.PARITY_ODD
        elif parity_str == "Mark":
            parity = serial.PARITY_MARK
        else: # "Space"
            parity = serial.PARITY_SPACE

        flowcontrol = self.flow_control_combo.currentText()

        self.serial_thread = SerialThread(port, baudrate, stopbits, databits, parity, flowcontrol)
        self.serial_thread.data_received.connect(self.data_received.emit)
        self.serial_thread.status_changed.connect(self.status_changed.emit)
        self.serial_thread.start()

        self.connect_button.setEnabled(False)
        self.disconnect_button.setEnabled(True)
        self.port_combo.setEnabled(False)
        self.baud_combo.setEnabled(False)
        self.stopbits_combo.setEnabled(False)
        self.databits_combo.setEnabled(False)
        self.parity_combo.setEnabled(False)
        self.flow_control_combo.setEnabled(False)
        # Data engine and interface combos are handled by MainWindow
        # self.data_engine_combo.setEnabled(False)
        # self.data_interface_combo.setEnabled(False)

    def disconnect_serial(self):
        if self.serial_thread and self.serial_thread.isRunning():
            self.serial_thread.stop()
            self.serial_thread.wait() # 等待线程结束

        self.connect_button.setEnabled(True)
        self.disconnect_button.setEnabled(False)
        self.port_combo.setEnabled(True)
        self.baud_combo.setEnabled(True)
        self.stopbits_combo.setEnabled(True)
        self.databits_combo.setEnabled(True)
        self.parity_combo.setEnabled(True)
        self.flow_control_combo.setEnabled(True)
        # Data engine and interface combos are handled by MainWindow
        # self.data_engine_combo.setEnabled(True)
        # self.data_interface_combo.setEnabled(True)
        self.status_changed.emit("串口已断开")

    def is_connected(self):
        return self.serial_thread is not None and self.serial_thread.isRunning()