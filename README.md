# 螺旋排屑槽设计工具

## 🎯 项目简介

这是一个**开源的螺旋排屑槽设计工具**，基于对商业CAD软件的逆向分析结果，完全独立实现。无需安装任何商业软件，即可进行专业的刀具设计计算和可视化。

**核心功能**：参数化设计螺旋排屑槽，生成精确的几何数据和可视化图形。

## ✨ 主要特性

- 🔬 **精确计算**：基于螺旋线几何理论的纯数学计算
- 📊 **实时可视化**：自动生成高清设计图形
- 📁 **多格式输出**：CSV数据文件 + PNG图形文件
- 🎛️ **参数化设计**：灵活调整螺旋角、直径、长度等参数
- 🔧 **专业级精度**：适合工业制造和CAD/CAM应用
- 📖 **开源透明**：代码公开，可验证计算过程

## 🚀 快速开始

### 1. 环境要求
- Python 3.6+
- matplotlib (绘图库)

### 2. 安装依赖
```bash
pip install matplotlib
```

### 3. 运行程序
```bash
python spiral_groove_designer.py
```

程序将自动：
- 计算螺旋排屑槽几何数据
- 显示实时图形预览
- 生成CSV数据文件
- 保存高清PNG图像

## 📋 输出文件

| 文件名 | 内容 | 用途 |
|--------|------|------|
| `spiral_center.csv` | 螺旋槽中心线坐标 | CAD导入绘制中心线 |
| `spiral_boundaries.csv` | 排屑槽边界坐标 | CAD导入绘制排屑区域 |
| `tool_outline.csv` | 刀具轮廓坐标 | CAD导入绘制刀具外形 |
| `spiral_groove_plot.png` | 高清设计图形 | 设计结果可视化 |

## 🎨 图形预览

程序生成的图形包含：
- **左侧**：螺旋排屑槽展开图（中心线、边界线、刀具轮廓）
- **右侧**：3D效果模拟图（螺旋线空间形态）
- **底部**：完整的设计参数和计算结果

## 🔧 技术实现

### 核心算法
```python
# 螺距计算
pitch = circumference / tan(螺旋角)

# 展开坐标
y = (x / pitch) * circumference

# 边界偏移
y_left = y_center + bladeWidth/2
y_right = y_center - bladeWidth/2
```

### 技术栈
- **计算引擎**：Python 纯数学实现
- **可视化**：matplotlib 高质量绘图
- **数据输出**：CSV 标准格式
- **验证**：内置参数检查和计算验证

## 📖 使用示例

### 基本使用
```python
from spiral_groove_designer import SpiralGrooveCalculator

# 计算螺旋槽
center_points = SpiralGrooveCalculator.calculate_spiral_groove(
    spiral_angle=30.0,      # 螺旋角（度）
    drill_diameter=10.0,    # 钻头直径（mm）
    total_length=50.0,      # 钻头总长（mm）
    blade_width=2.0,        # 刀瓣宽度（mm）
    blade_height=1.0        # 刀瓣高度（mm）
)

# 计算边界
boundaries = SpiralGrooveCalculator.calculate_boundaries(center_points, blade_width)

# 计算轮廓
outline = SpiralGrooveCalculator.calculate_tool_outline(drill_diameter, total_length)
```

### 设计参数范围
| 参数 | 说明 | 范围 |
|------|------|------|
| spiral_angle | 螺旋角 | 0° < angle < 90° |
| drill_diameter | 钻头直径 | > 0 mm |
| total_length | 钻头总长 | > 0 mm |
| blade_width | 刀瓣宽度 | > 0 mm |
| blade_height | 刀瓣高度 | > 0 mm |

## 🎯 应用场景

- **刀具设计**：螺旋排屑槽几何建模
- **CAD绘图**：参数化曲线生成
- **制造工程**：CAM编程数据准备
- **教育教学**：螺旋线几何原理演示
- **研究开发**：刀具优化算法验证

## 📚 项目文件

```
.
├── spiral_groove_designer.py     # 主程序
├── example_designs.py           # 示例脚本
├── test_calculation.py          # 计算验证
├── 使用说明.md                  # 详细文档
├── 项目结构说明.md              # 项目架构
├── final_analysis_report.md     # 技术分析
├── 开发文档.md                  # 原始文档
└── README.md                    # 本文件
```

## 🤝 技术来源

本工具基于对商业CAD软件的逆向分析，提取了其中的核心算法，并使用开源技术完全重新实现。所有计算公式和方法都是公开可验证的。

## 📄 许可证

本项目仅用于技术学习和研究目的。请遵守相关法律法规。

---

**开发语言**: Python 3
**绘图库**: matplotlib
**数据格式**: CSV + PNG
**适用平台**: 跨平台（Windows/macOS/Linux）
