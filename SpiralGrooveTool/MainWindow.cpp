#include "MainWindow.h"
#include "AutoCADDrawer.h"
#include <sstream>
#include <iomanip>

MainWindow* MainWindow::s_pInstance = nullptr;

MainWindow::MainWindow()
    : m_hWnd(NULL)
    , m_hEditSpiralAngle(NULL)
    , m_hEditDrillDiameter(NULL)
    , m_hEditTotalLength(NULL)
    , m_hEditBladeWidth(NULL)
    , m_hEditBladeHeight(NULL)
    , m_hButtonGenerate(NULL)
    , m_hStaticInfo(NULL)
    , m_scaleX(1.0)
    , m_scaleY(1.0)
    , m_offsetX(0.0)
    , m_offsetY(0.0)
{
}

MainWindow::~MainWindow()
{
}

bool MainWindow::Create(HINSTANCE hInstance, int nCmdShow)
{
    s_pInstance = this;
    
    // 注册窗口类
    WNDCLASSEX wcex = {};
    wcex.cbSize = sizeof(WNDCLASSEX);
    wcex.style = CS_HREDRAW | CS_VREDRAW;
    wcex.lpfnWndProc = WindowProc;
    wcex.cbClsExtra = 0;
    wcex.cbWndExtra = 0;
    wcex.hInstance = hInstance;
    wcex.hIcon = NULL;
    wcex.hCursor = LoadCursor(NULL, IDC_ARROW);
    wcex.hbrBackground = (HBRUSH)(COLOR_WINDOW + 1);
    wcex.lpszMenuName = NULL;
    wcex.lpszClassName = L"SpiralGrooveToolWindow";
    wcex.hIconSm = NULL;
    
    if (!RegisterClassEx(&wcex))
        return false;
    
    // 创建窗口
    m_hWnd = CreateWindowEx(
        0,
        L"SpiralGrooveToolWindow",
        L"螺旋排屑槽绘制工具",
        WS_OVERLAPPEDWINDOW,
        CW_USEDEFAULT, CW_USEDEFAULT,
        1200, 800,
        NULL, NULL, hInstance, this);
    
    if (!m_hWnd)
        return false;
    
    CreateControls();
    
    ShowWindow(m_hWnd, nCmdShow);
    UpdateWindow(m_hWnd);
    
    return true;
}

void MainWindow::CreateControls()
{
    // 创建输入控件
    int x = 20, y = 20;
    int labelWidth = 120;
    int editWidth = 100;
    int spacing = 30;
    
    // 螺旋角
    CreateWindow(L"STATIC", L"螺旋角（度）:", WS_VISIBLE | WS_CHILD,
        x, y, labelWidth, 20, m_hWnd, NULL, NULL, NULL);
    m_hEditSpiralAngle = CreateWindow(L"EDIT", L"30",
        WS_VISIBLE | WS_CHILD | WS_BORDER | ES_NUMBER,
        x + labelWidth, y, editWidth, 20, m_hWnd, NULL, NULL, NULL);
    y += spacing;
    
    // 钻头直径
    CreateWindow(L"STATIC", L"钻头直径（mm）:", WS_VISIBLE | WS_CHILD,
        x, y, labelWidth, 20, m_hWnd, NULL, NULL, NULL);
    m_hEditDrillDiameter = CreateWindow(L"EDIT", L"10",
        WS_VISIBLE | WS_CHILD | WS_BORDER | ES_NUMBER,
        x + labelWidth, y, editWidth, 20, m_hWnd, NULL, NULL, NULL);
    y += spacing;
    
    // 钻头总长
    CreateWindow(L"STATIC", L"钻头总长（mm）:", WS_VISIBLE | WS_CHILD,
        x, y, labelWidth, 20, m_hWnd, NULL, NULL, NULL);
    m_hEditTotalLength = CreateWindow(L"EDIT", L"50",
        WS_VISIBLE | WS_CHILD | WS_BORDER | ES_NUMBER,
        x + labelWidth, y, editWidth, 20, m_hWnd, NULL, NULL, NULL);
    y += spacing;
    
    // 刀瓣宽度
    CreateWindow(L"STATIC", L"刀瓣宽度（mm）:", WS_VISIBLE | WS_CHILD,
        x, y, labelWidth, 20, m_hWnd, NULL, NULL, NULL);
    m_hEditBladeWidth = CreateWindow(L"EDIT", L"2",
        WS_VISIBLE | WS_CHILD | WS_BORDER | ES_NUMBER,
        x + labelWidth, y, editWidth, 20, m_hWnd, NULL, NULL, NULL);
    y += spacing;
    
    // 刀瓣高度
    CreateWindow(L"STATIC", L"刀瓣高度（mm）:", WS_VISIBLE | WS_CHILD,
        x, y, labelWidth, 20, m_hWnd, NULL, NULL, NULL);
    m_hEditBladeHeight = CreateWindow(L"EDIT", L"1",
        WS_VISIBLE | WS_CHILD | WS_BORDER | ES_NUMBER,
        x + labelWidth, y, editWidth, 20, m_hWnd, NULL, NULL, NULL);
    y += spacing;
    
    // 生成按钮
    m_hButtonGenerate = CreateWindow(L"BUTTON", L"生成图形（使用AutoCAD API）",
        WS_VISIBLE | WS_CHILD | BS_PUSHBUTTON,
        x, y, 250, 30, m_hWnd, (HMENU)IDC_BUTTON_GENERATE, NULL, NULL);
    y += 40;
    
    // 信息显示
    m_hStaticInfo = CreateWindow(L"STATIC", L"请输入参数并点击生成",
        WS_VISIBLE | WS_CHILD,
        x, y, 400, 100, m_hWnd, NULL, NULL, NULL);
}

