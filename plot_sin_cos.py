#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
绘制最基础的cos和sin曲线
"""

import math
import matplotlib.pyplot as plt
import numpy as np

# 设置中文字体
import matplotlib.font_manager as fm
import sys
import os

# 确保控制台输出中文正常
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# 配置matplotlib中文字体
def set_chinese_font():
    font_paths = [
        'C:/Windows/Fonts/SimHei.ttf',  # 黑体
        'C:/Windows/Fonts/msyh.ttc',    # 微软雅黑
        '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc' # Linux下的文泉驿正黑
    ]
    
    found_font = None
    for font_path in font_paths:
        if os.path.exists(font_path):
            try:
                fm.fontManager.addfont(font_path)
                found_font = fm.FontProperties(fname=font_path)
                plt.rcParams['font.sans-serif'] = [found_font.get_name()]
                plt.rcParams['axes.unicode_minus'] = False
                print(f"已设置中文字体: {found_font.get_name()}")
                return found_font
            except Exception as e:
                print(f"加载字体 {font_path} 失败: {e}")
    
    print("警告: 未找到支持中文的字体，中文可能显示为方块。")
    return None

CHINESE_FONT_PROPERTIES = set_chinese_font()

# 创建图形
fig, ax = plt.subplots(figsize=(12, 6))

# 提高频率：增加周期数，使曲线更密集
# 通过除以一个小于1的系数来提高频率（增加周期）
frequency_factor = 0.5  # 提高频率，使曲线更密集（频率提高2倍）

# 减小曲率：使用更平滑的函数，通过增加采样点来使曲线更平滑
# 生成更多的采样点
x = np.linspace(0, 4 * math.pi, 2000)  # 增加采样点，使曲线更平滑

x_scaled = x / frequency_factor

# 继续减小振幅
amplitude = 0.3  # 振幅进一步降低到0.3

# 计算cos和sin值，让极值点对齐
# 使用cos和sin，但调整sin的相位使其极值点与cos对齐
# sin(x - π/2) = -cos(x)，这样sin的极值点就会和cos的极值点对齐
y_cos = amplitude * np.cos(x_scaled)
y_sin = amplitude * np.sin(x_scaled - math.pi/2)  # sin(x - π/2) = -cos(x)，使极值点对齐

# 绘制cos曲线（红色）
ax.plot(x, y_cos, 'r-', linewidth=2, label='cos(x)')

# 绘制sin曲线（蓝色）
ax.plot(x, y_sin, 'b-', linewidth=2, label='sin(x)')

# 设置标题和标签
ax.set_title('cos和sin曲线', fontsize=16, fontweight='bold', fontproperties=CHINESE_FONT_PROPERTIES)
ax.set_xlabel('角度 (弧度)', fontsize=12, fontproperties=CHINESE_FONT_PROPERTIES)
ax.set_ylabel('函数值', fontsize=12, fontproperties=CHINESE_FONT_PROPERTIES)

# 添加网格
ax.grid(True, alpha=0.3, linestyle='--')

# 添加图例
ax.legend(fontsize=12, prop=CHINESE_FONT_PROPERTIES)

# 设置x轴刻度（显示π的倍数）
ax.set_xticks([0, math.pi, 2*math.pi, 3*math.pi, 4*math.pi])
ax.set_xticklabels(['0', 'π', '2π', '3π', '4π'])

# 添加水平参考线（y=0）
ax.axhline(y=0, color='k', linestyle='-', linewidth=0.5, alpha=0.3)

# 调整布局
plt.tight_layout()

# 显示图形
plt.show()

# 保存图形
output_file = "sin_cos_plot.png"
fig.savefig(output_file, dpi=300, bbox_inches='tight')
print(f"图形已保存到: {output_file}")

