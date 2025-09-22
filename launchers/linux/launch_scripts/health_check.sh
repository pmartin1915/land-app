#!/bin/bash

# Alabama Auction Watcher - System Health Check (Linux)
# Comprehensive system diagnostics and status verification
# Checks all components, dependencies, and system health

echo "========================================================"
echo "Alabama Auction Watcher - System Health Check"
echo "========================================================"
echo
echo "Running comprehensive system diagnostics..."
echo

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
# Navigate to the auction root directory (three levels up from launchers/linux/launch_scripts)
cd "$SCRIPT_DIR/../../.."

# Initialize status tracking
OVERALL_STATUS="HEALTHY"
ISSUES=0

echo "========================================================"
echo "1. Environment Check"
echo "========================================================"

# Check working directory
if [ ! -f "streamlit_app/app.py" ]; then
    echo "[❌] CRITICAL: Cannot find streamlit_app/app.py"
    echo "     Make sure you're running from the correct directory"
    OVERALL_STATUS="CRITICAL"
    ((ISSUES++))
else
    echo "[✅] Working directory is correct"
fi

# Check Python installation
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
    PYTHON_VERSION=$($PYTHON_CMD --version 2>&1)
    echo "[✅] Python: $PYTHON_VERSION"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
    PYTHON_VERSION=$($PYTHON_CMD --version 2>&1)
    echo "[✅] Python: $PYTHON_VERSION"
else
    echo "[❌] CRITICAL: Python is not installed or not in PATH"
    OVERALL_STATUS="CRITICAL"
    ((ISSUES++))
    PYTHON_CMD=""
fi

# Check for virtual environment
if [ -d "venv" ]; then
    echo "[✅] Virtual environment: Found at venv/"
    source venv/bin/activate 2>/dev/null
elif [ -d ".venv" ]; then
    echo "[✅] Virtual environment: Found at .venv/"
    source .venv/bin/activate 2>/dev/null
else
    echo "[⚠️]  Virtual environment: Not found (using system Python)"
fi

echo

echo "========================================================"
echo "2. Dependencies Check"
echo "========================================================"

if [ -n "$PYTHON_CMD" ]; then
    # Check core dependencies
    DEPS_MISSING=0

    # Streamlit
    if $PYTHON_CMD -c "import streamlit; print('Streamlit:', streamlit.__version__)" 2>/dev/null; then
        STREAMLIT_VER=$($PYTHON_CMD -c "import streamlit; print(streamlit.__version__)" 2>/dev/null)
        echo "[✅] Streamlit: $STREAMLIT_VER"
    else
        echo "[❌] Streamlit: Missing"
        ((DEPS_MISSING++))
    fi

    # FastAPI
    if $PYTHON_CMD -c "import fastapi; print('FastAPI:', fastapi.__version__)" 2>/dev/null; then
        FASTAPI_VER=$($PYTHON_CMD -c "import fastapi; print(fastapi.__version__)" 2>/dev/null)
        echo "[✅] FastAPI: $FASTAPI_VER"
    else
        echo "[❌] FastAPI: Missing"
        ((DEPS_MISSING++))
    fi

    # Pandas
    if $PYTHON_CMD -c "import pandas; print('Pandas:', pandas.__version__)" 2>/dev/null; then
        PANDAS_VER=$($PYTHON_CMD -c "import pandas; print(pandas.__version__)" 2>/dev/null)
        echo "[✅] Pandas: $PANDAS_VER"
    else
        echo "[❌] Pandas: Missing"
        ((DEPS_MISSING++))
    fi

    # Plotly
    if $PYTHON_CMD -c "import plotly; print('Plotly:', plotly.__version__)" 2>/dev/null; then
        PLOTLY_VER=$($PYTHON_CMD -c "import plotly; print(plotly.__version__)" 2>/dev/null)
        echo "[✅] Plotly: $PLOTLY_VER"
    else
        echo "[❌] Plotly: Missing"
        ((DEPS_MISSING++))
    fi

    # SQLAlchemy
    if $PYTHON_CMD -c "import sqlalchemy; print('SQLAlchemy:', sqlalchemy.__version__)" 2>/dev/null; then
        SQLALCHEMY_VER=$($PYTHON_CMD -c "import sqlalchemy; print(sqlalchemy.__version__)" 2>/dev/null)
        echo "[✅] SQLAlchemy: $SQLALCHEMY_VER"
    else
        echo "[❌] SQLAlchemy: Missing"
        ((DEPS_MISSING++))
    fi

    if [ $DEPS_MISSING -gt 0 ]; then
        echo
        echo "[❌] Missing $DEPS_MISSING critical dependencies"
        echo "[INFO] Run: pip install -r requirements.txt"
        OVERALL_STATUS="DEGRADED"
        ((ISSUES+=DEPS_MISSING))
    fi
else
    echo "[❌] Cannot check dependencies - Python not available"
    OVERALL_STATUS="CRITICAL"
    ((ISSUES++))
fi

echo

echo "========================================================"
echo "3. Service Status Check"
echo "========================================================"

