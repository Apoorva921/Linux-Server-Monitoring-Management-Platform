param(
    [ValidateSet("auto", "docker", "local")]
    [string]$Mode = "auto",
    [switch]$NoDemo
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  SentinelOps - Easy One-Command Launcher " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Ensure .env exists
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "[+] Created .env from .env.example" -ForegroundColor Green
}

# Detect Docker availability in auto mode
if ($Mode -eq "auto") {
    $dockerReady = $false
    try {
        $null = docker info --format "{{.ServerVersion}}" 2>$null
        if ($LASTEXITCODE -eq 0) { $dockerReady = $true }
    } catch {}
    if ($dockerReady) {
        $Mode = "docker"
        Write-Host "[+] Docker daemon detected -> launching full Docker Compose stack (PostgreSQL + Nginx + FastAPI + React)" -ForegroundColor Green
    } else {
        $Mode = "local"
        Write-Host "[!] Docker Desktop is not running -> launching local single-port deployment (http://localhost:8000)" -ForegroundColor Yellow
    }
}

if ($Mode -eq "docker") {
    if ($NoDemo) {
        Write-Host "[+] Starting Docker Compose (Mode A: Real Linux Servers)..." -ForegroundColor Cyan
        Write-Host "    Dashboard: http://localhost:8080  |  Login: admin / Admin@SentinelOps123!" -ForegroundColor Green
        docker compose up --build
    } else {
        Write-Host "[+] Starting Docker Compose (Mode B: Demo Simulator enabled)..." -ForegroundColor Cyan
        Write-Host "    Dashboard: http://localhost:8080  |  Login: admin / Admin@SentinelOps123!" -ForegroundColor Green
        docker compose --profile demo up --build
    }
    exit $LASTEXITCODE
}

# Local Mode (Zero Docker required - serves built React SPA + FastAPI + WebSockets on port 8000)
$BackendPy = Join-Path $RepoRoot "backend\.venv\Scripts\python.exe"
if (-not (Test-Path $BackendPy)) {
    Write-Host "[+] Creating backend virtual environment and installing packages..." -ForegroundColor Cyan
    python -m venv backend\.venv
    & $BackendPy -m pip install -r backend\requirements.txt
}

$FrontendDist = Join-Path $RepoRoot "frontend\dist\index.html"
if (-not (Test-Path $FrontendDist)) {
    Write-Host "[+] Building frontend production bundle..." -ForegroundColor Cyan
    Push-Location frontend
    if (-not (Test-Path "node_modules")) { npm install }
    node .\node_modules\vite\bin\vite.js build
    Pop-Location
}

$env:DATABASE_URL = "sqlite:///$((Join-Path $RepoRoot 'sentinelops_local.db') -replace '\\','/')"
$env:SECRET_KEY = "sentinelops-local-dev-secret-key-at-least-32-chars"
$env:SERVE_STATIC_FRONTEND = "true"
$env:CORS_ORIGINS = "http://localhost:8000,http://127.0.0.1:8000,http://localhost:5173"
$env:INITIAL_ADMIN_USERNAME = "admin"
$env:INITIAL_ADMIN_EMAIL = "admin@sentinelops.local"
$env:INITIAL_ADMIN_PASSWORD = "Admin@SentinelOps123!"
$env:DEMO_API_URL = "http://127.0.0.1:8000"
$env:NO_PROXY = "127.0.0.1,localhost"

Write-Host ""
Write-Host "  Dashboard URL : http://localhost:8000" -ForegroundColor Green
Write-Host "  Swagger Docs  : http://localhost:8000/docs" -ForegroundColor Green
Write-Host "  Admin Login   : admin / Admin@SentinelOps123!" -ForegroundColor Yellow
Write-Host "  Press Ctrl+C to stop." -ForegroundColor DarkGray
Write-Host ""

$demoProc = $null
try {
    if (-not $NoDemo) {
        Write-Host "[+] Starting Demo Mode Simulator in background (4 clearly labeled [DEMO] Linux servers)..." -ForegroundColor Cyan
        $demoProc = Start-Process -FilePath "python" `
            -ArgumentList "`"$RepoRoot\monitoring-agent\demo_simulator.py`"" `
            -WorkingDirectory (Join-Path $RepoRoot "monitoring-agent") `
            -PassThru -NoNewWindow
    }

    Push-Location (Join-Path $RepoRoot "backend")
    & $BackendPy -m uvicorn app.main:app --host 0.0.0.0 --port 8000
    Pop-Location
} finally {
    if ($demoProc -and -not $demoProc.HasExited) {
        Write-Host "`n[+] Stopping Demo Simulator..." -ForegroundColor Yellow
        Stop-Process -Id $demoProc.Id -Force -ErrorAction SilentlyContinue
    }
}
