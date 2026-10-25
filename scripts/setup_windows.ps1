# LeadEngine — Windows Automated Setup Script
# Run with: powershell -ExecutionPolicy Bypass -File .\scripts\setup_windows.ps1

Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "         LEADENGINE — WINDOWS SETUP & DOCTOR         " -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Cyan

# 1. Check Python
Write-Host "`n[1/7] Checking Python installation..." -ForegroundColor Yellow
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) {
    Write-Host "Python not found in PATH! Please install Python 3.12+ from python.org" -ForegroundColor Red
    exit 1
}
$pyVer = python --version
Write-Host "Found: $pyVer" -ForegroundColor Green

# 2. Setup Virtual Environment
Write-Host "`n[2/7] Checking / Creating virtual environment (.venv)..." -ForegroundColor Yellow
if (-not (Test-Path ".venv")) {
    python -m venv .venv
    Write-Host "Created .venv successfully." -ForegroundColor Green
} else {
    Write-Host ".venv already exists." -ForegroundColor Green
}

# 3. Upgrade Pip & Install Requirements
Write-Host "`n[3/7] Installing Python dependencies..." -ForegroundColor Yellow
& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt --quiet
Write-Host "Python dependencies installed." -ForegroundColor Green

# 4. Check Node & Lighthouse
Write-Host "`n[4/7] Checking Node & Lighthouse..." -ForegroundColor Yellow
$node = Get-Command node -ErrorAction SilentlyContinue
if ($node) {
    Write-Host "Node.js detected: $(node --version)" -ForegroundColor Green
    if (-not (Test-Path "node_modules/.bin/lighthouse.cmd")) {
        Write-Host "Installing local Lighthouse via npm..." -ForegroundColor Yellow
        npm install lighthouse --quiet --no-fund
    }
    Write-Host "Lighthouse CLI is ready." -ForegroundColor Green
} else {
    Write-Host "Node.js not detected. Lighthouse deep performance audits will be skipped unless installed." -ForegroundColor DarkYellow
}

# 5. Playwright Chromium Setup
Write-Host "`n[5/7] Installing Playwright Chromium browser..." -ForegroundColor Yellow
& ".\.venv\Scripts\python.exe" -m playwright install chromium
Write-Host "Playwright Chromium ready." -ForegroundColor Green

# 6. Create runtime directories
Write-Host "`n[6/7] Creating data and output directories..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path "data", "data/lighthouse", "data/screenshots", "data/cache", "output", "output/reports", "logs" | Out-Null
Write-Host "Directories initialized." -ForegroundColor Green

# 7. Run LeadEngine Doctor
Write-Host "`n[7/7] Running LeadEngine Doctor..." -ForegroundColor Yellow
& ".\.venv\Scripts\python.exe" lead_engine.py doctor

Write-Host "`nSetup complete! You can now run:" -ForegroundColor Green
Write-Host "  .\.venv\Scripts\Activate.ps1" -ForegroundColor White
Write-Host "  python lead_engine.py run --market `"Austin, Texas, USA`" --vertical restaurant --target 250`n" -ForegroundColor White
