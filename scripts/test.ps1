$ErrorActionPreference = "Stop"
Push-Location "$PSScriptRoot\..\backend"
& .\.venv\Scripts\python -m pytest -q
$be = $LASTEXITCODE
Pop-Location
Push-Location "$PSScriptRoot\..\frontend"
npx vitest run
$fe = $LASTEXITCODE
Pop-Location
if ($be -ne 0 -or $fe -ne 0) { exit 1 }
