#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
螺旋排屑槽设计工具 - Python版本
基于图源刀具绘图系统的逆向分析结果实现

功能：
- 计算螺旋槽中心线
- 计算边界点
- 计算刀具轮廓
- 生成CSV文件输出
"""

import math
import csv
import os
import sys
from typing import List, Tuple

# 设置标准输出编码为UTF-8（解决Windows中文乱码问题）
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 绘图库
try:
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D
    from matplotlib.patches import Arc
    import matplotlib
    import matplotlib.font_manager as fm
    HAS_MATPLOTLIB = True
    
    # 配置matplotlib中文字体
    def setup_chinese_font():
        """设置matplotlib中文字体"""
        # Windows系统常见中文字体列表（按优先级排序）
        chinese_fonts = [
            'SimHei',           # 黑体
            'Microsoft YaHei',  # 微软雅黑
            'SimSun',           # 宋体
            'KaiTi',            # 楷体
            'FangSong',        # 仿宋
            'Arial Unicode MS', # Arial Unicode（如果安装了）
        ]
        
        # 获取系统所有可用字体
        available_fonts = [f.name for f in fm.fontManager.ttflist]
        
        # 查找第一个可用的中文字体
        selected_font = None
        for font in chinese_fonts:
            if font in available_fonts:
                selected_font = font
                break
        
        if selected_font:
            # 设置字体（确保在列表最前面）
            font_list = [selected_font]
            # 保留原有的字体作为fallback
            for existing_font in plt.rcParams['font.sans-serif']:
                if existing_font != selected_font:
                    font_list.append(existing_font)
            plt.rcParams['font.sans-serif'] = font_list
            # 同时设置默认字体
            matplotlib.rcParams['font.family'] = 'sans-serif'
            matplotlib.rcParams['font.sans-serif'] = font_list
            print(f"已设置中文字体: {selected_font}")
        else:
            # 如果没有找到中文字体，尝试使用系统默认字体
            print("警告: 未找到中文字体，中文可能显示为方框")
            print("建议: 安装中文字体（如SimHei或Microsoft YaHei）")
            # 使用默认字体列表
            plt.rcParams['font.sans-serif'] = ['DejaVu Sans'] + plt.rcParams['font.sans-serif']
        
        # 解决负号显示问题
        plt.rcParams['axes.unicode_minus'] = False
        matplotlib.rcParams['axes.unicode_minus'] = False
    
    # 设置中文字体
    setup_chinese_font()
        
except ImportError:
    HAS_MATPLOTLIB = False
    print("警告: 未安装matplotlib库，绘图功能将被禁用")
    print("安装方法: pip install matplotlib")

# 2D点类
class Point2D:
    def __init__(self, x: float = 0.0, y: float = 0.0):
        self.x = x
        self.y = y

    def __str__(self):
        return f"({self.x:.6f}, {self.y:.6f})"

# 螺旋槽计算器类
class SpiralGrooveCalculator:
    @staticmethod
    def calculate_spiral_groove(
        spiral_angle: float,        # 螺旋角（度）
        drill_diameter: float,      # 钻头直径（mm）
        total_length: float,        # 钻头总长（mm）
        blade_width: float,         # 刀瓣宽度（mm）
        blade_height: float,        # 刀瓣高度（mm）
        points_per_revolution: int = 100  # 每圈采样点数
    ) -> List[Point2D]:
        """
        计算螺旋槽中心线

        算法说明：
        - 将螺旋角转换为弧度
        - 计算螺旋的螺距：pitch = circumference / tan(angle)
        - 计算总圈数：totalRevolutions = totalLength / pitch
        - 生成展开图坐标：
          - X轴：沿钻头轴线的长度方向
          - Y轴：展开后的圆周方向
          - 公式：y = (x / pitch) * circumference
        """
        center_points = []

        # 参数验证
        if not SpiralGrooveCalculator._validate_parameters(
            spiral_angle, drill_diameter, total_length, blade_width, blade_height):
            print("参数验证失败！")
            return center_points

        # 将螺旋角转换为弧度
        angle_rad = math.radians(spiral_angle)

        # 计算半径
        radius = drill_diameter / 2.0

        # 计算圆周长度
        circumference = 2 * math.pi * radius

        # 计算螺距：pitch = circumference / tan(angle)
        pitch = circumference / math.tan(angle_rad)

        # 计算总圈数
        total_revolutions = total_length / pitch

        # 计算采样点总数（确保至少有两个点）
        total_points = max(2, int(total_revolutions * points_per_revolution))

        # 生成展开图坐标
        # x = 沿轴线的长度（0 到 totalLength）
        # y = (x / pitch) * circumference

        for i in range(total_points):
            t = i / (total_points - 1)  # 0 到 1 的参数
            x = t * total_length
            y = (x / pitch) * circumference

            center_points.append(Point2D(x, y))

        return center_points

    @staticmethod
    def calculate_boundaries(
        center_points: List[Point2D],  # 中心线点集
        blade_width: float            # 刀瓣宽度（mm）
    ) -> List[Tuple[Point2D, Point2D]]:
        """
        计算边界点

        算法说明：
        - 在展开图中，边界线平行于中心线
        - 左边界：Y方向向上偏移 +bladeWidth/2
        - 右边界：Y方向向下偏移 -bladeWidth/2
        """
        boundaries = []

        if not center_points:
            return boundaries

        half_width = blade_width / 2.0

        for center_point in center_points:
            # 左边界：Y方向向上偏移 +bladeWidth/2
            left_boundary = Point2D(center_point.x, center_point.y + half_width)
            # 右边界：Y方向向下偏移 -bladeWidth/2
            right_boundary = Point2D(center_point.x, center_point.y - half_width)

            boundaries.append((left_boundary, right_boundary))

        return boundaries

    @staticmethod
    def calculate_tool_outline(
        drill_diameter: float,  # 钻头直径（mm）
        total_length: float     # 钻头总长（mm）
    ) -> List[Point2D]:
        """
        计算刀具轮廓

        算法说明：
        - 生成矩形轮廓（展开图）
        - 高度 = 圆周长度 = 2 * π * radius
        - 宽度 = 总长度
        """
        outline = []

        # 计算半径
        radius = drill_diameter / 2.0

        # 计算圆周长度
        circumference = 2 * math.pi * radius

        # 生成矩形轮廓（展开图）
        # 左下角 (0, 0)
        outline.append(Point2D(0.0, 0.0))
        # 右下角 (totalLength, 0)
        outline.append(Point2D(total_length, 0.0))
        # 右上角 (totalLength, circumference)
        outline.append(Point2D(total_length, circumference))
        # 左上角 (0, circumference)
        outline.append(Point2D(0.0, circumference))
        # 闭合轮廓
        outline.append(Point2D(0.0, 0.0))

        return outline

    @staticmethod
    def _validate_parameters(
        spiral_angle: float,
        drill_diameter: float,
        total_length: float,
        blade_width: float,
        blade_height: float
    ) -> bool:
        """参数验证"""
        # 螺旋角范围检查 (0°, 90°)
        if spiral_angle <= 0.0 or spiral_angle >= 90.0:
            print(f"错误：螺旋角必须在 0° 到 90° 之间，当前值: {spiral_angle}°")
            return False

        # 直径检查
        if drill_diameter <= 0.0:
            print(f"错误：钻头直径必须大于 0，当前值: {drill_diameter}")
            return False

        # 总长检查
        if total_length <= 0.0:
            print(f"错误：钻头总长必须大于 0，当前值: {total_length}")
            return False

        # 刀瓣宽度检查
        if blade_width <= 0.0:
            print(f"错误：刀瓣宽度必须大于 0，当前值: {blade_width}")
            return False

        # 刀瓣高度检查
        if blade_height <= 0.0:
            print(f"错误：刀瓣高度必须大于 0，当前值: {blade_height}")
            return False

        return True

def save_points_to_csv(points: List[Point2D], filename: str) -> bool:
    """保存点集到CSV文件"""
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['X', 'Y'])  # 表头

            for point in points:
                writer.writerow([f"{point.x:.6f}", f"{point.y:.6f}"])

        print(f"数据已保存到: {filename}")
        return True
    except Exception as e:
        print(f"保存文件失败: {filename}, 错误: {e}")
        return False

def save_boundaries_to_csv(boundaries: List[Tuple[Point2D, Point2D]], filename: str) -> bool:
    """保存边界点到CSV文件"""
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['X', 'Y_Left', 'Y_Right'])  # 表头

            for left_boundary, right_boundary in boundaries:
                writer.writerow([
                    f"{left_boundary.x:.6f}",
                    f"{left_boundary.y:.6f}",
                    f"{right_boundary.y:.6f}"
                ])

        print(f"数据已保存到: {filename}")
        return True
    except Exception as e:
        print(f"保存文件失败: {filename}, 错误: {e}")
        return False

def print_usage_info():
    """打印使用说明"""
    print("=" * 60)
    print("         螺旋排屑槽设计工具 - Python版本")
    print("=" * 60)
    print()
    print("功能说明：")
    print("- 计算螺旋排屑槽的中心线坐标")
    print("- 计算排屑槽的左右边界")
    print("- 计算刀具外轮廓")
    print("- 生成CSV文件用于绘图软件")
    print()
    print("输出文件：")
    print("- spiral_center.csv     : 螺旋槽中心线坐标")
    print("- spiral_boundaries.csv : 排屑槽边界坐标")
    print("- tool_outline.csv      : 刀具轮廓坐标")
    print()
    print("使用方法：")
    print("1. 修改下面的参数值")
    print("2. 运行程序")
    print("3. 使用Excel或其他软件打开CSV文件")
    print("4. 绘制图形或导入CAD软件")
    print()

def main():
    """主函数"""
    print_usage_info()

    # 默认参数（可以根据需要修改）
    spiral_angle = 30.0    # 螺旋角（度）
    drill_diameter = 10.0  # 钻头直径（mm）
    total_length = 50.0    # 钻头总长（mm）
    blade_width = 2.0      # 刀瓣宽度（mm）
    blade_height = 1.0     # 刀瓣高度（mm）
    num_flutes = 2         # 螺旋槽数量（通常为2或3）

    print("当前计算参数：")
    print(f"  螺旋角: {spiral_angle}°")
    print(f"  钻头直径: {drill_diameter} mm")
    print(f"  钻头总长: {total_length} mm")
    print(f"  刀瓣宽度: {blade_width} mm")
    print(f"  刀瓣高度: {blade_height} mm")
    print(f"  螺旋槽数量: {num_flutes}")
    print()

    try:
        # 计算螺旋槽中心线
        print("正在计算螺旋槽中心线...")
        center_points = SpiralGrooveCalculator.calculate_spiral_groove(
            spiral_angle, drill_diameter, total_length, blade_width, blade_height
        )

        if not center_points:
            print("计算失败！请检查参数。")
            return

        print(f"中心线点数: {len(center_points)}")

        # 计算边界点
        print("正在计算边界点...")
        boundaries = SpiralGrooveCalculator.calculate_boundaries(center_points, blade_width)
        print(f"边界点数: {len(boundaries)}")

        # 计算刀具轮廓
        print("正在计算刀具轮廓...")
        tool_outline = SpiralGrooveCalculator.calculate_tool_outline(drill_diameter, total_length)
        print(f"轮廓点数: {len(tool_outline)}")

        # 保存结果到文件
        print("\n正在保存结果...")

        save_points_to_csv(center_points, "spiral_center.csv")
        save_boundaries_to_csv(boundaries, "spiral_boundaries.csv")
        save_points_to_csv(tool_outline, "tool_outline.csv")

        # 绘制图形
        if HAS_MATPLOTLIB:
            print("\n正在绘制图形...")
            plot_spiral_groove(center_points, boundaries, tool_outline,
                             spiral_angle, drill_diameter, total_length, 
                             blade_width, blade_height, num_flutes)

        # 显示计算结果统计
        print("\n计算结果统计：")

        # 计算螺旋的基本参数
        radius = drill_diameter / 2.0
        circumference = 2 * math.pi * radius
        pitch = circumference / math.tan(math.radians(spiral_angle))
        total_revolutions = total_length / pitch

        print(".2f")
        print(".2f")
        print(".2f")
        print(".1f")
        print("\n" + "=" * 60)
        print("计算完成！")
        print("可以使用Excel、LibreOffice或其他工具打开CSV文件查看结果。")
        print("将数据导入AutoCAD、SolidWorks等CAD软件可以绘制图形。")
        print("=" * 60)

    except Exception as e:
        print(f"计算过程中发生错误: {e}")
        print("请检查参数设置。")

def plot_spiral_groove(center_points: List[Point2D],
                      boundaries: List[Tuple[Point2D, Point2D]],
                      tool_outline: List[Point2D],
                      spiral_angle: float,
                      drill_diameter: float,
                      total_length: float,
                      blade_width: float,
                      blade_height: float,
                      num_flutes: int = 2) -> None:
    """
    绘制螺旋排屑槽图形

    Args:
        center_points: 螺旋槽中心线点集
        boundaries: 边界点对列表
        tool_outline: 刀具轮廓点集
        spiral_angle: 螺旋角（度）
        drill_diameter: 钻头直径（mm）
        total_length: 钻头总长（mm）
        blade_width: 刀瓣宽度（mm）
    """
    if not HAS_MATPLOTLIB:
        print("matplotlib未安装，跳过绘图")
        return

    try:
        # 计算基本参数
        radius = drill_diameter / 2.0
        circumference = 2 * math.pi * radius
        angle_rad = math.radians(spiral_angle)
        pitch = circumference / math.tan(angle_rad)
        total_revolutions = total_length / pitch
        
        # 计算每个螺旋槽之间的角度间隔
        angle_per_flute = 2 * math.pi / num_flutes

        # 创建图形 - 三个子图：展开图、3D视图、侧视图
        fig = plt.figure(figsize=(20, 7))
        ax1 = plt.subplot(1, 3, 1)  # 展开图
        ax2 = plt.subplot(1, 3, 2, projection='3d')  # 3D视图
        ax3 = plt.subplot(1, 3, 3)  # 侧视图

        # 提取坐标数据
        center_x = [p.x for p in center_points]
        center_y = [p.y for p in center_points]

        # 边界坐标
        boundary_x = [b[0].x for b in boundaries]
        left_y = [b[0].y for b in boundaries]
        right_y = [b[1].y for b in boundaries]

        # 刀具轮廓坐标
        outline_x = [p.x for p in tool_outline]
        outline_y = [p.y for p in tool_outline]

        # ========== 左侧子图：展开图 ==========
        ax1.set_title('展开图 (Unwrapped View)\n将圆柱面沿轴向切开并展开为平面', 
                     fontsize=12, fontweight='bold')
        ax1.set_xlabel('轴向长度 Z (mm)', fontsize=11)
        ax1.set_ylabel('圆周展开长度 (mm)', fontsize=11)
        ax1.grid(True, alpha=0.3, linestyle='--')
        
        # 添加说明文本
        ax1.text(0.02, 0.98, '注意: 展开后螺旋线变为直线\n这是数学上的正确表示', 
                transform=ax1.transAxes, fontsize=9, verticalalignment='top',
                bbox=dict(boxstyle='round,pad=0.5', facecolor='lightblue', alpha=0.7))

        # 绘制刀具轮廓
        ax1.fill(outline_x, outline_y, 'lightgray', alpha=0.3, label='刀具轮廓')
        ax1.plot(outline_x, outline_y, 'k-', linewidth=2, label='轮廓边界')

        # 绘制多个螺旋槽（如果有多个刀瓣）
        colors = ['red', 'blue', 'green', 'orange', 'purple']
        
        for flute_idx in range(num_flutes):
            color = colors[flute_idx % len(colors)]
            offset = (flute_idx * angle_per_flute / (2 * math.pi)) * circumference
            
            # 计算当前螺旋槽的边界（在展开图中偏移）
            left_y_offset = [y + offset for y in left_y]
            right_y_offset = [y + offset for y in right_y]
            center_y_offset = [y + offset for y in center_y]
            
            # 处理Y坐标超出圆周的情况（循环）
            for i in range(len(left_y_offset)):
                if left_y_offset[i] > circumference:
                    left_y_offset[i] -= circumference
                if right_y_offset[i] > circumference:
                    right_y_offset[i] -= circumference
                if center_y_offset[i] > circumference:
                    center_y_offset[i] -= circumference
            
            # 1. 填充槽的区域（显示完整的槽宽度）
            ax1.fill_between(boundary_x, left_y_offset, right_y_offset, 
                           color=color, alpha=0.4, 
                           label=f'排屑槽 {flute_idx+1}')
            
            # 2. 绘制槽的边界线
            ax1.plot(boundary_x, left_y_offset, color=color, linewidth=2, 
                    alpha=0.8, linestyle='-')
            ax1.plot(boundary_x, right_y_offset, color=color, linewidth=2, 
                    alpha=0.8, linestyle='-')

            # 3. 绘制螺旋槽中心线
            ax1.plot(center_x, center_y_offset, color=color, linewidth=2, 
                    label=f'中心线 {flute_idx+1}' if flute_idx < 2 else '', 
                    linestyle='--', alpha=0.7)
        
        # 4. 添加槽的深度指示（在几个关键点）
        depth_indicator_points = [0, len(center_x)//4, len(center_x)//2, 
                                  3*len(center_x)//4, len(center_x)-1]
        for idx in depth_indicator_points:
            if idx < len(center_x):
                x_pos = center_x[idx]
                y_pos = center_y[idx]
                # 绘制深度指示箭头（从中心线向下）
                ax1.annotate('', xy=(x_pos, y_pos - blade_width/4), 
                           xytext=(x_pos, y_pos),
                           arrowprops=dict(arrowstyle='->', color='purple', 
                                         lw=1.5, alpha=0.6))
                # 添加深度标注（只在第一个点）
                if idx == 0:
                    ax1.text(x_pos + 2, y_pos - blade_width/2, 
                           f'深度: {blade_height}mm', fontsize=8, 
                           bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7))

        # 添加图例
        ax1.legend(loc='upper left', fontsize=9)

        # 设置坐标轴范围
        ax1.set_xlim(-2, total_length + 2)
        ax1.set_ylim(-2, circumference + 2)
        ax1.set_aspect('equal', adjustable='box')

        # ========== 中间子图：3D螺旋线视图 ==========
        ax2.set_title('3D螺旋线视图', fontsize=12, fontweight='bold')
        ax2.set_xlabel('X (mm)', fontsize=10)
        ax2.set_ylabel('Y (mm)', fontsize=10)
        ax2.set_zlabel('轴向长度 Z (mm)', fontsize=10)

        # 计算槽的深度（从外圆向内）
        groove_depth = blade_height  # 槽深度
        groove_radius = radius - groove_depth  # 槽底部的半径
        
        # 为每个螺旋槽绘制完整的3D结构
        colors_3d = ['red', 'blue', 'green', 'orange', 'purple']
        
        for flute_idx in range(num_flutes):
            color = colors_3d[flute_idx % len(colors_3d)]
            base_angle_offset = flute_idx * angle_per_flute  # 基础角度偏移
            
            # 从展开坐标重建3D螺旋线 - 中心线
            x_3d_center = []
            y_3d_center = []
            z_3d_center = []

            # 从展开坐标重建3D螺旋线 - 左边界
            x_3d_left = []
            y_3d_left = []
            z_3d_left = []

            # 从展开坐标重建3D螺旋线 - 右边界
            x_3d_right = []
            y_3d_right = []
            z_3d_right = []

            for i, point in enumerate(center_points):
                # 从展开坐标转换回3D坐标
                z = point.x  # 轴向长度
                # 添加当前螺旋槽的角度偏移
                angle_center = (point.y / circumference) * 2 * math.pi + base_angle_offset
                
                # 中心线3D坐标（在外圆上）
                x_3d_center.append(radius * math.cos(angle_center))
                y_3d_center.append(radius * math.sin(angle_center))
                z_3d_center.append(z)

                # 计算左右边界在3D空间中的位置
                if i < len(boundaries):
                    left_point, right_point = boundaries[i]
                    
                    # 左边界角度（添加偏移）
                    angle_left = (left_point.y / circumference) * 2 * math.pi + base_angle_offset
                    # 右边界角度（添加偏移）
                    angle_right = (right_point.y / circumference) * 2 * math.pi + base_angle_offset
                    
                    # 左边界3D坐标（在槽底部）
                    x_3d_left.append(groove_radius * math.cos(angle_left))
                    y_3d_left.append(groove_radius * math.sin(angle_left))
                    z_3d_left.append(z)
                    
                    # 右边界3D坐标（在槽底部）
                    x_3d_right.append(groove_radius * math.cos(angle_right))
                    y_3d_right.append(groove_radius * math.sin(angle_right))
                    z_3d_right.append(z)

            # 绘制完整的螺旋槽结构
            # 1. 绘制中心线（在外圆上）
            ax2.plot(x_3d_center, y_3d_center, z_3d_center, color=color, 
                    linewidth=2.5, label=f'槽{flute_idx+1}中心线' if flute_idx < 3 else '', 
                    alpha=0.8, linestyle='--')
            
            # 2. 绘制左边界（槽的左侧边缘，在槽底部）
            ax2.plot(x_3d_left, y_3d_left, z_3d_left, color=color, 
                    linewidth=2.5, label=f'槽{flute_idx+1}左边界' if flute_idx == 0 else '', 
                    alpha=0.9)
            
            # 3. 绘制右边界（槽的右侧边缘，在槽底部）
            ax2.plot(x_3d_right, y_3d_right, z_3d_right, color=color, 
                    linewidth=2.5, label=f'槽{flute_idx+1}右边界' if flute_idx == 0 else '', 
                    alpha=0.9)
            
            # 4. 绘制槽的底部（连接左右边界的底部，显示槽的宽度）
            step = max(1, len(x_3d_left) // 15)  # 绘制约15条连接线
            for i in range(0, len(x_3d_left), step):
                ax2.plot([x_3d_left[i], x_3d_right[i]], 
                        [y_3d_left[i], y_3d_right[i]], 
                        [z_3d_left[i], z_3d_right[i]], 
                        color=color, linewidth=1.5, alpha=0.6)
            
            # 5. 绘制槽的深度（从外圆到槽底，显示槽的深度）
            depth_points = [0, len(x_3d_center)//4, len(x_3d_center)//2, 
                            3*len(x_3d_center)//4, len(x_3d_center)-1]
            for i in depth_points:
                if i < len(x_3d_center):
                    # 从外圆到槽底部的深度线
                    angle = (center_points[i].y / circumference) * 2 * math.pi + base_angle_offset
                    x_outer = radius * math.cos(angle)
                    y_outer = radius * math.sin(angle)
                    x_inner = groove_radius * math.cos(angle)
                    y_inner = groove_radius * math.sin(angle)
                    z_val = z_3d_center[i]
                    
                    ax2.plot([x_outer, x_inner], [y_outer, y_inner], [z_val, z_val],
                            color=color, linewidth=1.5, alpha=0.5, linestyle=':')
            
            # 6. 绘制槽的完整横截面（显示槽的完整形状）
            section_step = max(1, len(x_3d_center) // 8)  # 绘制约8个横截面
            for i in range(0, len(x_3d_center), section_step):
                if i < len(x_3d_left) and i < len(x_3d_right):
                    # 创建横截面：外圆点 -> 左边界点 -> 右边界点 -> 外圆点
                    angle_center = (center_points[i].y / circumference) * 2 * math.pi + base_angle_offset
                    x_outer = radius * math.cos(angle_center)
                    y_outer = radius * math.sin(angle_center)
                    z_val = z_3d_center[i]
                    
                    # 绘制横截面轮廓（显示槽的完整结构）
                    # 外圆到左边界
                    ax2.plot([x_outer, x_3d_left[i]], [y_outer, y_3d_left[i]], 
                            [z_val, z_val], color=color, linewidth=1.5, alpha=0.5)
                    # 左边界到右边界（槽底，加粗显示）
                    ax2.plot([x_3d_left[i], x_3d_right[i]], 
                            [y_3d_left[i], y_3d_right[i]], 
                            [z_val, z_val], color=color, linewidth=2.5, alpha=0.7)
                    # 右边界到外圆
                    ax2.plot([x_3d_right[i], x_outer], 
                            [y_3d_right[i], y_outer], 
                            [z_val, z_val], color=color, linewidth=1.5, alpha=0.5)
        
        # 计算第一个螺旋槽的坐标用于起点终点标记和俯视图
        x_3d_center = []
        y_3d_center = []
        z_3d_center = []
        for i, point in enumerate(center_points):
            z = point.x
            angle_center = (point.y / circumference) * 2 * math.pi
            x_3d_center.append(radius * math.cos(angle_center))
            y_3d_center.append(radius * math.sin(angle_center))
            z_3d_center.append(z)

        # 绘制起始点和结束点
        if x_3d_center:
            ax2.scatter([x_3d_center[0]], [y_3d_center[0]], [z_3d_center[0]], 
                       color='green', s=50, label='起点', zorder=5)
            ax2.scatter([x_3d_center[-1]], [y_3d_center[-1]], [z_3d_center[-1]], 
                       color='orange', s=50, label='终点', zorder=5)

        # 绘制刀具圆柱体（上下两个圆）
        theta = [i * 2 * math.pi / 50 for i in range(51)]
        for z_val in [0, total_length]:
            x_cyl = [radius * math.cos(t) for t in theta]
            y_cyl = [radius * math.sin(t) for t in theta]
            z_cyl = [z_val] * len(theta)
            ax2.plot(x_cyl, y_cyl, z_cyl, 'k--', linewidth=1.5, alpha=0.6)

        # 绘制圆柱体侧面（连接上下圆的线）
        for angle_idx in [0, 12, 25, 37, 50]:  # 均匀分布的几条线
            t = theta[angle_idx]
            x_start = radius * math.cos(t)
            y_start = radius * math.sin(t)
            x_end = radius * math.cos(t)
            y_end = radius * math.sin(t)
            ax2.plot([x_start, x_end], [y_start, y_end], [0, total_length], 
                    'k--', linewidth=0.8, alpha=0.4)

        # 绘制轴向线（Z轴）
        ax2.plot([0, 0], [0, 0], [0, total_length], 'k-', linewidth=2, alpha=0.5, label='中心轴线')

        # 设置视角 - 更好的观察角度
        ax2.view_init(elev=20, azim=45)  # elev=仰角, azim=方位角

        ax2.legend(fontsize=8, loc='upper left')
        ax2.set_box_aspect([1, 1, max(1, total_length/(radius*2))])  # 根据实际尺寸设置宽高比
        
        # 设置坐标轴范围
        ax2.set_xlim(-radius*1.5, radius*1.5)
        ax2.set_ylim(-radius*1.5, radius*1.5)
        ax2.set_zlim(-2, total_length + 2)

        # ========== 右侧子图：侧视图（2D工程图） ==========
        ax3.set_title('侧视图 (Side View)\n螺旋排屑槽工程图', fontsize=12, fontweight='bold')
        ax3.set_xlabel('轴向长度 (mm)', fontsize=11)
        ax3.set_ylabel('半径方向 (mm)', fontsize=11)
        ax3.grid(True, alpha=0.3, linestyle='--')
        
        # 计算侧视图中的螺旋槽边界
        # 侧视图是从侧面看圆柱体，需要计算每个轴向位置处的半径
        # 由于螺旋槽的存在，顶部和底部边界是波浪形的
        
        # 生成更密集的采样点用于平滑的波浪边界
        # 每个螺距至少50个点，确保波浪平滑
        num_samples = max(300, int(total_length / pitch * 50))
        z_samples = [i * total_length / (num_samples - 1) for i in range(num_samples)]
        
        # 计算顶部和底部边界（波浪形）
        # 直接使用cos和sin函数绘制波浪线
        top_boundary_y = []  # 顶部边界（Y坐标，正值）
        bottom_boundary_y = []  # 底部边界（Y坐标，负值）
        
        # 计算波浪幅度：使波浪向外凸，几乎贯穿到中间位置
        wave_amplitude = radius * 0.8  # 波浪幅度为半径的80%
        
        # 直接使用cos和sin函数绘制波浪
        for z in z_samples:
            # 计算角度：根据轴向位置z，转换为角度
            # 使用螺距来确定波浪的周期
            angle = (z / pitch) * (2 * math.pi)
            
            # 顶部边界：直接使用cos函数
            cos_value = math.cos(angle)
            top_radius = radius + wave_amplitude * cos_value
            
            # 底部边界：直接使用sin函数
            sin_value = math.sin(angle)
            bottom_radius = radius + wave_amplitude * sin_value
            
            top_boundary_y.append(top_radius)
            bottom_boundary_y.append(-bottom_radius)
        
        # 绘制顶部边界（波浪线）
        ax3.plot(z_samples, top_boundary_y, 'k-', linewidth=2.5, 
                label='顶部边界', alpha=0.9)
        
        # 绘制底部边界（波浪线）
        ax3.plot(z_samples, bottom_boundary_y, 'k-', linewidth=2.5, 
                label='底部边界', alpha=0.9)
        
        # 填充刀具区域
        ax3.fill_between(z_samples, bottom_boundary_y, top_boundary_y, 
                        color='lightgray', alpha=0.3, label='刀具主体')
        
        # 绘制中心轴线（虚线）
        ax3.axhline(y=0, color='k', linestyle='--', linewidth=1.5, 
                   alpha=0.5, label='中心轴线')
        
        # 绘制左侧尖端（钻头切削端）
        tip_length = total_length * 0.05  # 尖端长度约为总长的5%
        tip_x = [0, tip_length]
        tip_y_top = [radius, radius * 0.7]  # 尖端稍微锥形
        tip_y_bottom = [-radius, -radius * 0.7]
        ax3.plot(tip_x, tip_y_top, 'k-', linewidth=2.5, alpha=0.9)
        ax3.plot(tip_x, tip_y_bottom, 'k-', linewidth=2.5, alpha=0.9)
        
        # 绘制右侧切断线
        ax3.axvline(x=total_length, color='k', linestyle='-', 
                  linewidth=2, alpha=0.7)
        
        # 添加尺寸标注
        # D1: 直径标注（左侧）
        ax3.annotate('', xy=(0, -radius), xytext=(0, radius),
                    arrowprops=dict(arrowstyle='<->', lw=1.5, color='blue'))
        ax3.text(-total_length*0.08, 0, f'D1\n{drill_diameter:.1f}mm', 
                fontsize=10, ha='right', va='center',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))
        
        # L1: 有效槽长度（从起点到最后一个完整螺旋）
        l1_end = total_length * 0.8  # 假设L1是总长的80%
        ax3.annotate('', xy=(0, -radius*1.3), xytext=(l1_end, -radius*1.3),
                    arrowprops=dict(arrowstyle='<->', lw=1.5, color='blue'))
        ax3.text(l1_end/2, -radius*1.45, f'L1\n{l1_end:.1f}mm', 
                fontsize=10, ha='center', va='top',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))
        
        # L2: 总长度
        ax3.annotate('', xy=(0, -radius*1.5), xytext=(total_length, -radius*1.5),
                    arrowprops=dict(arrowstyle='<->', lw=1.5, color='blue'))
        ax3.text(total_length/2, -radius*1.65, f'L2\n{total_length:.1f}mm', 
                fontsize=10, ha='center', va='top',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))
        
        # A1: 螺旋角标注
        # 在中间位置标注螺旋角
        mid_z = total_length / 2
        mid_idx = int(len(z_samples) / 2)
        if mid_idx < len(top_boundary_y):
            # 计算螺旋角的角度线
            angle_line_length = radius * 0.3
            # 螺旋角的正切值
            tan_angle = math.tan(angle_rad)
            # 在侧视图中，角度线从中心轴指向边界
            angle_end_y = angle_line_length * tan_angle
            angle_end_z = mid_z + angle_line_length
            
            # 绘制角度弧线
            arc = Arc((mid_z, 0), width=radius*0.6, height=radius*0.6, 
                     angle=0, theta1=0, theta2=math.degrees(angle_rad),
                     lw=1.5, color='blue', linestyle='-')
            ax3.add_patch(arc)
            
            # 标注角度
            ax3.text(mid_z + radius*0.15, radius*0.15, f'A1\n{spiral_angle}°', 
                    fontsize=10, ha='left', va='bottom',
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))
        
        ax3.legend(fontsize=9, loc='upper right')
        ax3.set_xlim(-total_length*0.1, total_length*1.1)
        ax3.set_ylim(-radius*2, radius*1.5)
        ax3.set_aspect('equal', adjustable='box')

        # 添加参数信息文本
        param_text = f"""设计参数:
