#!/usr/bin/env bash
# Copia la app y los datos a public/ para el despliegue estático en Vercel.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PUBLIC="$ROOT/public"

mkdir -p "$PUBLIC/data" "$PUBLIC/.streamlit"

cp "$ROOT/streamlit_app.py" "$PUBLIC/"
cp -r "$ROOT/.streamlit/"* "$PUBLIC/.streamlit/"
cp "$ROOT/data/"*.xlsx "$PUBLIC/data/"

if [[ ! -f "$PUBLIC/index.html" ]]; then
  echo "Falta public/index.html" >&2
  exit 1
fi

echo "Listo: $(find "$PUBLIC" -type f | wc -l) archivos en public/"
