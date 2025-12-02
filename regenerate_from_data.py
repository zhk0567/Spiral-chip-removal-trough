#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从数据文件重新生成侧视图图像
"""

from spiral_groove_side_view import load_and_draw_from_data

if __name__ == "__main__":
    data_file = 'spiral_groove_side_view_lines_data.json'
    output_file = 'spiral_groove_from_data.png'
    
    print("从数据文件重新生成侧视图图像...")
    load_and_draw_from_data(data_file, output_file, dpi=300, figsize=(12, 8))
    print(f"\n完成！输出文件: {output_file}")

