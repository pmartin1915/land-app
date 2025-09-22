#!/bin/bash

# Alabama Auction Watcher - Enhanced Dashboard Launcher (macOS)
# Launches both backend API and main dashboard for full functionality
# with intelligent startup sequencing and health monitoring

echo "========================================================"
echo "Alabama Auction Watcher - Enhanced Dashboard Launcher"
echo "========================================================"
echo
echo "This launcher will start both the Backend API and Main Dashboard"
echo "for full system functionality with AI monitoring capabilities."
echo

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
# Navigate to the auction root directory (two levels up from launchers/macos)
cd "$SCRIPT_DIR/../.."

# Check if we're in the correct directory
if [ ! -f "streamlit_app/app.py" ]; then
    echo "[ERROR] Cannot find required files"
    echo "Make sure this launcher is in the launchers/macos directory"
    echo "of your Alabama Auction Watcher installation."
    echo
    read -p "Press Enter to exit..."
    exit 1
fi

echo "[INFO] Working directory: $(pwd)"
echo

# Check Python installation
echo "[INFO] Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        echo "[ERROR] Python is not installed or not in PATH"
        echo "Please install Python 3.10+ using Homebrew:"
        echo "  brew install python@3.10"
        echo "Or download from: https://www.python.org/downloads/"
        echo
        read -p "Press Enter to exit..."
        exit 1
    else
        PYTHON_CMD="python"
    fi
else
    PYTHON_CMD="python3"
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1)
echo "[SUCCESS] Found $PYTHON_VERSION"
echo

# Check for virtual environment
if [ -d "venv" ]; then
    echo "[INFO] Activating virtual environment..."
    source venv/bin/activate
    echo "[SUCCESS] Virtual environment activated"
    echo
elif [ -d ".venv" ]; then
    echo "[INFO] Activating virtual environment..."
    source .venv/bin/activate
    echo "[SUCCESS] Virtual environment activated"
    echo
else
    echo "[INFO] No virtual environment found, using system Python"
    echo
fi

# Quick dependency check
echo "[INFO] Performing quick dependency check..."
if ! $PYTHON_CMD -c "import streamlit, fastapi, uvicorn, pandas, plotly" 2>/dev/null; then
    echo "[ERROR] Missing critical dependencies"
    echo "[INFO] Installing dependencies..."
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "[ERROR] Failed to install dependencies"
        read -p "Press Enter to exit..."
        exit 1
    fi
fi
echo "[SUCCESS] Dependencies verified"
echo

# Function to check if a service is running
check_service() {
    local url=$1
    local timeout=30
    local counter=0

    while [ $counter -lt $timeout ]; do
        if curl -s "$url" >/dev/null 2>&1; then
            return 0
        fi
        sleep 1
        ((counter++))
    done
    return 1
}

# Step 1: Check and start Backend API
echo "========================================================"
echo "Step 1: Starting Backend API"
echo "========================================================"

# Check if backend is already running
if curl -s http://localhost:8001/health >/dev/null 2>&1; then
    echo "[INFO] Backend API is already running"
    echo "[SUCCESS] Health check passed"
else
    echo "[INFO] Starting Backend API on port 8001..."

    # Start backend in background
    osascript -e 'tell app "Terminal" to do script "cd '"$(pwd)"'; python start_backend_api.py"' >/dev/null 2>&1

    # Wait for backend to start
    echo "[INFO] Waiting for backend to initialize..."
    if check_service "http://localhost:8001/health"; then
        echo "[SUCCESS] Backend API started successfully"
    else
        echo "[ERROR] Backend failed to start within 30 seconds"
        echo "[INFO] Please check for errors and try again"
        read -p "Press Enter to exit..."
        exit 1
    fi
fi
echo

# Step 2: Start Main Dashboard
echo "========================================================"
echo "Step 2: Starting Main Dashboard"
echo "========================================================"

# Check if Streamlit is already running
if curl -s http://localhost:8501 >/dev/null 2>&1; then
    echo "[INFO] Streamlit dashboard is already running"
    echo "[SUCCESS] Dashboard is accessible"
else
    echo "[INFO] Starting Streamlit dashboard on port 8501..."

    # Set Streamlit environment variables
    export STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
    export STREAMLIT_SERVER_PORT=8501
    export STREAMLIT_SERVER_ADDRESS=localhost

    # Start Streamlit in a new Terminal window
    osascript -e 'tell app "Terminal" to do script "cd '"$(pwd)"'; python -m streamlit run streamlit_app/app.py --server.port=8501"' >/dev/null 2>&1

    # Wait for Streamlit to start
    echo "[INFO] Waiting for dashboard to initialize..."
    if check_service "http://localhost:8501"; then
        echo "[SUCCESS] Dashboard started successfully"
    else
        echo "[ERROR] Dashboard failed to start within 30 seconds"
        echo "[INFO] Please check for errors and try again"
        read -p "Press Enter to exit..."
        exit 1
    fi
fi
echo

# Final system status
echo "========================================================"
echo "Enhanced Dashboard Status"
echo "========================================================"
echo
echo "[SUCCESS] Alabama Auction Watcher Enhanced Dashboard is running!"
echo
echo "Available Services:"
echo "  🏠 Main Dashboard:     http://localhost:8501"
echo "  🔧 Backend API:        http://localhost:8001"
echo "  📚 API Documentation:  http://localhost:8001/api/docs"
echo "  🏥 Health Check:       http://localhost:8001/health"
echo
echo "Features Available:"
echo "  ✅ Interactive Property Browser"
echo "  ✅ Advanced Analytics Dashboard"
echo "  ✅ County Deep Dive Analysis"
echo "  ✅ Market Intelligence & Predictions"
echo "  ✅ AI Testing & Monitoring"
echo "  ✅ Enhanced Error Detection"
echo "  ✅ Performance Optimization"
echo

# Open browsers
echo "[INFO] Opening dashboard in browser..."
sleep 2
open http://localhost:8501

echo "[INFO] Enhanced Dashboard is now fully operational!"
echo
echo "To stop the system:"
echo "  - Close both Terminal windows, or"
echo "  - Press Ctrl+C in each Terminal window, or"
echo "  - Use Activity Monitor to end Python processes"
echo

read -p "Press Enter to exit this launcher..."