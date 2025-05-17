import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton, QComboBox, QStatusBar, QMenuBar, QMenu, QAction, QMessageBox, QFileDialog
from PyQt5.QtCore import QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QIcon # Import QIcon
import serial
import serial.tools.list_ports
import pyqtgraph as pg
import struct
import time
import csv
import os # For path joining in export
from ui_components import create_control_panel, create_data_display_area, create_menu_bar, create_status_bar, create_pixel_map_area # Import create_pixel_map_area
from plot_manager import PlotManager
from serial_manager import SerialManager

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TENG阵列多通道信号检测系统_V1.1")
        self.setGeometry(0, 0, 1920, 1080)

        self.serial_thread = None
        self.plot_widgets = []
        self.data_lines = []
        self.data_queues = [[] for _ in range(8)] # 每个通道一个数据队列 (voltage, time_s)
        self.max_data_points = 1000 # 图表上显示的最大数据点数
        self.hover_texts = [] # 用于存储每个图表的悬停文本对象
        self.is_synchronizing_x = False # Flag to prevent recursive X-axis sync
        self.sample_interval_s = 0.001 # 采样间隔，秒 (对应1ms)

        self.test_data_timer = QTimer(self) # 新增测试数据定时器

        self._init_ui()

        # Create PlotManager instance
        self.plot_manager = PlotManager(
            self.plot_widgets,
            self.data_lines,
            self.data_queues,
            self.voltage_labels,
            self.sample_interval_s,
            self.max_data_points,
            self.test_data_button,
            self.status_bar,
            self.test_data_timer,
            self.pixel_labels, # Pass pixel_labels to PlotManager
            self.frequency_spinbox, # Pass frequency spinbox
            self.points_spinbox, # Pass points spinbox
            self.digital_matrix_labels # Pass digital matrix labels
        )

        # Create SerialManager instance
        self.serial_manager = SerialManager(
            self.port_combo,
            self.baud_combo,
            self.flow_control_combo,
            self.parity_combo,
            self.databits_combo,
            self.stopbits_combo,
            self.connect_button,
            self.disconnect_button,
            self.status_bar # Pass status bar reference
        )

        # Connect SerialManager signals
        self.serial_manager.status_changed.connect(self.update_status_bar)
        self.serial_manager.data_received.connect(self.plot_manager.update_plots)

        # Connect PlotManager signal to update pixel map
        self.plot_manager.update_pixel_map_signal.connect(self.update_pixel_map)
        # Connect signal to update digital matrix
        self.plot_manager.update_digital_matrix_signal.connect(self.update_digital_matrix)


        # Call populate_serial_ports from SerialManager
        self.serial_manager.populate_serial_ports()

        # Link X-axes of all plot widgets to the first one for synchronization
        if self.plot_widgets:
            first_view_box = self.plot_widgets[0].getViewBox()
            for i in range(1, len(self.plot_widgets)):
                self.plot_widgets[i].getViewBox().setXLink(first_view_box)

        # Connect mouse moved signal using a dedicated slot creator
        for plot_widget in self.plot_widgets:
             plot_index = self.plot_widgets.index(plot_widget)
             plot_widget.scene().sigMouseMoved.connect(self._create_mouse_moved_slot(plot_widget, plot_index))

        # Connect control panel button signals
        self.connect_button.clicked.connect(self.serial_manager.connect_serial)
        self.disconnect_button.clicked.connect(self.serial_manager.disconnect_serial)
        self.test_data_button.clicked.connect(self.plot_manager.toggle_test_data_generation)
        self.reset_view_button.clicked.connect(self.plot_manager._reset_plot_views)
        self.clear_data_button.clicked.connect(self.plot_manager._clear_plot_data)
        self.export_data_button.clicked.connect(self.plot_manager.export_data_to_csv)

        # Connect menu actions
        self.about_action.triggered.connect(self.show_about_dialog)

        # Ensure default display of pixel map
        self.update_pixel_map(-1, -1)


    def _init_ui(self):
         # --- Central Widget and Layout --- #
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # Set window icon
        icon_path = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), 'icon.ico')
        self.setWindowIcon(QIcon(icon_path))

        # --- Left Control Panel --- #
        control_components = create_control_panel(self)
        main_layout.addWidget(control_components['control_panel'], 0) # Control panel fixed width

        # Assign control panel components to instance attributes
        self.voltage_labels = control_components['voltage_labels']
        self.data_engine_combo = control_components['data_engine_combo']
        self.data_interface_combo = control_components['data_interface_combo']
        self.port_combo = control_components['port_combo']
        self.baud_combo = control_components['baud_combo']
        self.flow_control_combo = control_components['flow_control_combo']
        self.parity_combo = control_components['parity_combo']
        self.databits_combo = control_components['databits_combo']
        self.stopbits_combo = control_components['stopbits_combo']
        self.connect_button = control_components['connect_button']
        self.disconnect_button = control_components['disconnect_button']
        self.test_data_button = control_components['test_data_button']
        self.reset_view_button = control_components['reset_view_button']
        self.clear_data_button = control_components['clear_data_button']
        self.export_data_button = control_components['export_data_button']
        self.frequency_spinbox = control_components['frequency_spinbox'] # Get frequency spinbox
        self.points_spinbox = control_components['points_spinbox'] # Get points spinbox

        # --- Data Display Area --- #
        data_display_components = create_data_display_area(self)
        main_layout.addWidget(data_display_components['data_display_area'], 3) # Plots take more space

        # Assign data display components to instance attributes
        self.plot_widgets = data_display_components['plot_widgets']
        self.data_lines = data_display_components['data_lines']
        self.hover_texts = data_display_components['hover_texts']

        # --- Pixel Map --- #
        pixel_map_components = create_pixel_map_area(self)
        main_layout.addWidget(pixel_map_components['pixel_map_widget'], 1) # Pixel map takes less space

        # Assign pixel map components to instance attributes
        self.pixel_labels = pixel_map_components['pixel_labels']
        self.clear_map_button = pixel_map_components['clear_map_button'] # Get clear map button
        self.digital_matrix_labels = pixel_map_components['digital_matrix_labels'] # Get digital matrix labels


        # --- Menu Bar --- #
        menu_actions = create_menu_bar(self)
        self.about_action = menu_actions['about_action']
        # self.exit_action = menu_actions['exit_action'] # exit_action is already connected inside create_menu_bar

        # --- Status Bar --- #
        self.status_bar = create_status_bar(self)

        # Connect clear map button signal
        self.clear_map_button.clicked.connect(self.clear_pixel_map)

    def update_pixel_map(self, row, col):
        """Updates the pixel map display based on the touched row and column."""
        # Only highlight the touched pixel if a valid touch is detected
        if 0 <= row < 4 and 0 <= col < 4:
            # Reset previous highlighted pixel if any (optional, depends on desired behavior)
            # For now, we'll just highlight the new one.
            self.pixel_labels[row][col].setStyleSheet("background-color: lightblue; border: none;")
        elif row == -1 and col == -1:
            # Clear all pixels if -1, -1 is received
            self.clear_pixel_map()


    def clear_pixel_map(self):
        """Clears the pixel map display and digital matrix."""
        for row in range(4):
            for col in range(4):
                self.pixel_labels[row][col].setStyleSheet("background-color: lightgray; border: none;")
                self.digital_matrix_labels[row][col].setText("0.000") # Clear digital matrix


    def update_digital_matrix(self, row, col, time_s):
        """Updates the digital matrix display with the touch time."""
        if 0 <= row < 4 and 0 <= col < 4:
            self.digital_matrix_labels[row][col].setText(f"{time_s:.3f}")


    def _create_mouse_moved_slot(self, plot_widget, plot_index):
        def mouse_moved_slot(pos):
            self.plot_manager._mouse_moved_on_plot(pos, plot_widget, plot_index)
        return mouse_moved_slot

    def update_status_bar(self, message):
        self.status_bar.showMessage(message)

    def show_about_dialog(self):
        QMessageBox.about(self, "关于", "PyQt 上位机软件\n版本 1.0\n作者: GQL")

    def closeEvent(self, event):
        self.serial_manager.disconnect_serial() #确保关闭时断开串口
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # 设置应用程序图标
    icon_path = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), 'icon.ico')
    app.setWindowIcon(QIcon(icon_path))
    main_win = MainWindow()
    main_win.showMaximized()
    sys.exit(app.exec_())