# Check Backend API
echo "Checking Backend API..."
if curl -s http://localhost:8001/health >/dev/null 2>&1; then
    echo "[✅] Backend API: Running on port 8001"

    # Get detailed health info if possible
    HEALTH_STATUS=$(curl -s http://localhost:8001/health 2>/dev/null)
    if [ -n "$HEALTH_STATUS" ]; then
        echo "     Status: $HEALTH_STATUS"
    fi
else
    echo "[❌] Backend API: Not running on port 8001"
    echo "     Use launch_backend_api.sh to start"
    ((ISSUES++))
fi

# Check Streamlit Dashboard
echo "Checking Streamlit Dashboard..."
if curl -s http://localhost:8501 >/dev/null 2>&1; then
    echo "[✅] Streamlit Dashboard: Running on port 8501"
else
    echo "[❌] Streamlit Dashboard: Not running on port 8501"
    echo "     Use launch_main_app.sh to start"
    ((ISSUES++))
fi

echo

echo "========================================================"
echo "4. Database Check"
echo "========================================================"

# Check database file
if [ -f "alabama_auction_watcher.db" ]; then
    echo "[✅] Database file: Found"

    # Check database size
    DB_SIZE=$(stat -c%s "alabama_auction_watcher.db" 2>/dev/null)
    if [ -n "$DB_SIZE" ]; then
        DB_SIZE_MB=$((DB_SIZE / 1024 / 1024))
        echo "     Size: ${DB_SIZE_MB} MB"
    fi

    # Test database connection if Python is available
    if [ -n "$PYTHON_CMD" ]; then
        TABLE_COUNT=$($PYTHON_CMD -c "import sqlite3; conn = sqlite3.connect('alabama_auction_watcher.db'); print(len(conn.execute('SELECT name FROM sqlite_master WHERE type=\"table\"').fetchall())); conn.close()" 2>/dev/null)
        if [ -n "$TABLE_COUNT" ]; then
            echo "[✅] Database: $TABLE_COUNT tables found"
        else
            echo "[⚠️]  Database: Connection test failed"
        fi
    fi
else
    echo "[⚠️]  Database file: Not found (will be created on first run)"
fi

echo

echo "========================================================"
echo "5. File System Check"
echo "========================================================"

# Check key directories
DIRS_MISSING=0

[ -d "scripts" ] && echo "[✅] scripts/ directory" || { echo "[❌] scripts/ directory missing"; ((DIRS_MISSING++)); }
[ -d "streamlit_app" ] && echo "[✅] streamlit_app/ directory" || { echo "[❌] streamlit_app/ directory missing"; ((DIRS_MISSING++)); }
[ -d "config" ] && echo "[✅] config/ directory" || { echo "[❌] config/ directory missing"; ((DIRS_MISSING++)); }
[ -d "backend_api" ] && echo "[✅] backend_api/ directory" || { echo "[❌] backend_api/ directory missing"; ((DIRS_MISSING++)); }

# Check key files
[ -f "requirements.txt" ] && echo "[✅] requirements.txt" || { echo "[❌] requirements.txt missing"; ((DIRS_MISSING++)); }
[ -f "start_backend_api.py" ] && echo "[✅] start_backend_api.py" || { echo "[❌] start_backend_api.py missing"; ((DIRS_MISSING++)); }

if [ $DIRS_MISSING -gt 0 ]; then
    OVERALL_STATUS="CRITICAL"
    ((ISSUES+=DIRS_MISSING))
fi

echo

echo "========================================================"
echo "6. Performance Check"
echo "========================================================"

# Check available memory
if command -v free >/dev/null 2>&1; then
    TOTAL_RAM=$(free -g | awk '/^Mem:/{print $2}')
    FREE_RAM=$(free -g | awk '/^Mem:/{print $7}')
    echo "[✅] Total RAM: ${TOTAL_RAM} GB"
    echo "[✅] Available RAM: ${FREE_RAM} GB"
fi

# Check disk space
DISK_FREE=$(df -h . | awk 'NR==2{print $4}')
echo "[✅] Free disk space: $DISK_FREE"

# Check CPU info
if [ -f "/proc/cpuinfo" ]; then
    CPU_COUNT=$(nproc)
    echo "[✅] CPU cores: $CPU_COUNT"
fi

echo

echo "========================================================"
echo "7. Overall System Status"
echo "========================================================"

if [ "$OVERALL_STATUS" = "HEALTHY" ]; then
    if [ $ISSUES -eq 0 ]; then
        echo "[🎉] SYSTEM STATUS: HEALTHY"
        echo "     All components are operational"
    else
        echo "[⚠️]  SYSTEM STATUS: MINOR ISSUES ($ISSUES warnings)"
        echo "     System is functional with minor warnings"
    fi
elif [ "$OVERALL_STATUS" = "DEGRADED" ]; then
    echo "[⚠️]  SYSTEM STATUS: DEGRADED ($ISSUES issues)"
    echo "     Some functionality may be limited"
else
    echo "[❌] SYSTEM STATUS: CRITICAL ($ISSUES critical issues)"
    echo "     System requires attention before use"
fi

echo
echo "Quick Actions:"
echo "  🚀 Launch Enhanced Dashboard: ./launch_enhanced_dashboard.sh"
echo "  🏠 Launch Main App Only:      ./launch_main_app.sh"
echo "  🔧 Launch Backend Only:       ./launch_backend_api.sh"
echo "  📊 View this health check:    ./health_check.sh"
echo

if [ $ISSUES -gt 0 ]; then
    echo "Issues found. Would you like to attempt automatic fixes? (y/n)"
    read -r RESPONSE
    if [ "$RESPONSE" = "y" ] || [ "$RESPONSE" = "Y" ]; then
        echo
        echo "Attempting automatic fixes..."

        if [ $DEPS_MISSING -gt 0 ] && [ -n "$PYTHON_CMD" ]; then
            echo "Installing missing dependencies..."
            pip install -r requirements.txt
            if [ $? -eq 0 ]; then
                echo "[✅] Dependencies installed successfully"
            fi
        fi
    fi
fi

echo
read -p "Press Enter to exit..."