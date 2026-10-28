# LeadEngine Phase 2 - Local Dual-Server Development Helper
# Starts FastAPI backend (port 8787) and Next.js frontend (port 3000)

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host " LeadEngine Phase 2 - Development Launcher       " -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

$pythonExe = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
    $pythonExe = "python"
}

Write-Host "`n[1/3] Running database migrations..." -ForegroundColor Yellow
& $pythonExe -c "from app.database.migrations import run_migrations; run_migrations()"

Write-Host "`n[2/3] Starting FastAPI backend on http://127.0.0.1:8787..." -ForegroundColor Yellow
$apiProcess = Start-Process -FilePath $pythonExe -ArgumentList "-m", "uvicorn", "app.api.server:app", "--host", "127.0.0.1", "--port", "8787", "--reload" -PassThru

Start-Sleep -Seconds 2

Write-Host "`n[3/3] Starting Next.js dashboard on http://127.0.0.1:3000..." -ForegroundColor Yellow
$frontendProcess = Start-Process -FilePath "npm.cmd" -ArgumentList "run", "dev" -WorkingDirectory "./dashboard" -PassThru

Write-Host "`nLeadEngine is ready!" -ForegroundColor Green
Write-Host "  Dashboard: http://127.0.0.1:3000" -ForegroundColor Cyan
Write-Host "  API Docs:  http://127.0.0.1:8787/docs" -ForegroundColor Cyan
Write-Host "`nPress Ctrl+C to terminate both servers..." -ForegroundColor Gray

try {
    while ($true) {
        Start-Sleep -Seconds 1
    }
} finally {
    Write-Host "`nShutting down LeadEngine servers..." -ForegroundColor Yellow
    if ($apiProcess -and -not $apiProcess.HasExited) {
        Stop-Process -Id $apiProcess.Id -Force -ErrorAction SilentlyContinue
    }
    if ($frontendProcess -and -not $frontendProcess.HasExited) {
        Stop-Process -Id $frontendProcess.Id -Force -ErrorAction SilentlyContinue
    }
    Write-Host "Shutdown complete." -ForegroundColor Green
}
