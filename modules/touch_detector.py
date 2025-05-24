# modules/touch_detector.py
#
# 触摸检测模块
# 负责检测触摸点并发出相应信号
#

from PyQt5.QtCore import QObject, pyqtSignal

class TouchDetector(QObject):
    """触摸检测器，负责检测触摸点并发出信号"""
    
    # 定义信号
    touch_detected = pyqtSignal(int, int)  # 触摸检测信号 (row, col)
    touch_with_time = pyqtSignal(int, int, float)  # 带时间的触摸信号 (row, col, time)
    
    def __init__(self, touch_threshold=0.5):
        super().__init__()
        self.touch_threshold = touch_threshold  # 触摸检测阈值
        
    def set_threshold(self, threshold):
        """设置触摸检测阈值"""
        self.touch_threshold = threshold
        
    def detect_touch(self, values, current_time=None):
        """检测触摸点
        
        Args:
            values: 8个通道的电压值列表 (CH1-CH4为行信号，CH5-CH8为列信号)
            current_time: 当前时间戳
            
        Returns:
            tuple: (touched_row, touched_col) 如果检测到单点触摸，否则返回 (-1, -1)
        """
        if not values or len(values) < 8:
            return -1, -1
            
        # CH1-CH4 是行信号，CH5-CH8 是列信号
        row_signals = values[:4]
        col_signals = values[4:]
        
        # 查找激活的行和列
        activated_rows = [i for i, signal in enumerate(row_signals) if signal > self.touch_threshold]
        activated_cols = [i for i, signal in enumerate(col_signals) if signal > self.touch_threshold]
        
        # 只有在单点触摸时才认为是有效触摸
        if len(activated_rows) == 1 and len(activated_cols) == 1:
            touched_row = activated_rows[0]
            touched_col = activated_cols[0]
            
            # 发出触摸检测信号
            self.touch_detected.emit(touched_row, touched_col)
            
            # 如果提供了时间戳，发出带时间的信号
            if current_time is not None:
                self.touch_with_time.emit(touched_row, touched_col, current_time)
                
            return touched_row, touched_col
            
        return -1, -1
        
    def is_touch_active(self, values):
        """检查是否有触摸活动
        
        Returns:
            bool: 如果检测到任何触摸活动返回True
        """
        if not values or len(values) < 8:
            return False
            
        # 检查是否有任何信号超过阈值
        return any(signal > self.touch_threshold for signal in values)
        
    def get_touch_strength(self, values):
        """获取触摸强度
        
        Returns:
            dict: 包含行和列触摸强度的字典
        """
        if not values or len(values) < 8:
            return {'rows': [0]*4, 'cols': [0]*4}
            
        row_signals = values[:4]
        col_signals = values[4:]
        
        # 计算相对于阈值的强度
        row_strengths = [max(0, signal - self.touch_threshold) for signal in row_signals]
        col_strengths = [max(0, signal - self.touch_threshold) for signal in col_signals]
        
        return {
            'rows': row_strengths,
            'cols': col_strengths
        }
        
    def get_multi_touch_points(self, values):
        """获取所有可能的触摸点（包括多点触摸）
        
        Returns:
            list: 触摸点列表 [(row, col), ...]
        """
        if not values or len(values) < 8:
            return []
            
        row_signals = values[:4]
        col_signals = values[4:]
        
        activated_rows = [i for i, signal in enumerate(row_signals) if signal > self.touch_threshold]
        activated_cols = [i for i, signal in enumerate(col_signals) if signal > self.touch_threshold]
        
        # 生成所有可能的触摸点组合
        touch_points = []
        for row in activated_rows:
            for col in activated_cols:
                touch_points.append((row, col))
                
        return touch_points