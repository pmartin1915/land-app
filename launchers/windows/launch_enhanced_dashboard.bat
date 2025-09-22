@echo off
setlocal EnableDelayedExpansion

:: Alabama Auction Watcher - Enhanced Dashboard Launcher
:: Launches both backend API and main dashboard for full functionality
:: with intelligent startup sequencing and health monitoring

title Alabama Auction Watcher - Enhanced Dashboard

echo ========================================================
echo Alabama Auction Watcher - Enhanced Dashboard Launcher
echo ========================================================
echo.
echo This launcher will start both the Backend API and Main Dashboard
echo for full system functionality with AI monitoring capabilities.
echo.

:: Change to the auction root directory
cd /d "%~dp0..\.."

:: Check if we're in the correct directory
if not exist "streamlit_app\app.py" (
    echo [ERROR] Cannot find required files
    echo Make sure this launcher is in the launchers\windows directory
    echo of your Alabama Auction Watcher installation.
    echo.
    pause
    exit /b 1
)

echo [INFO] Working directory: %CD%
echo.

:: Check Python installation
echo [INFO] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.10+ and add it to your PATH
    echo Download from: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [SUCCESS] Found !PYTHON_VERSION!
echo.

:: Check for virtual environment
if exist "venv\Scripts\activate.bat" (
    echo [INFO] Activating virtual environment...
    call venv\Scripts\activate.bat
    echo [SUCCESS] Virtual environment activated
    echo.
) else if exist ".venv\Scripts\activate.bat" (
    echo [INFO] Activating virtual environment...
    call .venv\Scripts\activate.bat
    echo [SUCCESS] Virtual environment activated
    echo.
) else (
    echo [INFO] No virtual environment found, using system Python
    echo.
)

:: Quick dependency check
echo [INFO] Performing quick dependency check...
python -c "import streamlit, fastapi, uvicorn, pandas, plotly" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Missing critical dependencies
    echo [INFO] Installing dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies
        pause
        exit /b 1
    )
)
echo [SUCCESS] Dependencies verified
echo.

:: Step 1: Check and start Backend API
echo ========================================================
echo Step 1: Starting Backend API
echo ========================================================

:: Check if backend is already running
curl -s http://localhost:8001/health >nul 2>&1
if not errorlevel 1 (
    echo [INFO] Backend API is already running
    echo [SUCCESS] Health check passed
) else (
    echo [INFO] Starting Backend API on port 8001...

    :: Start backend in a new window
    start "Alabama Auction Watcher - Backend API" /min cmd /c "python start_backend_api.py"

    :: Wait for backend to start
    echo [INFO] Waiting for backend to initialize...
    set /a COUNTER=0
    :backend_wait
    set /a COUNTER+=1
    if !COUNTER! gtr 30 (
        echo [ERROR] Backend failed to start within 30 seconds
        echo [INFO] Please check for errors and try again
        pause
        exit /b 1
    )

    timeout /t 1 /nobreak >nul
    curl -s http://localhost:8001/health >nul 2>&1
    if errorlevel 1 goto backend_wait

    echo [SUCCESS] Backend API started successfully
)
echo.

:: Step 2: Start Main Dashboard
echo ========================================================
echo Step 2: Starting Main Dashboard
echo ========================================================

:: Check if Streamlit is already running
curl -s http://localhost:8501 >nul 2>&1
if not errorlevel 1 (
    echo [INFO] Streamlit dashboard is already running
    echo [SUCCESS] Dashboard is accessible
) else (
    echo [INFO] Starting Streamlit dashboard on port 8501...

    :: Set Streamlit environment variables
    set STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
    set STREAMLIT_SERVER_PORT=8501
    set STREAMLIT_SERVER_ADDRESS=localhost

    :: Start Streamlit in a new window
    start "Alabama Auction Watcher - Dashboard" cmd /c "python -m streamlit run streamlit_app\app.py --server.port=8501"

    :: Wait for Streamlit to start
    echo [INFO] Waiting for dashboard to initialize...
    set /a COUNTER=0
    :streamlit_wait
    set /a COUNTER+=1
    if !COUNTER! gtr 20 (
        echo [ERROR] Dashboard failed to start within 20 seconds
        echo [INFO] Please check for errors and try again
        pause
        exit /b 1
    )

    timeout /t 1 /nobreak >nul
    curl -s http://localhost:8501 >nul 2>&1
    if errorlevel 1 goto streamlit_wait

    echo [SUCCESS] Dashboard started successfully
)
echo.

:: Final system status
echo ========================================================
echo Enhanced Dashboard Status
echo ========================================================
echo.
echo [SUCCESS] Alabama Auction Watcher Enhanced Dashboard is running!
echo.
echo Available Services:
echo  🏠 Main Dashboard:     http://localhost:8501
echo  🔧 Backend API:        http://localhost:8001
echo  📚 API Documentation:  http://localhost:8001/api/docs
echo  🏥 Health Check:       http://localhost:8001/health
echo.
echo Features Available:
echo  ✅ Interactive Property Browser
echo  ✅ Advanced Analytics Dashboard
echo  ✅ County Deep Dive Analysis
echo  ✅ Market Intelligence & Predictions
echo  ✅ AI Testing & Monitoring
echo  ✅ Enhanced Error Detection
echo  ✅ Performance Optimization
echo.

:: Open browsers
echo [INFO] Opening dashboard in browser...
timeout /t 2 /nobreak >nul
start "" http://localhost:8501

echo [INFO] Enhanced Dashboard is now fully operational!
echo.
echo To stop the system:
echo  - Close both application windows, or
echo  - Press Ctrl+C in each window, or
echo  - Use Task Manager to end Python processes
echo.

pause