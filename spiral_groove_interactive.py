#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
螺旋排屑槽三维建模工具 - 交互式版本
生成可直接操控的结果：
1. STL文件（可在CAD软件中打开）
2. 交互式HTML文件（可在浏览器中旋转、缩放、平移）
"""

import math
import numpy as np
import sys

# 设置标准输出编码为UTF-8
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 检查并导入必要的库
HAS_TRIMESH = False
HAS_PLOTLY = False

try:
    import trimesh
    HAS_TRIMESH = True
except ImportError:
    print("提示：安装trimesh库可以生成STL文件")
    print("  安装命令: pip install trimesh")

try:
    import plotly.graph_objects as go
    import plotly.offline as pyo
    HAS_PLOTLY = True
except ImportError:
    print("提示：安装plotly库可以生成交互式HTML")
    print("  安装命令: pip install plotly")

def generate_cylinder_mesh(radius, height, resolution=50):
    """生成圆柱体mesh"""
    vertices = []
    faces = []
    
    top_center = np.array([0, 0, height])
    bottom_center = np.array([0, 0, 0])
    
    angles = np.linspace(0, 2 * math.pi, resolution, endpoint=False)
    
    bottom_circle = []
    for angle in angles:
        x = radius * math.cos(angle)
        y = radius * math.sin(angle)
        bottom_circle.append([x, y, 0])
        vertices.append([x, y, 0])
    
    top_circle = []
    for angle in angles:
        x = radius * math.cos(angle)
        y = radius * math.sin(angle)
        top_circle.append([x, y, height])
        vertices.append([x, y, height])
    
    bottom_center_idx = len(vertices)
    vertices.append(bottom_center.tolist())
    top_center_idx = len(vertices)
    vertices.append(top_center.tolist())
    
    # 底面
    for i in range(resolution):
        next_i = (i + 1) % resolution
        faces.append([i, next_i, bottom_center_idx])
    
    # 顶面
    for i in range(resolution):
        next_i = (i + 1) % resolution
        faces.append([resolution + i, top_center_idx, resolution + next_i])
    
    # 侧面
    for i in range(resolution):
        next_i = (i + 1) % resolution
        faces.append([i, resolution + i, next_i])
        faces.append([next_i, resolution + i, resolution + next_i])
    
    return np.array(vertices), np.array(faces)

def generate_helix_path(radius, pitch, height, num_points=300):
    """生成螺旋线路径"""
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
        
        dx = -radius * math.sin(t)
        dy = radius * math.cos(t)
        dz = pitch / (2 * math.pi)
        tangent = np.array([dx, dy, dz])
        tangent = tangent / np.linalg.norm(tangent)
        tangents.append(tangent)
    
    return np.array(points), np.array(tangents)

def generate_sweep_cut_mesh(helix_points, helix_tangents, cut_radius, resolution=16):
    """沿螺旋线路径生成扫描切除体"""
    vertices = []
    faces = []
    
    sections = []
    
    for i, (point, tangent) in enumerate(zip(helix_points, helix_tangents)):
        if i == 0:
            ref_vec = np.array([1, 0, 0])
        else:
            ref_vec = sections[-1][1]
        
        normal = np.cross(tangent, ref_vec)
        if np.linalg.norm(normal) < 1e-6:
            normal = np.cross(tangent, np.array([0, 1, 0]))
        normal = normal / np.linalg.norm(normal)
        
        binormal = np.cross(tangent, normal)
        binormal = binormal / np.linalg.norm(binormal)
        
        section_points = []
        angles = np.linspace(0, 2 * math.pi, resolution, endpoint=False)
        
        for angle in angles:
            offset = normal * (cut_radius * math.cos(angle)) + binormal * (cut_radius * math.sin(angle))
            section_point = point + offset
            section_points.append(section_point)
            vertices.append(section_point.tolist())
        
        sections.append((section_points, normal))
    
    num_sections = len(sections)
    for i in range(num_sections - 1):
        base_idx_curr = i * resolution
        base_idx_next = (i + 1) * resolution
        
        for j in range(resolution):
            next_j = (j + 1) % resolution
            
            faces.append([
                base_idx_curr + j,
                base_idx_curr + next_j,
                base_idx_next + j
            ])
            
            faces.append([
                base_idx_curr + next_j,
                base_idx_next + next_j,
                base_idx_next + j
            ])
    
    if num_sections > 0:
        first_center = np.mean(sections[0][0], axis=0)
        first_center_idx = len(vertices)
        vertices.append(first_center.tolist())
        
        for j in range(resolution):
            next_j = (j + 1) % resolution
            faces.append([0, first_center_idx, next_j])
        
        last_center = np.mean(sections[-1][0], axis=0)
        last_center_idx = len(vertices)
        vertices.append(last_center.tolist())
        
        last_base = (num_sections - 1) * resolution
        for j in range(resolution):
            next_j = (j + 1) % resolution
            faces.append([last_base + j, last_base + next_j, last_center_idx])
    
    return np.array(vertices), np.array(faces)

def create_final_mesh_with_boolean(cylinder_vertices, cylinder_faces, cut_vertices, cut_faces):
    """使用布尔运算创建最终带螺旋槽的圆柱体"""
    if not HAS_TRIMESH:
        return None
    
    try:
        print("  正在创建mesh对象...")
        cylinder_mesh = trimesh.Trimesh(vertices=cylinder_vertices, faces=cylinder_faces)
        cut_mesh = trimesh.Trimesh(vertices=cut_vertices, faces=cut_faces)
        
        print("  正在执行布尔减运算（这可能需要一些时间）...")
        result_mesh = cylinder_mesh.difference(cut_mesh)
        
        if result_mesh is not None and len(result_mesh.vertices) > 0:
            # 确保mesh是水密的
            if not result_mesh.is_watertight:
                print("  警告：mesh不是水密的，正在尝试修复...")
                result_mesh.fill_holes()
            
            return result_mesh
        else:
            print("  警告：布尔运算结果为空")
            return None
    except Exception as e:
        print(f"  布尔运算失败: {e}")
        return None

def save_stl_file(mesh, filename):
    """保存STL文件"""
    if mesh is None:
        return False
    
    try:
        mesh.export(filename)
        return True
    except Exception as e:
        print(f"  保存STL文件失败: {e}")
        return False

def create_interactive_html(cylinder_vertices, cylinder_faces, 
                           helix_points, cut_vertices, cut_faces,
                           final_mesh, drill_diameter, total_length, spiral_angle):
    """创建交互式HTML文件"""
    if not HAS_PLOTLY:
        return False
    
    try:
        fig = go.Figure()
        
        radius = drill_diameter / 2.0
        
        # 1. 绘制圆柱体（简化显示）
        angles = np.linspace(0, 2 * math.pi, 50)
        top_circle_x = radius * np.cos(angles)
        top_circle_y = radius * np.sin(angles)
        top_circle_z = np.full_like(angles, total_length)
        bottom_circle_x = radius * np.cos(angles)
        bottom_circle_y = radius * np.sin(angles)
        bottom_circle_z = np.zeros_like(angles)
        
        # 圆柱体顶面圆周
        fig.add_trace(go.Scatter3d(
            x=top_circle_x,
            y=top_circle_y,
            z=top_circle_z,
            mode='lines',
            name='圆柱体顶面',
            line=dict(color='blue', width=3)
        ))
        
        # 圆柱体底面圆周
        fig.add_trace(go.Scatter3d(
            x=bottom_circle_x,
            y=bottom_circle_y,
            z=bottom_circle_z,
            mode='lines',
            name='圆柱体底面',
            line=dict(color='blue', width=3)
        ))
        
        # 2. 绘制螺旋线
        fig.add_trace(go.Scatter3d(
            x=helix_points[:, 0],
            y=helix_points[:, 1],
            z=helix_points[:, 2],
            mode='lines',
            name='螺旋线路径',
            line=dict(color='red', width=4)
        ))
        
        # 3. 如果有最终mesh，绘制最终结果
        if final_mesh is not None:
            # 使用mesh的顶点和面片绘制
            fig.add_trace(go.Mesh3d(
                x=final_mesh.vertices[:, 0],
                y=final_mesh.vertices[:, 1],
                z=final_mesh.vertices[:, 2],
                i=final_mesh.faces[:, 0],
                j=final_mesh.faces[:, 1],
                k=final_mesh.faces[:, 2],
                name='最终模型（带螺旋槽）',
                opacity=0.7,
                color='lightblue',
                showscale=False
            ))
        else:
            # 如果没有最终mesh，显示切除体
            if len(cut_vertices) > 0:
                # 简化显示切除体（只显示中心线）
                cut_center_line = []
                resolution = 16  # 假设每个截面16个点
                for i in range(0, len(cut_vertices), resolution):
                    if i + resolution <= len(cut_vertices):
                        section_center = np.mean(cut_vertices[i:i+resolution], axis=0)
                        cut_center_line.append(section_center)
                
                if len(cut_center_line) > 1:
                    cut_center_line = np.array(cut_center_line)
                    fig.add_trace(go.Scatter3d(
                        x=cut_center_line[:, 0],
                        y=cut_center_line[:, 1],
                        z=cut_center_line[:, 2],
                        mode='lines+markers',
                        name='切除体中心线',
                        line=dict(color='orange', width=3),
                        marker=dict(size=3, color='orange')
                    ))
        
        # 设置布局
        info_text = f'钻头直径: {drill_diameter:.1f} mm<br>'
        info_text += f'总长度: {total_length:.1f} mm<br>'
        info_text += f'螺旋角: {spiral_angle:.1f}°'
        
        fig.update_layout(
            title={
                'text': f'螺旋排屑槽三维模型<br><span style="font-size:12px">{info_text}</span>',
                'x': 0.5,
                'xanchor': 'center'
            },
            scene=dict(
                xaxis_title='X (mm)',
                yaxis_title='Y (mm)',
                zaxis_title='Z (mm)',
                aspectmode='data',
                camera=dict(
                    eye=dict(x=1.5, y=1.5, z=1.5)
                )
            ),
            width=1200,
            height=800,
            margin=dict(l=0, r=0, t=80, b=0)
        )
        
        # 保存HTML文件
        html_file = 'spiral_groove_interactive.html'
        fig.write_html(html_file)
        
        return True
    except Exception as e:
        print(f"  创建交互式HTML失败: {e}")
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("螺旋排屑槽三维建模工具 - 交互式版本")
    print("=" * 60)
    print()
    
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
    
    # 计算参数
    radius = drill_diameter / 2.0
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
    print(f"  ✓ 圆柱体顶点数: {len(cylinder_vertices)}")
    print(f"  ✓ 圆柱体面片数: {len(cylinder_faces)}")
    
    # 2. 生成螺旋线路径
    print("\n步骤2: 生成螺旋线路径...")
    helix_points, helix_tangents = generate_helix_path(radius, pitch, total_length, num_points=300)
    print(f"  ✓ 螺旋线点数: {len(helix_points)}")
    
    # 3. 生成扫描切除体
    print("\n步骤3: 生成扫描切除体...")
    cut_vertices, cut_faces = generate_sweep_cut_mesh(
        helix_points, helix_tangents, cut_radius, resolution=16
    )
    print(f"  ✓ 切除体顶点数: {len(cut_vertices)}")
    print(f"  ✓ 切除体面片数: {len(cut_faces)}")
    
    # 4. 执行布尔运算生成最终mesh
    final_mesh = None
    if HAS_TRIMESH:
        print("\n步骤4: 执行布尔减运算生成最终模型...")
        final_mesh = create_final_mesh_with_boolean(
            cylinder_vertices, cylinder_faces, cut_vertices, cut_faces
        )
        
        if final_mesh is not None:
            print(f"  ✓ 最终mesh顶点数: {len(final_mesh.vertices)}")
            print(f"  ✓ 最终mesh面片数: {len(final_mesh.faces)}")
            
            # 保存STL文件
            print("\n步骤5: 保存STL文件...")
            stl_file = 'spiral_groove_model.stl'
            if save_stl_file(final_mesh, stl_file):
                print(f"  ✓ STL文件已保存: {stl_file}")
                print(f"  ✓ 可以在CAD软件（如AutoCAD、SolidWorks、Fusion360等）中打开此文件")
            else:
                print("  ✗ STL文件保存失败")
        else:
            print("  ✗ 布尔运算失败，无法生成最终mesh")
    else:
        print("\n步骤4: 跳过布尔运算（需要trimesh库）")
    
    # 5. 生成交互式HTML
    if HAS_PLOTLY:
        print("\n步骤6: 生成交互式HTML文件...")
        if create_interactive_html(
            cylinder_vertices, cylinder_faces,
            helix_points, cut_vertices, cut_faces,
            final_mesh, drill_diameter, total_length, spiral_angle
        ):
            html_file = 'spiral_groove_interactive.html'
            print(f"  ✓ 交互式HTML已保存: {html_file}")
            print(f"  ✓ 可以在浏览器中打开此文件，进行旋转、缩放、平移操作")
        else:
            print("  ✗ 交互式HTML生成失败")
    else:
        print("\n步骤6: 跳过交互式HTML生成（需要plotly库）")
    
    print("\n" + "=" * 60)
    print("建模完成！")
    print("=" * 60)
    
    # 输出文件列表
    print("\n生成的文件：")
    if HAS_TRIMESH and final_mesh is not None:
        print("  • spiral_groove_model.stl - STL格式3D模型（可在CAD软件中打开）")
    if HAS_PLOTLY:
        print("  • spiral_groove_interactive.html - 交互式3D可视化（可在浏览器中打开）")
    
    if not HAS_TRIMESH and not HAS_PLOTLY:
        print("\n提示：请安装以下库以生成完整结果：")
        print("  pip install trimesh plotly")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n程序被用户中断")
    except Exception as e:
        print(f"\n程序执行出错: {e}")
        import traceback
        traceback.print_exc()

