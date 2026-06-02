#!/usr/bin/env bash
# FutureFunds - dev launcher (POSIX)
# Usage:  ./scripts/dev.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="$ROOT/backend"
VENV="$BACKEND/.venv"

# Create venv if missing.
if [ ! -d "$VENV" ]; then
    echo "[dev] creating virtualenv at $VENV"
    python3 -m venv "$VENV"
fi

# shellcheck disable=SC1091
source "$VENV/bin/activate"

echo "[dev] installing dependencies (editable + dev)"
python -m pip install --upgrade pip >/dev/null
python -m pip install -e "$BACKEND[dev]"

echo "[dev] applying database migrations"
( cd "$BACKEND" && alembic upgrade head )

echo "[dev] starting uvicorn on http://127.0.0.1:8000"
( cd "$BACKEND" && python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 )
