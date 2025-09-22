@echo off
setlocal EnableDelayedExpansion

:: Alabama Auction Watcher - System Health Check
:: Comprehensive system diagnostics and status verification
:: Checks all components, dependencies, and system health

title Alabama Auction Watcher - Health Check

echo ========================================================
echo Alabama Auction Watcher - System Health Check
echo ========================================================
echo.
echo Running comprehensive system diagnostics...
echo.

:: Change to the auction root directory
cd /d "%~dp0..\.."

:: Initialize status tracking
set OVERALL_STATUS=HEALTHY
set ISSUES=0

echo ========================================================
echo 1. Environment Check
echo ========================================================

:: Check working directory
if not exist "streamlit_app\app.py" (
    echo [❌] CRITICAL: Cannot find streamlit_app\app.py
    echo     Make sure you're running from the correct directory
    set OVERALL_STATUS=CRITICAL
    set /a ISSUES+=1
) else (
    echo [✅] Working directory is correct
)

:: Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo [❌] CRITICAL: Python is not installed or not in PATH
    set OVERALL_STATUS=CRITICAL
    set /a ISSUES+=1
) else (
    for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
    echo [✅] Python: !PYTHON_VERSION!
)

:: Check for virtual environment
if exist "venv\Scripts\activate.bat" (
    echo [✅] Virtual environment: Found at venv\
    call venv\Scripts\activate.bat >nul 2>&1
) else if exist ".venv\Scripts\activate.bat" (
    echo [✅] Virtual environment: Found at .venv\
    call .venv\Scripts\activate.bat >nul 2>&1
) else (
    echo [⚠️]  Virtual environment: Not found (using system Python)
)

echo.

echo ========================================================
echo 2. Dependencies Check
echo ========================================================

:: Check core dependencies
set DEPS_MISSING=0

:: Streamlit
python -c "import streamlit; print('Streamlit:', streamlit.__version__)" 2>nul
if errorlevel 1 (
    echo [❌] Streamlit: Missing
    set /a DEPS_MISSING+=1
) else (
    for /f "tokens=2" %%i in ('python -c "import streamlit; print('Streamlit:', streamlit.__version__)" 2^>nul') do echo [✅] Streamlit: %%i
)

:: FastAPI
python -c "import fastapi; print('FastAPI:', fastapi.__version__)" 2>nul
if errorlevel 1 (
    echo [❌] FastAPI: Missing
    set /a DEPS_MISSING+=1
) else (
    for /f "tokens=2" %%i in ('python -c "import fastapi; print('FastAPI:', fastapi.__version__)" 2^>nul') do echo [✅] FastAPI: %%i
)

:: Pandas
python -c "import pandas; print('Pandas:', pandas.__version__)" 2>nul
if errorlevel 1 (
    echo [❌] Pandas: Missing
    set /a DEPS_MISSING+=1
) else (
    for /f "tokens=2" %%i in ('python -c "import pandas; print('Pandas:', pandas.__version__)" 2^>nul') do echo [✅] Pandas: %%i
)

:: Plotly
python -c "import plotly; print('Plotly:', plotly.__version__)" 2>nul
if errorlevel 1 (
    echo [❌] Plotly: Missing
    set /a DEPS_MISSING+=1
) else (
    for /f "tokens=2" %%i in ('python -c "import plotly; print('Plotly:', plotly.__version__)" 2^>nul') do echo [✅] Plotly: %%i
)

:: SQLAlchemy
python -c "import sqlalchemy; print('SQLAlchemy:', sqlalchemy.__version__)" 2>nul
if errorlevel 1 (
    echo [❌] SQLAlchemy: Missing
    set /a DEPS_MISSING+=1
) else (
    for /f "tokens=2" %%i in ('python -c "import sqlalchemy; print('SQLAlchemy:', sqlalchemy.__version__)" 2^>nul') do echo [✅] SQLAlchemy: %%i
)

if !DEPS_MISSING! gtr 0 (
    echo.
    echo [❌] Missing !DEPS_MISSING! critical dependencies
    echo [INFO] Run: pip install -r requirements.txt
    set OVERALL_STATUS=DEGRADED
    set /a ISSUES+=!DEPS_MISSING!
)

echo.

echo ========================================================
echo 3. Service Status Check
echo ========================================================

:: Check Backend API
echo Checking Backend API...
curl -s http://localhost:8001/health >nul 2>&1
if errorlevel 1 (
    echo [❌] Backend API: Not running on port 8001
    echo     Use launch_backend_api.bat to start
    set /a ISSUES+=1
) else (
    echo [✅] Backend API: Running on port 8001

    :: Get detailed health info if possible
    for /f %%i in ('curl -s http://localhost:8001/health 2^>nul') do (
        echo     Status: %%i
    )
)

:: Check Streamlit Dashboard
echo Checking Streamlit Dashboard...
curl -s http://localhost:8501 >nul 2>&1
if errorlevel 1 (
    echo [❌] Streamlit Dashboard: Not running on port 8501
    echo     Use launch_main_app.bat to start
    set /a ISSUES+=1
) else (
    echo [✅] Streamlit Dashboard: Running on port 8501
)

