# Sets up (first run only) and starts the Waymark APAAR Hub: backend + frontend + browser.
# Normally started by double-clicking Start-App.bat in the repo root.
#   -Reset      wipe and re-create the demo data
#   -NoBrowser  do not open the browser (used for testing)
param([switch]$Reset, [switch]$NoBrowser, [int]$FrontendPort = 3000)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$be = Join-Path $root "backend"
$fe = Join-Path $root "frontend"
$vpy = Join-Path $be ".venv\Scripts\python.exe"

function Step($m) { Write-Host "`n==> $m" -ForegroundColor Cyan }
function Fail($m) { Write-Host "`nPROBLEM: $m" -ForegroundColor Red; Write-Host "Send a screenshot of this window to the team."; exit 1 }

# ---- 1. Python 3.11+ and Node 20.9+ -------------------------------------------------
Step "Checking Python and Node.js"
$pyCmd = $null
foreach ($c in @(@("py", "-3.11"), @("py", "-3.12"), @("py", "-3"), @("python"))) {
  try {
    $extra = @(); if ($c.Count -gt 1) { $extra = $c[1..($c.Count - 1)] }
    $ok = & $c[0] @extra -c "import sys;print(int(sys.version_info>=(3,11)))" 2>$null
    if ("$ok".Trim() -eq "1") { $pyCmd = $c; break }
  } catch { }
}
if (-not $pyCmd) { Fail "Python 3.11 or newer is not installed. Install it from https://www.python.org/downloads/ (tick 'Add python.exe to PATH'), then double-click Start-App.bat again." }

$nodeOk = $false
try {
  $v = (& node -v 2>$null).TrimStart("v").Split(".")
  $nodeOk = ([int]$v[0] -gt 20) -or ([int]$v[0] -eq 20 -and [int]$v[1] -ge 9)
} catch { }
if (-not $nodeOk) { Fail "Node.js 20.9 or newer is not installed. Install the LTS version from https://nodejs.org/, then double-click Start-App.bat again." }

foreach ($port in 8000, $FrontendPort) {
  if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) {
    Fail "Port $port is already in use. The app may already be running: close its black windows (or restart the computer) and try again."
  }
}

# ---- 2. Backend setup ------------------------------------------------------------------
Push-Location $be
if (-not (Test-Path $vpy)) {
  Step "Creating the backend environment (first run only, about 1 minute)"
  $extra = @(); if ($pyCmd.Count -gt 1) { $extra = $pyCmd[1..($pyCmd.Count - 1)] }
  & $pyCmd[0] @extra -m venv .venv
  if ($LASTEXITCODE -ne 0) { Pop-Location; Fail "Could not create the Python environment." }
}
$stamp = Join-Path $be ".venv\deps.stamp"
$want = (Get-FileHash (Join-Path $be "pyproject.toml")).Hash
if (-not ((Test-Path $stamp) -and ((Get-Content $stamp -Raw).Trim() -eq $want))) {
  Step "Installing backend packages (first run only, a few minutes)"
  $req = Join-Path $env:TEMP "apaar-requirements.txt"
  & $vpy -c "import tomllib;print('\n'.join(tomllib.load(open('pyproject.toml','rb'))['project']['dependencies']))" | Set-Content $req
  & $vpy -m pip install --disable-pip-version-check -r $req
  if ($LASTEXITCODE -ne 0) { Pop-Location; Fail "Installing backend packages failed. Check the internet connection and try again." }
  Set-Content $stamp $want
}
Step "Preparing the database"
& $vpy -m alembic upgrade head
if ($LASTEXITCODE -ne 0) { Pop-Location; Fail "Database setup failed." }
$seeded = Join-Path $be ".venv\seeded.stamp"
if ($Reset -or -not (Test-Path $seeded)) {
  Step "Loading demo data (all synthetic)"
  & $vpy -m app.seed --demo
  if ($LASTEXITCODE -ne 0) { Pop-Location; Fail "Loading demo data failed." }
  Set-Content $seeded "ok"
}
Pop-Location

# ---- 3. Frontend setup -----------------------------------------------------------------
if (-not (Test-Path (Join-Path $fe "node_modules"))) {
  Step "Installing frontend packages (first run only, a few minutes)"
  Push-Location $fe
  & npm.cmd install
  $code = $LASTEXITCODE
  Pop-Location
  if ($code -ne 0) { Fail "Installing frontend packages failed. Check the internet connection and try again." }
}

# ---- 4. Start both servers in their own windows -------------------------------------------
Step "Starting the app"
$beCmd = "`$host.UI.RawUI.WindowTitle='APAAR backend - close this window to stop'; Set-Location '$be'; & '$vpy' -m uvicorn app.main:app --port 8000"
$feCmd = "`$host.UI.RawUI.WindowTitle='APAAR frontend - close this window to stop'; Set-Location '$fe'; `$env:NEXT_PUBLIC_DEMO='1'; npm.cmd run dev -- -p $FrontendPort"
Start-Process powershell -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-NoExit", "-Command", $beCmd
Start-Process powershell -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-NoExit", "-Command", $feCmd

function Wait-Up($url, $secs) {
  $end = (Get-Date).AddSeconds($secs)
  while ((Get-Date) -lt $end) {
    try { Invoke-WebRequest -UseBasicParsing -TimeoutSec 5 $url | Out-Null; return $true } catch { Start-Sleep 2 }
  }
  return $false
}
Write-Host "Waiting for the backend..."
if (-not (Wait-Up "http://127.0.0.1:8000/health" 90)) { Fail "The backend did not start. Look at the window titled 'APAAR backend' for the error." }
Write-Host "Waiting for the frontend (the first start can take a minute)..."
if (-not (Wait-Up "http://localhost:$FrontendPort/login" 240)) { Fail "The frontend did not start. Look at the window titled 'APAAR frontend' for the error." }

if (-not $NoBrowser) { Start-Process "http://localhost:$FrontendPort" }
Write-Host "`nThe app is running at http://localhost:$FrontendPort" -ForegroundColor Green
Write-Host "Sign in with any of these (password for all: Demo@1234):"
Write-Host "  admin@demo.test        AICTE admin"
Write-Host "  officer@demo.test      AICTE officer"
Write-Host "  inst-admin@demo.test   Institution admin"
Write-Host "  staff@demo.test        Institution staff"
Write-Host "  verifier@demo.test     Verifier"
Write-Host "`nTo stop the app, close the two other black windows. This window can be closed now."
