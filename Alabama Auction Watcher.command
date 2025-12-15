#!/bin/bash

# Alabama Auction Watcher - Professional Desktop Launcher for macOS
# One-click launch with automatic port detection, authentication, and error handling
# Designed for non-technical users seeking a seamless experience

# Set script directory and change to project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Professional startup banner
echo ""
echo "========================================================"
echo "  🏡 Alabama Auction Watcher - Desktop Edition"
echo "========================================================"
echo "  Professional Real Estate Investment Tool"
echo "  Launching with automatic configuration..."
echo ""

# Check if we're in the correct directory
if [ ! -f "launchers/cross_platform/smart_launcher.py" ]; then
    echo "❌ Installation Error"
    echo "This launcher must be in the Alabama Auction Watcher directory."
    echo "Please ensure all files are properly installed."
    echo ""
    echo "Press Enter to exit..."
    read -r
    exit 1
fi

# Function to check if Python is available
check_python() {
    if command -v python3 >/dev/null 2>&1; then
        PYTHON_CMD="python3"
    elif command -v python >/dev/null 2>&1; then
        PYTHON_CMD="python"
    else
        return 1
    fi
    return 0
}

# Check Python installation
if ! check_python; then
    echo "❌ Python Required"
    echo "Python is not installed or not found in system PATH."
    echo ""
    echo "Please install Python 3.10+ from:"
    echo "  - Homebrew: brew install python"
    echo "  - Official: https://www.python.org/downloads/"
    echo ""
    echo "Press Enter to exit..."
    read -r
    exit 1
fi

# Get Python version for display
PYTHON_VERSION=$($PYTHON_CMD --version 2>&1)
echo "✅ Found $PYTHON_VERSION"

# Check for and activate virtual environment
if [ -f "venv/bin/activate" ]; then
    echo "🔧 Activating virtual environment..."
    source venv/bin/activate
elif [ -f ".venv/bin/activate" ]; then
    echo "🔧 Activating virtual environment..."
    source .venv/bin/activate
else
    echo "💡 Using system Python installation"
fi

# Quick dependency check for critical packages
echo "📦 Checking dependencies..."
if ! $PYTHON_CMD -c "import tkinter, requests, subprocess" >/dev/null 2>&1; then
    echo "⚠️  Installing missing GUI dependencies..."
    pip3 install requests >/dev/null 2>&1
    if [ $? -ne 0 ]; then
        echo "❌ Failed to install required packages"
        echo "Please run: pip3 install -r requirements.txt"
        echo ""
        echo "Press Enter to exit..."
        read -r
        exit 1
    fi
fi

echo "✅ All dependencies ready"

# Launch the Smart Launcher with professional GUI
echo ""
echo "🚀 Starting Alabama Auction Watcher Smart Launcher..."
echo "   - Automatic port detection"
echo "   - Intelligent service orchestration"
echo "   - Professional desktop interface"
echo "   - Real-time progress indicators"
echo ""

# Start the GUI launcher
$PYTHON_CMD launchers/cross_platform/smart_launcher.py

# Check launcher exit status
if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Launcher Error"
    echo "The Smart Launcher encountered an issue."
    echo "This may be due to missing dependencies or system conflicts."
    echo ""
    echo "Troubleshooting:"
    echo " 1. Ensure Python 3.10+ is installed"
    echo " 2. Run: pip3 install -r requirements.txt"
    echo " 3. Check System Preferences > Security & Privacy"
    echo " 4. Try running from Terminal for detailed errors"
    echo ""
    echo "Press Enter to exit..."
    read -r
    exit 1
fi

echo ""
echo "✅ Alabama Auction Watcher launcher closed successfully"
echo "Thank you for using Alabama Auction Watcher!"
echo ""

# Brief pause to show completion message
sleep 2

exit 0