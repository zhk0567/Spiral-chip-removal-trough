#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
螺旋排屑槽三维建模工具
功能：
- 生成圆柱体
- 创建螺旋线路径
- 沿螺旋线扫描切除
- 生成三维可视化图像
"""

import math
import numpy as np
import sys

# 设置标准输出编码为UTF-8（解决Windows中文乱码问题）
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 尝试导入必要的库
try:
    import matplotlib
    matplotlib.use('Agg')  # 使用非交互式后端，避免显示窗口
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    import matplotlib.font_manager as fm
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("警告：matplotlib未安装，将无法生成可视化图像")

try:
    import trimesh
    HAS_TRIMESH = True
except ImportError:
    HAS_TRIMESH = False
    print("警告：trimesh未安装，将使用简化方法生成3D模型")

# 配置matplotlib中文字体
def setup_chinese_font():
    """设置matplotlib中文字体"""
    if not HAS_MATPLOTLIB:
        return
    
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

def generate_cylinder_mesh(radius, height, resolution=50):
    """
    生成圆柱体mesh
    
    参数:
        radius: 圆柱体半径 (mm)
        height: 圆柱体高度 (mm)
        resolution: 圆周方向分辨率（点数）
    
    返回:
        vertices: 顶点数组 (N, 3)
        faces: 面片数组 (M, 3)
    """
    # 生成圆柱体顶点
    vertices = []
    faces = []
    
    # 顶面和底面中心点
    top_center = np.array([0, 0, height])
    bottom_center = np.array([0, 0, 0])
    
    # 生成圆周上的点
    angles = np.linspace(0, 2 * math.pi, resolution, endpoint=False)
    
    # 底面圆周点
    bottom_circle = []
    for angle in angles:
        x = radius * math.cos(angle)
        y = radius * math.sin(angle)
        bottom_circle.append([x, y, 0])
        vertices.append([x, y, 0])
    
    # 顶面圆周点
    top_circle = []
    for angle in angles:
        x = radius * math.cos(angle)
        y = radius * math.sin(angle)
        top_circle.append([x, y, height])
        vertices.append([x, y, height])
    
    # 添加中心点
    bottom_center_idx = len(vertices)
    vertices.append(bottom_center.tolist())
    top_center_idx = len(vertices)
    vertices.append(top_center.tolist())
    
    # 生成底面三角形面片
    for i in range(resolution):
        next_i = (i + 1) % resolution
        faces.append([i, next_i, bottom_center_idx])
    
    # 生成顶面三角形面片
    for i in range(resolution):
        next_i = (i + 1) % resolution
        faces.append([resolution + i, top_center_idx, resolution + next_i])
    
    # 生成侧面四边形（分成两个三角形）
    for i in range(resolution):
        next_i = (i + 1) % resolution
        # 第一个三角形
        faces.append([i, resolution + i, next_i])
        # 第二个三角形
        faces.append([next_i, resolution + i, resolution + next_i])
    
    return np.array(vertices), np.array(faces)

def generate_helix_path(radius, pitch, height, num_points=200):
    """
    生成螺旋线路径
    
    参数:
        radius: 螺旋线半径 (mm)
        pitch: 螺距 (mm) - 每圈上升的高度
        height: 总高度 (mm)
        num_points: 采样点数
    
    返回:
        points: 螺旋线上的点 (N, 3)
        tangents: 切线方向向量 (N, 3)
    """
    points = []
    tangents = []
    
    num_turns = height / pitch
    t_values = np.linspace(0, num_turns * 2 * math.pi, num_points)
    
    for t in t_values:
        z = (t / (2 * math.pi)) * pitch
        if z > height:
            z = height
        
        x = radius * math.cos(t)
        y = radius * math.sin(t)
        points.append([x, y, z])
        
        # 计算切线方向（归一化）
        dx = -radius * math.sin(t)
        dy = radius * math.cos(t)
        dz = pitch / (2 * math.pi)
        tangent = np.array([dx, dy, dz])
        tangent = tangent / np.linalg.norm(tangent)
        tangents.append(tangent)
    
    return np.array(points), np.array(tangents)

def generate_sweep_cut_mesh(helix_points, helix_tangents, cut_radius, resolution=16):
    """
    沿螺旋线路径生成扫描切除体
    
    参数:
        helix_points: 螺旋线上的点 (N, 3)
        helix_tangents: 切线方向 (N, 3)
        cut_radius: 切除截面半径 (mm)
        resolution: 截面圆周分辨率
    
    返回:
        vertices: 顶点数组
        faces: 面片数组
    """
    vertices = []
    faces = []
    
    # 为每个路径点生成一个圆形截面
    sections = []
    
    for i, (point, tangent) in enumerate(zip(helix_points, helix_tangents)):
        # 计算截面的法向量（垂直于切线）
        # 使用一个固定的参考向量来计算法向量
        if i == 0:
            # 第一个截面，使用默认方向
            ref_vec = np.array([1, 0, 0])
        else:
            # 使用前一个截面的法向量
            ref_vec = sections[-1][1]
        
        # 计算垂直于切线的法向量
        normal = np.cross(tangent, ref_vec)
        if np.linalg.norm(normal) < 1e-6:
            # 如果叉积为零，使用另一个参考向量
            normal = np.cross(tangent, np.array([0, 1, 0]))
        normal = normal / np.linalg.norm(normal)
        
        # 计算第二个法向量（形成正交基）
        binormal = np.cross(tangent, normal)
        binormal = binormal / np.linalg.norm(binormal)
        
        # 生成截面圆周上的点
        section_points = []
        angles = np.linspace(0, 2 * math.pi, resolution, endpoint=False)
        
        for angle in angles:
            offset = normal * (cut_radius * math.cos(angle)) + binormal * (cut_radius * math.sin(angle))
            section_point = point + offset
            section_points.append(section_point)
            vertices.append(section_point.tolist())
        
        sections.append((section_points, normal))
    
    # 生成面片（连接相邻截面）
    num_sections = len(sections)
    for i in range(num_sections - 1):
        curr_section = sections[i][0]
        next_section = sections[i + 1][0]
        
        base_idx_curr = i * resolution
        base_idx_next = (i + 1) * resolution
        
        # 连接相邻截面的点形成四边形（分成两个三角形）
        for j in range(resolution):
            next_j = (j + 1) % resolution
            
            # 第一个三角形
            faces.append([
                base_idx_curr + j,
                base_idx_curr + next_j,
                base_idx_next + j
            ])
            
            # 第二个三角形
            faces.append([
                base_idx_curr + next_j,
                base_idx_next + next_j,
                base_idx_next + j
            ])
    
    # 添加起始和结束端面
    if num_sections > 0:
        # 起始端面（第一个截面）
        first_center = np.mean(sections[0][0], axis=0)
        first_center_idx = len(vertices)
        vertices.append(first_center.tolist())
        
        for j in range(resolution):
            next_j = (j + 1) % resolution
            faces.append([0, first_center_idx, next_j])
        
        # 结束端面（最后一个截面）
        last_center = np.mean(sections[-1][0], axis=0)
        last_center_idx = len(vertices)
        vertices.append(last_center.tolist())
        
        last_base = (num_sections - 1) * resolution
        for j in range(resolution):
            next_j = (j + 1) % resolution
            faces.append([last_base + j, last_base + next_j, last_center_idx])
    
    return np.array(vertices), np.array(faces)

def visualize_3d_model(cylinder_vertices, cylinder_faces, 
                       helix_points, cut_mesh_vertices, cut_mesh_faces,
                       drill_diameter, total_length, spiral_angle):
    """
    可视化3D模型
    
    参数:
        cylinder_vertices: 圆柱体顶点
        cylinder_faces: 圆柱体面片
        helix_points: 螺旋线点
        cut_mesh_vertices: 切除体顶点
        cut_mesh_faces: 切除体面片
        drill_diameter: 钻头直径
        total_length: 总长度
        spiral_angle: 螺旋角
    """
    if not HAS_MATPLOTLIB:
        print("matplotlib未安装，无法生成可视化图像")
        return
    
    setup_chinese_font()
    
    fig = plt.figure(figsize=(16, 10))
    
    # 创建多个视角的子图
    ax1 = fig.add_subplot(2, 2, 1, projection='3d')
    ax2 = fig.add_subplot(2, 2, 2, projection='3d')
    ax3 = fig.add_subplot(2, 2, 3, projection='3d')
    ax4 = fig.add_subplot(2, 2, 4, projection='3d')
    
    # 子图1：完整模型（圆柱体 + 螺旋线 + 切除体）
    ax1.set_title('完整模型视图', fontsize=12, fontweight='bold')
    
    # 绘制圆柱体（简化显示，只显示轮廓）
    # 绘制圆柱体顶面和底面圆周
    radius = drill_diameter / 2.0
    angles = np.linspace(0, 2 * math.pi, 50)
    top_circle_x = radius * np.cos(angles)
    top_circle_y = radius * np.sin(angles)
    top_circle_z = np.full_like(angles, total_length)
    bottom_circle_x = radius * np.cos(angles)
    bottom_circle_y = radius * np.sin(angles)
    bottom_circle_z = np.zeros_like(angles)
    
    ax1.plot(top_circle_x, top_circle_y, top_circle_z, 'b-', linewidth=2, label='圆柱体顶面')
    ax1.plot(bottom_circle_x, bottom_circle_y, bottom_circle_z, 'b-', linewidth=2, label='圆柱体底面')
    
    # 绘制螺旋线
    ax1.plot(helix_points[:, 0], helix_points[:, 1], helix_points[:, 2], 
             'r-', linewidth=2.5, label='螺旋线路径', alpha=0.8)
    
    # 绘制切除体（简化显示）
    if len(cut_mesh_vertices) > 0:
        # 只显示切除体的中心线
        cut_center = np.mean(cut_mesh_vertices, axis=0)
        ax1.scatter(cut_mesh_vertices[:, 0], cut_mesh_vertices[:, 1], cut_mesh_vertices[:, 2],
                   c='orange', s=1, alpha=0.3, label='切除体')
    
    ax1.set_xlabel('X (mm)', fontsize=10)
    ax1.set_ylabel('Y (mm)', fontsize=10)
    ax1.set_zlabel('Z (mm)', fontsize=10)
    ax1.legend(fontsize=8)
    ax1.set_box_aspect([1, 1, 1])
    
    # 子图2：螺旋线路径特写
    ax2.set_title('螺旋线路径特写', fontsize=12, fontweight='bold')
    ax2.plot(helix_points[:, 0], helix_points[:, 1], helix_points[:, 2], 
             'r-', linewidth=3, label='螺旋线')
    ax2.scatter(helix_points[::10, 0], helix_points[::10, 1], helix_points[::10, 2],
               c='red', s=20, alpha=0.6, label='采样点')
    ax2.set_xlabel('X (mm)', fontsize=10)
    ax2.set_ylabel('Y (mm)', fontsize=10)
    ax2.set_zlabel('Z (mm)', fontsize=10)
    ax2.legend(fontsize=8)
    ax2.set_box_aspect([1, 1, 1])
    
    # 子图3：切除体特写
    ax3.set_title('扫描切除体', fontsize=12, fontweight='bold')
    if len(cut_mesh_vertices) > 0:
        ax3.scatter(cut_mesh_vertices[:, 0], cut_mesh_vertices[:, 1], cut_mesh_vertices[:, 2],
                   c='orange', s=5, alpha=0.6, label='切除体顶点')
        # 绘制切除体的中心线（沿螺旋线）
        cut_center_line = []
        for i in range(0, len(cut_mesh_vertices), 16):  # 假设每个截面16个点
            section_center = np.mean(cut_mesh_vertices[i:i+16], axis=0)
            cut_center_line.append(section_center)
        if len(cut_center_line) > 1:
            cut_center_line = np.array(cut_center_line)
            ax3.plot(cut_center_line[:, 0], cut_center_line[:, 1], cut_center_line[:, 2],
                    'g-', linewidth=2, label='切除体中心线')
    ax3.set_xlabel('X (mm)', fontsize=10)
    ax3.set_ylabel('Y (mm)', fontsize=10)
    ax3.set_zlabel('Z (mm)', fontsize=10)
    ax3.legend(fontsize=8)
    ax3.set_box_aspect([1, 1, 1])
    
    # 子图4：最终结果（带切除的圆柱体）
    ax4.set_title('最终结果（带螺旋槽的圆柱体）', fontsize=12, fontweight='bold')
    
    # 绘制圆柱体轮廓
    ax4.plot(top_circle_x, top_circle_y, top_circle_z, 'b-', linewidth=1.5, alpha=0.5)
    ax4.plot(bottom_circle_x, bottom_circle_y, bottom_circle_z, 'b-', linewidth=1.5, alpha=0.5)
    
    # 绘制螺旋槽（用螺旋线表示）
    ax4.plot(helix_points[:, 0], helix_points[:, 1], helix_points[:, 2], 
             'r-', linewidth=2, label='螺旋槽', alpha=0.8)
    
    # 添加一些说明文字
    info_text = f'钻头直径: {drill_diameter:.1f} mm\n'
    info_text += f'总长度: {total_length:.1f} mm\n'
    info_text += f'螺旋角: {spiral_angle:.1f}°'
    ax4.text2D(0.02, 0.98, info_text, transform=ax4.transAxes,
              fontsize=9, verticalalignment='top',
              bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    ax4.set_xlabel('X (mm)', fontsize=10)
    ax4.set_ylabel('Y (mm)', fontsize=10)
    ax4.set_zlabel('Z (mm)', fontsize=10)
    ax4.legend(fontsize=8)
    ax4.set_box_aspect([1, 1, 1])
    
    plt.tight_layout()
    
    # 保存图像
    output_file = 'spiral_groove_3d_model.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\n3D模型可视化已保存到: {output_file}")
    
    # 关闭图形以释放资源（使用Agg后端时不需要show）
    plt.close()
    print("提示：图像已保存，可以直接查看文件")

def main():
    """主函数"""
    try:
        print("=" * 60)
        print("螺旋排屑槽三维建模工具")
        print("=" * 60)
        print()
    except Exception as e:
        print(f"初始化错误: {e}")
        return
    
    # 默认参数
    spiral_angle = 30.0      # 螺旋角（度）
    drill_diameter = 10.0    # 钻头直径（mm）
    total_length = 50.0      # 钻头总长（mm）
    blade_width = 2.0        # 刀瓣宽度（mm）
    cut_radius = blade_width / 2.0  # 切除截面半径（mm）
    
    print("当前建模参数：")
    print(f"  螺旋角: {spiral_angle}°")
    print(f"  钻头直径: {drill_diameter} mm")
    print(f"  钻头总长: {total_length} mm")
    print(f"  切除半径: {cut_radius} mm")
    print()
    
    # 计算半径
    radius = drill_diameter / 2.0
    
    # 计算螺距
    angle_rad = math.radians(spiral_angle)
    circumference = 2 * math.pi * radius
    pitch = circumference / math.tan(angle_rad)
    
    print(f"计算得到的参数：")
    print(f"  半径: {radius:.3f} mm")
    print(f"  圆周长度: {circumference:.3f} mm")
    print(f"  螺距: {pitch:.3f} mm")
    print()
    
    # 1. 生成圆柱体
    print("步骤1: 生成圆柱体...")
    cylinder_vertices, cylinder_faces = generate_cylinder_mesh(radius, total_length, resolution=50)
    print(f"  圆柱体顶点数: {len(cylinder_vertices)}")
    print(f"  圆柱体面片数: {len(cylinder_faces)}")
    
    # 2. 生成螺旋线路径
    print("\n步骤2: 生成螺旋线路径...")
    helix_points, helix_tangents = generate_helix_path(radius, pitch, total_length, num_points=300)
    print(f"  螺旋线点数: {len(helix_points)}")
    
    # 3. 生成扫描切除体
    print("\n步骤3: 生成扫描切除体...")
    cut_vertices, cut_faces = generate_sweep_cut_mesh(
        helix_points, helix_tangents, cut_radius, resolution=16
    )
    print(f"  切除体顶点数: {len(cut_vertices)}")
    print(f"  切除体面片数: {len(cut_faces)}")
    
    # 4. 可视化
    print("\n步骤4: 生成三维可视化图像...")
    visualize_3d_model(
        cylinder_vertices, cylinder_faces,
        helix_points, cut_vertices, cut_faces,
        drill_diameter, total_length, spiral_angle
    )
    
    # 5. 如果安装了trimesh，可以尝试布尔运算（可选）
    if HAS_TRIMESH:
        print("\n步骤5: 尝试执行布尔减运算（切除操作）...")
        try:
            # 创建圆柱体mesh
            cylinder_mesh = trimesh.Trimesh(vertices=cylinder_vertices, faces=cylinder_faces)
            
            # 创建切除体mesh
            cut_mesh = trimesh.Trimesh(vertices=cut_vertices, faces=cut_faces)
            
            # 执行布尔减运算
            print("  正在执行布尔减运算（这可能需要一些时间）...")
            result_mesh = cylinder_mesh.difference(cut_mesh)
            
            if result_mesh is not None and len(result_mesh.vertices) > 0:
                print(f"  布尔运算成功！")
                print(f"  结果mesh顶点数: {len(result_mesh.vertices)}")
                print(f"  结果mesh面片数: {len(result_mesh.faces)}")
                
                # 保存结果mesh
                output_stl = 'spiral_groove_result.stl'
                result_mesh.export(output_stl)
                print(f"  结果已保存到: {output_stl}")
            else:
                print("  警告：布尔运算结果为空，可能由于mesh问题")
        except Exception as e:
            print(f"  布尔运算失败: {e}")
            print("  提示：这是正常的，布尔运算对mesh质量要求较高")
    else:
        print("\n提示：安装trimesh库可以执行真正的布尔减运算")
        print("  安装命令: pip install trimesh")
    
    print("\n" + "=" * 60)
    print("建模完成！")
    print("=" * 60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n程序被用户中断")
    except Exception as e:
        print(f"\n程序执行出错: {e}")
        import traceback
        traceback.print_exc()

