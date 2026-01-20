@echo off
REM Development Server Startup Script (Windows CMD)
REM Ensures clean port availability and starts both backend and frontend

setlocal enabledelayedexpansion

set BACKEND_PORT=8001
set FRONTEND_PORT=5173

if "%1"=="-k" goto :kill_only
if "%1"=="--kill-only" goto :kill_only

echo.
echo =================================
echo   Land Auction Dev Server
echo =================================
echo.

REM Kill processes on backend port
echo [Info] Checking port %BACKEND_PORT%...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%BACKEND_PORT% " ^| findstr "LISTENING"') do (
    echo [Warning] Killing process %%a on port %BACKEND_PORT%
    taskkill /F /PID %%a >nul 2>&1
)

REM Kill processes on frontend ports
for %%p in (%FRONTEND_PORT%, 5174, 5175) do (
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%%p " ^| findstr "LISTENING"') do (
        echo [Warning] Killing process %%a on port %%p
        taskkill /F /PID %%a >nul 2>&1
    )
)

echo [Success] Ports cleared
echo.

REM Get project root (parent of scripts folder)
set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..

REM Start Backend
echo [Info] Starting backend on port %BACKEND_PORT%...
start "Backend" cmd /k "cd /d %PROJECT_ROOT% && python -m uvicorn backend_api.main:app --port %BACKEND_PORT% --reload"

REM Wait for backend
echo [Info] Waiting for backend...
timeout /t 5 /nobreak >nul

REM Start Frontend
echo [Info] Starting frontend...
start "Frontend" cmd /k "cd /d %PROJECT_ROOT%\frontend && npm run dev"

echo.
echo =================================
echo   Servers Starting
echo =================================
echo.
echo [Info] Backend:  http://127.0.0.1:%BACKEND_PORT%
echo [Info] Frontend: http://localhost:%FRONTEND_PORT% (or next available)
echo.
echo [Info] Use 'scripts\start-dev.bat --kill-only' to stop all servers
goto :eof

:kill_only
echo [Info] Killing processes on ports...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%BACKEND_PORT% " ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)
for %%p in (%FRONTEND_PORT%, 5174, 5175) do (
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%%p " ^| findstr "LISTENING"') do (
        taskkill /F /PID %%a >nul 2>&1
    )
)
echo [Success] Ports cleared
goto :eof