echo.

echo ========================================================
echo 4. Database Check
echo ========================================================

:: Check database file
if exist "alabama_auction_watcher.db" (
    echo [✅] Database file: Found

    :: Check database size
    for %%i in (alabama_auction_watcher.db) do (
        set DB_SIZE=%%~zi
        set /a DB_SIZE_MB=!DB_SIZE!/1024/1024
        echo     Size: !DB_SIZE_MB! MB
    )

    :: Test database connection
    python -c "import sqlite3; conn = sqlite3.connect('alabama_auction_watcher.db'); print('Tables:', len(conn.execute('SELECT name FROM sqlite_master WHERE type=\"table\"').fetchall())); conn.close()" 2>nul
    if errorlevel 1 (
        echo [⚠️]  Database: Connection test failed
    ) else (
        for /f "tokens=2" %%i in ('python -c "import sqlite3; conn = sqlite3.connect('alabama_auction_watcher.db'); print('Tables:', len(conn.execute('SELECT name FROM sqlite_master WHERE type=\"table\"').fetchall())); conn.close()" 2^>nul') do echo [✅] Database: %%i tables found
    )
) else (
    echo [⚠️]  Database file: Not found (will be created on first run)
)

echo.

echo ========================================================
echo 5. File System Check
echo ========================================================

:: Check key directories
set DIRS_MISSING=0

if exist "scripts\" (echo [✅] scripts/ directory) else (echo [❌] scripts/ directory missing && set /a DIRS_MISSING+=1)
if exist "streamlit_app\" (echo [✅] streamlit_app/ directory) else (echo [❌] streamlit_app/ directory missing && set /a DIRS_MISSING+=1)
if exist "config\" (echo [✅] config/ directory) else (echo [❌] config/ directory missing && set /a DIRS_MISSING+=1)
if exist "backend_api\" (echo [✅] backend_api/ directory) else (echo [❌] backend_api/ directory missing && set /a DIRS_MISSING+=1)

:: Check key files
if exist "requirements.txt" (echo [✅] requirements.txt) else (echo [❌] requirements.txt missing && set /a DIRS_MISSING+=1)
if exist "start_backend_api.py" (echo [✅] start_backend_api.py) else (echo [❌] start_backend_api.py missing && set /a DIRS_MISSING+=1)

if !DIRS_MISSING! gtr 0 (
    set OVERALL_STATUS=CRITICAL
    set /a ISSUES+=!DIRS_MISSING!
)

echo.

echo ========================================================
echo 6. Performance Check
echo ========================================================

:: Check available memory
for /f "skip=1" %%i in ('wmic computersystem get TotalPhysicalMemory') do (
    if not "%%i"=="" (
        set /a TOTAL_RAM=%%i/1024/1024/1024
        echo [✅] Total RAM: !TOTAL_RAM! GB
        goto :ram_done
    )
)
:ram_done

:: Check disk space
for /f "tokens=3" %%i in ('dir /-c ^| find "bytes free"') do (
    set FREE_SPACE=%%i
    set FREE_SPACE=!FREE_SPACE:,=!
    set /a FREE_SPACE_GB=!FREE_SPACE!/1024/1024/1024
    echo [✅] Free disk space: !FREE_SPACE_GB! GB
)

echo.

echo ========================================================
echo 7. Overall System Status
echo ========================================================

if "!OVERALL_STATUS!"=="HEALTHY" (
    if !ISSUES! equ 0 (
        echo [🎉] SYSTEM STATUS: HEALTHY
        echo      All components are operational
    ) else (
        echo [⚠️]  SYSTEM STATUS: MINOR ISSUES (!ISSUES! warnings)
        echo      System is functional with minor warnings
    )
) else if "!OVERALL_STATUS!"=="DEGRADED" (
    echo [⚠️]  SYSTEM STATUS: DEGRADED (!ISSUES! issues)
    echo      Some functionality may be limited
) else (
    echo [❌] SYSTEM STATUS: CRITICAL (!ISSUES! critical issues)
    echo      System requires attention before use
)

echo.
echo Quick Actions:
echo  🚀 Launch Enhanced Dashboard: launch_enhanced_dashboard.bat
echo  🏠 Launch Main App Only:      launch_main_app.bat
echo  🔧 Launch Backend Only:       launch_backend_api.bat
echo  📊 View this health check:    health_check.bat
echo.

if !ISSUES! gtr 0 (
    echo Issues found. Would you like to attempt automatic fixes?
    echo Press Y to try automatic fixes, or any other key to exit
    choice /c YN /n >nul
    if errorlevel 2 goto :end

    echo.
    echo Attempting automatic fixes...

    if !DEPS_MISSING! gtr 0 (
        echo Installing missing dependencies...
        pip install -r requirements.txt
        if not errorlevel 1 (
            echo [✅] Dependencies installed successfully
        )
    )
)

:end
echo.
pause