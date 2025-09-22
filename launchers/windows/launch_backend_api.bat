@echo off
setlocal EnableDelayedExpansion

:: Alabama Auction Watcher - Backend API Launcher
:: Comprehensive Windows launcher for the FastAPI backend server
:: with database initialization, dependency checking, and health monitoring

title Alabama Auction Watcher - Backend API

echo ========================================================
echo Alabama Auction Watcher - Backend API Launcher
echo ========================================================
echo.

:: Change to the auction root directory
cd /d "%~dp0..\.."

:: Check if we're in the correct directory
if not exist "start_backend_api.py" (
    echo [ERROR] Cannot find start_backend_api.py
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

:: Check backend dependencies
echo [INFO] Checking backend dependencies...
set MISSING_DEPS=

python -c "import fastapi" >nul 2>&1
if errorlevel 1 set MISSING_DEPS=!MISSING_DEPS! fastapi

python -c "import uvicorn" >nul 2>&1
if errorlevel 1 set MISSING_DEPS=!MISSING_DEPS! uvicorn

python -c "import sqlalchemy" >nul 2>&1
if errorlevel 1 set MISSING_DEPS=!MISSING_DEPS! sqlalchemy

python -c "import databases" >nul 2>&1
if errorlevel 1 set MISSING_DEPS=!MISSING_DEPS! databases

python -c "import pydantic" >nul 2>&1
if errorlevel 1 set MISSING_DEPS=!MISSING_DEPS! pydantic

if not "!MISSING_DEPS!"=="" (
    echo [ERROR] Missing required backend dependencies:!MISSING_DEPS!
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

echo [SUCCESS] All backend dependencies are available
echo.

:: Check if port 8001 is already in use
echo [INFO] Checking if port 8001 is available...
netstat -an | find ":8001" >nul 2>&1
if not errorlevel 1 (
    echo [WARNING] Port 8001 appears to be in use
    echo [INFO] Backend API may already be running
    echo [INFO] You can check at: http://localhost:8001/health
    echo.

    :: Test if it's actually our API
    curl -s http://localhost:8001/health >nul 2>&1
    if not errorlevel 1 (
        echo [INFO] Backend API is already running and responding
        echo [INFO] Opening API documentation...
        start "" http://localhost:8001/api/docs
        echo.
        echo API Health Check: http://localhost:8001/health
        echo API Documentation: http://localhost:8001/api/docs
        echo.
        pause
        exit /b 0
    )
)

:: Set environment variables
set BACKEND_HOST=0.0.0.0
set BACKEND_PORT=8001
set DATABASE_URL=sqlite:///./alabama_auction_watcher.db

:: Launch the backend API
echo [INFO] Starting Alabama Auction Watcher Backend API...
echo [INFO] API will be available at: http://localhost:8001
echo [INFO] API documentation at: http://localhost:8001/api/docs
echo [INFO] Health check at: http://localhost:8001/health
echo.

:: Start the backend server
echo [INFO] Initializing database and starting server...
python start_backend_api.py

:: If we get here, the server has stopped
echo.
echo [INFO] Backend API has stopped
echo.

:: Check for error log
if exist "backend_error.log" (
    echo [INFO] Error log found:
    type backend_error.log
    echo.
)

pause