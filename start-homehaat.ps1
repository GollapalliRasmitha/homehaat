# HomeHaat - start everything locally.
# Run from the homehaat folder:   powershell -ExecutionPolicy Bypass -File .\start-homehaat.ps1
#
# What it does:
#   1. checks Docker Desktop, Node and Python are installed
#   2. creates .env from .env.example (first run only)
#   3. starts Postgres in Docker (port 5433)
#   4. installs Python and Node packages
#   5. runs database migrations and seed_categories
#   6. opens two windows: Django on :8000 and Next.js on :3000

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"
$python = Join-Path $backend ".venv\Scripts\python.exe"

function Step($text) { Write-Host ""; Write-Host "==> $text" -ForegroundColor Cyan }
function Fail($text) { Write-Host ""; Write-Host "X $text" -ForegroundColor Red; exit 1 }

# --- 1. Tools ---------------------------------------------------------------
Step "Checking tools"
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { Fail "Docker Desktop is not installed. Get it from https://www.docker.com/products/docker-desktop/" }
if (-not (Get-Command node -ErrorAction SilentlyContinue)) { Fail "Node.js is not installed. Get the LTS version from https://nodejs.org/" }
if (-not (Get-Command python -ErrorAction SilentlyContinue)) { Fail "Python is not installed. Get it from https://www.python.org/downloads/" }
Write-Host "Node $(node --version), $(python --version)"

docker info *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Docker Desktop is not running. Starting it..."
    $dockerApp = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    if (Test-Path $dockerApp) { Start-Process $dockerApp }
    for ($i = 0; $i -lt 60; $i++) {
        Start-Sleep -Seconds 3
        docker info *> $null
        if ($LASTEXITCODE -eq 0) { break }
    }
    if ($LASTEXITCODE -ne 0) { Fail "Docker Desktop didn't start. Open it by hand, wait for it to say 'running', then run this script again." }
}

# Oppora uses the same ports 3000 and 8000.
foreach ($port in 3000, 8000) {
    if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) {
        Fail "Port $port is already in use (is Oppora or an old HomeHaat window still open?). Close it and run this again."
    }
}

# --- 2. .env ------------------------------------------------------------------
Step "Checking .env"
$envFile = Join-Path $root ".env"
if (-not (Test-Path $envFile)) {
    $secret = -join ((48..57) + (97..122) | Get-Random -Count 50 | ForEach-Object { [char]$_ })
    $text = (Get-Content (Join-Path $root ".env.example") -Raw) -replace "change-me-to-a-long-random-string", $secret
    [System.IO.File]::WriteAllText($envFile, $text)  # UTF-8 without BOM
    Write-Host "Created .env from .env.example. Add your Razorpay test keys to it (see docs\razorpay-setup.md)."
} else {
    Write-Host ".env found."
}
if (-not (Select-String -Path $envFile -Pattern "^RAZORPAY_KEY_ID=rzp_test_" -Quiet)) {
    Write-Host "Note: Razorpay test keys are not set yet, so the Pay button will say payments are unavailable." -ForegroundColor Yellow
}

# --- 3. Postgres ----------------------------------------------------------------
Step "Starting Postgres (Docker, port 5433)"
Push-Location $root
docker compose up -d db
Pop-Location
for ($i = 0; $i -lt 40; $i++) {
    $health = docker inspect --format "{{.State.Health.Status}}" homehaat-db 2>$null
    if ($health -eq "healthy") { break }
    Start-Sleep -Seconds 2
}
if ($health -ne "healthy") { Fail "Postgres didn't become ready. Check Docker Desktop for errors." }
Write-Host "Postgres is ready."

# --- 4. Packages ----------------------------------------------------------------
Step "Installing Python packages"
if (-not (Test-Path $python)) { python -m venv (Join-Path $backend ".venv") }
& $python -m pip install --quiet --disable-pip-version-check -r (Join-Path $backend "requirements.txt")
if ($LASTEXITCODE -ne 0) { Fail "pip install failed." }

Step "Installing Node packages"
Push-Location $frontend
npm install --no-fund --no-audit
$npmExit = $LASTEXITCODE
Pop-Location
if ($npmExit -ne 0) { Fail "npm install failed." }

# --- 5. Database ----------------------------------------------------------------
Step "Migrating the database and seeding categories"
& $python (Join-Path $backend "manage.py") migrate --noinput
if ($LASTEXITCODE -ne 0) { Fail "migrate failed." }
& $python (Join-Path $backend "manage.py") seed_categories
if ($LASTEXITCODE -ne 0) { Fail "seed_categories failed." }

# --- 6. Two windows ---------------------------------------------------------------
Step "Opening Django (8000) and Next.js (3000)"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "`$host.UI.RawUI.WindowTitle='HomeHaat API :8000'; Set-Location '$backend'; & '$python' manage.py runserver 127.0.0.1:8000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "`$host.UI.RawUI.WindowTitle='HomeHaat web :3000'; Set-Location '$frontend'; npm run dev"

Write-Host ""
Write-Host "HomeHaat is starting. Open http://localhost:3000 in a few seconds." -ForegroundColor Green
Write-Host "Payments: local test payments are confirmed through /api/payments/verify/ (the Razorpay webhook needs a public URL; see docs\razorpay-setup.md)."
