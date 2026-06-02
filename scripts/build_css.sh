#!/usr/bin/env bash
# Build the production Tailwind CSS bundle.
# Phase 1 uses the Tailwind Play CDN at runtime; this script is a placeholder
# for the Phase 8 switch to a compiled stylesheet using the Tailwind
# standalone CLI (no Node required).
#
# To use later:
#   1. Download the Tailwind standalone CLI from https://tailwindcss.com/blog/standalone-cli
#   2. Put it on PATH as `tailwindcss`
#   3. Create backend/tailwind.config.js mirroring the inline config in base.html
#   4. Run this script.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="$ROOT/backend"
INPUT="$BACKEND/app/static/css/app.css"
OUTPUT="$BACKEND/app/static/css/app.compiled.css"

if ! command -v tailwindcss >/dev/null 2>&1; then
    echo "[build_css] tailwindcss CLI not found on PATH. Skipping." >&2
    echo "[build_css] Phase 1 uses the Tailwind Play CDN; this script is for future use." >&2
    exit 0
fi

echo "[build_css] compiling $INPUT -> $OUTPUT"
tailwindcss \
    --input "$INPUT" \
    --output "$OUTPUT" \
    --minify
echo "[build_css] done."
