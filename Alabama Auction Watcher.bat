@echo off
setlocal EnableDelayedExpansion

:: Alabama Auction Watcher - Professional Desktop Launcher
:: One-click launch with automatic port detection, authentication, and error handling
:: Designed for non-technical users seeking a seamless experience

title Alabama Auction Watcher
color 0F

:: Set working directory to script location
cd /d "%~dp0"

:: Professional startup banner
echo.
echo ========================================================
echo   🏡 Alabama Auction Watcher - Desktop Edition
echo ========================================================
echo   Professional Real Estate Investment Tool
echo   Launching with automatic configuration...
echo.

:: Check if we're in the correct directory
if not exist "launchers\cross_platform\smart_launcher.py" (
    echo ❌ Installation Error
    echo This launcher must be in the Alabama Auction Watcher directory.
    echo Please ensure all files are properly installed.
    echo.
    echo Press any key to exit...
    pause >nul
    exit /b 1
)

:: Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python Required
    echo Python is not installed or not found in system PATH.
    echo.
    echo Please install Python 3.10+ from: https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    echo Press any key to exit...
    pause >nul
    exit /b 1
)

:: Get Python version for display
for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo ✅ Found !PYTHON_VERSION!

:: Check for and activate virtual environment
if exist "venv\Scripts\activate.bat" (
    echo 🔧 Activating virtual environment...
    call venv\Scripts\activate.bat
) else if exist ".venv\Scripts\activate.bat" (
    echo 🔧 Activating virtual environment...
    call .venv\Scripts\activate.bat
) else (
    echo 💡 Using system Python installation
)

:: Quick dependency check for critical packages
echo 📦 Checking dependencies...
python -c "import tkinter, requests, subprocess" >nul 2>&1
if errorlevel 1 (
    echo ⚠️  Installing missing GUI dependencies...
    pip install requests >nul 2>&1
    if errorlevel 1 (
        echo ❌ Failed to install required packages
        echo Please run: pip install -r requirements.txt
        echo.
        echo Press any key to exit...
        pause >nul
        exit /b 1
    )
)

echo ✅ All dependencies ready

:: Launch the Smart Launcher with professional GUI
echo.
echo 🚀 Starting Alabama Auction Watcher Smart Launcher...
echo    - Automatic port detection
echo    - Intelligent service orchestration
echo    - Professional desktop interface
echo    - Real-time progress indicators
echo.

:: Start the GUI launcher
python launchers\cross_platform\smart_launcher.py

:: Check if launcher exited with error
if errorlevel 1 (
    echo.
    echo ❌ Launcher Error
    echo The Smart Launcher encountered an issue.
    echo This may be due to missing dependencies or system conflicts.
    echo.
    echo Troubleshooting:
    echo  1. Ensure Python 3.10+ is installed
    echo  2. Run: pip install -r requirements.txt
    echo  3. Check antivirus software isn't blocking the application
    echo  4. Try running as Administrator
    echo.
    echo Press any key to exit...
    pause >nul
    exit /b 1
)

echo.
echo ✅ Alabama Auction Watcher launcher closed successfully
echo Thank you for using Alabama Auction Watcher!
echo.

:: Keep window open for a moment to show completion message
timeout /t 2 /nobreak >nul

exit /b 0