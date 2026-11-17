#!/usr/bin/env bash
# Ejecuta todo el proyecto con un solo comando en Linux/macOS.
set -euo pipefail
cd "$(dirname "$0")"

if command -v uv >/dev/null 2>&1; then
    exec uv run \
        --with pandas \
        --with openpyxl \
        --with matplotlib \
        --with jsonschema \
        --with referencing \
        python ejecutar_todo.py "$@"
fi

exec python3 ejecutar_todo.py "$@"
