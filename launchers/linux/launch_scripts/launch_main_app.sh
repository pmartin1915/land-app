#!/bin/bash

# Alabama Auction Watcher - Main Application Launcher (Linux)
# Comprehensive Linux launcher for the Streamlit dashboard
# with dependency checking, error handling, and auto-browser launch

echo "========================================================"
echo "Alabama Auction Watcher - Main Application Launcher"
echo "========================================================"
echo

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
# Navigate to the auction root directory (three levels up from launchers/linux/launch_scripts)
cd "$SCRIPT_DIR/../../.."

# Check if we're in the correct directory
if [ ! -f "streamlit_app/app.py" ]; then
    echo "[ERROR] Cannot find streamlit_app/app.py"
    echo "Make sure this launcher is in the launchers/linux/launch_scripts directory"
    echo "of your Alabama Auction Watcher installation."
    echo
    read -p "Press Enter to exit..."
    exit 1
fi

echo "[INFO] Working directory: $(pwd)"
echo

# Check Python installation
echo "[INFO] Checking Python installation..."
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "[ERROR] Python is not installed or not in PATH"
    echo "Please install Python 3.10+ using your package manager:"
    echo "  Ubuntu/Debian: sudo apt update && sudo apt install python3 python3-pip"
    echo "  Fedora/RHEL:   sudo dnf install python3 python3-pip"
    echo "  Arch:          sudo pacman -S python python-pip"
    echo "Or download from: https://www.python.org/downloads/"
    echo
    read -p "Press Enter to exit..."
    exit 1
fi

# Display Python version
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

# Check critical dependencies
echo "[INFO] Checking critical dependencies..."
MISSING_DEPS=""

if ! $PYTHON_CMD -c "import streamlit" 2>/dev/null; then
    MISSING_DEPS="$MISSING_DEPS streamlit"
fi

if ! $PYTHON_CMD -c "import pandas" 2>/dev/null; then
    MISSING_DEPS="$MISSING_DEPS pandas"
fi

if ! $PYTHON_CMD -c "import plotly" 2>/dev/null; then
    MISSING_DEPS="$MISSING_DEPS plotly"
fi

if ! $PYTHON_CMD -c "import numpy" 2>/dev/null; then
    MISSING_DEPS="$MISSING_DEPS numpy"
fi

if [ -n "$MISSING_DEPS" ]; then
    echo "[ERROR] Missing required dependencies:$MISSING_DEPS"
    echo
    echo "[INFO] Installing missing dependencies..."
    echo "Running: pip install -r requirements.txt"
    echo
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "[ERROR] Failed to install dependencies"
        echo "Please run manually: pip install -r requirements.txt"
        echo "You may need to install pip first:"
        echo "  Ubuntu/Debian: sudo apt install python3-pip"
        echo "  Fedora/RHEL:   sudo dnf install python3-pip"
        echo
        read -p "Press Enter to exit..."
        exit 1
    fi
    echo "[SUCCESS] Dependencies installed successfully"
    echo
fi

echo "[SUCCESS] All dependencies are available"
echo

# Check if backend is running (optional)
echo "[INFO] Checking backend API status..."
if curl -s http://localhost:8001/health >/dev/null 2>&1; then
    echo "[SUCCESS] Backend API is running"
    echo
else
    echo "[WARNING] Backend API is not running"
    echo "[INFO] You may want to start the backend for full functionality"
    echo "[INFO] Use launch_backend_api.sh to start the backend"
    echo
fi

# Set environment variables for optimal performance
export STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
export STREAMLIT_SERVER_PORT=8501
export STREAMLIT_SERVER_ADDRESS=localhost

# Launch the application
echo "[INFO] Starting Alabama Auction Watcher Dashboard..."
echo "[INFO] Dashboard will be available at: http://localhost:8501"
echo "[INFO] Opening browser in 3 seconds..."
echo

# Start Streamlit in background
$PYTHON_CMD -m streamlit run streamlit_app/app.py --server.headless=false --server.port=8501 &
STREAMLIT_PID=$!

# Wait a moment for Streamlit to start
sleep 3

# Check if Streamlit started successfully
if curl -s http://localhost:8501 >/dev/null 2>&1; then
    echo "[SUCCESS] Application started successfully!"
    echo "[INFO] Opening browser..."

    # Try different browsers (Linux)
    if command -v xdg-open &> /dev/null; then
        xdg-open http://localhost:8501
    elif command -v firefox &> /dev/null; then
        firefox http://localhost:8501 &
    elif command -v google-chrome &> /dev/null; then
        google-chrome http://localhost:8501 &
    elif command -v chromium-browser &> /dev/null; then
        chromium-browser http://localhost:8501 &
    else
        echo "[INFO] Could not detect a browser. Please open http://localhost:8501 manually"
    fi

    echo
    echo "========================================================"
    echo "Alabama Auction Watcher is now running!"
    echo
    echo "Dashboard URL: http://localhost:8501"
    echo
    echo "Press Ctrl+C to stop the application"
    echo "Or simply close this terminal window"
    echo "========================================================"
    echo

    # Wait for the Streamlit process
    wait $STREAMLIT_PID

else
    echo "[ERROR] Failed to start Streamlit application"
    if [ -f "streamlit_error.log" ]; then
        echo "[INFO] Check streamlit_error.log for details"
        echo
        echo "Error log contents:"
        cat streamlit_error.log
    fi
    echo
    read -p "Press Enter to exit..."
    exit 1
fi

echo
echo "[INFO] Goodbye!"