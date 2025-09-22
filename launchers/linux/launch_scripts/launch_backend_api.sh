#!/bin/bash

# Alabama Auction Watcher - Backend API Launcher (Linux)
# Comprehensive Linux launcher for the FastAPI backend server
# with database initialization, dependency checking, and health monitoring

echo "========================================================"
echo "Alabama Auction Watcher - Backend API Launcher"
echo "========================================================"
echo

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
# Navigate to the auction root directory (three levels up from launchers/linux/launch_scripts)
cd "$SCRIPT_DIR/../../.."

# Check if we're in the correct directory
if [ ! -f "start_backend_api.py" ]; then
    echo "[ERROR] Cannot find start_backend_api.py"
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

# Check backend dependencies
echo "[INFO] Checking backend dependencies..."
MISSING_DEPS=""

if ! $PYTHON_CMD -c "import fastapi" 2>/dev/null; then
    MISSING_DEPS="$MISSING_DEPS fastapi"
fi

if ! $PYTHON_CMD -c "import uvicorn" 2>/dev/null; then
    MISSING_DEPS="$MISSING_DEPS uvicorn"
fi

if ! $PYTHON_CMD -c "import sqlalchemy" 2>/dev/null; then
    MISSING_DEPS="$MISSING_DEPS sqlalchemy"
fi

if ! $PYTHON_CMD -c "import databases" 2>/dev/null; then
    MISSING_DEPS="$MISSING_DEPS databases"
fi

if ! $PYTHON_CMD -c "import pydantic" 2>/dev/null; then
    MISSING_DEPS="$MISSING_DEPS pydantic"
fi

if [ -n "$MISSING_DEPS" ]; then
    echo "[ERROR] Missing required backend dependencies:$MISSING_DEPS"
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

echo "[SUCCESS] All backend dependencies are available"
echo

# Check if port 8001 is already in use
echo "[INFO] Checking if port 8001 is available..."
if ss -tuln | grep -q ":8001 "; then
    echo "[WARNING] Port 8001 appears to be in use"
    echo "[INFO] Backend API may already be running"
    echo "[INFO] You can check at: http://localhost:8001/health"
    echo

    # Test if it's actually our API
    if curl -s http://localhost:8001/health >/dev/null 2>&1; then
        echo "[INFO] Backend API is already running and responding"
        echo "[INFO] Opening API documentation..."

        # Try different browsers (Linux)
        if command -v xdg-open &> /dev/null; then
            xdg-open http://localhost:8001/api/docs
        elif command -v firefox &> /dev/null; then
            firefox http://localhost:8001/api/docs &
        elif command -v google-chrome &> /dev/null; then
            google-chrome http://localhost:8001/api/docs &
        fi

        echo
        echo "API Health Check: http://localhost:8001/health"
        echo "API Documentation: http://localhost:8001/api/docs"
        echo
        read -p "Press Enter to exit..."
        exit 0
    fi
fi

# Set environment variables
export BACKEND_HOST=0.0.0.0
export BACKEND_PORT=8001
export DATABASE_URL=sqlite:///./alabama_auction_watcher.db

# Launch the backend API
echo "[INFO] Starting Alabama Auction Watcher Backend API..."
echo "[INFO] API will be available at: http://localhost:8001"
echo "[INFO] API documentation at: http://localhost:8001/api/docs"
echo "[INFO] Health check at: http://localhost:8001/health"
echo

# Start the backend server
echo "[INFO] Initializing database and starting server..."
$PYTHON_CMD start_backend_api.py

# If we get here, the server has stopped
echo
echo "[INFO] Backend API has stopped"
echo

# Check for error log
if [ -f "backend_error.log" ]; then
    echo "[INFO] Error log found:"
    cat backend_error.log
    echo
fi

read -p "Press Enter to exit..."