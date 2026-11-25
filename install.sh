#!/bin/sh
set -eu

root=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
if [ "$#" -eq 1 ]; then
    set -- "$(realpath -- "$1")"
fi
cd "$root"

uv_bin=${UV_BIN:-uv}
if [ -x "$root/.runtime/bin/uv" ] && [ -z "${UV_BIN:-}" ]; then
    uv_bin="$root/.runtime/bin/uv"
fi
if ! command -v "$uv_bin" >/dev/null 2>&1; then
    echo "Install uv or point UV_BIN to its executable." >&2
    exit 1
fi

export UV_CACHE_DIR="$root/.runtime/cache"
export UV_PYTHON_INSTALL_DIR="$root/.runtime/python"
export UV_PYTHON_BIN_DIR="$root/.runtime/bin"
export PLAYWRIGHT_BROWSERS_PATH="$root/.browsers"
mkdir -p "$root/.runtime/tmp"
export TMPDIR="$root/.runtime/tmp"

if [ ! -x .venv/bin/python ]; then
    "$uv_bin" venv --python 3.12 .venv
fi
if [ "$#" -eq 0 ]; then
    set -- dist/leadengine-*.whl
    if [ "$#" -eq 1 ] && [ ! -f "$1" ]; then
        "$uv_bin" build --wheel
    fi
    set -- dist/leadengine-*.whl
fi
if [ "$#" -ne 1 ] || [ ! -f "$1" ]; then
    echo "Pass the path to a single leadEngine wheel." >&2
    exit 1
fi
"$uv_bin" pip install --python .venv/bin/python --reinstall-package leadengine "$1"
.venv/bin/python -m playwright install chromium
bin/leadengine --help
