@echo off
title Alabama Auction Watcher - Uninstaller

:: Navigate to the auction root directory
cd /d "%~dp0.."

:: Launch the cross-platform GUI uninstaller
python uninstallers/cross_platform/uninstaller_gui.py

:: Keep window open if there's an error
if errorlevel 1 (
    echo.
    echo [ERROR] Uninstaller failed to start
    pause
)