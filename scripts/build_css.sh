#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="$ROOT/backend"
BIN_DIR="$BACKEND/.bin"
STANDALONE_BASE="$BIN_DIR/tailwindcss"
STANDALONE="$STANDALONE_BASE"
CONFIG="$BACKEND/tailwind.config.js"
INPUT="$BACKEND/app/static/css/app.css"
OUTPUT="$BACKEND/app/static/css/app.compiled.css"
TAILWIND_VERSION="${TAILWIND_VERSION:-v3.4.19}"

mkdir -p "$BIN_DIR"

case "$(uname -s)" in
    MINGW*|MSYS*|CYGWIN*) STANDALONE="${STANDALONE_BASE}.exe" ;;
esac

download_standalone() {
    local os arch asset url tmp

    case "$(uname -s)" in
        Linux*) os="linux" ;;
        Darwin*) os="macos" ;;
        MINGW*|MSYS*|CYGWIN*) os="windows" ;;
        *)
            echo "[build_css] unsupported OS for standalone download: $(uname -s)" >&2
            return 1
            ;;
    esac

    case "$(uname -m)" in
        x86_64|amd64) arch="x64" ;;
        arm64|aarch64) arch="arm64" ;;
        *)
            echo "[build_css] unsupported CPU architecture for standalone download: $(uname -m)" >&2
            return 1
            ;;
    esac

    asset="tailwindcss-${os}-${arch}"
    if [ "$os" = "windows" ]; then
        asset="${asset}.exe"
        STANDALONE="${STANDALONE_BASE}.exe"
    fi

    url="https://github.com/tailwindlabs/tailwindcss/releases/download/${TAILWIND_VERSION}/${asset}"
    tmp="${STANDALONE}.tmp"

    echo "[build_css] downloading standalone Tailwind CLI ${TAILWIND_VERSION}"
    if command -v curl >/dev/null 2>&1; then
        curl -fsSL "$url" -o "$tmp"
    elif command -v wget >/dev/null 2>&1; then
        wget -qO "$tmp" "$url"
    else
        echo "[build_css] curl or wget is required to download the standalone Tailwind CLI." >&2
        return 1
    fi

    mv "$tmp" "$STANDALONE"
    chmod +x "$STANDALONE"
}

if [ ! -x "$STANDALONE" ]; then
    download_standalone || {
        if [ -x "$BACKEND/node_modules/.bin/tailwindcss" ]; then
            echo "[build_css] standalone download unavailable; using backend/node_modules/.bin/tailwindcss"
            TWCSS="$BACKEND/node_modules/.bin/tailwindcss"
        elif command -v tailwindcss >/dev/null 2>&1; then
            echo "[build_css] standalone download unavailable; using tailwindcss from PATH"
            TWCSS="$(command -v tailwindcss)"
        else
            exit 1
        fi
    }
fi

if [ -z "${TWCSS:-}" ]; then
    TWCSS="$STANDALONE"
fi

echo "[build_css] compiling $INPUT -> $OUTPUT"
"$TWCSS" \
    --config "$CONFIG" \
    --input "$INPUT" \
    --output "$OUTPUT" \
    --minify
echo "[build_css] done."
