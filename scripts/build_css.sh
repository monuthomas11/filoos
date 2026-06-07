#!/usr/bin/env bash
# Build the production Tailwind CSS bundle.
# Download the Tailwind standalone CLI from https://tailwindcss.com/blog/standalone-cli
# and place it on PATH as `tailwindcss`.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="$ROOT/backend"
CONFIG="$BACKEND/tailwind.config.js"
INPUT="$BACKEND/app/static/css/app.css"
OUTPUT="$BACKEND/app/static/css/app.compiled.css"

if ! command -v tailwindcss >/dev/null 2>&1; then
    echo "[build_css] tailwindcss CLI not found on PATH. Skipping." >&2
    exit 0
fi

echo "[build_css] compiling $INPUT -> $OUTPUT"
tailwindcss \
    --config "$CONFIG" \
    --input "$INPUT" \
    --output "$OUTPUT" \
    --minify
echo "[build_css] done."
