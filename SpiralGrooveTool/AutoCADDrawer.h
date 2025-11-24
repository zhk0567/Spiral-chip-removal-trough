#pragma once

#include "SpiralCalculator.h"
#include <vector>

/**
 * AutoCAD绘制器
 * 使用AutoCAD COM API生成和优化图形数据
 * AutoCAD没有直接生成螺旋排屑槽的API，但可以使用以下方法：
 * 1. AddHelix - 创建螺旋线（如果可用）
 * 2. AddPolyline - 创建多段线
 * 3. AddSpline - 创建样条曲线
 * 图形最终显示在本程序窗口中
 */
class AutoCADDrawer
{
public:
    /**
     * 使用AutoCAD API生成并优化图形数据
     * @param centerPoints 中心线点集（输入输出）
     * @param boundaries 边界点对集合（输入输出）
     * @param toolOutline 刀具轮廓点集（输入输出）
     * @return 是否成功
     */
    static bool GenerateWithAutoCADAPI(
        std::vector<Point2D>& centerPoints,
        std::vector<std::pair<Point2D, Point2D>>& boundaries,
        std::vector<Point2D>& toolOutline);
    
    /**
     * 尝试使用AutoCAD的AddHelix方法创建螺旋线（如果可用）
     * @param spiralAngle 螺旋角（度）
     * @param drillDiameter 钻头直径
     * @param totalLength 总长度
     * @param outputPoints 输出的点集
     * @return 是否成功
     */
    static bool CreateHelixWithAutoCAD(
        double spiralAngle,
        double drillDiameter,
        double totalLength,
        std::vector<Point2D>& outputPoints);
    
    /**
     * 使用AutoCAD的几何计算功能优化点数据
     * @param points 点集（输入输出）
     * @return 是否成功
     */
    static bool OptimizePointsWithAutoCAD(std::vector<Point2D>& points);
    
private:
    /**
     * 检查AutoCAD是否可用
     */
    static bool IsAutoCADAvailable();
    
    /**
     * 获取AutoCAD应用程序对象
     */
    static bool GetAutoCADApp(void** ppApp);
    
    /**
     * 使用AutoCAD的几何库进行平滑处理
     */
    static bool SmoothPolylineWithAutoCAD(const std::vector<Point2D>& input, std::vector<Point2D>& output);
    
    /**
     * 使用AutoCAD的AddPolyline创建多段线并获取优化后的点
     */
    static bool CreatePolylineWithAutoCAD(const std::vector<Point2D>& input, std::vector<Point2D>& output);
};
