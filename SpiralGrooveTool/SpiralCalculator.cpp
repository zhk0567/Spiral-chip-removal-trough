#include "SpiralCalculator.h"
#include <algorithm>
#include <cmath>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

std::vector<Point2D> SpiralCalculator::CalculateSpiralGroove(
    double spiralAngle,
    double drillDiameter,
    double totalLength,
    double bladeWidth,
    double bladeHeight,
    int pointsPerRevolution)
{
    std::vector<Point2D> points;
    
    // 将角度转换为弧度
    double angleRad = spiralAngle * M_PI / 180.0;
    
    // 计算螺旋参数
    double radius = drillDiameter / 2.0;
    double circumference = 2.0 * M_PI * radius;
    
    // 计算螺旋的螺距（pitch）
    // pitch = circumference / tan(螺旋角)
    double pitch = circumference / tan(angleRad);
    
    // 计算总圈数
    double totalRevolutions = totalLength / pitch;
    if (totalRevolutions <= 0 || std::isnan(totalRevolutions) || std::isinf(totalRevolutions))
    {
        totalRevolutions = 1.0;
        if (totalLength > 0) {
            pitch = totalLength;
        } else {
            pitch = 1.0;
        }
    }
    
    // 计算总点数
    int totalPoints = (int)(totalRevolutions * pointsPerRevolution);
    if (totalPoints < 10) totalPoints = 10;
    
    // 生成螺旋点（展开图）
    // X轴：沿钻头轴线的长度方向
    // Y轴：展开后的圆周方向
    // 在展开图中，螺旋线是一条斜线，斜率为 circumference / pitch
    for (int i = 0; i <= totalPoints; i++)
    {
        double t = (double)i / totalPoints;
        double x = t * totalLength; // X轴：沿钻头轴线的长度
        
        // Y轴：展开的圆周位置
        // 在展开图中：Y = (X / pitch) * circumference
        // 这等价于：Y = X * tan(螺旋角)
        double y = (x / pitch) * circumference;
        
        points.push_back(Point2D(x, y));
    }
    
    return points;
}

std::vector<std::pair<Point2D, Point2D>> SpiralCalculator::CalculateBoundaries(
    const std::vector<Point2D>& centerPoints,
    double bladeWidth)
{
    std::vector<std::pair<Point2D, Point2D>> boundaries;
    
    if (centerPoints.size() < 2)
        return boundaries;
    
    double halfWidth = bladeWidth / 2.0;
    
    // 在展开图中，边界线应该平行于中心线
    // 边界线在Y方向（圆周方向）上偏移±halfWidth
    // 因为展开图是：X轴=轴向，Y轴=圆周展开方向
    // 刀瓣宽度是在圆周方向上的宽度，所以在Y方向上偏移
    
    // 生成边界点
    // 边界线平行于中心线，在Y方向上偏移
    for (size_t i = 0; i < centerPoints.size(); i++)
    {
        Point2D center = centerPoints[i];
        
        // 左边界：Y方向向上偏移（Y值增加）
        // 右边界：Y方向向下偏移（Y值减少）
        // 注意：这里"左"和"右"是相对于中心线的，在展开图中是Y方向的上下
        Point2D left(center.x, center.y + halfWidth);
        Point2D right(center.x, center.y - halfWidth);
        
        boundaries.push_back(std::make_pair(left, right));
    }
    
    return boundaries;
}

std::vector<Point2D> SpiralCalculator::CalculateToolOutline(
    double drillDiameter,
    double totalLength)
{
    std::vector<Point2D> outline;
    double radius = drillDiameter / 2.0;
    
    // 生成矩形轮廓（展开图）
    // 在展开图中，刀具是一个矩形
    // Y轴范围：-radius 到 +radius（圆周展开方向）
    // X轴范围：0 到 totalLength（轴向）
    
    // 左下角
    outline.push_back(Point2D(0, -radius));
    // 右下角
    outline.push_back(Point2D(totalLength, -radius));
    // 右上角
    outline.push_back(Point2D(totalLength, radius));
    // 左上角
    outline.push_back(Point2D(0, radius));
    // 闭合
    outline.push_back(Point2D(0, -radius));
    
    return outline;
}
