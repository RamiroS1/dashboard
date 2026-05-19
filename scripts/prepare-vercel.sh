#!/usr/bin/env bash
# Prepara public/ para Vercel: datos JSON + assets estáticos.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PUBLIC="$ROOT/public"

mkdir -p "$PUBLIC/data" "$PUBLIC/assets"

# Datos: usar JSON ya generado o exportar si hay Python + pandas
if [[ -f "$ROOT/data/santos.json" ]]; then
  cp "$ROOT/data/santos.json" "$PUBLIC/data/"
elif command -v python3 &>/dev/null; then
  python3 -m pip install -q pandas openpyxl 2>/dev/null || true
  python3 "$ROOT/scripts/export_data.py"
else
  echo "Falta data/santos.json — ejecuta: python scripts/export_data.py" >&2
  exit 1
fi

# Assets ya están en public/assets/ (versionados en git)

if [[ ! -f "$PUBLIC/index.html" ]]; then
  echo "Falta public/index.html" >&2
  exit 1
fi

echo "Listo: $(find "$PUBLIC" -type f | wc -l) archivos en public/"
