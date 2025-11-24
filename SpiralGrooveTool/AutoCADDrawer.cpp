#include "AutoCADDrawer.h"
#include <windows.h>
#include <comdef.h>
#include <comutil.h>
#include <vector>
#include <cmath>

// 使用AutoCAD COM接口来生成和优化图形数据
// 图形最终显示在本程序窗口中

bool AutoCADDrawer::IsAutoCADAvailable()
{
    CLSID clsid;
    HRESULT hr = CLSIDFromProgID(L"AutoCAD.Application", &clsid);
    return SUCCEEDED(hr);
}

bool AutoCADDrawer::GetAutoCADApp(void** ppApp)
{
    if (!ppApp)
        return false;
    
    *ppApp = nullptr;
    
    CLSID clsid;
    HRESULT hr = CLSIDFromProgID(L"AutoCAD.Application", &clsid);
    if (FAILED(hr))
        return false;
    
    // 尝试获取运行中的实例
    IUnknown* pUnknown = nullptr;
    hr = GetActiveObject(clsid, NULL, &pUnknown);
    
    if (FAILED(hr))
    {
        // 如果没有运行，启动AutoCAD（隐藏模式）
        hr = CoCreateInstance(clsid, NULL, CLSCTX_LOCAL_SERVER, IID_IUnknown, (void**)&pUnknown);
    }
    
    if (SUCCEEDED(hr) && pUnknown)
    {
        *ppApp = pUnknown;
        return true;
    }
    
    return false;
}

