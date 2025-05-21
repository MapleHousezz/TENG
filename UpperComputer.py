# UpperComputer.py
#
# 文件功能说明:
# 这是上位机软件的主文件，包含 MainWindow 类。
# MainWindow 类负责设置主窗口的布局和组件，连接信号和槽，
# 并协调 PlotManager 和 SerialManager 类来处理数据采集、图表显示和用户交互。
# 它是整个应用程序的入口点。
#

import sys
from PyQt5 import QtCore  # 添加QtCore导入
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton, QComboBox, QStatusBar, QMenuBar, QMenu, QAction, QMessageBox, QFileDialog
from PyQt5.QtCore import QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QIcon # 导入 QIcon
import serial
import serial.tools.list_ports
import pyqtgraph as pg
import struct
import time
import csv
import os # 用于导出路径拼接
from ui_components import create_control_panel, create_data_display_area, create_menu_bar, create_status_bar, create_pixel_map_area # 导入 create_pixel_map_area
from plot_manager import PlotManager
from serial_manager import SerialManager

class MainWindow(QMainWindow):
    """主窗口类，设置 UI 并协调 PlotManager 和 SerialManager。"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TENG阵列多通道信号检测系统_V1.1")
        self.setGeometry(0, 0, 1920, 1080)

        self.serial_thread = None
        self.plot_widgets = []
        self.data_lines = []
        self.hover_texts = []
        self.is_synchronizing_x = False
        self.sample_interval_s = 0.001
        self.start_time = None  # 全局开始时间
        self.last_time_offset = 0.0  # 上次断开时的时间偏移

        self.test_data_timer = QTimer(self) # 新增测试数据定时器

        self._init_ui() # 初始化用户界面

        # 创建 PlotManager 实例
        self.plot_manager = PlotManager(
            self, # 传递 MainWindow 实例
            self.plot_widgets,
            self.data_lines,
            self.voltage_labels,
            self.sample_interval_s,
            self.test_data_button,
            self.status_bar,
            self.test_data_timer,
            self.pixel_labels, # 将 pixel_labels 传递给 PlotManager
            self.frequency_spinbox, # 将 frequency spinbox 传递给 PlotManager
            self.points_spinbox, # 将 points spinbox 传递给 PlotManager
            self.digital_matrix_labels # 将 digital matrix labels 传递给 PlotManager
        )

        # 创建 SerialManager 实例
        self.serial_manager = SerialManager(
            self.port_combo,
            self.baud_combo,
            self.flow_control_combo,
            self.parity_combo,
            self.databits_combo,
            self.stopbits_combo,
            self.connect_button,
            self.disconnect_button,
            self.status_bar,
            self  # 传递MainWindow引用以访问时间信息
        )

        # 连接 SerialManager 信号
        # 使用QueuedConnection确保跨线程通信安全
        self.serial_manager.status_changed.connect(self.update_status_bar, QtCore.Qt.QueuedConnection)
        self.serial_manager.data_received.connect(self.plot_manager.update_plots, QtCore.Qt.QueuedConnection)

        # 连接 PlotManager 信号以更新像素地图
        self.plot_manager.update_pixel_map_signal.connect(self.update_pixel_map, QtCore.Qt.QueuedConnection)
        # 连接信号以更新数字矩阵
        self.plot_manager.update_digital_matrix_signal.connect(self.update_digital_matrix, QtCore.Qt.QueuedConnection)


        # 从 SerialManager 调用 populate_serial_ports
        self.serial_manager.populate_serial_ports() # 填充可用串口

        # 将所有图表控件的 X 轴链接到第一个图表，以实现同步
        if self.plot_widgets:
            first_view_box = self.plot_widgets[0].getViewBox() # 获取第一个图表的 ViewBox
            for i in range(1, len(self.plot_widgets)):
                self.plot_widgets[i].getViewBox().setXLink(first_view_box) # 链接 X 轴

        # 使用专用的槽创建器连接鼠标移动信号
        for plot_widget in self.plot_widgets:
             plot_index = self.plot_widgets.index(plot_widget) # 获取图表索引
             plot_widget.scene().sigMouseMoved.connect(self._create_mouse_moved_slot(plot_widget, plot_index)) # 连接鼠标移动信号

        # 连接控制面板按钮信号
        self.connect_button.clicked.connect(self.serial_manager.connect_serial) # 连接连接按钮信号
        self.disconnect_button.clicked.connect(self.serial_manager.disconnect_serial) # 连接断开按钮信号
        self.test_data_button.clicked.connect(self.plot_manager.toggle_test_data_generation) # 连接测试数据生成按钮信号
        self.reset_view_button.clicked.connect(self.plot_manager._reset_plot_views) # 连接复位图表按钮信号
        self.clear_data_button.clicked.connect(self.plot_manager._clear_plot_data) # 连接清空数据按钮信号
        self.export_data_button.clicked.connect(self.plot_manager.export_data_to_csv) # 连接导出数据按钮信号

        # 连接菜单动作
        self.about_action.triggered.connect(self.show_about_dialog) # 连接关于动作信号

        # 确保像素地图的默认显示
        self.update_pixel_map(-1, -1) # 初始清空像素地图


    def _init_ui(self):
         # --- 中心控件和布局 --- #
        central_widget = QWidget() # 创建中心控件
        self.setCentralWidget(central_widget) # 设置中心控件
        main_layout = QHBoxLayout(central_widget) # 创建主水平布局

        # 设置窗口图标
        icon_path = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), 'icon.ico') # 获取图标路径
        self.setWindowIcon(QIcon(icon_path)) # 设置窗口图标

        # --- 左侧控制面板 --- #
        control_components = create_control_panel(self) # 创建控制面板
        main_layout.addWidget(control_components['control_panel'], 0) # 添加控制面板到主布局，固定宽度

        # 将控制面板组件分配给实例属性
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
        self.frequency_spinbox = control_components['frequency_spinbox'] # 获取频率微调框
        self.points_spinbox = control_components['points_spinbox'] # 获取点数微调框

        # --- 数据显示区域 --- #
        data_display_components = create_data_display_area(self) # 创建数据显示区域
        main_layout.addWidget(data_display_components['data_display_area'], 3) # 添加数据显示区域到主布局，占据更多空间

        # 将数据显示组件分配给实例属性
        self.plot_widgets = data_display_components['plot_widgets']
        self.data_lines = data_display_components['data_lines']
        self.hover_texts = data_display_components['hover_texts']

        # --- 像素地图 --- #
        pixel_map_components = create_pixel_map_area(self) # 创建像素地图区域
        main_layout.addWidget(pixel_map_components['pixel_map_widget'], 1) # 添加像素地图区域到主布局，占据较少空间

        # 将像素地图组件分配给实例属性
        self.pixel_labels = pixel_map_components['pixel_labels']
        self.clear_map_button = pixel_map_components['clear_map_button'] # 获取清空地图按钮
        self.digital_matrix_labels = pixel_map_components['digital_matrix_labels'] # 获取数字矩阵标签


        # --- 菜单栏 --- #
        menu_actions = create_menu_bar(self) # 创建菜单栏
        self.about_action = menu_actions['about_action'] # 获取关于动作
        # self.exit_action = menu_actions['exit_action'] # exit_action 已在 create_menu_bar 内部连接

        # --- 状态栏 --- #
        self.status_bar = create_status_bar(self) # 创建状态栏

        # 连接清空地图按钮信号
        self.clear_map_button.clicked.connect(self.clear_pixel_map) # 连接清空像素地图信号

    def update_pixel_map(self, row, col):
        """根据触摸的行和列更新像素地图显示。"""
        # 仅在高亮显示检测到有效触摸时更新
        if 0 <= row < 4 and 0 <= col < 4:
            # 重置之前高亮的像素（可选，取决于所需行为）
            # 目前，我们只高亮新的像素。
            self.pixel_labels[row][col].setStyleSheet("background-color: lightblue; border: none;") # 设置高亮样式
        elif row == -1 and col == -1:
            # 如果接收到 -1, -1，则清除所有像素
            self.clear_pixel_map() # 调用清空像素地图函数


    def clear_pixel_map(self):
        """清除像素地图显示和数字矩阵。"""
        for row in range(4):
            for col in range(4):
                self.pixel_labels[row][col].setStyleSheet("background-color: lightgray; border: none;") # 重置为默认样式
                self.digital_matrix_labels[row][col].setText("0.000") # 清空数字矩阵文本


    def update_digital_matrix(self, row, col, time_s):
        """使用触摸时间更新数字矩阵显示。"""
        if 0 <= row < 4 and 0 <= col < 4:
            self.digital_matrix_labels[row][col].setText(f"{time_s:.3f}") # 设置数字矩阵文本


    def _create_mouse_moved_slot(self, plot_widget, plot_index):
        """为每个图表创建鼠标移动槽函数。"""
        def mouse_moved_slot(pos):
            self.plot_manager._mouse_moved_on_plot(pos, plot_widget, plot_index) # 调用 PlotManager 中的处理函数
        return mouse_moved_slot # 返回槽函数

    def update_status_bar(self, message):
        """更新状态栏消息。"""
        self.status_bar.showMessage(message) # 显示消息

    def show_about_dialog(self):
        """显示关于对话框。"""
        QMessageBox.about(self, "关于", "PyQt 上位机软件\n版本 1.0\n作者: GQL") # 显示关于信息

    def closeEvent(self, event):
        """处理窗口关闭事件。"""
        self.serial_manager.disconnect_serial() # 确保关闭时断开串口
        super().closeEvent(event) # 调用父类的 closeEvent

if __name__ == "__main__":
    app = QApplication(sys.argv) # 创建 QApplication 实例
    # 设置应用程序图标
    icon_path = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), 'icon.ico') # 获取图标路径
    app.setWindowIcon(QIcon(icon_path)) # 设置应用程序图标
    main_win = MainWindow() # 创建 MainWindow 实例
    main_win.showMaximized() # 最大化显示窗口
    sys.exit(app.exec_()) # 运行应用程序事件循环