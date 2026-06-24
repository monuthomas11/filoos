# Filoos - dev launcher (Windows PowerShell 5.1+)
# Usage:  .\scripts\dev.ps1
# Stops on first error.

$ErrorActionPreference = "Stop"

$root      = Split-Path -Parent $PSScriptRoot
$backend   = Join-Path $root "backend"
$venv      = Join-Path $backend ".venv"
$venvAct   = Join-Path $venv "Scripts\Activate.ps1"

# Create venv if missing.
if (-not (Test-Path -LiteralPath $venv)) {
    Write-Host "[dev] creating virtualenv at $venv" -ForegroundColor Cyan
    python -m venv $venv
}

# Activate venv.
Write-Host "[dev] activating $venvAct" -ForegroundColor Cyan
& $venvAct

# Normalize a bad DEBUG value from the shell environment.
if ($env:DEBUG -and $env:DEBUG -notmatch '^(?i:true|false|1|0|yes|no|on|off)$') {
    Write-Host "[dev] ignoring invalid DEBUG=$env:DEBUG; using true" -ForegroundColor Yellow
    $env:DEBUG = "true"
}

# Install/update deps on every run (idempotent; pip is fast when up-to-date).
Set-Location -LiteralPath $backend
Write-Host "[dev] installing dependencies (editable + dev)" -ForegroundColor Cyan
python -m pip install --upgrade pip | Out-Null
python -m pip install -e ".[dev]" | Out-Null

# Apply any pending migrations.
Write-Host "[dev] applying database migrations" -ForegroundColor Cyan
python -m alembic upgrade head

# Start uvicorn (single process; Ctrl+C cleanly stops it).
Write-Host "[dev] starting uvicorn on http://127.0.0.1:8000" -ForegroundColor Green
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
