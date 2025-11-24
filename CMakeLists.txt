cmake_minimum_required(VERSION 3.15)
project(SpiralGrooveTool)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Windows特定设置
if(WIN32)
    set(CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS ON)
    add_definitions(-DUNICODE -D_UNICODE)
endif()

# 源文件
set(SOURCES
    SpiralGrooveTool/main.cpp
    SpiralGrooveTool/MainWindow.cpp
    SpiralGrooveTool/SpiralCalculator.cpp
    SpiralGrooveTool/AutoCADDrawer.cpp
)

# 头文件
set(HEADERS
    SpiralGrooveTool/MainWindow.h
    SpiralGrooveTool/SpiralCalculator.h
    SpiralGrooveTool/AutoCADDrawer.h
    SpiralGrooveTool/resource.h
)

# 创建可执行文件
add_executable(${PROJECT_NAME} WIN32 ${SOURCES} ${HEADERS})

# Windows资源文件
if(WIN32)
    enable_language(RC)
    target_sources(${PROJECT_NAME} PRIVATE SpiralGrooveTool/SpiralGrooveTool.rc)
    set(CMAKE_RC_COMPILER_INIT windres)
endif()

# Windows特定链接库
if(WIN32)
    target_link_libraries(${PROJECT_NAME} 
        gdiplus
        ole32
        oleaut32
    )
endif()

# 包含目录
target_include_directories(${PROJECT_NAME} PRIVATE
    SpiralGrooveTool
)

# 输出目录
set_target_properties(${PROJECT_NAME} PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin
    RUNTIME_OUTPUT_DIRECTORY_DEBUG ${CMAKE_BINARY_DIR}/bin
    RUNTIME_OUTPUT_DIRECTORY_RELEASE ${CMAKE_BINARY_DIR}/bin
)

