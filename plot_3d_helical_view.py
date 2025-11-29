#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
3D螺旋线视图生成工具
单独提取并生成螺旋排屑槽的3D螺旋线视图
"""

import math
import sys
from typing import List, Tuple

# 设置标准输出编码为UTF-8（解决Windows中文乱码问题）
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 绘图库
try:
    import matplotlib
    # 使用交互式后端（TkAgg适用于Windows，Qt5Agg也常用）
    # 如果TkAgg不可用，会自动尝试其他交互式后端
    try:
        matplotlib.use('TkAgg')  # Windows上常用的交互式后端
    except:
        try:
            matplotlib.use('Qt5Agg')  # 备选交互式后端
        except:
            pass  # 如果都不可用，使用默认后端
    
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D
    import matplotlib.font_manager as fm
    HAS_MATPLOTLIB = True
    
    # 启用交互模式
    plt.ion()
    
    # 配置matplotlib中文字体
    def setup_chinese_font():
        """设置matplotlib中文字体"""
        chinese_fonts = [
            'SimHei',           # 黑体
            'Microsoft YaHei',  # 微软雅黑
            'SimSun',           # 宋体
            'KaiTi',            # 楷体
            'FangSong',        # 仿宋
        ]
        
        available_fonts = [f.name for f in fm.fontManager.ttflist]
        
        for font_name in chinese_fonts:
            if font_name in available_fonts:
                plt.rcParams['font.sans-serif'] = [font_name]
                plt.rcParams['axes.unicode_minus'] = False
                print(f"已设置中文字体: {font_name}")
                return
        
        print("警告：未找到合适的中文字体，可能无法正确显示中文")
    
except ImportError:
    HAS_MATPLOTLIB = False
    print("错误：matplotlib未安装，无法生成图像")
    print("请运行: pip install matplotlib")

class Point2D:
    """2D点类"""
    def __init__(self, x: float = 0.0, y: float = 0.0):
        self.x = x
        self.y = y

    def __str__(self):
        return f"({self.x:.6f}, {self.y:.6f})"

class SpiralGrooveCalculator:
    """螺旋槽计算器类"""
    @staticmethod
    def calculate_spiral_groove(
        spiral_angle: float,        # 螺旋角（度）
        drill_diameter: float,      # 钻头直径（mm）
        total_length: float,        # 钻头总长（mm）
        blade_width: float,         # 刀瓣宽度（mm）
        blade_height: float,        # 刀瓣高度（mm）
        points_per_revolution: int = 100  # 每圈采样点数
    ) -> List[Point2D]:
        """计算螺旋槽中心线"""
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
        """计算边界点"""
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
    def _validate_parameters(
        spiral_angle: float,
        drill_diameter: float,
        total_length: float,
        blade_width: float,
        blade_height: float
    ) -> bool:
        """参数验证"""
        if spiral_angle <= 0.0 or spiral_angle >= 90.0:
            print(f"错误：螺旋角必须在 0° 到 90° 之间，当前值: {spiral_angle}°")
            return False

        if drill_diameter <= 0.0:
            print(f"错误：钻头直径必须大于 0，当前值: {drill_diameter}")
            return False

        if total_length <= 0.0:
            print(f"错误：钻头总长必须大于 0，当前值: {total_length}")
            return False

        if blade_width <= 0.0:
            print(f"错误：刀瓣宽度必须大于 0，当前值: {blade_width}")
            return False

        if blade_height <= 0.0:
            print(f"错误：刀瓣高度必须大于 0，当前值: {blade_height}")
            return False

        return True

def plot_3d_helical_view(
    center_points: List[Point2D],
    boundaries: List[Tuple[Point2D, Point2D]],
    spiral_angle: float,
    drill_diameter: float,
    total_length: float,
    blade_width: float,
    blade_height: float,
    num_flutes: int = 2
) -> None:
    """
    绘制3D螺旋线视图
    
    参数:
        center_points: 螺旋槽中心线点集
        boundaries: 边界点对列表
        spiral_angle: 螺旋角（度）
        drill_diameter: 钻头直径（mm）
        total_length: 钻头总长（mm）
        blade_width: 刀瓣宽度（mm）
        blade_height: 刀瓣高度（mm）
        num_flutes: 螺旋槽数量（通常为2或3）
    """
    if not HAS_MATPLOTLIB:
        print("matplotlib未安装，无法生成图像")
        return

    setup_chinese_font()

    # 计算基本参数
    radius = drill_diameter / 2.0
    circumference = 2 * math.pi * radius
    angle_rad = math.radians(spiral_angle)
    pitch = circumference / math.tan(angle_rad)
    
    # 计算每个螺旋槽之间的角度间隔
    angle_per_flute = 2 * math.pi / num_flutes

    # 创建图形 - 3D视图和XZ映射图
    fig = plt.figure(figsize=(16, 8))
    
    # 左侧：3D视图
    ax = fig.add_subplot(121, projection='3d')
    ax.set_title('3D螺旋线视图', fontsize=14, fontweight='bold', pad=20)
    ax.set_xlabel('X (mm)', fontsize=11)
    ax.set_ylabel('Y (mm)', fontsize=11)
    ax.set_zlabel('轴向长度 Z (mm)', fontsize=11)
    
    # 右侧：XZ映射图（侧视图）
    ax2d = fig.add_subplot(122)
    ax2d.set_title('XZ映射图（侧视图）', fontsize=14, fontweight='bold')
    ax2d.set_xlabel('轴向长度 Z (mm)', fontsize=11)
    ax2d.set_ylabel('X (mm)', fontsize=11)
    ax2d.grid(True, alpha=0.3, linestyle='--')
    ax2d.set_aspect('equal', adjustable='box')

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
        # 1. 绘制中心线（在外圆上）- 已移除
        # ax.plot(x_3d_center, y_3d_center, z_3d_center, color=color, 
        #         linewidth=2.5, label=f'槽{flute_idx+1}中心线' if flute_idx < 3 else '', 
        #         alpha=0.8)
        
        # 2. 绘制左边界（槽的左侧边缘，在槽底部）
        ax.plot(x_3d_left, y_3d_left, z_3d_left, color=color, 
                linewidth=2.5, label=f'槽{flute_idx+1}左边界' if flute_idx == 0 else '', 
                alpha=0.9)
        
        # 3. 绘制右边界（槽的右侧边缘，在槽底部）
        ax.plot(x_3d_right, y_3d_right, z_3d_right, color=color, 
                linewidth=2.5, label=f'槽{flute_idx+1}右边界' if flute_idx == 0 else '', 
                alpha=0.9)
        
        # 4. 绘制槽的底部（连接左右边界的底部，显示槽的宽度）
        step = max(1, len(x_3d_left) // 15)  # 绘制约15条连接线
        for i in range(0, len(x_3d_left), step):
            ax.plot([x_3d_left[i], x_3d_right[i]], 
                    [y_3d_left[i], y_3d_right[i]], 
                    [z_3d_left[i], z_3d_right[i]], 
                    color=color, linewidth=1.5, alpha=0.6)
        
        # 5. 绘制槽的深度（从外圆到槽底，显示槽的深度）- 已移除
        # depth_points = [0, len(x_3d_center)//4, len(x_3d_center)//2, 
        #                 3*len(x_3d_center)//4, len(x_3d_center)-1]
        # for i in depth_points:
        #     if i < len(x_3d_center):
        #         # 从外圆到槽底部的深度线
        #         angle = (center_points[i].y / circumference) * 2 * math.pi + base_angle_offset
        #         x_outer = radius * math.cos(angle)
        #         y_outer = radius * math.sin(angle)
        #         x_inner = groove_radius * math.cos(angle)
        #         y_inner = groove_radius * math.sin(angle)
        #         z_val = z_3d_center[i]
        #         
        #         ax.plot([x_outer, x_inner], [y_outer, y_inner], [z_val, z_val],
        #                 color=color, linewidth=1.5, alpha=0.5)
        
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
                ax.plot([x_outer, x_3d_left[i]], [y_outer, y_3d_left[i]], 
                        [z_val, z_val], color=color, linewidth=1.5, alpha=0.5)
                # 左边界到右边界（槽底，加粗显示）
                ax.plot([x_3d_left[i], x_3d_right[i]], 
                        [y_3d_left[i], y_3d_right[i]], 
                        [z_val, z_val], color=color, linewidth=2.5, alpha=0.7)
                # 右边界到外圆
                ax.plot([x_3d_right[i], x_outer], 
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
        ax.scatter([x_3d_center[0]], [y_3d_center[0]], [z_3d_center[0]], 
                   color='green', s=50, label='起点', zorder=5)
        ax.scatter([x_3d_center[-1]], [y_3d_center[-1]], [z_3d_center[-1]], 
                   color='orange', s=50, label='终点', zorder=5)

    # 绘制刀具圆柱体（上下两个圆）- 已移除
    # theta = [i * 2 * math.pi / 50 for i in range(51)]
    # for z_val in [0, total_length]:
    #     x_cyl = [radius * math.cos(t) for t in theta]
    #     y_cyl = [radius * math.sin(t) for t in theta]
    #     z_cyl = [z_val] * len(theta)
    #     ax.plot(x_cyl, y_cyl, z_cyl, 'k-', linewidth=1.5, alpha=0.6)

    # 绘制圆柱体侧面（连接上下圆的线）- 已移除
    # for angle_idx in [0, 12, 25, 37, 50]:  # 均匀分布的几条线
    #     t = theta[angle_idx]
    #     x_start = radius * math.cos(t)
    #     y_start = radius * math.sin(t)
    #     x_end = radius * math.cos(t)
    #     y_end = radius * math.sin(t)
    #     ax.plot([x_start, x_end], [y_start, y_end], [0, total_length], 
    #             'k-', linewidth=0.8, alpha=0.4)

    # 绘制轴向线（Z轴）
    ax.plot([0, 0], [0, 0], [0, total_length], 'k-', linewidth=2, alpha=0.5, label='中心轴线')

    # 设置视角 - 更好的观察角度
    ax.view_init(elev=20, azim=45)  # elev=仰角, azim=方位角

    ax.legend(fontsize=9, loc='upper left')
    ax.set_box_aspect([1, 1, max(1, total_length/(radius*2))])  # 根据实际尺寸设置宽高比
    
    # 设置坐标轴范围
    ax.set_xlim(-radius*1.5, radius*1.5)
    ax.set_ylim(-radius*1.5, radius*1.5)
    ax.set_zlim(-2, total_length + 2)
    
    # ========== 绘制XZ映射图（侧视图） ==========
    # 收集所有螺旋槽在XZ平面的投影数据，考虑遮挡关系
    colors_2d = ['red', 'blue', 'green', 'orange', 'purple']
    
    for flute_idx in range(num_flutes):
        color = colors_2d[flute_idx % len(colors_2d)]
        base_angle_offset = flute_idx * angle_per_flute
        
        # 收集XZ坐标（只收集可见部分）
        x_proj = []  # X坐标
        z_proj = []  # Z坐标（轴向长度）
        
        # 收集左边界和右边界的XZ坐标（只收集可见部分）
        x_left_proj = []
        z_left_proj = []
        x_right_proj = []
        z_right_proj = []
        
        for i, point in enumerate(center_points):
            z = point.x  # 轴向长度
            angle_center = (point.y / circumference) * 2 * math.pi + base_angle_offset
            
            # 计算Y坐标来判断可见性（从Y轴方向看，Y>0的部分在前，Y<0的部分在后）
            y_center = radius * math.sin(angle_center)
            
            # 只显示Y>=0的部分（前面的部分，可见）
            if y_center >= 0:
                # 中心线在XZ平面的投影（X坐标）
                x_center = radius * math.cos(angle_center)
                x_proj.append(x_center)
                z_proj.append(z)
                
                # 边界在XZ平面的投影
                if i < len(boundaries):
                    left_point, right_point = boundaries[i]
                    angle_left = (left_point.y / circumference) * 2 * math.pi + base_angle_offset
                    angle_right = (right_point.y / circumference) * 2 * math.pi + base_angle_offset
                    
                    # 检查边界点的Y坐标
                    y_left = groove_radius * math.sin(angle_left)
                    y_right = groove_radius * math.sin(angle_right)
                    
                    # 只添加可见的边界点（Y>=0）
                    if y_left >= 0:
                        x_left = groove_radius * math.cos(angle_left)
                        x_left_proj.append(x_left)
                        z_left_proj.append(z)
                    
                    if y_right >= 0:
                        x_right = groove_radius * math.cos(angle_right)
                        x_right_proj.append(x_right)
                        z_right_proj.append(z)
        
        # 绘制中心线投影（只绘制可见部分）
        if len(z_proj) > 0:
            ax2d.plot(z_proj, x_proj, color=color, linewidth=2, 
                     linestyle='--', alpha=0.7, label=f'槽{flute_idx+1}中心线' if flute_idx < 3 else '')
        
        # 绘制左边界投影（只绘制可见部分）
        if len(z_left_proj) > 0:
            ax2d.plot(z_left_proj, x_left_proj, color=color, linewidth=2, 
                     alpha=0.9, label=f'槽{flute_idx+1}左边界' if flute_idx == 0 else '')
        
        # 绘制右边界投影（只绘制可见部分）
        if len(z_right_proj) > 0:
            ax2d.plot(z_right_proj, x_right_proj, color=color, linewidth=2, 
                     alpha=0.9, label=f'槽{flute_idx+1}右边界' if flute_idx == 0 else '')
        
        # 填充槽的区域（只填充可见部分）
        # 需要将左右边界合并以形成闭合区域
        if len(z_left_proj) > 0 and len(z_right_proj) > 0:
            # 找到对应的Z值进行配对
            z_fill = []
            x_fill = []
            
            # 创建字典以便快速查找对应的X值
            left_dict = dict(zip(z_left_proj, x_left_proj))
            right_dict = dict(zip(z_right_proj, x_right_proj))
            
            # 找到共同的Z值
            common_z = sorted(set(z_left_proj) & set(z_right_proj))
            
            if len(common_z) > 1:
                # 按Z值排序
                for z_val in common_z:
                    if z_val in left_dict and z_val in right_dict:
                        z_fill.append(z_val)
                        x_fill.append(left_dict[z_val])
                
                # 添加右边界（反向）
                for z_val in reversed(common_z):
                    if z_val in right_dict:
                        z_fill.append(z_val)
                        x_fill.append(right_dict[z_val])
                
                if len(z_fill) > 2:
                    ax2d.fill(z_fill, x_fill, color=color, alpha=0.2)
    
    # 绘制中心轴线（Z轴）
    ax2d.axhline(y=0, color='black', linewidth=2, linestyle='-', alpha=0.5, label='中心轴线')
    
    # 绘制外圆边界（在XZ平面的投影范围）
    ax2d.axhline(y=radius, color='gray', linewidth=1, linestyle=':', alpha=0.5)
    ax2d.axhline(y=-radius, color='gray', linewidth=1, linestyle=':', alpha=0.5)
    
    # 添加起点和终点标记（只标记可见的）
    if center_points:
        # 起点
        first_z = center_points[0].x
        first_angle = (center_points[0].y / circumference) * 2 * math.pi
        first_y = radius * math.sin(first_angle)
        if first_y >= 0:  # 只标记可见的起点
            first_x = radius * math.cos(first_angle)
            ax2d.scatter([first_z], [first_x], color='green', s=50, zorder=5, label='起点')
        
        # 终点
        last_z = center_points[-1].x
        last_angle = (center_points[-1].y / circumference) * 2 * math.pi
        last_y = radius * math.sin(last_angle)
        if last_y >= 0:  # 只标记可见的终点
            last_x = radius * math.cos(last_angle)
            ax2d.scatter([last_z], [last_x], color='orange', s=50, zorder=5, label='终点')
    
    ax2d.legend(fontsize=9, loc='upper right')
    ax2d.set_xlim(-2, total_length + 2)
    ax2d.set_ylim(-radius*1.2, radius*1.2)

    # 保存图像
    output_file = '3d_helical_view.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\n3D螺旋线视图已保存到: {output_file}")
    
    # 显示交互式窗口
    print("\n" + "=" * 60)
    print("交互式3D视图已打开！")
    print("=" * 60)
    print("操作说明：")
    print("  • 鼠标左键拖拽：旋转视图")
    print("  • 鼠标滚轮：缩放视图")
    print("  • 鼠标右键拖拽：平移视图")
    print("  • 关闭窗口：程序将继续运行")
    print("=" * 60)
    
    # 显示交互式窗口（阻塞模式，直到窗口关闭）
    plt.show(block=True)
    
    print("\n窗口已关闭，程序结束。")

def main():
    """主函数"""
    print("=" * 60)
    print("3D螺旋线视图生成工具")
    print("=" * 60)
    print()

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

        # 绘制3D视图
        print("\n正在生成3D螺旋线视图...")
        plot_3d_helical_view(
            center_points, boundaries,
            spiral_angle, drill_diameter, total_length,
            blade_width, blade_height, num_flutes
        )

        print("\n" + "=" * 60)
        print("完成！")
        print("=" * 60)

    except Exception as e:
        print(f"\n程序执行出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