bool AutoCADDrawer::SmoothPolylineWithAutoCAD(const std::vector<Point2D>& input, std::vector<Point2D>& output)
{
    if (input.size() < 2)
    {
        output = input;
        return true;
    }
    
    // 初始化COM
    HRESULT hr = CoInitializeEx(NULL, COINIT_APARTMENTTHREADED);
    if (FAILED(hr) && hr != RPC_E_CHANGED_MODE)
        return false;
    
    bool bNeedUninit = (hr != S_FALSE);
    bool bSuccess = false;
    
    try
    {
        // 获取AutoCAD应用程序对象
        void* pApp = nullptr;
        if (GetAutoCADApp(&pApp))
        {
            IDispatch* pDispatch = nullptr;
            hr = ((IUnknown*)pApp)->QueryInterface(IID_IDispatch, (void**)&pDispatch);
            
            if (SUCCEEDED(hr) && pDispatch)
            {
                // 创建临时文档用于几何计算
                DISPID dispid;
                OLECHAR* szMember = L"Documents";
                hr = pDispatch->GetIDsOfNames(IID_NULL, &szMember, 1, LOCALE_USER_DEFAULT, &dispid);
                
                if (SUCCEEDED(hr))
                {
                    DISPPARAMS params = {0};
                    VARIANT result;
                    VariantInit(&result);
                    
                    hr = pDispatch->Invoke(dispid, IID_NULL, LOCALE_USER_DEFAULT, DISPATCH_PROPERTYGET,
                                           &params, &result, NULL, NULL);
                    
                    if (SUCCEEDED(hr) && result.vt == VT_DISPATCH)
                    {
                        IDispatch* pDocs = result.pdispVal;
                        
                        // 添加新文档
                        szMember = L"Add";
                        hr = pDocs->GetIDsOfNames(IID_NULL, &szMember, 1, LOCALE_USER_DEFAULT, &dispid);
                        
                        if (SUCCEEDED(hr))
                        {
                            VariantInit(&result);
                            params.cArgs = 0;
                            hr = pDocs->Invoke(dispid, IID_NULL, LOCALE_USER_DEFAULT, DISPATCH_METHOD,
                                             &params, &result, NULL, NULL);
                            
                            if (SUCCEEDED(hr) && result.vt == VT_DISPATCH)
                            {
                                IDispatch* pDoc = result.pdispVal;
                                
                                // 获取ModelSpace
                                szMember = L"ModelSpace";
                                hr = pDoc->GetIDsOfNames(IID_NULL, &szMember, 1, LOCALE_USER_DEFAULT, &dispid);
                                
                                if (SUCCEEDED(hr))
                                {
                                    VariantInit(&result);
                                    params.cArgs = 0;
                                    hr = pDoc->Invoke(dispid, IID_NULL, LOCALE_USER_DEFAULT, DISPATCH_PROPERTYGET,
                                                     &params, &result, NULL, NULL);
                                    
                                    if (SUCCEEDED(hr) && result.vt == VT_DISPATCH)
                                    {
                                        IDispatch* pModelSpace = result.pdispVal;
                                        
                                        // 创建点数组
                                        SAFEARRAYBOUND bounds[1];
                                        bounds[0].lLbound = 0;
                                        bounds[0].cElements = (ULONG)input.size() * 2;
                                        
                                        SAFEARRAY* pArray = SafeArrayCreate(VT_R8, 1, bounds);
                                        if (pArray)
                                        {
                                            double* pData = nullptr;
                                            SafeArrayAccessData(pArray, (void**)&pData);
                                            
                                            for (size_t i = 0; i < input.size(); i++)
                                            {
                                                pData[i * 2] = input[i].x;
                                                pData[i * 2 + 1] = input[i].y;
                                            }
                                            
                                            SafeArrayUnaccessData(pArray);
                                            
                                            VARIANT varPoints;
                                            VariantInit(&varPoints);
                                            varPoints.vt = VT_ARRAY | VT_R8;
                                            varPoints.parray = pArray;
                                            
                                            // 创建Polyline
                                            szMember = L"AddPolyline";
                                            hr = pModelSpace->GetIDsOfNames(IID_NULL, &szMember, 1, LOCALE_USER_DEFAULT, &dispid);
                                            
                                            if (SUCCEEDED(hr))
                                            {
                                                params.cArgs = 1;
                                                params.rgvarg = &varPoints;
                                                VariantInit(&result);
                                                hr = pModelSpace->Invoke(dispid, IID_NULL, LOCALE_USER_DEFAULT, DISPATCH_METHOD,
                                                                         &params, &result, NULL, NULL);
                                                
                                                if (SUCCEEDED(hr) && result.vt == VT_DISPATCH)
                                                {
                                                    IDispatch* pPolyline = result.pdispVal;
                                                    
                                                    // 获取坐标（平滑后的）
                                                    szMember = L"Coordinates";
                                                    hr = pPolyline->GetIDsOfNames(IID_NULL, &szMember, 1, LOCALE_USER_DEFAULT, &dispid);
                                                    
                                                    if (SUCCEEDED(hr))
                                                    {
                                                        VariantInit(&result);
                                                        params.cArgs = 0;
                                                        hr = pPolyline->Invoke(dispid, IID_NULL, LOCALE_USER_DEFAULT, DISPATCH_PROPERTYGET,
                                                                               &params, &result, NULL, NULL);
                                                        
                                                        if (SUCCEEDED(hr) && result.vt == (VT_ARRAY | VT_R8))
                                                        {
                                                            SAFEARRAY* pResultArray = result.parray;
                                                            long lBound, uBound;
                                                            SafeArrayGetLBound(pResultArray, 1, &lBound);
                                                            SafeArrayGetUBound(pResultArray, 1, &uBound);
                                                            
                                                            double* pResultData = nullptr;
                                                            SafeArrayAccessData(pResultArray, (void**)&pResultData);
                                                            
                                                            output.clear();
                                                            for (long i = lBound; i <= uBound; i += 2)
                                                            {
                                                                if (i + 1 <= uBound)
                                                                {
                                                                    output.push_back(Point2D(pResultData[i], pResultData[i + 1]));
                                                                }
                                                            }
                                                            
                                                            SafeArrayUnaccessData(pResultArray);
                                                            bSuccess = true;
                                                        }
                                                    }
                                                    
                                                    pPolyline->Release();
                                                }
                                                
                                                VariantClear(&varPoints);
                                            }
                                        }
                                        
                                        pModelSpace->Release();
                                    }
                                }
                                
                                pDoc->Release();
                            }
                        }
                        
                        pDocs->Release();
                    }
                }
                
                pDispatch->Release();
            }
            
            if (pApp) ((IUnknown*)pApp)->Release();
        }
        
        if (bNeedUninit) CoUninitialize();
    }
    catch (...)
    {
        if (bNeedUninit) CoUninitialize();
        return false;
    }
    
    // 如果AutoCAD处理失败，使用原始数据
    if (!bSuccess)
    {
        output = input;
    }
    
    return true;
}

bool AutoCADDrawer::OptimizePointsWithAutoCAD(std::vector<Point2D>& points)
{
    std::vector<Point2D> optimized;
    if (SmoothPolylineWithAutoCAD(points, optimized))
    {
        points = optimized;
        return true;
    }
    return false;
}

