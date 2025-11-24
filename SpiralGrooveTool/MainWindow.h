#pragma once

#include <windows.h>
#include <gdiplus.h>
#include "SpiralCalculator.h"
#include "resource.h"

using namespace Gdiplus;
#pragma comment(lib, "gdiplus.lib")

/**
 * 主窗口类
 * 负责用户界面和图形绘制
 */
class MainWindow
{
public:
    MainWindow();
    ~MainWindow();
    
    bool Create(HINSTANCE hInstance, int nCmdShow);
    void OnPaint();
    void OnCommand(WPARAM wParam);
    
    static LRESULT CALLBACK WindowProc(HWND hwnd, UINT uMsg, WPARAM wParam, LPARAM lParam);
    
private:
    HWND m_hWnd;
    HWND m_hEditSpiralAngle;
    HWND m_hEditDrillDiameter;
    HWND m_hEditTotalLength;
    HWND m_hEditBladeWidth;
    HWND m_hEditBladeHeight;
    HWND m_hButtonGenerate;
    HWND m_hStaticInfo;
    
    // 图形数据
    std::vector<Point2D> m_centerPoints;
    std::vector<std::pair<Point2D, Point2D>> m_boundaries;
    std::vector<Point2D> m_toolOutline;
    
    // 绘制参数
    double m_scaleX;
    double m_scaleY;
    double m_offsetX;
    double m_offsetY;
    
    void CreateControls();
    void GenerateSpiral();
    void DrawGraphics(Graphics& graphics);
    void UpdateInfo();
    void DrawToAutoCAD();
    
    static MainWindow* s_pInstance;
};