void MainWindow::GenerateSpiral()
{
    // 获取输入参数
    wchar_t buffer[256];
    
    GetWindowText(m_hEditSpiralAngle, buffer, 256);
    double spiralAngle = _wtof(buffer);
    
    GetWindowText(m_hEditDrillDiameter, buffer, 256);
    double drillDiameter = _wtof(buffer);
    
    GetWindowText(m_hEditTotalLength, buffer, 256);
    double totalLength = _wtof(buffer);
    
    GetWindowText(m_hEditBladeWidth, buffer, 256);
    double bladeWidth = _wtof(buffer);
    
    GetWindowText(m_hEditBladeHeight, buffer, 256);
    double bladeHeight = _wtof(buffer);
    
    // 验证参数
    if (spiralAngle <= 0 || spiralAngle >= 90 ||
        drillDiameter <= 0 || totalLength <= 0 ||
        bladeWidth <= 0 || bladeHeight <= 0)
    {
        MessageBox(m_hWnd, L"请输入有效的参数值！", L"错误", MB_OK | MB_ICONERROR);
        return;
    }
    
    // 计算螺旋槽
    m_centerPoints = SpiralCalculator::CalculateSpiralGroove(
        spiralAngle, drillDiameter, totalLength, bladeWidth, bladeHeight);
    
    m_boundaries = SpiralCalculator::CalculateBoundaries(m_centerPoints, bladeWidth);
    m_toolOutline = SpiralCalculator::CalculateToolOutline(drillDiameter, totalLength);
    
    // 计算缩放和偏移（包含边界线）
    if (!m_centerPoints.empty())
    {
        double minX = m_centerPoints[0].x, maxX = m_centerPoints[0].x;
        double minY = m_centerPoints[0].y, maxY = m_centerPoints[0].y;
        
        // 计算中心线的范围
        for (const auto& pt : m_centerPoints)
        {
            minX = std::min(minX, pt.x);
            maxX = std::max(maxX, pt.x);
            minY = std::min(minY, pt.y);
            maxY = std::max(maxY, pt.y);
        }
        
        // 计算边界线的范围
        for (const auto& boundary : m_boundaries)
        {
            minX = std::min(minX, std::min(boundary.first.x, boundary.second.x));
            maxX = std::max(maxX, std::max(boundary.first.x, boundary.second.x));
            minY = std::min(minY, std::min(boundary.first.y, boundary.second.y));
            maxY = std::max(maxY, std::max(boundary.first.y, boundary.second.y));
        }
        
        // 计算刀具轮廓的范围
        for (const auto& pt : m_toolOutline)
        {
            minX = std::min(minX, pt.x);
            maxX = std::max(maxX, pt.x);
            minY = std::min(minY, pt.y);
            maxY = std::max(maxY, pt.y);
        }
        
        RECT rect;
        GetClientRect(m_hWnd, &rect);
        int clientWidth = rect.right - rect.left - 250; // 留出左侧控件空间
        int clientHeight = rect.bottom - rect.top - 20;
        
        double rangeX = maxX - minX;
        double rangeY = maxY - minY;
        
        // 添加一些边距
        if (rangeX > 0 && rangeY > 0)
        {
            m_scaleX = clientWidth / rangeX * 0.85;
            m_scaleY = clientHeight / rangeY * 0.85;
            // 使用统一的缩放比例，保持纵横比
            double scale = std::min(m_scaleX, m_scaleY);
            m_scaleX = scale;
            m_scaleY = scale;
            m_offsetX = 250 + (clientWidth - rangeX * m_scaleX) / 2 - minX * m_scaleX;
            m_offsetY = 10 + (clientHeight - rangeY * m_scaleY) / 2 - minY * m_scaleY;
        }
    }
    
    UpdateInfo();
    InvalidateRect(m_hWnd, NULL, TRUE);
}

void MainWindow::UpdateInfo()
{
    std::wstringstream ss;
    ss << L"参数信息:\n";
    ss << L"中心线点数: " << m_centerPoints.size() << L"\n";
    if (!m_centerPoints.empty())
    {
        ss << std::fixed << std::setprecision(2);
        ss << L"X范围: " << m_centerPoints[0].x << L" - " 
           << m_centerPoints.back().x << L"\n";
        ss << L"Y范围: " << m_centerPoints[0].y << L" - " 
           << m_centerPoints.back().y;
    }
    SetWindowText(m_hStaticInfo, ss.str().c_str());
}