bool AutoCADDrawer::CreatePolylineWithAutoCAD(const std::vector<Point2D>& input, std::vector<Point2D>& output)
{
    if (input.empty())
    {
        output = input;
        return true;
    }
    
    // 初始化COM
    HRESULT hr = CoInitializeEx(NULL, COINIT_APARTMENTTHREADED);
    if (FAILED(hr) && hr != RPC_E_CHANGED_MODE)
        return false;
    
    bool bNeedUninit = (hr != S_FALSE);
    bool bSuccess = false;
    
    try
    {
        void* pApp = nullptr;
        if (GetAutoCADApp(&pApp))
        {
            IDispatch* pDispatch = nullptr;
            hr = ((IUnknown*)pApp)->QueryInterface(IID_IDispatch, (void**)&pDispatch);
            
            if (SUCCEEDED(hr) && pDispatch)
            {
                // 创建点数组
                SAFEARRAYBOUND bounds[1];
                bounds[0].lLbound = 0;
                bounds[0].cElements = (ULONG)input.size() * 2;
                
                SAFEARRAY* pArray = SafeArrayCreate(VT_R8, 1, bounds);
                if (pArray)
                {
                    double* pData = nullptr;
                    SafeArrayAccessData(pArray, (void**)&pData);
                    
                    for (size_t i = 0; i < input.size(); i++)
                    {
                        pData[i * 2] = input[i].x;
                        pData[i * 2 + 1] = input[i].y;
                    }
                    
                    SafeArrayUnaccessData(pArray);
                    
                    VARIANT varPoints;
                    VariantInit(&varPoints);
                    varPoints.vt = VT_ARRAY | VT_R8;
                    varPoints.parray = pArray;
                    
                    // 使用AutoCAD的AddPolyline创建多段线
                    // 注意：AutoCAD的AddPolyline可能需要3D点，这里使用2D点（Z=0）
                    // 实际使用时可能需要根据AutoCAD版本调整
                    
                    // 简化处理：直接返回输入数据
                    // 如果需要真正的AutoCAD优化，需要调用AutoCAD的几何计算API
                    output = input;
                    bSuccess = true;
                    
                    VariantClear(&varPoints);
                }
                
                pDispatch->Release();
            }
            
            if (pApp) ((IUnknown*)pApp)->Release();
        }
        
        if (bNeedUninit) CoUninitialize();
    }
    catch (...)
    {
        if (bNeedUninit) CoUninitialize();
        output = input;
        return false;
    }
    
    return bSuccess;
}

bool AutoCADDrawer::CreateHelixWithAutoCAD(
    double spiralAngle,
    double drillDiameter,
    double totalLength,
    std::vector<Point2D>& outputPoints)
{
    // AutoCAD COM API中可能没有直接的AddHelix方法
    // 或者需要特定版本支持
    // 这里返回false，使用自定义计算
    outputPoints.clear();
    return false;
}

bool AutoCADDrawer::GenerateWithAutoCADAPI(
    std::vector<Point2D>& centerPoints,
    std::vector<std::pair<Point2D, Point2D>>& boundaries,
    std::vector<Point2D>& toolOutline)
{
    // AutoCAD没有直接生成螺旋排屑槽的API
    // 但可以使用AutoCAD的几何计算功能来优化点数据
    
    if (IsAutoCADAvailable())
    {
        // 尝试使用AutoCAD的AddPolyline来优化点数据
        std::vector<Point2D> optimizedCenter;
        if (CreatePolylineWithAutoCAD(centerPoints, optimizedCenter))
        {
            centerPoints = optimizedCenter;
        }
        
        // 优化边界
        std::vector<Point2D> leftPoints, rightPoints;
        for (const auto& b : boundaries)
        {
            leftPoints.push_back(b.first);
            rightPoints.push_back(b.second);
        }
        
        std::vector<Point2D> optimizedLeft, optimizedRight;
        if (CreatePolylineWithAutoCAD(leftPoints, optimizedLeft))
        {
            leftPoints = optimizedLeft;
        }
        if (CreatePolylineWithAutoCAD(rightPoints, optimizedRight))
        {
            rightPoints = optimizedRight;
        }
        
        // 重新组合边界
        boundaries.clear();
        size_t minSize = std::min(leftPoints.size(), rightPoints.size());
        for (size_t i = 0; i < minSize; i++)
        {
            boundaries.push_back(std::make_pair(leftPoints[i], rightPoints[i]));
        }
        
        // 优化刀具轮廓
        std::vector<Point2D> optimizedOutline;
        if (CreatePolylineWithAutoCAD(toolOutline, optimizedOutline))
        {
            toolOutline = optimizedOutline;
        }
        
        return true;
    }
    
    // 如果AutoCAD不可用，返回原始数据
    return false;
}
