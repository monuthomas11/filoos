# FutureFunds - dev launcher (Windows PowerShell 5.1+)
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

# Install/update deps on every run (idempotent; pip is fast when up-to-date).
Write-Host "[dev] installing dependencies (editable + dev)" -ForegroundColor Cyan
python -m pip install --upgrade pip | Out-Null
python -m pip install -e ".[dev]" | Out-Null

# Apply any pending migrations.
Write-Host "[dev] applying database migrations" -ForegroundColor Cyan
Set-Location -LiteralPath $backend
alembic upgrade head

# Start uvicorn with auto-reload.
Write-Host "[dev] starting uvicorn on http://127.0.0.1:8000" -ForegroundColor Green
Set-Location -LiteralPath $backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
