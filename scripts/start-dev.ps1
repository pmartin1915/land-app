# Development Server Startup Script
# Ensures clean port availability and starts both backend and frontend

param(
    [int]$BackendPort = 8001,
    [int]$FrontendPort = 5173,
    [switch]$KillOnly,
    [switch]$BackendOnly,
    [switch]$FrontendOnly
)

$ErrorActionPreference = "Stop"

function Write-Status {
    param([string]$Message, [string]$Type = "Info")
    $colors = @{
        "Info" = "Cyan"
        "Success" = "Green"
        "Warning" = "Yellow"
        "Error" = "Red"
    }
    Write-Host "[$Type] $Message" -ForegroundColor $colors[$Type]
}

function Stop-ProcessOnPort {
    param([int]$Port)

    $connections = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
    if ($connections) {
        $processIds = $connections | Select-Object -ExpandProperty OwningProcess -Unique
        foreach ($procId in $processIds) {
            $process = Get-Process -Id $procId -ErrorAction SilentlyContinue
            if ($process) {
                Write-Status "Stopping $($process.ProcessName) (PID: $procId) on port $Port" "Warning"
                Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
                Start-Sleep -Milliseconds 500
            }
        }
        Write-Status "Port $Port cleared" "Success"
        return $true
    }
    Write-Status "Port $Port is available" "Info"
    return $false
}

function Test-PortAvailable {
    param([int]$Port)
    $connection = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
    return ($null -eq $connection)
}

# Banner
Write-Host ""
Write-Host "=================================" -ForegroundColor Cyan
Write-Host "  Land Auction Dev Server" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan
Write-Host ""

# Get script directory and project root
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

# Clear ports
Write-Status "Checking ports..." "Info"

if (-not $FrontendOnly) {
    Stop-ProcessOnPort -Port $BackendPort | Out-Null
}

if (-not $BackendOnly) {
    # Check frontend ports (Vite may use 5173, 5174, 5175, etc.)
    foreach ($port in @($FrontendPort, ($FrontendPort + 1), ($FrontendPort + 2))) {
        Stop-ProcessOnPort -Port $port | Out-Null
    }
}

if ($KillOnly) {
    Write-Status "Ports cleared. Exiting." "Success"
    exit 0
}

Write-Host ""

# Start Backend
if (-not $FrontendOnly) {
    Write-Status "Starting backend on port $BackendPort..." "Info"

    $backendCmd = "cd '$ProjectRoot' && python -m uvicorn backend_api.main:app --port $BackendPort --reload"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd -WindowStyle Normal

    # Wait for backend to be ready
    $maxAttempts = 30
    $attempt = 0
    while ($attempt -lt $maxAttempts) {
        Start-Sleep -Seconds 1
        $attempt++
        try {
            $response = Invoke-WebRequest -Uri "http://127.0.0.1:$BackendPort/health" -TimeoutSec 2 -ErrorAction SilentlyContinue
            if ($response.StatusCode -eq 200) {
                Write-Status "Backend ready at http://127.0.0.1:$BackendPort" "Success"
                break
            }
        } catch {
            Write-Host "." -NoNewline -ForegroundColor Gray
        }
    }

    if ($attempt -eq $maxAttempts) {
        Write-Status "Backend may still be starting..." "Warning"
    }
}

Write-Host ""

# Start Frontend
if (-not $BackendOnly) {
    Write-Status "Starting frontend..." "Info"

    $frontendCmd = "cd '$ProjectRoot\frontend' && npm run dev"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd -WindowStyle Normal

    # Wait for frontend to be ready
    Start-Sleep -Seconds 3
    Write-Status "Frontend starting (Vite will auto-select available port)" "Success"
}

Write-Host ""
Write-Host "=================================" -ForegroundColor Green
Write-Host "  Servers Starting" -ForegroundColor Green
Write-Host "=================================" -ForegroundColor Green
Write-Host ""
Write-Status "Backend:  http://127.0.0.1:$BackendPort" "Info"
Write-Status "Frontend: http://localhost:$FrontendPort (or next available)" "Info"
Write-Host ""
Write-Status "Use './scripts/start-dev.ps1 -KillOnly' to stop all servers" "Info"
