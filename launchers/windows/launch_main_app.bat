@echo off
setlocal EnableDelayedExpansion

:: Alabama Auction Watcher - Main Application Launcher
:: Comprehensive Windows launcher for the Streamlit dashboard
:: with dependency checking, error handling, and auto-browser launch

title Alabama Auction Watcher - Main Application

echo ========================================================
echo Alabama Auction Watcher - Main Application Launcher
echo ========================================================
echo.

:: Change to the auction root directory
cd /d "%~dp0..\.."

:: Check if we're in the correct directory
if not exist "streamlit_app\app.py" (
    echo [ERROR] Cannot find streamlit_app\app.py
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

:: Display Python version
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

:: Check critical dependencies
echo [INFO] Checking critical dependencies...
set MISSING_DEPS=

python -c "import streamlit" >nul 2>&1
if errorlevel 1 set MISSING_DEPS=!MISSING_DEPS! streamlit

python -c "import pandas" >nul 2>&1
if errorlevel 1 set MISSING_DEPS=!MISSING_DEPS! pandas

python -c "import plotly" >nul 2>&1
if errorlevel 1 set MISSING_DEPS=!MISSING_DEPS! plotly

python -c "import numpy" >nul 2>&1
if errorlevel 1 set MISSING_DEPS=!MISSING_DEPS! numpy

if not "!MISSING_DEPS!"=="" (
    echo [ERROR] Missing required dependencies:!MISSING_DEPS!
    echo.
    echo [INFO] Installing missing dependencies...
    echo Running: pip install -r requirements.txt
    echo.
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies
        echo Please run manually: pip install -r requirements.txt
        echo.
        pause
        exit /b 1
    )
    echo [SUCCESS] Dependencies installed successfully
    echo.
)

echo [SUCCESS] All dependencies are available
echo.

:: Check if backend is running (optional)
echo [INFO] Checking backend API status...
curl -s http://localhost:8001/health >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Backend API is not running
    echo [INFO] You may want to start the backend for full functionality
    echo [INFO] Use launch_backend_api.bat to start the backend
    echo.
) else (
    echo [SUCCESS] Backend API is running
    echo.
)

:: Set environment variables for optimal performance
set STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
set STREAMLIT_SERVER_PORT=8501
set STREAMLIT_SERVER_ADDRESS=localhost

:: Launch the application
echo [INFO] Starting Alabama Auction Watcher Dashboard...
echo [INFO] Dashboard will be available at: http://localhost:8501
echo [INFO] Opening browser in 3 seconds...
echo.

:: Start Streamlit in background and capture PID
start /b python -m streamlit run streamlit_app\app.py --server.headless=false --server.port=8501 2>streamlit_error.log

:: Wait a moment for Streamlit to start
timeout /t 3 /nobreak >nul

:: Check if Streamlit started successfully
curl -s http://localhost:8501 >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Failed to start Streamlit application
    echo [INFO] Check streamlit_error.log for details
    if exist streamlit_error.log (
        echo.
        echo Error log contents:
        type streamlit_error.log
    )
    echo.
    pause
    exit /b 1
)

:: Open browser
echo [SUCCESS] Application started successfully!
echo [INFO] Opening browser...
start "" http://localhost:8501

echo.
echo ========================================================
echo Alabama Auction Watcher is now running!
echo.
echo Dashboard URL: http://localhost:8501
echo.
echo Press Ctrl+C to stop the application
echo Or simply close this window
echo ========================================================
echo.

:: Keep the window open and wait for Ctrl+C
:wait_loop
timeout /t 5 >nul
goto wait_loop

:: This won't be reached due to the infinite loop above,
:: but it's here for completeness
echo.
echo [INFO] Goodbye!
pause