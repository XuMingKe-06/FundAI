@echo off
chcp 65001 >nul
echo ========================================
echo   FundAI - 多智能体场外基金分析决策系统
echo ========================================
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.12+
    pause
    exit /b 1
)

REM 检查 Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Node.js，请先安装 Node.js 22+
    pause
    exit /b 1
)

REM 检查是否首次运行（检查虚拟环境和 node_modules）
if not exist ".venv\Scripts\activate.bat" (
    echo [信息] 首次运行，正在安装后端依赖...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    pip install -r requirements.txt
) else (
    call .venv\Scripts\activate.bat
)

if not exist "frontend\node_modules" (
    echo [信息] 首次运行，正在安装前端依赖...
    cd frontend
    npm install
    cd ..
)

REM 创建数据目录
if not exist "data" mkdir data
if not exist "data\chroma" mkdir data\chroma

echo.
echo [信息] 正在启动后端服务...
start "FundAI Backend" cmd /c "python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"

echo [信息] 正在启动前端服务...
start "FundAI Frontend" cmd /c "cd frontend && npm run dev"

echo.
echo ========================================
echo   FundAI 已启动！
echo   后端地址: http://localhost:8000
echo   前端地址: http://localhost:3000
echo   API文档:  http://localhost:8000/docs
echo ========================================
echo.
echo 按任意键退出此窗口（服务将继续运行）...
pause >nul
