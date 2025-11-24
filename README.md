# 螺旋排屑槽绘制工具

## 简介

独立的Windows图形绘制工具，使用AutoCAD COM API生成和优化图形数据，图形显示在本程序窗口中。

## 功能

- 输入参数：螺旋角、钻头直径、钻头总长、刀瓣宽度、刀瓣高度
- 自动生成二维展开图
- 使用AutoCAD API优化图形数据（如果AutoCAD可用）
- 在本程序窗口中显示图形

## 编译和运行

### 使用CLion

1. 打开CLion
2. 选择 `File` -> `Open`，选择项目根目录
3. CLion会自动检测CMakeLists.txt并配置项目
4. 点击运行按钮或按 `Shift+F10` 运行程序

### 使用CMake命令行

```bash
mkdir build
cd build
cmake ..
cmake --build . --config Debug
```

运行：
```bash
bin/SpiralGrooveTool.exe
```

## 使用

1. 运行程序后，在左侧输入框中输入5个参数
2. 点击"生成图形（使用AutoCAD API）"按钮
3. 程序会尝试使用AutoCAD API优化图形数据（如果AutoCAD已安装）
4. 图形显示在右侧窗口中

## 技术

- 语言：C++
- CAD接口：AutoCAD COM API（用于图形数据优化）
- 图形显示：Windows GDI+
- 构建系统：CMake
- 平台：Windows 7+
- 可选依赖：AutoCAD（如果已安装，会使用其API优化图形）

## 关于AutoCAD API

**注意**：AutoCAD本身**没有直接生成螺旋排屑槽的API**。本程序使用以下方法：

1. **自定义计算**：使用数学公式计算螺旋槽的展开图
2. **AutoCAD优化**（可选）：如果AutoCAD可用，使用其几何计算API优化点数据
3. **可用的AutoCAD API**：
   - `AddPolyline` - 创建多段线
   - `AddSpline` - 创建样条曲线
   - `AddHelix` - 创建螺旋线（部分版本支持，但主要用于3D，不适用于2D展开图）

本程序主要使用自定义算法生成2D展开图，AutoCAD API仅用于可选的几何优化。

## 项目结构

```
.
├── CMakeLists.txt          # CMake配置文件
├── SpiralGrooveTool/
│   ├── main.cpp            # 程序入口
│   ├── MainWindow.h/cpp   # 主窗口和绘制
│   ├── SpiralCalculator.h/cpp # 螺旋槽计算
│   ├── AutoCADDrawer.h/cpp # AutoCAD API调用（图形优化）
│   └── SpiralGrooveTool.rc  # 资源文件
└── README.md
```