void MainWindow::DrawGraphics(Graphics& graphics)
{
    graphics.SetSmoothingMode(SmoothingModeAntiAlias);
    
    // 清除背景
    graphics.Clear(Color(255, 255, 255));
    
    if (m_centerPoints.empty())
        return;
    
    // 绘制刀具轮廓
    if (m_toolOutline.size() >= 2)
    {
        Pen outlinePen(Color(200, 200, 200), 1.0f);
        PointF* points = new PointF[m_toolOutline.size()];
        for (size_t i = 0; i < m_toolOutline.size(); i++)
        {
            points[i].X = (float)(m_toolOutline[i].x * m_scaleX + m_offsetX);
            points[i].Y = (float)(m_toolOutline[i].y * m_scaleY + m_offsetY);
        }
        graphics.DrawLines(&outlinePen, points, (int)m_toolOutline.size());
        delete[] points;
    }
    
    // 绘制螺旋槽边界
    if (m_boundaries.size() >= 2)
    {
        // 左边界
        Pen leftPen(Color(255, 0, 0), 2.0f); // 红色
        PointF* leftPoints = new PointF[m_boundaries.size()];
        for (size_t i = 0; i < m_boundaries.size(); i++)
        {
            leftPoints[i].X = (float)(m_boundaries[i].first.x * m_scaleX + m_offsetX);
            leftPoints[i].Y = (float)(m_boundaries[i].first.y * m_scaleY + m_offsetY);
        }
        graphics.DrawLines(&leftPen, leftPoints, (int)m_boundaries.size());
        delete[] leftPoints;
        
        // 右边界
        Pen rightPen(Color(0, 0, 255), 2.0f); // 蓝色
        PointF* rightPoints = new PointF[m_boundaries.size()];
        for (size_t i = 0; i < m_boundaries.size(); i++)
        {
            rightPoints[i].X = (float)(m_boundaries[i].second.x * m_scaleX + m_offsetX);
            rightPoints[i].Y = (float)(m_boundaries[i].second.y * m_scaleY + m_offsetY);
        }
        graphics.DrawLines(&rightPen, rightPoints, (int)m_boundaries.size());
        delete[] rightPoints;
    }
    
    // 绘制中心线
    if (m_centerPoints.size() >= 2)
    {
        Pen centerPen(Color(0, 255, 0), 1.0f); // 绿色
        PointF* centerPoints = new PointF[m_centerPoints.size()];
        for (size_t i = 0; i < m_centerPoints.size(); i++)
        {
            centerPoints[i].X = (float)(m_centerPoints[i].x * m_scaleX + m_offsetX);
            centerPoints[i].Y = (float)(m_centerPoints[i].y * m_scaleY + m_offsetY);
        }
        graphics.DrawLines(&centerPen, centerPoints, (int)m_centerPoints.size());
        delete[] centerPoints;
    }
}

void MainWindow::OnPaint()
{
    PAINTSTRUCT ps;
    HDC hdc = BeginPaint(m_hWnd, &ps);
    
    Graphics graphics(hdc);
    DrawGraphics(graphics);
    
    EndPaint(m_hWnd, &ps);
}

void MainWindow::DrawToAutoCAD()
{
    if (m_centerPoints.empty())
    {
        MessageBox(m_hWnd, L"请先生成螺旋槽数据！", L"提示", MB_OK | MB_ICONINFORMATION);
        return;
    }
    
    // 使用AutoCAD API优化图形数据（图形显示在本程序窗口中）
    if (AutoCADDrawer::GenerateWithAutoCADAPI(m_centerPoints, m_boundaries, m_toolOutline))
    {
        // 刷新显示
        InvalidateRect(m_hWnd, NULL, TRUE);
        UpdateWindow(m_hWnd);
    }
    else
    {
        // AutoCAD不可用时，使用原始数据
        InvalidateRect(m_hWnd, NULL, TRUE);
        UpdateWindow(m_hWnd);
    }
}

void MainWindow::OnCommand(WPARAM wParam)
{
    if (LOWORD(wParam) == IDC_BUTTON_GENERATE)
    {
        GenerateSpiral();
        DrawToAutoCAD();
    }
}

LRESULT CALLBACK MainWindow::WindowProc(HWND hwnd, UINT uMsg, WPARAM wParam, LPARAM lParam)
{
    MainWindow* pWindow = nullptr;
    
    if (uMsg == WM_NCCREATE)
    {
        CREATESTRUCT* pCreate = (CREATESTRUCT*)lParam;
        pWindow = (MainWindow*)pCreate->lpCreateParams;
        SetWindowLongPtr(hwnd, GWLP_USERDATA, (LONG_PTR)pWindow);
    }
    else
    {
        pWindow = (MainWindow*)GetWindowLongPtr(hwnd, GWLP_USERDATA);
    }
    
    if (pWindow)
    {
        switch (uMsg)
        {
        case WM_PAINT:
            pWindow->OnPaint();
            return 0;
            
        case WM_COMMAND:
            pWindow->OnCommand(wParam);
            return 0;
            
        case WM_DESTROY:
            PostQuitMessage(0);
            return 0;
        }
    }
    
    return DefWindowProc(hwnd, uMsg, wParam, lParam);
}

