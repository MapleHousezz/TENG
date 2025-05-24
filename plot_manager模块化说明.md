# PlotManager 模块化重构说明

## 概述

原来的 `plot_manager.py` 文件包含了500行代码，功能复杂且耦合度高。为了提高代码的可维护性和可扩展性，我们将其重构为模块化的设计。

## 模块结构

### 1. 核心模块目录：`modules/`

#### `modules/data_manager.py` - 数据管理模块
- **功能**：负责图表数据的存储、更新和缓存
- **主要特性**：
  - 双缓存数据存储机制
  - 8通道数据管理
  - 时间范围查询
  - 数据插值功能
  - 内存优化的数据清理

#### `modules/touch_detector.py` - 触摸检测模块
- **功能**：检测触摸点并发出相应信号
- **主要特性**：
  - 可配置的触摸检测阈值
  - 多点触摸支持
  - 触摸强度计算
  - 实时触摸状态监控

#### `modules/test_data_generator.py` - 测试数据生成模块
- **功能**：生成模拟的触摸传感器数据
- **主要特性**：
  - 可配置的生成频率和持续时间
  - 模拟触摸点生成
  - 信号参数自定义
  - 异步数据生成

#### `modules/data_exporter.py` - 数据导出模块
- **功能**：将采集的数据导出为不同格式
- **主要特性**：
  - CSV格式导出
  - JSON格式导出
  - 摘要报告生成
  - 错误处理和用户反馈

#### `modules/plot_synchronizer.py` - 图表同步模块
- **功能**：管理多个图表的视图同步
- **主要特性**：
  - X轴范围同步
  - Y轴范围管理
  - 自动缩放功能
  - 视图重置和导航

#### `modules/plot_updater.py` - 图表更新模块
- **功能**：处理图表的实时数据更新和显示
- **主要特性**：
  - 实时数据绘制
  - 电压标签更新
  - 性能优化的更新频率控制
  - 图表样式管理

### 2. 重构后的主文件：`plot_manager_new.py`

- **功能**：作为各模块的协调器和主要接口
- **主要改进**：
  - 代码行数从500行减少到约300行
  - 清晰的模块职责分离
  - 更好的错误处理
  - 统一的信号管理

## 使用方法

### 1. 替换原文件

```bash
# 备份原文件
cp plot_manager.py plot_manager_backup.py

# 使用新的模块化版本
cp plot_manager_new.py plot_manager.py
```

### 2. 确保模块导入

在你的主程序中，确保 `modules` 目录在 Python 路径中：

```python
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from plot_manager import PlotManager
```

### 3. 使用示例

```python
# 创建PlotManager实例（与原来相同）
plot_manager = PlotManager(
    main_window=self,
    plot_widgets=self.plot_widgets,
    data_lines=self.data_lines,
    voltage_labels=self.voltage_labels,
    sample_interval_s=self.sample_interval_s,
    test_data_button=self.test_data_button,
    status_bar=self.status_bar,
    test_data_timer=self.test_data_timer,
    pixel_labels=self.pixel_labels,
    frequency_spinbox=self.frequency_spinbox,
    digital_matrix_labels=self.digital_matrix_labels
)

# 使用新的模块化功能
data_manager = plot_manager.get_data_manager()
touch_detector = plot_manager.get_touch_detector()

# 设置触摸检测阈值
plot_manager.set_touch_threshold(0.3)

# 获取数据统计信息
stats = plot_manager.get_current_data_stats()
```

## 模块化的优势

### 1. **可维护性**
- 每个模块职责单一，易于理解和修改
- 模块间低耦合，修改一个模块不会影响其他模块
- 清晰的接口定义

### 2. **可扩展性**
- 可以轻松添加新的功能模块
- 可以独立升级某个模块
- 支持插件式的功能扩展

### 3. **可测试性**
- 每个模块可以独立进行单元测试
- 模拟依赖更加容易
- 测试覆盖率更高

### 4. **代码复用**
- 模块可以在其他项目中复用
- 减少代码重复
- 标准化的接口设计

### 5. **性能优化**
- 按需加载模块
- 更好的内存管理
- 优化的数据处理流程

## 向后兼容性

重构后的 `PlotManager` 类保持了与原版本的接口兼容性：

- 所有公共方法保持相同的签名
- 信号定义保持不变
- 初始化参数保持一致

## 注意事项

1. **依赖关系**：确保所有模块文件都在正确的位置
2. **导入路径**：检查 Python 路径设置
3. **信号连接**：验证所有信号连接正常工作
4. **测试**：在替换前进行充分的功能测试

## 未来扩展建议

1. **配置管理模块**：添加配置文件支持
2. **日志模块**：统一的日志记录系统
3. **插件系统**：支持第三方插件
4. **数据分析模块**：高级数据分析功能
5. **网络模块**：远程数据传输支持

## 故障排除

如果遇到问题，请检查：

1. 所有模块文件是否存在
2. 导入路径是否正确
3. 依赖库是否安装
4. 信号连接是否正常

如需回滚到原版本，只需恢复备份的 `plot_manager_backup.py` 文件。