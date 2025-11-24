#pragma once

#include <vector>
#include <cmath>

/**
 * 点结构体（二维）
 */
struct Point2D
{
    double x;
    double y;
    
    Point2D() : x(0), y(0) {}
    Point2D(double x_, double y_) : x(x_), y(y_) {}
};

/**
 * 螺旋槽计算器
 * 输入参数：螺旋角、钻头直径、钻头总长、刀瓣宽度、刀瓣高度
 * 输出：螺旋排屑槽的二维图形点集
 */
class SpiralCalculator
{
public:
    /**
     * 计算螺旋排屑槽的点坐标
     * @param spiralAngle 螺旋角（度）
     * @param drillDiameter 钻头直径（mm）
     * @param totalLength 钻头总长（mm）
     * @param bladeWidth 刀瓣宽度（mm）
     * @param bladeHeight 刀瓣高度（mm）
     * @param pointsPerRevolution 每圈采样点数，默认100
     * @return 螺旋槽中心线点集合
     */
    static std::vector<Point2D> CalculateSpiralGroove(
        double spiralAngle,
        double drillDiameter,
        double totalLength,
        double bladeWidth,
        double bladeHeight,
        int pointsPerRevolution = 100);
    
    /**
     * 计算螺旋槽的左右边界点
     * @param centerPoints 中心线点集
     * @param bladeWidth 刀瓣宽度（mm）
     * @return 左右边界点对集合（first=左边界，second=右边界）
     */
    static std::vector<std::pair<Point2D, Point2D>> CalculateBoundaries(
        const std::vector<Point2D>& centerPoints,
        double bladeWidth);
    
    /**
     * 计算刀具轮廓点
     * @param drillDiameter 钻头直径（mm）
     * @param totalLength 钻头总长（mm）
     * @return 刀具轮廓点集合（矩形轮廓）
     */
    static std::vector<Point2D> CalculateToolOutline(
        double drillDiameter,
        double totalLength);
};

