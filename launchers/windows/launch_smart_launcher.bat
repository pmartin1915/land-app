@echo off
:: Alabama Auction Watcher - Smart Launcher Starter
:: Simple batch file to start the cross-platform GUI launcher

title Alabama Auction Watcher - Smart Launcher

:: Change to the auction root directory
cd /d "%~dp0..\.."

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    pause
    exit /b 1
)

:: Launch the smart GUI launcher
echo [INFO] Starting Alabama Auction Watcher Smart Launcher...
python "launchers\cross_platform\smart_launcher.py"

:: Keep window open if there's an error
if errorlevel 1 (
    echo.
    echo [ERROR] Smart launcher failed to start
    pause
)