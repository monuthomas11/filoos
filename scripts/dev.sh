#!/usr/bin/env bash
# Filoos - dev launcher (POSIX)
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

# Normalize a bad DEBUG value from the shell environment.
case "${DEBUG:-}" in
    ""|true|false|1|0|yes|no|on|off) ;;
    *)
        echo "[dev] ignoring invalid DEBUG=$DEBUG; using true"
        export DEBUG=true
        ;;
esac

cd "$BACKEND"

echo "[dev] installing dependencies (editable + dev)"
python -m pip install --upgrade pip >/dev/null
python -m pip install -e ".[dev]"

echo "[dev] applying database migrations"
python -m alembic upgrade head

echo "[dev] starting uvicorn on http://127.0.0.1:8000"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