螺旋角: {spiral_angle}°
直径: {drill_diameter} mm
长度: {total_length} mm
刀瓣宽: {blade_width} mm

计算结果:
圆周长: {circumference:.2f} mm
螺距: {pitch:.2f} mm
总圈数: {total_revolutions:.2f} 圈
采样点数: {len(center_points)} 点"""

        # 在图上添加参数文本（使用中文字体，不使用monospace）
        fig.text(0.02, 0.02, param_text, fontsize=10,
                verticalalignment='bottom',
                bbox=dict(boxstyle='round,pad=0.5', facecolor='lightyellow', alpha=0.8))

        # 设置整体标题
        fig.suptitle(f'螺旋排屑槽设计结果 (螺旋角: {spiral_angle}°)',
                    fontsize=16, fontweight='bold', y=0.98)

        # 调整布局
        plt.tight_layout()
        plt.subplots_adjust(top=0.9)
        
        # 确保所有文本使用中文字体（在保存前）
        # 获取当前设置的中文字体
        current_font = plt.rcParams['font.sans-serif'][0] if plt.rcParams['font.sans-serif'] else 'SimHei'
        
        # 为所有文本元素设置字体（如果需要）
        for ax in [ax1, ax2, ax3]:
            for text in ax.texts:
                text.set_fontfamily(current_font)
        
        # 显示图形
        plt.show()

        # 保存图形（使用中文字体）
        output_file = "spiral_groove_plot.png"
        # 在保存前确保使用正确的字体
        fig.savefig(output_file, dpi=300, bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        print(f"图形已保存到: {output_file}")

    except Exception as e:
        print(f"绘图过程中发生错误: {e}")
        print("可能的原因: matplotlib版本问题或图形显示配置问题")

if __name__ == "__main__":
    main()
