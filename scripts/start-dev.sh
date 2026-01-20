#!/bin/bash
# Development Server Startup Script (Bash/WSL)
# Ensures clean port availability and starts both backend and frontend

BACKEND_PORT=${1:-8001}
FRONTEND_PORT=${2:-5173}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

info() { echo -e "${CYAN}[Info]${NC} $1"; }
success() { echo -e "${GREEN}[Success]${NC} $1"; }
warning() { echo -e "${YELLOW}[Warning]${NC} $1"; }
error() { echo -e "${RED}[Error]${NC} $1"; }

kill_port() {
    local port=$1
    local pids=$(lsof -ti:$port 2>/dev/null || netstat -ano 2>/dev/null | grep ":$port " | awk '{print $NF}' | sort -u)

    if [ -n "$pids" ]; then
        for pid in $pids; do
            if [ "$pid" != "0" ] && [ -n "$pid" ]; then
                warning "Killing process $pid on port $port"
                kill -9 $pid 2>/dev/null || taskkill //F //PID $pid 2>/dev/null
            fi
        done
        success "Port $port cleared"
    else
        info "Port $port is available"
    fi
}

echo ""
echo -e "${CYAN}=================================${NC}"
echo -e "${CYAN}  Land Auction Dev Server${NC}"
echo -e "${CYAN}=================================${NC}"
echo ""

# Kill existing processes on ports
info "Checking ports..."
kill_port $BACKEND_PORT
kill_port $FRONTEND_PORT
kill_port $((FRONTEND_PORT + 1))
kill_port $((FRONTEND_PORT + 2))

if [ "$1" = "--kill-only" ] || [ "$1" = "-k" ]; then
    success "Ports cleared. Exiting."
    exit 0
fi

echo ""

# Start Backend
info "Starting backend on port $BACKEND_PORT..."
cd "$PROJECT_ROOT"

# Check if we're in Windows (Git Bash/MSYS)
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    # Windows: start in new terminal
    start "" cmd /c "python -m uvicorn backend_api.main:app --port $BACKEND_PORT --reload"
else
    # Unix: start in background
    python -m uvicorn backend_api.main:app --port $BACKEND_PORT --reload &
fi

# Wait for backend
info "Waiting for backend..."
for i in {1..30}; do
    if curl -s "http://127.0.0.1:$BACKEND_PORT/health" > /dev/null 2>&1; then
        success "Backend ready at http://127.0.0.1:$BACKEND_PORT"
        break
    fi
    echo -n "."
    sleep 1
done
echo ""

# Start Frontend
info "Starting frontend..."
cd "$PROJECT_ROOT/frontend"

if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    start "" cmd /c "npm run dev"
else
    npm run dev &
fi

sleep 3

echo ""
echo -e "${GREEN}=================================${NC}"
echo -e "${GREEN}  Servers Starting${NC}"
echo -e "${GREEN}=================================${NC}"
echo ""
info "Backend:  http://127.0.0.1:$BACKEND_PORT"
info "Frontend: http://localhost:$FRONTEND_PORT (or next available)"
echo ""
info "Use './scripts/start-dev.sh --kill-only' to stop all servers"
