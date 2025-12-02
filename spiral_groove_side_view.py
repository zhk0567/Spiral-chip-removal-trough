#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
螺旋排屑槽3D模型侧视图生成工具
只绘制边缘线条，生成侧视图投影
"""

import math
import numpy as np
import sys
import json
import os
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.collections import LineCollection

# 设置标准输出编码为UTF-8
if sys.platform == 'win32':
    try:
        import io
        if sys.stdout.encoding != 'utf-8':
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        if sys.stderr.encoding != 'utf-8':
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    except:
        pass  # 如果已经关闭，忽略错误

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
            return
    
    plt.rcParams['axes.unicode_minus'] = False

setup_chinese_font()

# 检查并导入必要的库
try:
    import trimesh
except ImportError:
    print("错误：trimesh库未安装")
    print("  安装命令: pip install trimesh")
    sys.exit(1)

try:
    import open3d as o3d
    HAS_OPEN3D = True
    import warnings
    warnings.filterwarnings('ignore', category=UserWarning, module='open3d')
    o3d.utility.set_verbosity_level(o3d.utility.VerbosityLevel.Error)
except ImportError:
    HAS_OPEN3D = False
    print("提示：安装open3d库可以获得更好的3D可视化效果")
    print("  安装命令: pip install open3d")


def extract_edge_lines(mesh, view_direction='xz', sample_ratio=0.1):
    """
    从mesh中提取边缘线条（侧视图可见的边缘）
    返回边缘线段的列表，每个线段是[(x1, y1, z1), (x2, y2, z2)]
    
    参数:
        mesh: trimesh mesh对象
        view_direction: 视图方向，'xz'或'yz'
        sample_ratio: 采样比例，用于减少边的数量（0.0-1.0）
    """
    print("  提取mesh边缘...")
    
    # 获取所有唯一的边
    edges_set = set()
    for face in mesh.faces:
        for i in range(3):
            v1 = face[i]
            v2 = face[(i + 1) % 3]
            edge = tuple(sorted([v1, v2]))
            edges_set.add(edge)
    
    edges_list = list(edges_set)
    print(f"  找到 {len(edges_list)} 条边")
    
    # 如果边太多，进行采样
    if sample_ratio < 1.0 and len(edges_list) > 10000:
        import random
        sample_size = int(len(edges_list) * sample_ratio)
        edges_list = random.sample(edges_list, sample_size)
        print(f"  采样到 {len(edges_list)} 条边")
    
    # 转换为坐标
    edge_lines = []
    for edge in edges_list:
        v1_idx, v2_idx = edge
        p1 = mesh.vertices[v1_idx]
        p2 = mesh.vertices[v2_idx]
        edge_lines.append([p1, p2])
    
    return edge_lines


def project_to_side_view(edge_lines, view_direction='xz', return_depth=False):
    """
    将3D边缘线投影到侧视图（XZ平面），可选返回深度信息
    
    参数:
        edge_lines: 边缘线列表，每个元素是[(x1, y1, z1), (x2, y2, z2)]
        view_direction: 视图方向，'xz'表示XZ平面投影
        return_depth: 是否返回深度信息（Y坐标）
    
    返回:
        如果return_depth=False: 投影后的2D线段列表，每个元素是[(x1, z1), (x2, z2)]
        如果return_depth=True: (投影后的2D线段列表, 深度列表)，深度是Y坐标的平均值
    """
    projected_lines = []
    depths = []
    
    for line in edge_lines:
        p1, p2 = line
        
        if view_direction == 'xz':
            # XZ平面投影：保留X和Z坐标，忽略Y坐标
            proj_p1 = np.array([p1[0], p1[2]])
            proj_p2 = np.array([p2[0], p2[2]])
            # Y坐标表示深度（前后关系）
            depth = (p1[1] + p2[1]) / 2.0
        elif view_direction == 'yz':
            # YZ平面投影：保留Y和Z坐标，忽略X坐标
            proj_p1 = np.array([p1[1], p1[2]])
            proj_p2 = np.array([p2[1], p2[2]])
            # X坐标表示深度
            depth = (p1[0] + p2[0]) / 2.0
        else:
            # 默认XZ投影
            proj_p1 = np.array([p1[0], p1[2]])
            proj_p2 = np.array([p2[0], p2[2]])
            depth = (p1[1] + p2[1]) / 2.0
        
        projected_lines.append([proj_p1, proj_p2])
        depths.append(depth)
    
    if return_depth:
        return projected_lines, depths
    return projected_lines


def handle_occlusion(segments_with_depth_and_color, tolerance=0.05):
    """
    处理遮挡关系，移除被遮挡的线段（优化版本：使用空间网格加速）
    
    参数:
        segments_with_depth_and_color: 列表，每个元素是(segment, depth, color)
            segment: [[x1, z1], [x2, z2]]
            depth: 深度值（Y坐标的平均值，越大越靠前）
            color: 颜色
        tolerance: 判断线段重叠的容差（mm）
    
    返回:
        可见线段列表，每个元素是(segment, color)
    """
    if not segments_with_depth_and_color:
        return []
    
    # 如果线段数量较少，使用简单方法
    if len(segments_with_depth_and_color) < 1000:
        return handle_occlusion_simple(segments_with_depth_and_color, tolerance)
    
    # 按深度排序（深度大的在前，即Y值大的在前，更靠近观察者）
    sorted_segments = sorted(segments_with_depth_and_color, key=lambda x: x[1], reverse=True)
    
    # 计算X和Z的范围，用于创建空间网格
    all_x = []
    all_z = []
    for segment, _, _ in sorted_segments:
        p1, p2 = segment
        all_x.extend([float(p1[0]), float(p2[0])])
        all_z.extend([float(p1[1]), float(p2[1])])
    
    if not all_x:
        return []
    
    x_min, x_max = min(all_x), max(all_x)
    z_min, z_max = min(all_z), max(all_z)
    
    # 创建空间网格（将空间划分为网格，只检查同一网格内的线段）
    grid_size = max((x_max - x_min) / 50, (z_max - z_min) / 50, tolerance * 10)  # 网格大小
    grid = {}  # {(grid_x, grid_z): [segments]}
    
    def get_grid_key(x, z):
        """获取点所在的网格坐标"""
        gx = int((x - x_min) / grid_size)
        gz = int((z - z_min) / grid_size)
        return (gx, gz)
    
    visible_segments = []
    occluded_count = 0
    
    for segment, depth, color in sorted_segments:
        p1, p2 = segment
        x1, z1 = float(p1[0]), float(p1[1])
        x2, z2 = float(p2[0]), float(p2[1])
        
        # 确保x1 <= x2（规范化线段方向）
        if x1 > x2:
            x1, x2 = x2, x1
            z1, z2 = z2, z1
        
        # 获取线段覆盖的网格
        grid_keys = set()
        grid_keys.add(get_grid_key(x1, z1))
        grid_keys.add(get_grid_key(x2, z2))
        # 如果线段跨越多个网格，添加中间网格
        num_steps = max(1, int((x2 - x1) / grid_size) + 1)
        for i in range(num_steps + 1):
            t = i / num_steps if num_steps > 0 else 0
            x = x1 + t * (x2 - x1)
            z = z1 + t * (z2 - z1)
            grid_keys.add(get_grid_key(x, z))
        
        # 检查这条线段是否被已处理的线段遮挡
        is_occluded = False
        
        # 只检查相关网格中的线段
        candidate_segments = []
        for gk in grid_keys:
            if gk in grid:
                candidate_segments.extend(grid[gk])
        
        # 对于候选线段，检查当前线段是否被遮挡
        for seen_seg, seen_depth, _ in candidate_segments:
            if seen_depth <= depth:  # 已处理的线段在后面（深度小），不会遮挡当前线段
                continue
            
            seen_p1, seen_p2 = seen_seg
            sx1, sz1 = float(seen_p1[0]), float(seen_p1[1])
            sx2, sz2 = float(seen_p2[0]), float(seen_p2[1])
            
            if sx1 > sx2:
                sx1, sx2 = sx2, sx1
                sz1, sz2 = sz2, sz1
            
            # 快速检查：X方向是否重叠
            if x2 < sx1 - tolerance or x1 > sx2 + tolerance:
                continue
            
            # 计算重叠区域
            overlap_x1 = max(x1, sx1)
            overlap_x2 = min(x2, sx2)
            
            if overlap_x2 - overlap_x1 <= tolerance:
                continue
            
            # 有重叠，检查Z坐标
            overlap_x_mid = (overlap_x1 + overlap_x2) / 2.0
            
            # 在当前线段上插值Z值
            if abs(x2 - x1) > tolerance:
                t1 = (overlap_x_mid - x1) / (x2 - x1)
                z_current = z1 + t1 * (z2 - z1)
            else:
                z_current = (z1 + z2) / 2.0
            
            # 在已处理线段上插值Z值
            if abs(sx2 - sx1) > tolerance:
                t2 = (overlap_x_mid - sx1) / (sx2 - sx1)
                z_seen = sz1 + t2 * (sz2 - sz1)
            else:
                z_seen = (sz1 + sz2) / 2.0
            
            # 如果Z值接近（在容差内），且已处理线段深度更大（更靠前），则当前线段被遮挡
            z_tolerance = tolerance * 2
            if abs(z_current - z_seen) < z_tolerance:
                # 检查重叠比例
                overlap_ratio = (overlap_x2 - overlap_x1) / max(abs(x2 - x1), tolerance)
                if overlap_ratio > 0.8:  # 80%以上重叠
                    is_occluded = True
                    occluded_count += 1
                    break
        
        if not is_occluded:
            visible_segments.append((segment, depth, color))
            # 将线段添加到网格中
            for gk in grid_keys:
                if gk not in grid:
                    grid[gk] = []
                grid[gk].append((segment, depth, color))
    
    print(f"    移除了 {occluded_count} 条被遮挡的线段")
    
    # 返回可见线段和颜色
    return [(seg, color) for seg, _, color in visible_segments]


def handle_occlusion_simple(segments_with_depth_and_color, tolerance=0.05):
    """
    简单的遮挡处理（用于少量线段）
    """
    if not segments_with_depth_and_color:
        return []
    
    # 按深度排序
    sorted_segments = sorted(segments_with_depth_and_color, key=lambda x: x[1], reverse=True)
    visible_segments = []
    
    for segment, depth, color in sorted_segments:
        p1, p2 = segment
        x1, z1 = float(p1[0]), float(p1[1])
        x2, z2 = float(p2[0]), float(p2[1])
        
        if x1 > x2:
            x1, x2 = x2, x1
            z1, z2 = z2, z1
        
        is_occluded = False
        
        for seen_seg, seen_depth, _ in visible_segments:
            if seen_depth <= depth:
                continue
            
            seen_p1, seen_p2 = seen_seg
            sx1, sz1 = float(seen_p1[0]), float(seen_p1[1])
            sx2, sz2 = float(seen_p2[0]), float(seen_p2[1])
            
            if sx1 > sx2:
                sx1, sx2 = sx2, sx1
                sz1, sz2 = sz2, sz1
            
            if x2 < sx1 - tolerance or x1 > sx2 + tolerance:
                continue
            
            overlap_x1 = max(x1, sx1)
            overlap_x2 = min(x2, sx2)
            
            if overlap_x2 - overlap_x1 > tolerance:
                overlap_x_mid = (overlap_x1 + overlap_x2) / 2.0
                
                if abs(x2 - x1) > tolerance:
                    t1 = (overlap_x_mid - x1) / (x2 - x1)
                    z_current = z1 + t1 * (z2 - z1)
                else:
                    z_current = (z1 + z2) / 2.0
                
                if abs(sx2 - sx1) > tolerance:
                    t2 = (overlap_x_mid - sx1) / (sx2 - sx1)
                    z_seen = sz1 + t2 * (sz2 - sz1)
                else:
                    z_seen = (sz1 + sz2) / 2.0
                
                z_tolerance = tolerance * 2
                if abs(z_current - z_seen) < z_tolerance:
                    overlap_ratio = (overlap_x2 - overlap_x1) / max(abs(x2 - x1), tolerance)
                    if overlap_ratio > 0.8:
                        is_occluded = True
                        break
        
        if not is_occluded:
            visible_segments.append((segment, depth, color))
    
    return [(seg, color) for seg, _, color in visible_segments]


def create_side_view(mesh, params, output_file='spiral_groove_side_view.png', 
                    view_direction='xz', dpi=300, figsize=(12, 8)):
    """
    创建侧视图，只绘制边缘线条，使用和主程序相同的颜色方案
    
    参数:
        mesh: trimesh.Trimesh对象
        params: 参数字典
        output_file: 输出文件名
        view_direction: 视图方向，'xz'或'yz'
        dpi: 输出分辨率
        figsize: 图像大小
    """
    print("=" * 60)
    print("生成侧视图（只绘制线条，使用相同颜色方案）")
    print("=" * 60)
    
    # 导入主程序的边缘提取函数
    try:
        from spiral_groove_3d_cad import (
            _extract_circle_edge_points,
            _extract_spiral_edge_points,
            NUM_CIRCLE_POINTS
        )
    except ImportError:
        print("错误：无法导入主程序的边缘提取函数")
        return None
    
    # 提取边缘点（使用和主程序相同的方法）
    print("提取边缘点...")
    vertices = mesh.vertices
    bounds = mesh.bounds
    radius = params['D1'] / 2.0
    
    # 提取端面圆周
    bottom_z = max(params['L1'] * 0.5, bounds[0][2] + 0.1) if params['L1'] > 0 else bounds[0][2] + 0.1
    bottom_circle_points = _extract_circle_edge_points(vertices, bounds, radius, bottom_z) if bottom_z > bounds[0][2] else None
    top_circle_points = _extract_circle_edge_points(vertices, bounds, radius, bounds[1][2])
    
    # 提取螺旋槽边缘点
    # 注意：_extract_spiral_edge_points内部使用L1作为起始点，但实际螺旋槽从z=0开始
    # 我们需要修改参数，使边缘提取覆盖整个范围（从0到L1+L2）
    # 同时减少采样点数以提高性能（侧视图不需要那么高的精度）
    modified_params = params.copy()
    # 临时修改L1为0，使边缘提取从z=0开始
    original_L1 = modified_params['L1']
    modified_params['L1'] = 0.0
    modified_params['L2'] = original_L1 + modified_params['L2']  # 扩展L2以覆盖整个范围
    
    # 减少采样点数以提高性能（侧视图可以使用较少的点）
    # 原来NUM_SPIRAL_POINTS=1500，对于侧视图200-300点就足够了
    side_view_spiral_points = 250  # 侧视图使用的采样点数（进一步减少以提高速度）
    spiral_edge_points = _extract_spiral_edge_points(vertices, modified_params, num_points=side_view_spiral_points)
    
    # 恢复原始参数
    modified_params['L1'] = original_L1
    modified_params['L2'] = modified_params['L2'] - original_L1
    
    # 定义颜色方案（和主程序相同）
    bottom_circle_color = (0.0, 0.0, 1.0)  # 深蓝色（使用元组以便作为字典键）
    top_circle_color = (0.0, 1.0, 0.0)     # 深绿色（使用元组以便作为字典键）
    
    # 螺旋槽颜色方案（和主程序相同）
    # 16条线：0=底部左, 1=底部右, 2=外边缘左(峰), 3=外边缘右(峰), 4=侧面左, 5=侧面右, 6=锋左, 7=锋右,
    #         8=起始端左, 9=起始端右, 10=结束端左, 11=结束端右, 12=起始端底部圆周, 13=起始端外边缘圆周, 14=结束端底部圆周, 15=结束端外边缘圆周
    spiral_colors = [
        # 槽1：使用红色系
        [[1.0, 0.0, 0.0], [0.7, 0.0, 0.0],  # 底部：鲜红/深红
         [1.0, 1.0, 0.0], [1.0, 0.8, 0.0],  # 峰（外边缘）：亮黄/金黄
         [1.0, 0.6, 0.8], [0.9, 0.4, 0.6],  # 侧面：粉红/浅粉红
         [1.0, 0.5, 0.0], [0.8, 0.4, 0.0],  # 锋：橙色/深橙
         [1.0, 0.3, 0.0], [0.7, 0.2, 0.0],  # 起始/结束端：橙红/深橙红
         [1.0, 1.0, 0.3], [1.0, 0.9, 0.2],  # 圆周：黄色/深黄色
         [1.0, 1.0, 0.3], [1.0, 0.9, 0.2]],
        # 槽2：使用蓝色系
        [[0.0, 1.0, 1.0], [0.0, 0.9, 0.9],  # 峰（外边缘）：青色/亮青
         [0.5, 0.7, 1.0], [0.3, 0.5, 0.9],  # 侧面：天蓝/浅天蓝
         [0.0, 0.6, 1.0], [0.0, 0.5, 0.8],  # 锋：青蓝/深青蓝
         [0.3, 0.0, 1.0], [0.2, 0.0, 0.7],  # 起始/结束端：蓝紫/深蓝紫
         [0.0, 1.0, 0.8], [0.0, 0.9, 0.7],  # 圆周：青色/深青色
         [0.0, 1.0, 0.8], [0.0, 0.9, 0.7]],
        # 槽3：使用绿色系
        [[0.7, 1.0, 0.0], [0.6, 0.9, 0.0],  # 峰（外边缘）：黄绿/亮黄绿
         [0.6, 1.0, 0.6], [0.4, 0.9, 0.4],  # 侧面：浅绿/浅绿
         [0.4, 1.0, 0.2], [0.3, 0.8, 0.1],  # 锋：草绿/深草绿
         [0.5, 1.0, 0.0], [0.4, 0.8, 0.0],  # 起始/结束端：绿黄/深绿黄
         [0.7, 1.0, 0.4], [0.6, 0.9, 0.3],  # 圆周：黄绿/深黄绿
         [0.7, 1.0, 0.4], [0.6, 0.9, 0.3]],
        # 槽4：使用紫色系
        [[1.0, 0.5, 1.0], [0.9, 0.4, 0.9],  # 峰（外边缘）：粉紫/亮粉紫
         [0.9, 0.6, 1.0], [0.7, 0.4, 0.9],  # 侧面：浅紫/浅紫
         [0.8, 0.2, 1.0], [0.6, 0.1, 0.8],  # 锋：紫红/深紫红
         [0.6, 0.0, 1.0], [0.4, 0.0, 0.7],  # 起始/结束端：紫蓝/深紫蓝
         [1.0, 0.6, 0.8], [0.9, 0.5, 0.7],  # 圆周：粉紫/深粉紫
         [1.0, 0.6, 0.8], [0.9, 0.5, 0.7]],
    ]
    
    # 投影到侧视图
    print(f"投影到{view_direction.upper()}平面...")
    
    # 创建图形
    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
    ax.set_aspect('equal')
    
    # 端面圆周将在遮挡处理时一起处理，这里先不单独绘制
    
    # 绘制螺旋槽边缘（使用相同颜色方案）- 优化版本，批量绘制
    print(f"绘制螺旋槽边缘...")
    print(f"  提取到 {len(spiral_edge_points)} 条边缘线")
    num_flutes = params.get('num_flutes', 3)
    edges_per_flute = 16  # 每个槽16种类型的边缘线
    
    edge_idx_in_flute = 0
    current_flute = 0
    
    # 按颜色分组，准备批量绘制
    color_groups = {}  # {color: [segments]}
    
    # RGB(255, 225, 118)转换为0-1范围约为(1.0, 0.882, 0.463)
    target_rgb_0_255_1 = (255, 225, 118)
    target_rgb_0_1_1 = (255/255.0, 225/255.0, 118/255.0)  # (1.0, 0.882, 0.463)
    
    # RGB(255, 230, 51)转换为0-1范围约为(1.0, 0.902, 0.2) - 深黄色
    target_rgb_0_255_2 = (255, 230, 51)
    target_rgb_0_1_2 = (255/255.0, 230/255.0, 51/255.0)  # (1.0, 0.902, 0.2)
    
    removed_edge_count = 0
    
    for spiral_edge in spiral_edge_points:
        if spiral_edge is not None and len(spiral_edge) >= 2:
            # 计算当前边缘线属于哪个槽和哪种类型
            if edge_idx_in_flute >= edges_per_flute:
                edge_idx_in_flute = 0
                current_flute += 1
            
            # 确保edge_type在有效范围内（0-15）
            edge_type = min(edge_idx_in_flute, edges_per_flute - 1)
            
            # 获取颜色
            flute_color_idx = current_flute % len(spiral_colors)
            if flute_color_idx < len(spiral_colors) and edge_type < len(spiral_colors[flute_color_idx]):
                color = tuple(spiral_colors[flute_color_idx][edge_type])  # 转换为tuple作为字典键
            else:
                color = (1.0, 0.0, 0.0)  # 默认红色
            
            # 检查是否是目标颜色，如果是则跳过整条边缘线
            is_target_color = False
            if len(color) >= 3:
                # 如果颜色值在0-1范围
                if all(0 <= c <= 1 for c in color):
                    # RGB(255, 225, 118) = (1.0, 0.882, 0.463)
                    is_target_1 = (abs(color[0] - target_rgb_0_1_1[0]) < 0.1 and
                                   abs(color[1] - target_rgb_0_1_1[1]) < 0.15 and
                                   abs(color[2] - target_rgb_0_1_1[2]) < 0.15)
                    # RGB(255, 230, 51) = (1.0, 0.902, 0.2) - 深黄色
                    # 代码中实际使用的是 (1.0, 0.9, 0.2)，需要精确匹配
                    # 检查是否是深黄色：R接近1.0，G接近0.9，B接近0.2
                    is_target_2 = (abs(color[0] - 1.0) < 0.01 and
                                   abs(color[1] - 0.9) < 0.02 and
                                   abs(color[2] - 0.2) < 0.01)
                    # 也检查精确的RGB(255, 230, 51)值 (1.0, 0.902, 0.2)
                    is_target_2_exact = (abs(color[0] - target_rgb_0_1_2[0]) < 0.01 and
                                         abs(color[1] - target_rgb_0_1_2[1]) < 0.02 and
                                         abs(color[2] - target_rgb_0_1_2[2]) < 0.01)
                    is_target_color = is_target_1 or is_target_2 or is_target_2_exact
                # 如果颜色值在0-255范围
                elif all(0 <= c <= 255 for c in color):
                    is_target_1 = (abs(color[0] - target_rgb_0_255_1[0]) < 10 and
                                  abs(color[1] - target_rgb_0_255_1[1]) < 20 and
                                  abs(color[2] - target_rgb_0_255_1[2]) < 20)
                    is_target_2 = (abs(color[0] - 255) < 5 and
                                  abs(color[1] - 230) < 10 and
                                  abs(color[2] - 51) < 5)
                    is_target_color = is_target_1 or is_target_2
            
            if is_target_color:
                # 跳过这条边缘线，不处理
                removed_edge_count += 1
                edge_idx_in_flute += 1
                continue
            
            # 投影并准备线段
            try:
                segments = []
                if isinstance(spiral_edge[0], (list, np.ndarray)) and len(spiral_edge[0]) == 3:
                    # 多点组成的线（列表中的每个元素是[x, y, z]）
                    if len(spiral_edge) >= 2:
                        # 将多点转换为线段对
                        line_pairs = [[spiral_edge[i], spiral_edge[i+1]] 
                                     for i in range(len(spiral_edge)-1)]
                        projected = project_to_side_view(line_pairs, view_direction, return_depth=False)
                        for line in projected:
                            if len(line) == 2:
                                p1, p2 = line
                                # 检查点是否有效，并确保是numpy数组
                                p1_arr = np.array(p1) if not isinstance(p1, np.ndarray) else p1
                                p2_arr = np.array(p2) if not isinstance(p2, np.ndarray) else p2
                                # 确保是1D数组，并提取标量值
                                p1_arr = np.asarray(p1_arr).flatten()
                                p2_arr = np.asarray(p2_arr).flatten()
                                if (len(p1_arr) >= 2 and len(p2_arr) >= 2 and
                                    not np.any(np.isnan(p1_arr[:2])) and not np.any(np.isnan(p2_arr[:2]))):
                                    # LineCollection需要的格式：每个segment是[[x1, y1], [x2, y2]]
                                    segment = [[float(p1_arr[0]), float(p1_arr[1])], 
                                              [float(p2_arr[0]), float(p2_arr[1])]]
                                    segments.append(segment)
                elif len(spiral_edge) == 2:
                    # 两点组成的线（spiral_edge本身就是[p1, p2]）
                    if (isinstance(spiral_edge[0], (list, np.ndarray)) and 
                        isinstance(spiral_edge[1], (list, np.ndarray)) and
                        len(spiral_edge[0]) == 3 and len(spiral_edge[1]) == 3):
                        projected = project_to_side_view([spiral_edge], view_direction, return_depth=False)
                        if projected and len(projected) > 0 and len(projected[0]) == 2:
                            p1, p2 = projected[0]
                            # 检查点是否有效，并确保是numpy数组
                            p1_arr = np.array(p1) if not isinstance(p1, np.ndarray) else p1
                            p2_arr = np.array(p2) if not isinstance(p2, np.ndarray) else p2
                            # 确保是1D数组，并提取标量值
                            p1_arr = np.asarray(p1_arr).flatten()
                            p2_arr = np.asarray(p2_arr).flatten()
                            if (len(p1_arr) >= 2 and len(p2_arr) >= 2 and
                                not np.any(np.isnan(p1_arr[:2])) and not np.any(np.isnan(p2_arr[:2]))):
                                # LineCollection需要的格式：每个segment是[[x1, y1], [x2, y2]]
                                segment = [[float(p1_arr[0]), float(p1_arr[1])], 
                                          [float(p2_arr[0]), float(p2_arr[1])]]
                                segments.append(segment)
                
                # 将线段添加到对应颜色的组
                if segments:
                    if color not in color_groups:
                        color_groups[color] = []
                    color_groups[color].extend(segments)
                    
            except Exception as e:
                # 输出错误信息以便调试
                print(f"  警告: 处理边缘线时出错: {e}")
                import traceback
                traceback.print_exc()
            
            edge_idx_in_flute += 1
    
    if removed_edge_count > 0:
        print(f"  去除目标颜色(RGB(255,225,118)和RGB(255,230,51))的边缘线: {removed_edge_count} 条")
    
    # 添加端面圆周
    if bottom_circle_points and len(bottom_circle_points) >= 2:
        line_pairs = [[bottom_circle_points[i], bottom_circle_points[i+1]] 
                      for i in range(len(bottom_circle_points)-1)]
        projected = project_to_side_view(line_pairs, view_direction, return_depth=False)
        for line in projected:
            if len(line) == 2:
                p1, p2 = line
                # 检查点是否有效，并确保是numpy数组
                p1_arr = np.array(p1) if not isinstance(p1, np.ndarray) else p1
                p2_arr = np.array(p2) if not isinstance(p2, np.ndarray) else p2
                # 确保是1D数组，并提取标量值
                p1_arr = np.asarray(p1_arr).flatten()
                p2_arr = np.asarray(p2_arr).flatten()
                if (len(p1_arr) >= 2 and len(p2_arr) >= 2 and
                    not np.any(np.isnan(p1_arr[:2])) and not np.any(np.isnan(p2_arr[:2]))):
                    segment = [[float(p1_arr[0]), float(p1_arr[1])], 
                              [float(p2_arr[0]), float(p2_arr[1])]]
                    if bottom_circle_color not in color_groups:
                        color_groups[bottom_circle_color] = []
                    color_groups[bottom_circle_color].append(segment)
    
    if top_circle_points and len(top_circle_points) >= 2:
        line_pairs = [[top_circle_points[i], top_circle_points[i+1]] 
                      for i in range(len(top_circle_points)-1)]
        projected = project_to_side_view(line_pairs, view_direction, return_depth=False)
        for line in projected:
            if len(line) == 2:
                p1, p2 = line
                # 检查点是否有效，并确保是numpy数组
                p1_arr = np.array(p1) if not isinstance(p1, np.ndarray) else p1
                p2_arr = np.array(p2) if not isinstance(p2, np.ndarray) else p2
                # 确保是1D数组，并提取标量值
                p1_arr = np.asarray(p1_arr).flatten()
                p2_arr = np.asarray(p2_arr).flatten()
                if (len(p1_arr) >= 2 and len(p2_arr) >= 2 and
                    not np.any(np.isnan(p1_arr[:2])) and not np.any(np.isnan(p2_arr[:2]))):
                    segment = [[float(p1_arr[0]), float(p1_arr[1])], 
                              [float(p2_arr[0]), float(p2_arr[1])]]
                    if top_circle_color not in color_groups:
                        color_groups[top_circle_color] = []
                    color_groups[top_circle_color].append(segment)
    
    # 重新按颜色分组（确保颜色是元组以便作为字典键）
    # 不再清除多余的线条，直接保留所有线条
    deduplicated_color_groups = {}
    
    # 处理所有线段，直接按颜色分组，不做任何删除或特殊处理
    for color, segments in color_groups.items():
        # 确保颜色是元组（如果是列表则转换）
        color_tuple = tuple(color) if isinstance(color, (list, np.ndarray)) else color
        
        # 直接添加到分组中，保留所有线段
        if color_tuple not in deduplicated_color_groups:
            deduplicated_color_groups[color_tuple] = []
        deduplicated_color_groups[color_tuple].extend(segments)
    
    total_after = sum(len(segments) for segments in deduplicated_color_groups.values())
    print(f"  总共: {total_after} 条线段（保留所有线条，未进行任何过滤）")
    
    # 显示所有颜色的统计
    print(f"\n  所有颜色的统计:")
    for color_key, segments in deduplicated_color_groups.items():
        print(f"    颜色 {color_key}: {len(segments)} 条线段")
    
    # 保存线条坐标数据到JSON文件（便于后续操作）
    lines_data = {
        'segments_by_color': {},
        'metadata': {
            'total_colors': len(deduplicated_color_groups),
            'total_segments': sum(len(segments) for segments in deduplicated_color_groups.values()),
            'coordinate_system': 'XZ_plane',  # XZ平面投影
            'units': 'mm',
            'view_direction': view_direction
        }
    }
    
    for color, segments in deduplicated_color_groups.items():
        # 将颜色元组转换为列表（JSON不支持元组）
        color_key = list(color) if isinstance(color, tuple) else color
        # 将线段转换为可序列化的格式
        segments_data = []
        for seg in segments:
            if len(seg) == 2:
                p1, p2 = seg
                segments_data.append({
                    'p1': [float(p1[0]), float(p1[1])],  # [x, z] 在XZ投影中
                    'p2': [float(p2[0]), float(p2[1])]   # [x, z]
                })
        lines_data['segments_by_color'][str(color_key)] = segments_data
    
    # 保存到JSON文件
    data_file = output_file.replace('.png', '_lines_data.json')
    with open(data_file, 'w', encoding='utf-8') as f:
        json.dump(lines_data, f, indent=2, ensure_ascii=False)
    print(f"  线条坐标数据已保存到: {data_file}")
    print(f"  共 {len(deduplicated_color_groups)} 种颜色, {sum(len(segments) for segments in deduplicated_color_groups.values())} 条线段")
    
    # 批量绘制所有线段（使用去重后的数据）
    print(f"  批量绘制 {len(deduplicated_color_groups)} 种颜色的线段...")
    total_segments = 0
    for color, segments in deduplicated_color_groups.items():
        if segments:
            # 确保segments是正确的格式（numpy数组）
            segments_array = np.array(segments)
            # LineCollection需要segments的形状是 (N, 2, 2)，即N个线段，每个线段2个点，每个点2个坐标
            if segments_array.ndim == 3 and segments_array.shape[1] == 2 and segments_array.shape[2] == 2:
                # 对于只有少量线段的颜色，使用更粗的线条以便可见
                linewidth = 2.0 if len(segments) <= 5 else 0.8
                lc = LineCollection(segments_array, colors=color, linewidths=linewidth, alpha=0.9)
                ax.add_collection(lc)
                total_segments += len(segments)
                print(f"    绘制颜色 {color}: {len(segments)} 条线段, 线宽={linewidth}")
            else:
                print(f"  警告: segments格式不正确，形状: {segments_array.shape}")
    
    print(f"  成功绘制 {total_segments} 条边缘线段")
    
    # 自动调整坐标轴范围以适应数据
    if total_segments > 0:
        # 收集所有点的坐标（使用去重后的数据）
        all_x = []
        all_y = []
        for segments in deduplicated_color_groups.values():
            for seg in segments:
                all_x.extend([seg[0][0], seg[1][0]])
                all_y.extend([seg[0][1], seg[1][1]])
        
        if all_x and all_y:
            x_min, x_max = min(all_x), max(all_x)
            y_min, y_max = min(all_y), max(all_y)
            # 添加一些边距
            x_margin = (x_max - x_min) * 0.1 if x_max > x_min else 1.0
            y_margin = (y_max - y_min) * 0.1 if y_max > y_min else 1.0
            ax.set_xlim(x_min - x_margin, x_max + x_margin)
            ax.set_ylim(y_min - y_margin, y_max + y_margin)
            print(f"  坐标轴范围: X=[{x_min-x_margin:.2f}, {x_max+x_margin:.2f}], Z=[{y_min-y_margin:.2f}, {y_max+y_margin:.2f}]")
    
    # 设置坐标轴标签
    if view_direction == 'xz':
        ax.set_xlabel('X (mm)', fontsize=12)
        ax.set_ylabel('Z (mm)', fontsize=12)
        ax.set_title('螺旋排屑槽侧视图 (XZ投影)', fontsize=14, fontweight='bold')
    else:
        ax.set_xlabel('Y (mm)', fontsize=12)
        ax.set_ylabel('Z (mm)', fontsize=12)
        ax.set_title('螺旋排屑槽侧视图 (YZ投影)', fontsize=14, fontweight='bold')
    
    # 添加网格
    ax.grid(True, alpha=0.3, linestyle='--')
    
    # 保存图像
    print(f"保存图像到 {output_file}...")
    plt.tight_layout()
    plt.savefig(output_file, dpi=dpi, bbox_inches='tight')
    print(f"✓ 侧视图已保存到 {output_file}")
    
    plt.close()
    
    # 旋转图像：逆时针旋转90度
    try:
        from PIL import Image
        print("旋转图像（逆时针90度）...")
        img = Image.open(output_file)
        # 逆时针旋转90度 = 顺时针旋转270度
        img_rotated = img.rotate(-90, expand=True)
        img_rotated.save(output_file)
        print(f"✓ 图像已旋转并保存到 {output_file}")
    except ImportError:
        print("警告: PIL/Pillow未安装，无法旋转图像")
        print("  安装命令: pip install Pillow")
    except Exception as e:
        print(f"警告: 旋转图像时出错: {e}")
    
    return output_file


def load_and_draw_from_data(data_file, output_file='spiral_groove_from_data.png', 
                            dpi=300, figsize=(12, 8)):
    """
    从JSON数据文件加载线条坐标并绘制
    
    参数:
        data_file: JSON数据文件路径
        output_file: 输出图像文件名
        dpi: 输出分辨率
        figsize: 图像大小
    """
    print("=" * 60)
    print("从数据文件加载并绘制线条")
    print("=" * 60)
    
    # 读取JSON数据
    with open(data_file, 'r', encoding='utf-8') as f:
        lines_data = json.load(f)
    
    metadata = lines_data.get('metadata', {})
    segments_by_color = lines_data.get('segments_by_color', {})
    
    print(f"  加载数据: {len(segments_by_color)} 种颜色, {metadata.get('total_segments', 0)} 条线段")
    print(f"  坐标系: {metadata.get('coordinate_system', 'unknown')}")
    print(f"  保留所有线条，未进行任何过滤")
    
    # 设置中文字体
    setup_chinese_font()
    
    # 创建图形
    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
    ax.set_aspect('equal')
    
    # 绘制所有线段，使用原始颜色
    total_segments = 0
    
    for color_str, segments_data in segments_by_color.items():
        # 将颜色字符串转换为元组
        try:
            original_color = eval(color_str)
            if isinstance(original_color, list):
                original_color = tuple(original_color)
        except:
            # 如果无法解析颜色，使用默认颜色
            original_color = (0.5, 0.5, 0.5)  # 灰色
        
        # 转换线段数据为numpy数组格式
        segments = []
        for seg_data in segments_data:
            p1 = seg_data['p1']
            p2 = seg_data['p2']
            segments.append([[p1[0], p1[1]], [p2[0], p2[1]]])
        
        if segments:
            segments_array = np.array(segments)
            if segments_array.ndim == 3 and segments_array.shape[1] == 2 and segments_array.shape[2] == 2:
                # 对于只有少量线段的颜色，使用更粗的线条以便可见
                linewidth = 2.0 if len(segments) <= 5 else 1.0
                # 使用原始颜色
                lc = LineCollection(segments_array, colors=original_color, linewidths=linewidth, alpha=0.9)
                ax.add_collection(lc)
                total_segments += len(segments)
                print(f"    颜色 {original_color}: {len(segments)} 条线段, 线宽={linewidth}")
    
    print(f"  成功绘制 {total_segments} 条线段")
    
    # 自动调整坐标轴范围
    if total_segments > 0:
        all_x = []
        all_y = []
        for segments_data in segments_by_color.values():
            for seg_data in segments_data:
                all_x.extend([seg_data['p1'][0], seg_data['p2'][0]])
                all_y.extend([seg_data['p1'][1], seg_data['p2'][1]])
        
        if all_x and all_y:
            x_min, x_max = min(all_x), max(all_x)
            y_min, y_max = min(all_y), max(all_y)
            x_margin = (x_max - x_min) * 0.1 if x_max > x_min else 1.0
            y_margin = (y_max - y_min) * 0.1 if y_max > y_min else 1.0
            ax.set_xlim(x_min - x_margin, x_max + x_margin)
            ax.set_ylim(y_min - y_margin, y_max + y_margin)
            print(f"  坐标轴范围: X=[{x_min-x_margin:.2f}, {x_max+x_margin:.2f}], Z=[{y_min-y_margin:.2f}, {y_max+y_margin:.2f}]")
    
    # 设置坐标轴标签
    view_direction = metadata.get('view_direction', 'xz')
    if view_direction == 'xz':
        ax.set_xlabel('X (mm)', fontsize=12)
        ax.set_ylabel('Z (mm)', fontsize=12)
        ax.set_title('螺旋排屑槽侧视图 (从数据文件加载)', fontsize=14, fontweight='bold')
    else:
        ax.set_xlabel('Y (mm)', fontsize=12)
        ax.set_ylabel('Z (mm)', fontsize=12)
        ax.set_title('螺旋排屑槽侧视图 (从数据文件加载)', fontsize=14, fontweight='bold')
    
    ax.grid(True, alpha=0.3, linestyle='--')
    
    # 保存图像
    plt.tight_layout()
    plt.savefig(output_file, dpi=dpi, bbox_inches='tight')
    plt.close()
    
    print(f"✓ 图像已保存到 {output_file}")
    
    # 旋转图像：逆时针旋转90度
    try:
        from PIL import Image
        print("旋转图像（逆时针90度）...")
        img = Image.open(output_file)
        # 逆时针旋转90度 = 顺时针旋转270度
        img_rotated = img.rotate(-90, expand=True)
        img_rotated.save(output_file)
        print(f"✓ 图像已旋转并保存到 {output_file}")
    except ImportError:
        print("警告: PIL/Pillow未安装，无法旋转图像")
        print("  安装命令: pip install Pillow")
    except Exception as e:
        print(f"警告: 旋转图像时出错: {e}")
    
    return output_file


def main():
    """主函数"""
    # 导入主程序中的模型创建函数
    try:
        from spiral_groove_3d_cad import create_spiral_groove_mesh
    except ImportError:
        print("错误：无法导入 spiral_groove_3d_cad 模块")
        print("  请确保 spiral_groove_3d_cad.py 在同一目录下")
        sys.exit(1)
    
    # 使用与主程序相同的参数
    D1 = 10.0           # 刀具直径 (mm)
    L1 = 5.0            # 导向长度 (mm)
    L2 = 150.0          # 排屑槽长度 (mm)
    A1 = 40.0           # 螺旋角 (度)
    blade_height = 1.5  # 槽深 (mm)
    num_flutes = 3      # 螺旋槽数量
    
    print("=" * 60)
    print("螺旋排屑槽侧视图生成工具")
    print("=" * 60)
    print(f"参数: D1={D1}mm, L1={L1}mm, L2={L2}mm, A1={A1}°")
    print(f"      槽深={blade_height}mm, 槽数={num_flutes}")
    print("=" * 60)
    
    try:
        # 创建3D模型
        print("\n创建3D模型...")
        mesh, params = create_spiral_groove_mesh(
            D1=D1,
            L1=L1,
            L2=L2,
            A1=A1,
            blade_height=blade_height,
            num_flutes=num_flutes,
            z_resolution=400,
            theta_resolution=160
        )
        
        print(f"模型信息:")
        print(f"  顶点数: {len(mesh.vertices)}")
        print(f"  面片数: {len(mesh.faces)}")
        print(f"  边数: {len(mesh.edges)}")
        
        # 生成侧视图
        print("\n生成侧视图...")
        output_file = create_side_view(
            mesh,
            params,
            output_file='spiral_groove_side_view.png',
            view_direction='xz',
            dpi=300,
            figsize=(12, 8)
        )
        
        print("\n" + "=" * 60)
        print("侧视图生成完成！")
        print(f"输出文件: {output_file}")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

