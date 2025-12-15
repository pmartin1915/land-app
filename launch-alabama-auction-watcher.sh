#!/bin/bash

# Alabama Auction Watcher - Professional Desktop Launcher for Linux
# One-click launch with automatic port detection, authentication, and error handling
# Designed for non-technical users seeking a seamless experience

# Set script directory and change to project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for better visual feedback
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Professional startup banner
echo ""
echo -e "${CYAN}========================================================${NC}"
echo -e "${CYAN}  🏡 Alabama Auction Watcher - Desktop Edition${NC}"
echo -e "${CYAN}========================================================${NC}"
echo -e "${BLUE}  Professional Real Estate Investment Tool${NC}"
echo -e "${BLUE}  Launching with automatic configuration...${NC}"
echo ""

# Check if we're in the correct directory
if [ ! -f "launchers/cross_platform/smart_launcher.py" ]; then
    echo -e "${RED}❌ Installation Error${NC}"
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
        # Check if it's Python 3
        PYTHON_VERSION=$(python --version 2>&1)
        if [[ $PYTHON_VERSION == *"Python 3"* ]]; then
            PYTHON_CMD="python"
        else
            return 1
        fi
    else
        return 1
    fi
    return 0
}

# Check Python installation
if ! check_python; then
    echo -e "${RED}❌ Python Required${NC}"
    echo "Python 3.10+ is not installed or not found in system PATH."
    echo ""
    echo "Please install Python 3.10+ using your distribution's package manager:"
    echo -e "${YELLOW}Ubuntu/Debian:${NC} sudo apt install python3 python3-pip python3-venv python3-tk"
    echo -e "${YELLOW}Fedora/RHEL:${NC}  sudo dnf install python3 python3-pip python3-tkinter"
    echo -e "${YELLOW}Arch Linux:${NC}   sudo pacman -S python python-pip tk"
    echo -e "${YELLOW}openSUSE:${NC}     sudo zypper install python3 python3-pip python3-tk"
    echo ""
    echo "Or install from: https://www.python.org/downloads/"
    echo ""
    echo "Press Enter to exit..."
    read -r
    exit 1
fi

# Get Python version for display
PYTHON_VERSION=$($PYTHON_CMD --version 2>&1)
echo -e "${GREEN}✅ Found $PYTHON_VERSION${NC}"

# Check for tkinter (common issue on Linux)
if ! $PYTHON_CMD -c "import tkinter" >/dev/null 2>&1; then
    echo -e "${RED}❌ GUI Support Missing${NC}"
    echo "Python tkinter module is required for the GUI launcher."
    echo ""
    echo "Please install tkinter using your distribution's package manager:"
    echo -e "${YELLOW}Ubuntu/Debian:${NC} sudo apt install python3-tk"
    echo -e "${YELLOW}Fedora/RHEL:${NC}  sudo dnf install python3-tkinter"
    echo -e "${YELLOW}Arch Linux:${NC}   sudo pacman -S tk"
    echo -e "${YELLOW}openSUSE:${NC}     sudo zypper install python3-tk"
    echo ""
    echo "Press Enter to exit..."
    read -r
    exit 1
fi

# Check for and activate virtual environment
if [ -f "venv/bin/activate" ]; then
    echo -e "${BLUE}🔧 Activating virtual environment...${NC}"
    source venv/bin/activate
elif [ -f ".venv/bin/activate" ]; then
    echo -e "${BLUE}🔧 Activating virtual environment...${NC}"
    source .venv/bin/activate
else
    echo -e "${YELLOW}💡 Using system Python installation${NC}"
fi

# Quick dependency check for critical packages
echo -e "${BLUE}📦 Checking dependencies...${NC}"
if ! $PYTHON_CMD -c "import requests, subprocess" >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Installing missing dependencies...${NC}"

    # Try pip3 first, then pip
    if command -v pip3 >/dev/null 2>&1; then
        PIP_CMD="pip3"
    elif command -v pip >/dev/null 2>&1; then
        PIP_CMD="pip"
    else
        echo -e "${RED}❌ pip not found${NC}"
        echo "Please install pip using your distribution's package manager:"
        echo -e "${YELLOW}Ubuntu/Debian:${NC} sudo apt install python3-pip"
        echo -e "${YELLOW}Fedora/RHEL:${NC}  sudo dnf install python3-pip"
        echo -e "${YELLOW}Arch Linux:${NC}   sudo pacman -S python-pip"
        echo ""
        echo "Press Enter to exit..."
        read -r
        exit 1
    fi

    $PIP_CMD install requests >/dev/null 2>&1
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Failed to install required packages${NC}"
        echo "Please run: $PIP_CMD install -r requirements.txt"
        echo ""
        echo "Press Enter to exit..."
        read -r
        exit 1
    fi
fi

echo -e "${GREEN}✅ All dependencies ready${NC}"

# Launch the Smart Launcher with professional GUI
echo ""
echo -e "${PURPLE}🚀 Starting Alabama Auction Watcher Smart Launcher...${NC}"
echo -e "${BLUE}   - Automatic port detection${NC}"
echo -e "${BLUE}   - Intelligent service orchestration${NC}"
echo -e "${BLUE}   - Professional desktop interface${NC}"
echo -e "${BLUE}   - Real-time progress indicators${NC}"
echo ""

# Start the GUI launcher
$PYTHON_CMD launchers/cross_platform/smart_launcher.py

# Check launcher exit status
if [ $? -ne 0 ]; then
    echo ""
    echo -e "${RED}❌ Launcher Error${NC}"
    echo "The Smart Launcher encountered an issue."
    echo "This may be due to missing dependencies or system conflicts."
    echo ""
    echo -e "${YELLOW}Troubleshooting:${NC}"
    echo " 1. Ensure Python 3.10+ is installed"
    echo " 2. Install GUI support: sudo apt install python3-tk (Ubuntu/Debian)"
    echo " 3. Run: $PIP_CMD install -r requirements.txt"
    echo " 4. Check system permissions and firewall settings"
    echo " 5. Try running from terminal for detailed errors"
    echo ""
    echo "Press Enter to exit..."
    read -r
    exit 1
fi

echo ""
echo -e "${GREEN}✅ Alabama Auction Watcher launcher closed successfully${NC}"
echo -e "${BLUE}Thank you for using Alabama Auction Watcher!${NC}"
echo ""

# Brief pause to show completion message
sleep 2

exit 0