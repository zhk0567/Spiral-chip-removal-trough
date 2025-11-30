#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
螺旋排屑槽三维CAD建模工具
直接生成带螺旋槽的圆柱体表面mesh，使用Open3D进行专业可视化
"""

import math
import numpy as np
import sys

# ==================== 常量定义 ====================
# 几何参数常量
GROOVE_WIDTH_RATIO = 0.90  # 槽宽比例（槽宽/槽间距）- 大幅增加以使峰更细（峰宽 = (1-0.90)*槽间距 = 10%）
DEPTH_MULTIPLIER = 2.5  # 槽深系数 - 大幅增加以使槽更深，峰更突出
TRANSITION_WIDTH_RATIO = 1.001  # 过渡区域宽度比例 - 极小值以使过渡极陡峭，峰极锋利
GROOVE_DEPTH_POWER = 0.05  # 槽深平滑函数指数 - 极小值以使槽底极尖锐
TRANSITION_POWER = 100  # 过渡函数指数 - 极大值以使过渡极陡峭，峰极锋利
Z_TRANSITION_POWER = 2  # Z方向过渡函数指数
# TIP_LENGTH 和 ELLIPSE_RATIO 已移除，因为顶部是螺旋槽的自然交汇点

# 可视化常量
NUM_CIRCLE_POINTS = 800  # 圆周边缘采样点数（增加以确保平滑）
NUM_SPIRAL_POINTS = 1500  # 螺旋边缘采样点数（增加以确保平滑）
LINE_RADIUS_RATIO = 0.001  # 线条半径比例（相对于模型尺寸，减小以细化线条）
TUBE_RESOLUTION = 16  # 管道截面分辨率（增加以提高平滑度）
BATCH_SIZE = 500  # 管道批处理大小
MAX_TUBES_BEFORE_BATCH = 1000  # 批处理阈值
MIN_LINE_SEGMENT_LENGTH = 0.01  # 最小线段长度（避免重复点）

# 性能优化常量
MAX_FACES_FOR_SIMPLIFICATION = 50000  # 需要简化的面片数阈值
MAX_FACES_FOR_INTERACTIVE = 10000  # 交互式模式最大面片数
Z_RESOLUTION_DEFAULT = 400  # 默认Z方向分辨率（增加以获得更平滑的表面）
THETA_RESOLUTION_DEFAULT = 160  # 默认圆周方向分辨率（增加以获得更平滑的表面）
Z_RESOLUTION_INTERACTIVE = 200  # 交互式模式Z方向分辨率
THETA_RESOLUTION_INTERACTIVE = 80  # 交互式模式圆周方向分辨率

# 边缘提取常量
Z_TOLERANCE = 0.1  # Z坐标容差
Z_SPIRAL_TOLERANCE = 0.5  # 螺旋边缘Z坐标容差
RADIUS_THRESHOLD_RATIO = 0.8  # 槽内点半径阈值比例

# 设置标准输出编码为UTF-8
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

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
    # 抑制Open3D的GLFW警告（Windows上的常见问题，不影响功能）
    import warnings
    warnings.filterwarnings('ignore', category=UserWarning, module='open3d')
    # 设置Open3D日志级别，减少警告输出
    o3d.utility.set_verbosity_level(o3d.utility.VerbosityLevel.Error)
except ImportError:
    HAS_OPEN3D = False
    print("提示：安装open3d库可以获得更好的3D可视化效果")
    print("  安装命令: pip install open3d")

try:
    import plotly.graph_objects as go
    import plotly.offline as pyo
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

try:
    import matplotlib.pyplot as plt
    import matplotlib.font_manager as fm
    from matplotlib.widgets import Slider, Button
    HAS_MATPLOTLIB = True
    
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
    
except ImportError:
    HAS_MATPLOTLIB = False


def create_spiral_groove_mesh(
    D1: float,
    L1: float,
    L2: float,
    A1: float,
    blade_height: float,
    num_flutes: int = 3,
    z_resolution: int = 300,
    theta_resolution: int = 120
):
    """
    直接生成带螺旋槽的圆柱体mesh
    
    参数:
        D1: 刀具直径 (mm)
        L1: 导向长度 (mm)
        L2: 排屑槽长度 (mm)
        A1: 螺旋角 (度)
        blade_height: 槽深 (mm)
        num_flutes: 螺旋槽数量
        z_resolution: Z方向采样点数
        theta_resolution: 圆周方向采样点数
    
    返回:
        mesh: trimesh.Trimesh对象
        params: 参数字典，用于标注
    """
    print("=" * 60)
    print("螺旋排屑槽3D建模")
    print("=" * 60)
    print(f"参数: D1={D1}mm, L1={L1}mm, L2={L2}mm, A1={A1}°, 槽深={blade_height}mm, 槽数={num_flutes}")
    
    # 计算基本参数
    radius = D1 / 2.0
    total_length = L1 + L2
    angle_rad = math.radians(A1)
    circumference = math.pi * D1
    pitch = circumference / math.tan(angle_rad)
    
    print(f"计算参数: 半径={radius:.3f}mm, 螺距={pitch:.3f}mm")
    print("生成网格点...")
    
    # 生成网格
    z_values = np.linspace(0, total_length, z_resolution)
    theta_values = np.linspace(0, 2 * math.pi, theta_resolution, endpoint=False)
    
    vertices = []
    angle_per_flute = 2 * math.pi / num_flutes
    groove_width_angle = (2 * math.pi / num_flutes) * GROOVE_WIDTH_RATIO
    
    # 生成顶点
    for z in z_values:
        for theta in theta_values:
            is_in_groove = False
            groove_depth_factor = 0.0
            
            # 检查每个螺旋槽
            # 让螺旋槽从z=0延伸到L1+L2，这样它们会在z=0处自然交汇
            for flute_idx in range(num_flutes):
                if 0 <= z <= L1 + L2:
                    # 计算螺旋线的角度
                    # 从z=0开始计算螺旋角度，这样在z=0时所有槽都会交汇
                    spiral_angle = z * 2 * math.pi / pitch
                    base_angle = flute_idx * angle_per_flute
                    groove_center_angle = base_angle + spiral_angle
                    
                    # 计算角度差
                    angle_diff = theta - groove_center_angle
                    angle_diff = math.atan2(math.sin(angle_diff), math.cos(angle_diff))
                    
                    half_width = groove_width_angle / 2
                    transition_width = half_width * TRANSITION_WIDTH_RATIO
                    
                    # 确保槽的边缘（left_angle和right_angle）也被包含在槽内，以保证侧面连续
                    # 使用稍微大一点的阈值来确保边缘顶点被包含
                    edge_tolerance = 0.001  # 边缘容差，确保边缘顶点被包含
                    
                    if abs(angle_diff) < half_width + edge_tolerance:
                        is_in_groove = True
                        # 限制depth_factor在[0, 1]范围内
                        depth_factor = min(1.0, abs(angle_diff) / half_width)
                        smooth_factor = (1.0 - math.cos(depth_factor * math.pi)) / 2.0
                        smooth_factor = smooth_factor ** GROOVE_DEPTH_POWER
                        groove_depth_factor = max(groove_depth_factor, smooth_factor)
                    elif abs(angle_diff) < transition_width + edge_tolerance:
                        is_in_groove = True
                        transition_factor = (abs(angle_diff) - half_width) / (transition_width - half_width)
                        transition_factor = max(0.0, min(1.0, transition_factor))  # 限制在[0, 1]范围内
                        smooth_factor = (1.0 - transition_factor ** TRANSITION_POWER)
                        groove_depth_factor = max(groove_depth_factor, smooth_factor)
            
            if is_in_groove:
                z_smooth = 1.0
                # 在z=0附近，让槽深度逐渐减小到0，形成自然交汇
                if z < L1 + 1.0:
                    if z < L1:
                        # z < L1时，槽深度逐渐减小，在z=0时为0
                        z_smooth = max(0, min(1, z / max(L1, 0.1)))
                        z_smooth = z_smooth ** Z_TRANSITION_POWER
                    else:
                        # L1 <= z < L1 + 1.0时，正常过渡
                        z_smooth = max(0, min(1, (z - L1) / 1.0))
                        z_smooth = z_smooth ** Z_TRANSITION_POWER
                elif z > L1 + L2 - 1.0:
                    z_smooth = max(0, min(1, (L1 + L2 - z) / 1.0))
                    z_smooth = z_smooth ** Z_TRANSITION_POWER
                
                current_radius = radius - blade_height * groove_depth_factor * z_smooth * DEPTH_MULTIPLIER
            else:
                current_radius = radius
            
            # 在z=0处，让所有顶点汇聚到中心点，形成自然交汇
            # 使用平滑函数，在z=0附近逐渐缩小半径
            if z < L1:
                # 在L1之前，让半径逐渐缩小到0，形成自然交汇
                convergence_factor = z / max(L1, 0.1)  # 归一化到[0, 1]
                convergence_factor = convergence_factor ** 1.5  # 平滑过渡
                current_radius = current_radius * convergence_factor
            
            # 生成3D坐标
            x = current_radius * math.cos(theta)
            y = current_radius * math.sin(theta)
            vertices.append([x, y, z])
    
    # 添加端面中心点（用于形成封闭的端面，确保模型是一个完整的体）
    # 下端面中心点（z=0）- 这是尖端顶点，所有下端面顶点都汇聚到这里
    vertices.append([0, 0, 0])
    bottom_tip_idx = len(vertices) - 1
    
    # 上端面中心点（z=total_length，total_length已在前面定义）
    vertices.append([0, 0, total_length])
    top_center_idx = len(vertices) - 1
    
    vertices = np.array(vertices)
    print(f"  生成了 {len(vertices)} 个顶点（包括2个端面中心点）")
    
    # 生成面片（移除槽内的面片，只保留"峰"的边缘）
    print("生成面片...")
    faces = []
    
    # 创建一个函数来检查顶点是否在槽内
    def is_vertex_in_groove(z, theta, num_flutes, angle_per_flute, groove_width_angle, L1, L2, pitch):
        """检查顶点是否在槽内"""
        # 让螺旋槽从z=0延伸到L1+L2，这样它们会在z=0处自然交汇
        if not (0 <= z <= L1 + L2):
            return False
        for flute_idx in range(num_flutes):
            # 从z=0开始计算螺旋角度
            spiral_angle = z * 2 * math.pi / pitch
            base_angle = flute_idx * angle_per_flute
            groove_center_angle = base_angle + spiral_angle
            angle_diff = theta - groove_center_angle
            angle_diff = math.atan2(math.sin(angle_diff), math.cos(angle_diff))
            half_width = groove_width_angle / 2
            transition_width = half_width * TRANSITION_WIDTH_RATIO
            if abs(angle_diff) < transition_width:
                return True
        return False
    
    for i in range(z_resolution - 1):
        for j in range(theta_resolution):
            z_curr = z_values[i]
            z_next = z_values[i + 1]
            theta_curr = theta_values[j]
            theta_next = theta_values[(j + 1) % theta_resolution]
            
            idx_curr = i * theta_resolution + j
            idx_curr_next = i * theta_resolution + (j + 1) % theta_resolution
            idx_next = (i + 1) * theta_resolution + j
            idx_next_next = (i + 1) * theta_resolution + (j + 1) % theta_resolution
            
            # 检查四个顶点是否在槽内
            in_groove_curr = is_vertex_in_groove(z_curr, theta_curr, num_flutes, angle_per_flute, groove_width_angle, L1, L2, pitch)
            in_groove_curr_next = is_vertex_in_groove(z_curr, theta_next, num_flutes, angle_per_flute, groove_width_angle, L1, L2, pitch)
            in_groove_next = is_vertex_in_groove(z_next, theta_curr, num_flutes, angle_per_flute, groove_width_angle, L1, L2, pitch)
            in_groove_next_next = is_vertex_in_groove(z_next, theta_next, num_flutes, angle_per_flute, groove_width_angle, L1, L2, pitch)
            
            # 检查是否在槽的起始端或结束端（用于连接左右"锋"边缘）
            is_at_start = abs(z_curr - 0) < 0.01 or abs(z_next - 0) < 0.01  # 起始端在z=0
            is_at_end = abs(z_curr - (L1 + L2)) < 0.01 or abs(z_next - (L1 + L2)) < 0.01
            
            # 确保所有面片都被添加，保持模型的连续性
            # 关键：在槽范围内，我们需要保留所有面片以确保模型是连续的体
            # 只移除完全在槽外的圆柱侧面（在槽的中间部分），但保留所有跨越边缘的面片
            # 槽从z=0延伸到L1+L2
            in_groove_range = (0 <= z_curr <= L1 + L2) or (0 <= z_next <= L1 + L2)
            
            if in_groove_range:
                # 在槽范围内
                # 关键：为了确保模型是连续的体（无孔洞），我们需要保留所有面片
                # 即使完全在槽外的面片也要保留，因为跳过它们会导致边界边和孔洞
                # 槽的视觉效果通过顶点位置的调整来实现（槽内的顶点半径更小），而不是通过移除面片
                # 注意：顶点顺序要确保法向量指向外部（右手定则）
                faces.append([idx_curr, idx_curr_next, idx_next])
                faces.append([idx_curr_next, idx_next_next, idx_next])
            else:
                # 在槽范围外（L1之前和L1+L2之后），保留所有面片，确保连续性
                # 注意：顶点顺序要确保法向量指向外部（右手定则）
                faces.append([idx_curr, idx_curr_next, idx_next])
                faces.append([idx_curr_next, idx_next_next, idx_next])
    
    # 添加端面（确保端面正确连接，形成封闭的整体）
    # 下端面（z=0）- 螺旋槽自然交汇点，连接圆周上的顶点到中心点
    # 注意：从外部看，下端面的法向量应该指向-Z方向（向下）
    # 所以顶点顺序应该是逆时针（从中心看）
    # 由于螺旋槽从z=0开始，在z=0处所有槽都会自然交汇到中心点
    for j in range(theta_resolution):
        idx0 = j
        idx1 = (j + 1) % theta_resolution
        # 下端面：从中心点向外连接相邻的圆周顶点（逆时针顺序，确保法向量向下）
        # 在z=0处，由于半径已经缩小到0，所有顶点都汇聚到中心点，形成自然交汇
        faces.append([bottom_tip_idx, idx0, idx1])
    
    # 上端面（z=total_length）- 连接圆周上的顶点到中心点
    # 注意：从外部看，上端面的法向量应该指向+Z方向（向上）
    # 所以顶点顺序应该是顺时针（从中心看）
    top_base = (z_resolution - 1) * theta_resolution
    for j in range(theta_resolution):
        idx0 = top_base + j
        idx1 = top_base + (j + 1) % theta_resolution
        # 上端面：从中心点向外连接相邻的圆周顶点（顺时针顺序，确保法向量向上）
        faces.append([top_center_idx, idx1, idx0])
    
    faces = np.array(faces)
    print(f"  生成了 {len(faces)} 个面片")
    
    # 创建并修复mesh
    print("修复mesh...")
    mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
    mesh.remove_unreferenced_vertices()
    mesh.process()
    
    # 检查mesh状态
    print(f"  初始状态: 封闭={mesh.is_watertight}, 体积={mesh.volume:.3f} mm³")
    
    # 确保mesh是连续的（填充所有孔洞）
    if not mesh.is_watertight:
        print("  填充孔洞以确保连续性...")
        try:
            mesh.fill_holes()
            mesh.process()
            print(f"  填充后状态: 封闭={mesh.is_watertight}, 体积={mesh.volume:.3f} mm³")
        except Exception as e:
            print(f"  填充孔洞失败: {e}")
            print("  提示: 安装networkx库可以自动填充孔洞")
            print("  安装命令: pip install networkx")
    
    # 确保mesh是封闭的（如果还不是）
    if not mesh.is_watertight:
        print("  警告: mesh仍然不是封闭的，尝试修复...")
        # 尝试修复法向量
        try:
            mesh.fix_normals()
            mesh.process()
            # 再次尝试填充孔洞
            if not mesh.is_watertight:
                try:
                    mesh.fill_holes()
                    mesh.process()
                except Exception as e:
                    print(f"  再次填充孔洞失败: {e}")
            print(f"  修复后状态: 封闭={mesh.is_watertight}, 体积={mesh.volume:.3f} mm³")
        except Exception as e:
            print(f"  修复失败: {e}")
    
    # 平滑mesh表面（使用Open3D的平滑功能）
    print("平滑mesh表面...")
    try:
        # 转换为Open3D进行平滑
        o3d_mesh_temp = o3d.geometry.TriangleMesh()
        o3d_mesh_temp.vertices = o3d.utility.Vector3dVector(mesh.vertices)
        o3d_mesh_temp.triangles = o3d.utility.Vector3iVector(mesh.faces)
        o3d_mesh_temp.compute_vertex_normals()
        
        # 使用简单平滑滤波器
        o3d_mesh_temp = o3d_mesh_temp.filter_smooth_simple(number_of_iterations=3)
        o3d_mesh_temp.compute_vertex_normals()
        
        # 转换回trimesh
        vertices_smoothed = np.asarray(o3d_mesh_temp.vertices)
        faces_smoothed = np.asarray(o3d_mesh_temp.triangles)
        mesh = trimesh.Trimesh(vertices=vertices_smoothed, faces=faces_smoothed)
        mesh.process()
        print("  已应用平滑处理")
    except Exception as e:
        print(f"  平滑处理失败: {e}，使用原始mesh")
        mesh.process()  # 重新处理以确保法向量正确
    
    print(f"  Mesh状态: 封闭={mesh.is_watertight}, 体积={mesh.volume:.3f} mm³")
    print("建模完成！\n")
    
    # 返回mesh和参数
    params = {'D1': D1, 'L1': L1, 'L2': L2, 'A1': A1, 'blade_height': blade_height, 'num_flutes': num_flutes}
    return mesh, params


def _extract_circle_edge_points(vertices, bounds, radius, z_target, num_points=NUM_CIRCLE_POINTS):
    """生成平滑的圆周边缘点（直接计算，不依赖mesh顶点）"""
    theta_circle = np.linspace(0, 2 * math.pi, num_points, endpoint=True)
    circle_points = []
    
    for theta in theta_circle:
        # 直接使用数学公式计算平滑的圆周点
        x = radius * math.cos(theta)
        y = radius * math.sin(theta)
        z = z_target
        circle_points.append([x, y, z])
    
    return circle_points


def _smooth_and_deduplicate_points(points, min_distance=MIN_LINE_SEGMENT_LENGTH):
    """
    平滑并去重点集，确保线条连续且不重叠
    返回：numpy数组或None（如果点数不足）
    """
    if points is None or len(points) < 2:
        return None
    
    points = np.array(points)
    if len(points) < 2:
        return None
    
    smoothed = [points[0]]
    
    for i in range(1, len(points)):
        # 计算与上一个点的距离
        dist = np.linalg.norm(points[i] - smoothed[-1])
        if dist >= min_distance:
            smoothed.append(points[i])
        # 如果距离太小，跳过该点（去重）
    
    # 确保首尾连接（对于闭合曲线）
    if len(smoothed) > 2:
        dist_first_last = np.linalg.norm(smoothed[-1] - smoothed[0])
        if dist_first_last < min_distance:
            # 如果首尾距离太小，移除最后一个点
            smoothed = smoothed[:-1]
    
    if len(smoothed) < 2:
        return None
    
    return np.array(smoothed)


def _extract_mesh_grid_lines(vertices, params, num_z_lines=20, num_theta_lines=16):
    """
    生成覆盖整个模型的网格线（布满整个模型表面）
    返回：
    - z_lines: 在不同Z高度的圆周线
    - theta_lines: 在不同角度的纵向线
    """
    D1 = params['D1']
    L1 = params['L1']
    L2 = params['L2']
    A1 = params['A1']
    blade_height = params.get('blade_height', 1.5)
    num_flutes = params.get('num_flutes', 3)
    
    radius = D1 / 2.0
    total_length = L1 + L2
    angle_rad = math.radians(A1)
    circumference = math.pi * D1
    pitch = circumference / math.tan(angle_rad)
    angle_per_flute = 2 * math.pi / num_flutes
    groove_width_angle = (2 * math.pi / num_flutes) * GROOVE_WIDTH_RATIO
    half_width = groove_width_angle / 2
    bottom_radius = radius - blade_height * DEPTH_MULTIPLIER
    
    grid_lines = []
    grid_colors = []
    
    # 1. 生成Z方向的圆周线（在不同高度）
    # 避免在端面位置生成线（端面已有专门的圆周线）
    z_start = 0.1  # 避免在z=0处生成线
    z_end = total_length - 0.1  # 避免在z=total_length处生成线
    z_values_grid = np.linspace(z_start, z_end, num_z_lines)
    for z in z_values_grid:
        circle_points = []
        theta_circle = np.linspace(0, 2 * math.pi, NUM_CIRCLE_POINTS, endpoint=True)
        
        for theta in theta_circle:
            # 计算该位置的实际半径（考虑槽的影响）
            is_in_groove = False
            groove_depth_factor = 0.0
            
            if L1 <= z <= L1 + L2:
                for flute_idx in range(num_flutes):
                    spiral_angle = (z - L1) * 2 * math.pi / pitch
                    base_angle = flute_idx * angle_per_flute
                    groove_center_angle = base_angle + spiral_angle
                    angle_diff = theta - groove_center_angle
                    angle_diff = math.atan2(math.sin(angle_diff), math.cos(angle_diff))
                    
                    transition_width = half_width * TRANSITION_WIDTH_RATIO
                    edge_tolerance = 0.001
                    
                    if abs(angle_diff) < half_width + edge_tolerance:
                        is_in_groove = True
                        depth_factor = min(1.0, abs(angle_diff) / half_width)
                        smooth_factor = (1.0 - math.cos(depth_factor * math.pi)) / 2.0
                        smooth_factor = smooth_factor ** GROOVE_DEPTH_POWER
                        groove_depth_factor = max(groove_depth_factor, smooth_factor)
                    elif abs(angle_diff) < transition_width + edge_tolerance:
                        is_in_groove = True
                        transition_factor = max(0.0, min(1.0, (abs(angle_diff) - half_width) / (transition_width - half_width)))
                        smooth_factor = (1.0 - transition_factor ** TRANSITION_POWER)
                        groove_depth_factor = max(groove_depth_factor, smooth_factor)
            
            if is_in_groove:
                z_smooth = 1.0
                if z < L1 + 1.0:
                    z_smooth = max(0, min(1, (z - L1) / 1.0))
                    z_smooth = z_smooth ** Z_TRANSITION_POWER
                elif z > L1 + L2 - 1.0:
                    z_smooth = max(0, min(1, (L1 + L2 - z) / 1.0))
                    z_smooth = z_smooth ** Z_TRANSITION_POWER
                current_radius = radius - blade_height * groove_depth_factor * z_smooth * DEPTH_MULTIPLIER
            else:
                current_radius = radius
            
            x = current_radius * math.cos(theta)
            y = current_radius * math.sin(theta)
            circle_points.append([x, y, z])
        
        # 平滑并去重圆周线点
        circle_points = _smooth_and_deduplicate_points(circle_points)
        if circle_points is not None:
            grid_lines.append(circle_points)
            # 使用灰色系区分网格线（与边缘线明显区分）
            # 从浅灰（底部）到中灰（顶部）
            color_factor = z / total_length
            gray_value = 0.3 + color_factor * 0.3  # 0.3到0.6的灰色
            grid_colors.append([gray_value, gray_value, gray_value])
    
    # 2. 生成theta方向的纵向线（在不同角度）
    theta_values_grid = np.linspace(0, 2 * math.pi, num_theta_lines, endpoint=False)
    z_values_long = np.linspace(0, total_length, NUM_SPIRAL_POINTS)
    
    for theta in theta_values_grid:
        long_line_points = []
        for z in z_values_long:
            # 计算该位置的实际半径（考虑槽的影响）
            is_in_groove = False
            groove_depth_factor = 0.0
            
            if L1 <= z <= L1 + L2:
                for flute_idx in range(num_flutes):
                    spiral_angle = (z - L1) * 2 * math.pi / pitch
                    base_angle = flute_idx * angle_per_flute
                    groove_center_angle = base_angle + spiral_angle
                    angle_diff = theta - groove_center_angle
                    angle_diff = math.atan2(math.sin(angle_diff), math.cos(angle_diff))
                    
                    transition_width = half_width * TRANSITION_WIDTH_RATIO
                    edge_tolerance = 0.001
                    
                    if abs(angle_diff) < half_width + edge_tolerance:
                        is_in_groove = True
                        depth_factor = min(1.0, abs(angle_diff) / half_width)
                        smooth_factor = (1.0 - math.cos(depth_factor * math.pi)) / 2.0
                        smooth_factor = smooth_factor ** GROOVE_DEPTH_POWER
                        groove_depth_factor = max(groove_depth_factor, smooth_factor)
                    elif abs(angle_diff) < transition_width + edge_tolerance:
                        is_in_groove = True
                        transition_factor = max(0.0, min(1.0, (abs(angle_diff) - half_width) / (transition_width - half_width)))
                        smooth_factor = (1.0 - transition_factor ** TRANSITION_POWER)
                        groove_depth_factor = max(groove_depth_factor, smooth_factor)
            
            if is_in_groove:
                z_smooth = 1.0
                if z < L1 + 1.0:
                    z_smooth = max(0, min(1, (z - L1) / 1.0))
                    z_smooth = z_smooth ** Z_TRANSITION_POWER
                elif z > L1 + L2 - 1.0:
                    z_smooth = max(0, min(1, (L1 + L2 - z) / 1.0))
                    z_smooth = z_smooth ** Z_TRANSITION_POWER
                current_radius = radius - blade_height * groove_depth_factor * z_smooth * DEPTH_MULTIPLIER
            else:
                current_radius = radius
            
            x = current_radius * math.cos(theta)
            y = current_radius * math.sin(theta)
            long_line_points.append([x, y, z])
        
        # 平滑并去重纵向线点
        long_line_points = _smooth_and_deduplicate_points(long_line_points)
        if long_line_points is not None:
            grid_lines.append(long_line_points)
            # 使用深灰色系区分纵向网格线（与边缘线明显区分）
            # 根据角度变化，但保持在灰色范围内
            theta_normalized = theta / (2 * math.pi)
            gray_base = 0.4
            gray_variation = 0.2
            gray_value = gray_base + theta_normalized * gray_variation
            grid_colors.append([gray_value, gray_value, gray_value])
    
    return grid_lines, grid_colors


def _extract_spiral_edge_points(vertices, params, num_points=NUM_SPIRAL_POINTS):
    """
    生成平滑的螺旋槽边缘点（直接计算，不依赖mesh顶点）
    返回多种类型的边缘线：
    1. 槽与圆柱外边缘的交界线（槽的边缘，峰的位置）
    2. 槽的侧面边缘线（从侧壁到外边缘）
    3. 槽的"锋"边缘线（过渡区域）
    4. 槽的起始端和结束端边缘线
    注意：不包含底部边缘线，以实现平滑过渡
    """
    D1 = params['D1']
    L1 = params['L1']
    L2 = params['L2']
    A1 = params['A1']
    blade_height = params.get('blade_height', 1.5)
    num_flutes = params.get('num_flutes', 3)
    
    radius = D1 / 2.0
    angle_rad = math.radians(A1)
    circumference = math.pi * D1
    pitch = circumference / math.tan(angle_rad)
    angle_per_flute = 2 * math.pi / num_flutes
    groove_width_angle = (2 * math.pi / num_flutes) * GROOVE_WIDTH_RATIO
    half_width = groove_width_angle / 2
    bottom_radius = radius - blade_height * DEPTH_MULTIPLIER
    
    z_spiral = np.linspace(L1, L1 + L2, num_points)
    spiral_edge_points = []
    
    for flute_idx in range(num_flutes):
        base_angle = flute_idx * angle_per_flute
        
        # 1. 槽与圆柱外边缘的交界线（槽的边缘，在圆柱外边缘上）
        outer_left_points = []
        outer_right_points = []
        
        # 2. 槽的侧面边缘线（从底部到外边缘的垂直连接线）
        side_left_points = []  # 左边缘的侧面线
        side_right_points = []  # 右边缘的侧面线
        
        # 3. 槽的"锋"边缘线（过渡区域的边缘，在transition_width位置）
        blade_left_points = []  # 左边缘的锋线
        blade_right_points = []  # 右边缘的锋线
        
        transition_width = half_width * TRANSITION_WIDTH_RATIO
        
        for z in z_spiral:
            # 计算螺旋角度
            spiral_angle = (z - L1) * 2 * math.pi / pitch
            groove_center_angle = base_angle + spiral_angle
            
            # 计算槽的边缘角度（用于其他边缘线）
            left_angle = groove_center_angle - half_width
            right_angle = groove_center_angle + half_width
            
            # 槽与圆柱外边缘的交界线（"峰"的位置）
            # 峰应该在两个槽之间，即不在槽内的位置
            # 对于槽1，峰在槽1的右边缘和槽2的左边缘之间
            # 峰的位置：在槽的右边缘之后，下一个槽的左边缘之前
            # 计算峰的角度：在槽的右边缘（right_angle）之后，下一个槽的左边缘之前
            peak_angle = groove_center_angle + half_width + (angle_per_flute - groove_width_angle) / 2
            # 确保峰的角度在正确范围内
            peak_angle = math.atan2(math.sin(peak_angle), math.cos(peak_angle))
            # 峰在圆柱外边缘上，半径就是原始半径
            x = radius * math.cos(peak_angle)
            y = radius * math.sin(peak_angle)
            outer_left_points.append([x, y, z])
            outer_right_points.append([x, y, z])  # 峰线在峰的中心位置
            
            # 槽的侧面边缘线（从底部到外边缘的垂直连接线）
            # 注意：槽底部应该平滑过渡，不绘制底部边缘线
            # 侧面线从槽的侧壁开始，不包含底部点
            # 左边缘的侧面：在槽的侧壁位置（不包含底部）
            # 右边缘的侧面：在槽的侧壁位置（不包含底部）
            # 这些线将在槽的侧壁和外边缘之间，不绘制底部线以实现平滑过渡
            
            # 槽的"锋"边缘线（在transition_width位置，这是槽和圆柱外边缘的过渡区域）
            # 左边缘的锋：在transition_width位置
            blade_left_angle = groove_center_angle - transition_width
            # 锋的位置应该在过渡区域，半径在底部和外边缘之间
            blade_radius = radius - blade_height * 0.3 * DEPTH_MULTIPLIER  # 锋的位置在30%深度处
            x = blade_radius * math.cos(blade_left_angle)
            y = blade_radius * math.sin(blade_left_angle)
            blade_left_points.append([x, y, z])
            
            # 右边缘的锋：在transition_width位置
            blade_right_angle = groove_center_angle + transition_width
            x = blade_radius * math.cos(blade_right_angle)
            y = blade_radius * math.sin(blade_right_angle)
            blade_right_points.append([x, y, z])
        
        # 4. 槽的起始端和结束端边缘线
        # 起始端（L1位置）
        start_spiral_angle = 0.0
        start_groove_center_angle = base_angle + start_spiral_angle
        start_left_angle = start_groove_center_angle - half_width
        start_right_angle = start_groove_center_angle + half_width
        
        start_left_bottom = [bottom_radius * math.cos(start_left_angle), bottom_radius * math.sin(start_left_angle), L1]
        start_left_outer = [radius * math.cos(start_left_angle), radius * math.sin(start_left_angle), L1]
        start_right_bottom = [bottom_radius * math.cos(start_right_angle), bottom_radius * math.sin(start_right_angle), L1]
        start_right_outer = [radius * math.cos(start_right_angle), radius * math.sin(start_right_angle), L1]
        
        # 结束端（L1+L2位置）
        end_spiral_angle = L2 * 2 * math.pi / pitch
        end_groove_center_angle = base_angle + end_spiral_angle
        end_left_angle = end_groove_center_angle - half_width
        end_right_angle = end_groove_center_angle + half_width
        
        end_left_bottom = [bottom_radius * math.cos(end_left_angle), bottom_radius * math.sin(end_left_angle), L1 + L2]
        end_left_outer = [radius * math.cos(end_left_angle), radius * math.sin(end_left_angle), L1 + L2]
        end_right_bottom = [bottom_radius * math.cos(end_right_angle), bottom_radius * math.sin(end_right_angle), L1 + L2]
        end_right_outer = [radius * math.cos(end_right_angle), radius * math.sin(end_right_angle), L1 + L2]
        
        # 平滑并去重所有边缘线点
        # 注意：不添加底部边缘线，以实现平滑过渡
        outer_left_points = _smooth_and_deduplicate_points(outer_left_points)
        outer_right_points = _smooth_and_deduplicate_points(outer_right_points)
        side_left_points = _smooth_and_deduplicate_points(side_left_points)
        side_right_points = _smooth_and_deduplicate_points(side_right_points)
        blade_left_points = _smooth_and_deduplicate_points(blade_left_points)
        blade_right_points = _smooth_and_deduplicate_points(blade_right_points)
        
        # 不添加槽的底部线，以实现平滑过渡
        
        # 添加槽与圆柱外边缘的交界线
        if outer_left_points is not None:
            spiral_edge_points.append(outer_left_points)
        if outer_right_points is not None:
            spiral_edge_points.append(outer_right_points)
        
        # 添加槽的侧面边缘线
        if side_left_points is not None:
            spiral_edge_points.append(side_left_points)
        if side_right_points is not None:
            spiral_edge_points.append(side_right_points)
        
        # 添加槽的"锋"边缘线
        if blade_left_points is not None:
            spiral_edge_points.append(blade_left_points)
        if blade_right_points is not None:
            spiral_edge_points.append(blade_right_points)
        
        # 添加槽的起始端边缘线
        spiral_edge_points.append([start_left_bottom, start_left_outer])  # 起始端左边缘
        spiral_edge_points.append([start_right_bottom, start_right_outer])  # 起始端右边缘
        
        # 添加槽的结束端边缘线
        spiral_edge_points.append([end_left_bottom, end_left_outer])  # 结束端左边缘
        spiral_edge_points.append([end_right_bottom, end_right_outer])  # 结束端右边缘
        
        # 5. 槽的起始端和结束端的底部圆周和外边缘圆周
        # 起始端底部圆周（在L1位置，从左边缘到右边缘的底部圆周）
        start_bottom_circle = []
        num_circle_segments = NUM_CIRCLE_POINTS // 4  # 槽宽对应的圆周段数
        for i in range(num_circle_segments + 1):
            angle_frac = i / num_circle_segments
            angle = start_left_angle + (start_right_angle - start_left_angle) * angle_frac
            # 归一化角度
            angle = math.atan2(math.sin(angle), math.cos(angle))
            x = bottom_radius * math.cos(angle)
            y = bottom_radius * math.sin(angle)
            start_bottom_circle.append([x, y, L1])
        
        # 起始端外边缘圆周（在L1位置，从左边缘到右边缘的外边缘圆周）
        start_outer_circle = []
        for i in range(num_circle_segments + 1):
            angle_frac = i / num_circle_segments
            angle = start_left_angle + (start_right_angle - start_left_angle) * angle_frac
            angle = math.atan2(math.sin(angle), math.cos(angle))
            x = radius * math.cos(angle)
            y = radius * math.sin(angle)
            start_outer_circle.append([x, y, L1])
        
        # 结束端底部圆周（在L1+L2位置，从左边缘到右边缘的底部圆周）
        end_bottom_circle = []
        for i in range(num_circle_segments + 1):
            angle_frac = i / num_circle_segments
            angle = end_left_angle + (end_right_angle - end_left_angle) * angle_frac
            angle = math.atan2(math.sin(angle), math.cos(angle))
            x = bottom_radius * math.cos(angle)
            y = bottom_radius * math.sin(angle)
            end_bottom_circle.append([x, y, L1 + L2])
        
        # 结束端外边缘圆周（在L1+L2位置，从左边缘到右边缘的外边缘圆周）
        end_outer_circle = []
        for i in range(num_circle_segments + 1):
            angle_frac = i / num_circle_segments
            angle = end_left_angle + (end_right_angle - end_left_angle) * angle_frac
            angle = math.atan2(math.sin(angle), math.cos(angle))
            x = radius * math.cos(angle)
            y = radius * math.sin(angle)
            end_outer_circle.append([x, y, L1 + L2])
        
        # 添加起始端和结束端的圆周
        spiral_edge_points.append(start_bottom_circle)
        spiral_edge_points.append(start_outer_circle)
        spiral_edge_points.append(end_bottom_circle)
        spiral_edge_points.append(end_outer_circle)
    
    return spiral_edge_points


def _create_tube_mesh(p1, p2, line_radius, color=None, resolution=TUBE_RESOLUTION):
    """创建连接两个点的管道mesh"""
    direction = p2 - p1
    length = np.linalg.norm(direction)
    
    if length < 1e-6:
        return None
    
    direction = direction / length
    cylinder = o3d.geometry.TriangleMesh.create_cylinder(
        radius=line_radius, height=length, resolution=resolution
    )
    
    z_axis = np.array([0, 0, 1])
    if not np.allclose(direction, z_axis) and not np.allclose(direction, -z_axis):
        rotation_axis = np.cross(z_axis, direction)
        rotation_axis_norm = np.linalg.norm(rotation_axis)
        if rotation_axis_norm > 1e-6:
            rotation_axis = rotation_axis / rotation_axis_norm
            rotation_angle = np.arccos(np.clip(np.dot(z_axis, direction), -1, 1))
            R = o3d.geometry.get_rotation_matrix_from_axis_angle(rotation_axis * rotation_angle)
            cylinder.rotate(R, center=[0, 0, 0])
    
    center = (p1 + p2) / 2
    cylinder.translate(center)
    
    # 如果没有指定颜色，使用黑色
    if color is None:
        color = [0.0, 0.0, 0.0]
    cylinder.paint_uniform_color(color)
    
    return cylinder


def visualize_open3d(mesh, params=None, interactive=True):
    """使用Open3D进行3D可视化（推荐）"""
    if not HAS_OPEN3D:
        return False
    
    print("使用Open3D进行3D可视化...")
    
    # 如果没有提供参数，尝试从mesh估算
    if params is None:
        bounds = mesh.bounds
        extent = bounds[1] - bounds[0]
        params = {
            'D1': extent[0] * 2,
            'L1': 5.0,
            'L2': extent[2] - 5.0,
            'A1': 30.0
        }
    
    try:
        # 转换为Open3D mesh
        o3d_mesh = o3d.geometry.TriangleMesh()
        o3d_mesh.vertices = o3d.utility.Vector3dVector(mesh.vertices)
        o3d_mesh.triangles = o3d.utility.Vector3iVector(mesh.faces)
        
        # 计算法向量（使用平滑法向量以获得平滑着色）
        o3d_mesh.compute_vertex_normals(normalized=True)
        o3d_mesh.compute_triangle_normals(normalized=True)
        
        # 设置颜色
        o3d_mesh.paint_uniform_color([0.7, 0.8, 1.0])
        
        # 性能优化：如果面片太多则简化
        if len(mesh.faces) > MAX_FACES_FOR_SIMPLIFICATION:
            print("  简化mesh以提高性能...")
            o3d_mesh = o3d_mesh.simplify_quadric_decimation(target_number_of_triangles=MAX_FACES_FOR_SIMPLIFICATION)
            o3d_mesh.compute_vertex_normals()
        
        if interactive:
            # 先获取参数，用于窗口标题
            D1 = params['D1']
            L1 = params['L1']
            L2 = params['L2']
            A1 = params['A1']
            
            print("\n" + "=" * 60)
            print("Open3D交互式3D视图")
            print("操作: 左键旋转 | 滚轮缩放 | 右键平移 | Q/关闭退出")
            print("=" * 60)
            
            # 创建窗口，标题包含参数信息
            param_title = f"螺旋排屑槽3D模型 - D1={D1:.1f}mm L1={L1:.1f}mm L2={L2:.1f}mm A1={A1:.1f}°"
            vis = o3d.visualization.Visualizer()
            # 创建窗口，添加错误处理以避免GLFW警告
            try:
                vis.create_window(window_name=param_title, width=1200, height=800)
            except Exception as e:
                # 如果创建窗口失败，尝试使用默认设置
                print(f"  警告: 创建窗口时出现问题: {e}")
                vis.create_window(window_name=param_title, width=1200, height=800, visible=True)
            vis.add_geometry(o3d_mesh)
            
            # 添加边缘描边（从mesh动态提取边缘，不硬编码参数）
            print("  添加关键边缘描边...")
            try:
                vertices = mesh.vertices
                bounds = mesh.bounds
                radius = D1 / 2.0
                
                # 提取边缘点
                # 下端面：由于是螺旋槽的自然交汇点（z=0处半径已经为0），不提取z=0的圆周
                # 提取z=L1附近的圆周作为下端面的参考（如果L1>0）
                bottom_z = max(L1 * 0.5, bounds[0][2] + 0.1) if L1 > 0 else bounds[0][2] + 0.1
                bottom_circle_points = _extract_circle_edge_points(vertices, bounds, radius, bottom_z) if bottom_z > bounds[0][2] else None
                top_circle_points = _extract_circle_edge_points(vertices, bounds, radius, bounds[1][2])
                spiral_edge_points = _extract_spiral_edge_points(vertices, params)
                
                # 提取网格线（布满整个模型）- 已禁用，去除灰色网格线
                # print("  生成网格线（布满整个模型）...")
                # grid_lines, grid_colors = _extract_mesh_grid_lines(vertices, params, num_z_lines=30, num_theta_lines=24)
                grid_lines = []
                grid_colors = []
                
                # 定义颜色方案 - 使用鲜明对比的颜色区分不同类型
                # 下端面圆周：深蓝色（明显区分）
                bottom_circle_color = [0.0, 0.0, 1.0]
                # 上端面圆周：深绿色（明显区分）
                top_circle_color = [0.0, 1.0, 0.0]
                # 螺旋槽边缘：每个槽用不同颜色，每种类型用明显不同的颜色
                # 16条线：0=底部左, 1=底部右, 2=外边缘左(峰), 3=外边缘右(峰), 4=侧面左, 5=侧面右, 6=锋左, 7=锋右,
                #         8=起始端左, 9=起始端右, 10=结束端左, 11=结束端右, 12=起始端底部圆周, 13=起始端外边缘圆周, 14=结束端底部圆周, 15=结束端外边缘圆周
                spiral_colors = [
                    # 槽1：使用红色系
                    # 底部：鲜红色/深红色
                    # 峰（外边缘）：亮黄色/金黄色（突出显示）
                    # 侧面：粉红色/浅粉红
                    # 锋：橙色/深橙色
                    # 起始/结束端：橙红色/深橙红
                    # 圆周：黄色/深黄色
                    [[1.0, 0.0, 0.0], [0.7, 0.0, 0.0],  # 底部：鲜红/深红
                     [1.0, 1.0, 0.0], [1.0, 0.8, 0.0],  # 峰（外边缘）：亮黄/金黄
                     [1.0, 0.6, 0.8], [0.9, 0.4, 0.6],  # 侧面：粉红/浅粉红
                     [1.0, 0.5, 0.0], [0.8, 0.4, 0.0],  # 锋：橙色/深橙
                     [1.0, 0.3, 0.0], [0.7, 0.2, 0.0],  # 起始/结束端：橙红/深橙红
                     [1.0, 1.0, 0.3], [1.0, 0.9, 0.2],  # 圆周：黄色/深黄色
                     [1.0, 1.0, 0.3], [1.0, 0.9, 0.2]],
                    # 槽2：使用蓝色系
                    # 峰（外边缘）：青色/亮青色（突出显示）
                    # 侧面：天蓝色/浅天蓝
                    # 锋：青蓝色/深青蓝
                    # 起始/结束端：蓝紫色/深蓝紫
                    # 圆周：青色/深青色
                    [[0.0, 1.0, 1.0], [0.0, 0.9, 0.9],  # 峰（外边缘）：青色/亮青
                     [0.5, 0.7, 1.0], [0.3, 0.5, 0.9],  # 侧面：天蓝/浅天蓝
                     [0.0, 0.6, 1.0], [0.0, 0.5, 0.8],  # 锋：青蓝/深青蓝
                     [0.3, 0.0, 1.0], [0.2, 0.0, 0.7],  # 起始/结束端：蓝紫/深蓝紫
                     [0.0, 1.0, 0.8], [0.0, 0.9, 0.7],  # 圆周：青色/深青色
                     [0.0, 1.0, 0.8], [0.0, 0.9, 0.7]],
                    # 槽3：使用绿色系
                    # 峰（外边缘）：黄绿色/亮黄绿（突出显示）
                    # 侧面：浅绿色/浅绿
                    # 锋：草绿色/深草绿
                    # 起始/结束端：绿黄色/深绿黄
                    # 圆周：黄绿色/深黄绿
                    [[0.7, 1.0, 0.0], [0.6, 0.9, 0.0],  # 峰（外边缘）：黄绿/亮黄绿
                     [0.6, 1.0, 0.6], [0.4, 0.9, 0.4],  # 侧面：浅绿/浅绿
                     [0.3, 0.8, 0.0], [0.2, 0.6, 0.0],  # 锋：草绿/深草绿
                     [0.5, 0.8, 0.0], [0.4, 0.6, 0.0],  # 起始/结束端：绿黄/深绿黄
                     [0.7, 1.0, 0.3], [0.6, 0.9, 0.2],  # 圆周：黄绿/深黄绿
                     [0.7, 1.0, 0.3], [0.6, 0.9, 0.2]],
                    # 槽4：使用紫色系
                    # 峰（外边缘）：粉紫色/亮粉紫（突出显示）
                    # 侧面：浅紫色/浅紫
                    # 锋：紫红色/深紫红
                    # 起始/结束端：紫蓝色/深紫蓝
                    # 圆周：粉紫色/深粉紫
                    [[1.0, 0.5, 1.0], [0.9, 0.4, 0.9],  # 峰（外边缘）：粉紫/亮粉紫
                     [0.9, 0.6, 1.0], [0.7, 0.4, 0.9],  # 侧面：浅紫/浅紫
                     [0.8, 0.2, 1.0], [0.6, 0.1, 0.8],  # 锋：紫红/深紫红
                     [0.6, 0.0, 1.0], [0.4, 0.0, 0.7],  # 起始/结束端：紫蓝/深紫蓝
                     [1.0, 0.6, 0.8], [0.9, 0.5, 0.7],  # 圆周：粉紫/深粉紫
                     [1.0, 0.6, 0.8], [0.9, 0.5, 0.7]],
                ]
                
                # 收集所有有效的边缘点列表和对应的颜色（包含所有边缘，不过滤）
                edge_data = []  # [(curve_points, color), ...]
                
                # 添加端面圆周
                if bottom_circle_points and len(bottom_circle_points) >= 2:
                    edge_data.append((bottom_circle_points, bottom_circle_color))
                if top_circle_points and len(top_circle_points) >= 2:
                    edge_data.append((top_circle_points, top_circle_color))
                
                # 添加所有螺旋槽边缘线（不进行颜色过滤，显示所有边缘）
                num_flutes = params.get('num_flutes', 3)
                # 每个槽最多有16种边缘线类型
                edges_per_flute = 16
                # 定义边缘线类型到颜色索引的映射（按添加顺序）
                # 0=底部左, 1=底部右, 2=外边缘左(峰), 3=外边缘右(峰), 4=侧面左, 5=侧面右, 
                # 6=锋左, 7=锋右, 8=起始端左, 9=起始端右, 10=结束端左, 11=结束端右,
                # 12=起始端底部圆周, 13=起始端外边缘圆周, 14=结束端底部圆周, 15=结束端外边缘圆周
                
                edge_idx_in_flute = 0
                current_flute = 0
                
                for spiral_edge in spiral_edge_points:
                    if spiral_edge is not None and len(spiral_edge) >= 2:
                        # 计算当前边缘线属于哪个槽和哪种类型
                        if edge_idx_in_flute >= edges_per_flute:
                            # 移动到下一个槽
                            edge_idx_in_flute = 0
                            current_flute += 1
                        
                        # 确保edge_type在有效范围内（0-15）
                        edge_type = min(edge_idx_in_flute, edges_per_flute - 1)
                        
                        # 获取颜色（确保索引安全）
                        flute_color_idx = current_flute % len(spiral_colors)
                        if flute_color_idx < len(spiral_colors) and edge_type < len(spiral_colors[flute_color_idx]):
                            color = spiral_colors[flute_color_idx][edge_type]
                        else:
                            # 如果超出范围，使用默认颜色（红色）
                            color = [1.0, 0.0, 0.0]
                        
                        # 添加边缘线
                        edge_data.append((spiral_edge, color))
                        edge_idx_in_flute += 1
                
                # 添加网格线（布满整个模型）- 已禁用，去除灰色网格线
                # for grid_line, grid_color in zip(grid_lines, grid_colors):
                #     if grid_line is not None and len(grid_line) >= 2:
                #         edge_data.append((grid_line, grid_color))
                
                print(f"  提取到 {len(edge_data)} 条边缘线")
                print(f"    - 下端面圆周: {len(bottom_circle_points) if bottom_circle_points else 0} 个点 (蓝色)")
                print(f"    - 上端面圆周: {len(top_circle_points) if top_circle_points else 0} 个点 (绿色)")
                print(f"    - 螺旋槽边缘: {len(spiral_edge_points)} 条螺旋线 (不同颜色)")
                print(f"    - 网格线: {len(grid_lines)} 条 (圆周线+纵向线，不同颜色)")
                
                if edge_data:
                    print("  创建平滑粗边缘线...")
                    extent_mesh = bounds[1] - bounds[0]
                    line_radius = max(extent_mesh) * LINE_RADIUS_RATIO
                    
                    all_tube_meshes = []
                    seen_segments = set()  # 用于检测重复线段
                    
                    for curve_points, color in edge_data:
                        if len(curve_points) < 2:
                            continue
                        
                        curve_points = np.array(curve_points)
                        # 确保曲线点已平滑和去重
                        curve_points = _smooth_and_deduplicate_points(curve_points)
                        
                        if len(curve_points) < 2:
                            continue
                        
                        for i in range(len(curve_points) - 1):
                            p1 = curve_points[i]
                            p2 = curve_points[i + 1]
                            
                            # 检查线段长度（避免重复点）
                            segment_length = np.linalg.norm(p2 - p1)
                            if segment_length < MIN_LINE_SEGMENT_LENGTH:
                                continue
                            
                            # 生成线段唯一标识（用于去重）
                            # 使用四舍五入到小数点后6位来避免浮点误差
                            seg_id = (
                                round(float(p1[0]), 6), round(float(p1[1]), 6), round(float(p1[2]), 6),
                                round(float(p2[0]), 6), round(float(p2[1]), 6), round(float(p2[2]), 6)
                            )
                            seg_id_reverse = (
                                round(float(p2[0]), 6), round(float(p2[1]), 6), round(float(p2[2]), 6),
                                round(float(p1[0]), 6), round(float(p1[1]), 6), round(float(p1[2]), 6)
                            )
                            
                            # 检查是否已存在相同的线段（避免重叠）
                            if seg_id in seen_segments or seg_id_reverse in seen_segments:
                                continue
                            
                            seen_segments.add(seg_id)
                            
                            tube = _create_tube_mesh(p1, p2, line_radius, color=color)
                            if tube is not None:
                                all_tube_meshes.append(tube)
                    
                    print(f"  创建了 {len(all_tube_meshes)} 个管道段")
                    
                    if all_tube_meshes:
                        print(f"  准备添加 {len(all_tube_meshes)} 个管道段...")
                        
                        if len(all_tube_meshes) > MAX_TUBES_BEFORE_BATCH:
                            print(f"  管道数量较多({len(all_tube_meshes)})，分批添加...")
                            for i in range(0, len(all_tube_meshes), BATCH_SIZE):
                                batch = all_tube_meshes[i:i+BATCH_SIZE]
                                if len(batch) > 0:
                                    combined_mesh = batch[0]
                                    for mesh_item in batch[1:]:
                                        combined_mesh += mesh_item
                                    vis.add_geometry(combined_mesh)
                                    print(f"    已添加批次 {i//BATCH_SIZE + 1}，包含 {len(batch)} 个管道段")
                        else:
                            # 逐个添加管道，确保所有边缘线都显示
                            for i, tube_mesh in enumerate(all_tube_meshes):
                                vis.add_geometry(tube_mesh)
                            print(f"  已逐个添加 {len(all_tube_meshes)} 个管道段")
                        
                        print(f"  已添加平滑粗边缘线（所有边缘，不同颜色）")
                        print(f"    - 总管道段数: {len(all_tube_meshes)}")
                        print(f"    - 线条半径: {line_radius:.4f}mm")
                        print(f"    - 颜色说明: 下端面(蓝色), 上端面(绿色), 螺旋槽边缘(多种颜色区分)")
                        print(f"    - 每个槽有17条边缘线，使用不同颜色区分")
                    else:
                        print("  警告：未创建任何管道段")
                else:
                    print("  未找到关键边缘")
            except Exception as e:
                print(f"  提取关键边缘时出错: {e}")
                import traceback
                traceback.print_exc()
                print("  跳过边缘描边")
            
            # 获取mesh的边界和中心
            bounds = o3d_mesh.get_axis_aligned_bounding_box()
            center = bounds.get_center()
            extent = bounds.get_extent()
            
            # 优化渲染选项（确保平滑着色）
            render_option = vis.get_render_option()
            render_option.mesh_show_back_face = True
            render_option.mesh_show_wireframe = False
            # 平滑着色（如果支持）
            try:
                render_option.mesh_shade_option = o3d.visualization.MeshShadeOption.SmoothShade
            except AttributeError:
                # 如果SmoothShade不可用，使用默认着色
                pass
            render_option.background_color = np.array([0.95, 0.95, 0.95])  # 浅灰背景
            
            # 设置视角为XZ正方向（从Y轴正方向看）
            ctr = vis.get_view_control()
            
            # 相机位置：在Y轴正方向，看向原点
            camera_distance = max(extent) * 2.0
            camera_pos = np.array([center[0], center[1] + camera_distance, center[2]])
            look_at = center
            up = np.array([0, 0, 1])  # Z轴向上（XZ平面中Z是垂直方向）
            
            # 设置相机参数
            ctr.set_lookat(look_at)
            ctr.set_up(up)
            ctr.set_front(camera_pos - look_at)
            ctr.set_zoom(0.8)
            
            # 保存front视图（向左旋转90度）
            print("\n保存front视图（向左旋转90度，高清晰度）...")
            bounds = mesh.bounds
            center = mesh.centroid
            extent = bounds[1] - bounds[0]
            max_extent = np.max(extent)
            
            # 设置高分辨率渲染（确保平滑着色）
            render_option = vis.get_render_option()
            render_option.mesh_show_back_face = False
            render_option.mesh_show_wireframe = False
            # 平滑着色（如果支持）
            try:
                render_option.mesh_shade_option = o3d.visualization.MeshShadeOption.SmoothShade
            except AttributeError:
                # 如果SmoothShade不可用，使用默认着色
                pass
            render_option.point_size = 3.0
            render_option.line_width = 2.0
            
            # 前视图（从+X看），然后向左旋转90度（从+Y看）
            ctr = vis.get_view_control()
            look_at = center
            # 先设置到+X方向（前视图）
            ctr.set_lookat(look_at)
            ctr.set_up([0, 0, 1])  # Z轴向上
            # 设置初始方向为+X（前视图）
            front_vector = np.array([1, 0, 0])  # X轴正方向
            ctr.set_front(front_vector)
            vis.poll_events()
            vis.update_renderer()
            # 向左旋转90度（水平旋转）
            ctr.rotate(90.0, 0.0)  # 第一个参数是水平旋转角度（度），第二个是垂直旋转角度
            ctr.set_zoom(0.7)
            vis.poll_events()
            vis.update_renderer()
            
            # 使用高分辨率截图（4K分辨率）
            filename = "spiral_groove_front.png"
            vis.capture_screen_image(filename, do_render=True)
            print(f"  已保存: {filename}")
            
            vis.run()
            vis.destroy_window()
            print("窗口已关闭。\n")
        else:
            # 非交互模式：保存front视图（向左旋转90度，高清晰度）
            print("\n保存front视图（向左旋转90度，高清晰度）...")
            # 使用4K分辨率（3840x2160）以获得更高清晰度
            vis = o3d.visualization.Visualizer()
            # 创建不可见窗口用于截图，添加错误处理
            try:
                vis.create_window(visible=False, width=3840, height=2160)
            except Exception as e:
                # 如果创建不可见窗口失败，尝试使用可见窗口
                print(f"  警告: 创建不可见窗口时出现问题: {e}")
                vis.create_window(visible=True, width=3840, height=2160)
            vis.add_geometry(o3d_mesh)
            
            # 设置高分辨率渲染选项（确保平滑着色）
            render_option = vis.get_render_option()
            render_option.mesh_show_back_face = False
            render_option.mesh_show_wireframe = False
            # 平滑着色（如果支持）
            try:
                render_option.mesh_shade_option = o3d.visualization.MeshShadeOption.SmoothShade
            except AttributeError:
                # 如果SmoothShade不可用，使用默认着色
                pass
            render_option.point_size = 3.0
            render_option.line_width = 2.0
            render_option.background_color = np.array([0.95, 0.95, 0.95])
            
            bounds = mesh.bounds
            center = mesh.centroid
            extent = bounds[1] - bounds[0]
            max_extent = np.max(extent)
            camera_distance = max_extent * 2.0
            
            # 前视图向左旋转90度：从+Y方向看（左视图方向）
            ctr = vis.get_view_control()
            look_at = center
            # 先设置到+X方向（前视图），然后向左旋转90度
            ctr.set_lookat(look_at)
            ctr.set_up([0, 0, 1])  # Z轴向上
            # 设置初始方向为+X（前视图）
            front_vector = np.array([1, 0, 0])  # X轴正方向
            ctr.set_front(front_vector)
            # 向左旋转90度（水平旋转）
            ctr.rotate(90.0, 0.0)  # 水平旋转90度（向左旋转）
            ctr.set_zoom(0.7)
            vis.poll_events()
            vis.update_renderer()
            
            filename = "spiral_groove_front.png"
            vis.capture_screen_image(filename, do_render=True)
            print(f"  已保存: {filename} (4K分辨率)")
            
            vis.destroy_window()
            print("  截图已保存完成。")
        
        return True
        
    except Exception as e:
        print(f"  Open3D可视化失败: {e}")
        return False


def visualize_plotly(mesh, params=None, output_file='spiral_groove_interactive.html'):
    """使用plotly生成交互式HTML（支持3D文本标注）"""
    if not HAS_PLOTLY:
        return False
    
    print(f"生成交互式HTML（带文本标注）: {output_file}...")
    
    # 如果没有提供参数，尝试从mesh估算
    if params is None:
        bounds = mesh.bounds
        extent = bounds[1] - bounds[0]
        params = {
            'D1': extent[0] * 2,
            'L1': 5.0,
            'L2': extent[2] - 5.0,
            'A1': 30.0
        }
    
    D1 = params['D1']
    L1 = params['L1']
    L2 = params['L2']
    A1 = params['A1']
    
    vertices = mesh.vertices
    faces = mesh.faces
    
    # 如果面片太多，尝试简化（如果fast_simplification可用）
    if len(faces) > MAX_FACES_FOR_SIMPLIFICATION:
        try:
            simplified_mesh = mesh.simplify_quadric_decimation(face_count=50000)
            vertices = simplified_mesh.vertices
            faces = simplified_mesh.faces
            print(f"  已简化mesh: {len(faces)} 个面片")
        except (ImportError, AttributeError):
            # 如果fast_simplification不可用，使用采样方法
            print(f"  警告：fast_simplification未安装，使用采样方法简化")
            print(f"  提示：安装 fast_simplification 可以获得更好的简化效果")
            print(f"  安装命令: pip install fast_simplification")
            # 采样面片
            step = max(1, len(faces) // MAX_FACES_FOR_SIMPLIFICATION)
            faces = faces[::step]
            print(f"  采样后: {len(faces)} 个面片")
    
    # 创建3D mesh
    fig = go.Figure(data=[go.Mesh3d(
        x=vertices[:, 0].tolist(),
        y=vertices[:, 1].tolist(),
        z=vertices[:, 2].tolist(),
        i=faces[:, 0].tolist(),
        j=faces[:, 1].tolist(),
        k=faces[:, 2].tolist(),
        opacity=0.9,
        color='lightblue',
        flatshading=False,
        showscale=False,
        lighting=dict(ambient=0.7, diffuse=0.8, specular=0.2, roughness=0.3),
        lightposition=dict(x=100, y=100, z=100)
    )])
    
    # 计算标注位置
    bounds = mesh.bounds
    center = mesh.centroid
    extent = bounds[1] - bounds[0]
    
    # D1标注（刀具直径）：垂直方向，在左侧
    d1_x = bounds[0][0] - extent[0] * 0.3
    d1_z_top = bounds[1][2]
    d1_z_bottom = bounds[0][2]
    d1_y = center[1]
    d1_label_pos = [d1_x - extent[0] * 0.1, d1_y, (d1_z_top + d1_z_bottom) / 2]
    
    # L1标注（导向长度）：水平方向，在底部，从起点到L1位置
    l1_z = bounds[0][2] - extent[2] * 0.1
    l1_x_start = bounds[0][0]
    l1_x_end = bounds[0][0] + L1  # L1是导向长度，从起点开始
    l1_y = center[1]
    l1_label_pos = [(l1_x_start + l1_x_end) / 2, l1_y, l1_z - extent[2] * 0.05]
    
    # L2标注（排屑槽长度）：水平方向，在L1下方，从L1到L1+L2
    l2_z = l1_z - extent[2] * 0.08
    l2_x_start = bounds[0][0] + L1  # L2从L1位置开始
    l2_x_end = bounds[0][0] + L1 + L2  # L2结束位置
    l2_y = center[1]
    l2_label_pos = [(l2_x_start + l2_x_end) / 2, l2_y, l2_z - extent[2] * 0.05]
    
    # A1标注（螺旋角）：在螺旋槽区域中间
    a1_z = bounds[0][2] + L1 + L2 / 2
    a1_x = bounds[1][0] + extent[0] * 0.2
    a1_y = center[1]
    a1_label_pos = [a1_x, a1_y, a1_z]
    
    # 添加标注线
    # D1标注线（垂直）
    fig.add_trace(go.Scatter3d(
        x=[d1_x, d1_x],
        y=[d1_y, d1_y],
        z=[d1_z_top, d1_z_bottom],
        mode='lines',
        line=dict(color='black', width=2),
        showlegend=False,
        hoverinfo='skip'
    ))
    # D1箭头
    arrow_size = extent[2] * 0.02
    fig.add_trace(go.Scatter3d(
        x=[d1_x, d1_x - arrow_size, d1_x, d1_x + arrow_size],
        y=[d1_y, d1_y, d1_y, d1_y],
        z=[d1_z_top, d1_z_top - arrow_size, d1_z_top, d1_z_top - arrow_size],
        mode='lines',
        line=dict(color='black', width=2),
        showlegend=False,
        hoverinfo='skip'
    ))
    fig.add_trace(go.Scatter3d(
        x=[d1_x, d1_x - arrow_size, d1_x, d1_x + arrow_size],
        y=[d1_y, d1_y, d1_y, d1_y],
        z=[d1_z_bottom, d1_z_bottom + arrow_size, d1_z_bottom, d1_z_bottom + arrow_size],
        mode='lines',
        line=dict(color='black', width=2),
        showlegend=False,
        hoverinfo='skip'
    ))
    
    # L1标注线（水平）- 导向长度，从起点到L1位置
    l1_x_start = bounds[0][0]
    l1_x_end = bounds[0][0] + L1
    fig.add_trace(go.Scatter3d(
        x=[l1_x_start, l1_x_end],
        y=[l1_y, l1_y],
        z=[l1_z, l1_z],
        mode='lines',
        line=dict(color='black', width=2),
        showlegend=False,
        hoverinfo='skip'
    ))
    
    # L2标注线（水平）- 排屑槽长度，从L1到L1+L2
    l2_x_start = bounds[0][0] + L1
    l2_x_end = bounds[0][0] + L1 + L2
    fig.add_trace(go.Scatter3d(
        x=[l2_x_start, l2_x_end],
        y=[l2_y, l2_y],
        z=[l2_z, l2_z],
        mode='lines',
        line=dict(color='black', width=2),
        showlegend=False,
        hoverinfo='skip'
    ))
    
    # 添加文本标签（使用plotly的3D文本功能）
    # D1：刀具直径
    fig.add_trace(go.Scatter3d(
        x=[d1_label_pos[0]],
        y=[d1_label_pos[1]],
        z=[d1_label_pos[2]],
        mode='text',
        text=[f'D1={D1:.1f}'],
        textfont=dict(size=16, color='black'),
        showlegend=False,
        hoverinfo='skip'
    ))
    
    # L1：导向长度
    fig.add_trace(go.Scatter3d(
        x=[l1_label_pos[0]],
        y=[l1_label_pos[1]],
        z=[l1_label_pos[2]],
        mode='text',
        text=[f'L1={L1:.1f}'],
        textfont=dict(size=16, color='black'),
        showlegend=False,
        hoverinfo='skip'
    ))
    
    # L2：排屑槽长度
    fig.add_trace(go.Scatter3d(
        x=[l2_label_pos[0]],
        y=[l2_label_pos[1]],
        z=[l2_label_pos[2]],
        mode='text',
        text=[f'L2={L2:.1f}'],
        textfont=dict(size=16, color='black'),
        showlegend=False,
        hoverinfo='skip'
    ))
    
    # A1：螺旋角
    fig.add_trace(go.Scatter3d(
        x=[a1_label_pos[0]],
        y=[a1_label_pos[1]],
        z=[a1_label_pos[2]],
        mode='text',
        text=[f'A1={A1:.1f}°'],
        textfont=dict(size=16, color='black'),
        showlegend=False,
        hoverinfo='skip'
    ))
    
    fig.update_layout(
        title=f'螺旋排屑槽3D模型 - D1={D1:.1f}mm L1={L1:.1f}mm L2={L2:.1f}mm A1={A1:.1f}°',
        scene=dict(
            xaxis_title='X (mm)',
            yaxis_title='Y (mm)',
            zaxis_title='Z (mm)',
            aspectmode='data',
            camera=dict(
                eye=dict(x=0, y=2, z=0),  # 侧视图
                center=dict(x=0, y=0, z=0),
                up=dict(x=0, y=0, z=1)
            )
        ),
        width=1200,
        height=800
    )
    
    pyo.plot(fig, filename=output_file, auto_open=True)
    print(f"  已保存到: {output_file}")
    print(f"  参数标注: D1={D1:.1f}mm, L1={L1:.1f}mm, L2={L2:.1f}mm, A1={A1:.1f}°\n")
    return True


def generate_side_projection(mesh, params=None, output_file='spiral_groove_side_view.png'):
    """
    生成模型的侧面投影图（XZ平面投影）
    
    参数:
        mesh: trimesh对象
        params: 参数字典
        output_file: 输出文件名
    """
    if not HAS_MATPLOTLIB:
        print("matplotlib未安装，跳过侧面投影图生成")
        return
    
    print(f"\n生成侧面投影图: {output_file}...")
    
    # 如果没有提供参数，尝试从mesh估算
    if params is None:
        bounds = mesh.bounds
        extent = bounds[1] - bounds[0]
        params = {
            'D1': extent[0] * 2,
            'L1': 5.0,
            'L2': extent[2] - 5.0,
            'A1': 30.0
        }
    
    D1 = params['D1']
    L1 = params['L1']
    L2 = params['L2']
    A1 = params['A1']
    blade_height = params.get('blade_height', 1.5)  # 默认值1.5mm
    
    # 获取mesh的顶点和面片
    vertices = mesh.vertices
    faces = mesh.faces
    
    # 投影到XZ平面（从Y轴正方向看，投影到XZ平面）
    # 方法：只显示边缘轮廓线，不显示内部网格线
    
    # 计算Y坐标的范围，用于选择可见的点
    y_coords = vertices[:, 1]
    y_center = np.mean(y_coords)
    y_threshold = (np.max(y_coords) - np.min(y_coords)) * 0.15
    
    # 创建图形
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # 提取边缘线：对于每个Z值，找X的最大值和最小值（轮廓），以及槽的边缘
    bounds = mesh.bounds
    z_min, z_max = bounds[0][2], bounds[1][2]
    z_samples = np.linspace(z_min, z_max, 500)  # 增加采样点以获得更平滑的轮廓
    
    x_upper = []  # 上轮廓
    x_lower = []  # 下轮廓
    z_upper = []
    z_lower = []
    
    # 槽的边缘线（左右边缘）
    groove_edges_left = []   # 槽的左边缘（X较小的一侧）
    groove_edges_right = []  # 槽的右边缘（X较大的一侧）
    groove_z_left = []
    groove_z_right = []
    
    # 计算半径，用于识别槽的边缘
    radius = D1 / 2.0
    
    for z_val in z_samples:
        # 找到Z值附近的顶点（在Y方向可见的）
        z_mask = np.abs(vertices[:, 2] - z_val) < (z_max - z_min) / 500
        y_mask = np.abs(vertices[:, 1] - y_center) < y_threshold
        combined_mask = z_mask & y_mask
        
        if np.any(combined_mask):
            nearby_vertices = vertices[combined_mask]
            x_vals = nearby_vertices[:, 0]
            z_vals = nearby_vertices[:, 2]
            
            # 计算每个点的半径
            r_vals = np.sqrt(nearby_vertices[:, 0]**2 + nearby_vertices[:, 1]**2)
            
            if len(x_vals) > 0:
                # 只取X的最大值和最小值（外轮廓边缘）
                x_max_idx = np.argmax(x_vals)
                x_min_idx = np.argmin(x_vals)
                
                x_upper.append(x_vals[x_max_idx])
                z_upper.append(z_vals[x_max_idx])
                x_lower.append(x_vals[x_min_idx])
                z_lower.append(z_vals[x_min_idx])
                
                # 识别槽的边缘：找到半径变化最大的地方（槽的边界）
                if L1 <= z_val <= L1 + L2:  # 只在槽的区域内查找
                    # 对X值排序，然后找到半径变化最大的地方
                    x_sorted_idx = np.argsort(x_vals)
                    x_sorted = x_vals[x_sorted_idx]
                    r_sorted = r_vals[x_sorted_idx]
                    z_sorted = z_vals[x_sorted_idx]
                    
                    if len(x_sorted) > 2:
                        # 计算半径的变化率（梯度）
                        r_diff = np.abs(np.diff(r_sorted))
                        
                        # 找到半径变化最大的位置（槽的边缘）
                        # 槽的边缘应该是半径从正常值突然变化到槽深值的地方
                        if len(r_diff) > 0:
                            # 计算正常半径和槽深半径
                            normal_radius = radius
                            groove_radius = radius - blade_height * 0.8  # 槽深约80%的位置作为边缘
                            
                            # 找到半径接近槽深的位置（槽的边缘）
                            # 方法：找到半径从正常值变化到槽深值的过渡点
                            left_edge_found = False
                            right_edge_found = False
                            
                            # 从左到右查找左边缘（第一个进入槽的位置）
                            for i in range(len(r_sorted) - 1):
                                if r_sorted[i] > groove_radius and r_sorted[i+1] <= groove_radius:
                                    # 找到从正常半径到槽深的过渡点
                                    groove_edges_left.append(x_sorted[i])
                                    groove_z_left.append(z_sorted[i])
                                    left_edge_found = True
                                    break
                            
                            # 从右到左查找右边缘（最后一个离开槽的位置）
                            for i in range(len(r_sorted) - 1, 0, -1):
                                if r_sorted[i] > groove_radius and r_sorted[i-1] <= groove_radius:
                                    # 找到从槽深到正常半径的过渡点
                                    groove_edges_right.append(x_sorted[i])
                                    groove_z_right.append(z_sorted[i])
                                    right_edge_found = True
                                    break
                            
                            # 如果没找到明确的过渡点，使用半径变化最大的位置
                            if not left_edge_found or not right_edge_found:
                                max_diff = np.max(r_diff)
                                if max_diff > 0:
                                    threshold = max_diff * 0.3  # 变化超过最大变化的30%
                                    edge_mask = r_diff > threshold
                                    
                                    if np.any(edge_mask):
                                        edge_indices = np.where(edge_mask)[0]
                                        
                                        # 左边缘：X较小的边缘点
                                        if not left_edge_found and len(edge_indices) > 0:
                                            left_edge_idx = edge_indices[0]
                                            if left_edge_idx < len(x_sorted):
                                                groove_edges_left.append(x_sorted[left_edge_idx])
                                                groove_z_left.append(z_sorted[left_edge_idx])
                                        
                                        # 右边缘：X较大的边缘点
                                        if not right_edge_found and len(edge_indices) > 0:
                                            right_edge_idx = edge_indices[-1]
                                            if right_edge_idx + 1 < len(x_sorted):
                                                groove_edges_right.append(x_sorted[right_edge_idx + 1])
                                                groove_z_right.append(z_sorted[right_edge_idx + 1])
    
    # 绘制上下轮廓线（外边缘线）
    if len(x_upper) > 0:
        ax.plot(z_upper, x_upper, 'b-', linewidth=1.5, alpha=0.9, label='上轮廓')
    if len(x_lower) > 0:
        ax.plot(z_lower, x_lower, 'b-', linewidth=1.5, alpha=0.9, label='下轮廓')
    
    # 绘制槽的边缘线
    if len(groove_edges_left) > 0:
        # 对槽边缘点按Z排序
        groove_left_sorted = sorted(zip(groove_z_left, groove_edges_left), key=lambda p: p[0])
        groove_z_left_sorted, groove_x_left_sorted = zip(*groove_left_sorted)
        ax.plot(groove_z_left_sorted, groove_x_left_sorted, 'b-', linewidth=1.5, alpha=0.9, label='槽左边缘')
    
    if len(groove_edges_right) > 0:
        # 对槽边缘点按Z排序
        groove_right_sorted = sorted(zip(groove_z_right, groove_edges_right), key=lambda p: p[0])
        groove_z_right_sorted, groove_x_right_sorted = zip(*groove_right_sorted)
        ax.plot(groove_z_right_sorted, groove_x_right_sorted, 'b-', linewidth=1.5, alpha=0.9, label='槽右边缘')
    
    # 填充区域（可选，使用更低的透明度）
    if len(x_upper) > 0 and len(x_lower) > 0:
        z_fill = np.concatenate([z_upper, z_lower[::-1]])
        x_fill = np.concatenate([x_upper, x_lower[::-1]])
        ax.fill(z_fill, x_fill, alpha=0.2, color='lightblue')
    
    # 添加参数标注
    extent = bounds[1] - bounds[0]
    extent = bounds[1] - bounds[0]
    
    # D1标注（垂直方向）
    d1_x = bounds[0][0] - extent[0] * 0.15
    d1_z_top = bounds[1][2]
    d1_z_bottom = bounds[0][2]
    ax.plot([d1_x, d1_x], [d1_z_bottom, d1_z_top], 'k-', linewidth=2)
    ax.annotate(f'D1={D1:.1f}', xy=(d1_x - extent[0] * 0.1, (d1_z_top + d1_z_bottom) / 2),
                fontsize=14, ha='right', va='center')
    
    # L1标注（水平方向）
    l1_z = bounds[0][2] - extent[2] * 0.08
    l1_x_start = bounds[0][0]
    l1_x_end = bounds[0][0] + L1
    ax.plot([l1_x_start, l1_x_end], [l1_z, l1_z], 'k-', linewidth=2)
    ax.annotate(f'L1={L1:.1f}', xy=((l1_x_start + l1_x_end) / 2, l1_z - extent[2] * 0.05),
                fontsize=14, ha='center', va='top')
    
    # L2标注（水平方向）
    l2_z = l1_z - extent[2] * 0.06
    l2_x_start = bounds[0][0] + L1
    l2_x_end = bounds[0][0] + L1 + L2
    ax.plot([l2_x_start, l2_x_end], [l2_z, l2_z], 'k-', linewidth=2)
    ax.annotate(f'L2={L2:.1f}', xy=((l2_x_start + l2_x_end) / 2, l2_z - extent[2] * 0.05),
                fontsize=14, ha='center', va='top')
    
    # A1标注
    a1_z = bounds[0][2] + L1 + L2 / 2
    a1_x = bounds[1][0] + extent[0] * 0.15
    ax.annotate(f'A1={A1:.1f}°', xy=(a1_x, a1_z),
                fontsize=14, ha='left', va='center')
    
    # 设置坐标轴
    ax.set_xlabel('Z (mm)', fontsize=12)
    ax.set_ylabel('X (mm)', fontsize=12)
    ax.set_title('螺旋排屑槽侧面投影图', fontsize=16, fontweight='bold', pad=20)
    ax.grid(True, alpha=0.3)
    ax.set_aspect('equal', adjustable='box')
    
    # 设置坐标轴范围
    margin = max(extent) * 0.1
    ax.set_xlim(bounds[0][2] - margin, bounds[1][2] + margin)
    ax.set_ylim(bounds[0][0] - margin, bounds[1][0] + margin)
    
    # 保存图像
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"  侧面投影图已保存到: {output_file}")


def interactive_parameter_adjustment():
    """
    交互式参数调整界面
    使用matplotlib滑块动态调整参数并实时显示3D模型
    """
    if not HAS_MATPLOTLIB:
        print("matplotlib未安装，无法使用交互式参数调整功能")
        return
    
    print("=" * 60)
    print("交互式参数调整界面")
    print("=" * 60)
    
    # 初始参数
    initial_D1 = 10.0
    initial_L1 = 5.0
    initial_L2 = 150.0  # 增加默认长度以增加螺旋圈数（波浪数量）
    initial_A1 = 40.0
    initial_blade_height = 1.5
    initial_num_flutes = 3
    
    # 创建图形和3D子图
    fig = plt.figure(figsize=(16, 10))
    ax_3d = fig.add_subplot(121, projection='3d')
    
    # 存储当前的mesh和参数
    current_mesh = None
    current_params = None
    
    def update_model(D1, L1, L2, A1, blade_height, num_flutes):
        """更新3D模型"""
        nonlocal current_mesh, current_params
        
        try:
            # 创建新的mesh
            mesh, params = create_spiral_groove_mesh(
                D1=D1,
                L1=L1,
                L2=L2,
                A1=A1,
                blade_height=blade_height,
                num_flutes=int(num_flutes),
                z_resolution=Z_RESOLUTION_INTERACTIVE,
                theta_resolution=THETA_RESOLUTION_INTERACTIVE
            )
            
            current_mesh = mesh
            current_params = params
            
            # 清空当前图形
            ax_3d.clear()
            
            # 绘制3D模型（使用简化版本以提高性能）
            vertices = mesh.vertices
            faces = mesh.faces
            
            # 采样面片以提高性能
            if len(faces) > MAX_FACES_FOR_INTERACTIVE:
                sample_step = len(faces) // MAX_FACES_FOR_INTERACTIVE
                faces = faces[::sample_step]
            
            # 绘制mesh
            ax_3d.plot_trisurf(
                vertices[:, 0], 
                vertices[:, 1], 
                vertices[:, 2],
                triangles=faces,
                alpha=0.8,
                color='lightblue',
                edgecolor='none'
            )
            
            # 设置坐标轴
            bounds = mesh.bounds
            extent = bounds[1] - bounds[0]
            center = mesh.centroid
            
            ax_3d.set_xlim(center[0] - extent[0]/2, center[0] + extent[0]/2)
            ax_3d.set_ylim(center[1] - extent[1]/2, center[1] + extent[1]/2)
            ax_3d.set_zlim(center[2] - extent[2]/2, center[2] + extent[2]/2)
            
            ax_3d.set_xlabel('X (mm)')
            ax_3d.set_ylabel('Y (mm)')
            ax_3d.set_zlabel('Z (mm)')
            ax_3d.set_title(f'螺旋排屑槽3D模型\nD1={D1:.1f}mm L1={L1:.1f}mm L2={L2:.1f}mm A1={A1:.1f}°')
            
            plt.draw()
            
        except Exception as e:
            print(f"更新模型时出错: {e}")
    
    # 创建滑块
    plt.subplots_adjust(left=0.05, bottom=0.25, right=0.65)
    
    # D1滑块
    ax_D1 = plt.axes([0.7, 0.85, 0.25, 0.03])
    slider_D1 = Slider(ax_D1, 'D1 (mm)', 5.0, 20.0, valinit=initial_D1, valstep=0.1)
    
    # L1滑块
    ax_L1 = plt.axes([0.7, 0.80, 0.25, 0.03])
    slider_L1 = Slider(ax_L1, 'L1 (mm)', 0.0, 20.0, valinit=initial_L1, valstep=0.1)
    
    # L2滑块
    ax_L2 = plt.axes([0.7, 0.75, 0.25, 0.03])
    slider_L2 = Slider(ax_L2, 'L2 (mm)', 10.0, 300.0, valinit=initial_L2, valstep=5.0)  # 增加最大值到300mm
    
    # A1滑块
    ax_A1 = plt.axes([0.7, 0.70, 0.25, 0.03])
    slider_A1 = Slider(ax_A1, 'A1 (°)', 10.0, 60.0, valinit=initial_A1, valstep=1.0)
    
    # blade_height滑块
    ax_blade_height = plt.axes([0.7, 0.65, 0.25, 0.03])
    slider_blade_height = Slider(ax_blade_height, '槽深 (mm)', 0.5, 5.0, valinit=initial_blade_height, valstep=0.1)
    
    # num_flutes滑块
    ax_num_flutes = plt.axes([0.7, 0.60, 0.25, 0.03])
    slider_num_flutes = Slider(ax_num_flutes, '槽数', 1, 4, valinit=initial_num_flutes, valstep=1, valfmt='%d')
    
    # 更新函数
    def update(val):
        D1 = slider_D1.val
        L1 = slider_L1.val
        L2 = slider_L2.val
        A1 = slider_A1.val
        blade_height = slider_blade_height.val
        num_flutes = int(slider_num_flutes.val)
        update_model(D1, L1, L2, A1, blade_height, num_flutes)
    
    # 连接滑块事件
    slider_D1.on_changed(update)
    slider_L1.on_changed(update)
    slider_L2.on_changed(update)
    slider_A1.on_changed(update)
    slider_blade_height.on_changed(update)
    slider_num_flutes.on_changed(update)
    
    # 添加Open3D查看按钮
    ax_view_3d = plt.axes([0.7, 0.43, 0.25, 0.05])
    button_view_3d = Button(ax_view_3d, 'Open3D查看')
    
    def view_open3d(event):
        """在Open3D中查看当前模型"""
        if current_mesh is not None and current_params is not None:
            if HAS_OPEN3D:
                visualize_open3d(current_mesh, params=current_params, interactive=True)
            else:
                print("Open3D未安装，无法使用3D查看功能")
        else:
            print("没有可查看的模型")
    
    button_view_3d.on_clicked(view_open3d)
    
    # 初始绘制
    update_model(initial_D1, initial_L1, initial_L2, initial_A1, initial_blade_height, initial_num_flutes)
    
    print("\n使用说明:")
    print("  - 拖动滑块调整参数，模型会实时更新")
    print("  - 点击'Open3D查看'按钮在Open3D中查看高质量3D模型")
    print("  - 关闭窗口退出")
    print("=" * 60)
    
    plt.show()


def main():
    """主函数"""
    import sys
    
    # 检查是否有命令行参数指定使用交互式模式
    if len(sys.argv) > 1 and sys.argv[1] == '--interactive':
        interactive_parameter_adjustment()
        return
    
    # 参数配置
    D1 = 10.0           # 刀具直径 (mm)
    L1 = 5.0           # 导向长度 (mm)
    L2 = 150.0         # 排屑槽长度 (mm) - 增加长度以增加螺旋圈数（波浪数量）
    A1 = 40.0          # 螺旋角 (度)
    blade_height = 1.5 # 槽深 (mm)
    num_flutes = 3     # 螺旋槽数量
    
    try:
        # 创建3D模型
        mesh, params = create_spiral_groove_mesh(
            D1=D1,
            L1=L1,
            L2=L2,
            A1=A1,
            blade_height=blade_height,
            num_flutes=num_flutes,
            z_resolution=Z_RESOLUTION_DEFAULT,
            theta_resolution=THETA_RESOLUTION_DEFAULT
        )
        
        # 可视化（使用Open3D）
        if not visualize_open3d(mesh, params=params, interactive=True):
            print("错误: Open3D不可用，无法进行3D可视化")
            return
        
        # 不再生成侧面投影图，只保存front视图截图
        
        print("=" * 60)
        print("所有文件生成完成！")
        print("提示: 使用 'python spiral_groove_3d_cad.py --interactive' 启动交互式参数调整界面")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
