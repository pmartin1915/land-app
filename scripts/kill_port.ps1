# Kill processes listening on a specific port
param([int]$Port = 8001)

$connections = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
if ($connections) {
    foreach ($conn in $connections) {
        $procId = $conn.OwningProcess
        Write-Host "Killing process $procId on port $Port"
        Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
    }
    Write-Host "Done"
} else {
    Write-Host "No processes found on port $Port"
}
