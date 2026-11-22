#!/usr/bin/env sh
DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -x "$DIR/.venv/bin/python" ]; then PY="$DIR/.venv/bin/python"; else PY="$DIR/.venv/Scripts/python.exe"; fi
cd "$DIR" && exec "$PY" -m careem_mcp.cli "$@"
