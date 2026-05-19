# Dashboard — Matriz de santos

Análisis exploratorio de la matriz de santos (Excel) con mapas, KPIs y gráficos Plotly.

## Desarrollo local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Los datos deben estar en `data/Estructura genérica de santos - con datos.xlsx`.

## Despliegue en Vercel

Vercel no ejecuta servidores Streamlit. Este proyecto se publica como **sitio estático** con [Stlite](https://stlite.net/) (Python/Streamlit en el navegador vía WebAssembly).

1. Conecta el repositorio en [Vercel](https://vercel.com).
2. **Root Directory:** carpeta `dashboard` (si el repo incluye más carpetas).
3. **Framework Preset:** Other.
4. Vercel usará `vercel.json`: el build copia `app.py` y `data/` a `public/` y sirve esa carpeta.

Tras el deploy, la primera carga puede tardar 1–2 minutos mientras se descargan las dependencias de Python en el cliente.

### Build manual

```bash
bash scripts/prepare-vercel.sh
```

La salida queda en `public/` (incluye `index.html`, `app.py`, `data/`, `.streamlit/`).

## Estructura

| Ruta | Uso |
|------|-----|
| `app.py` | App Streamlit (local y Stlite) |
| `data/*.xlsx` | Fuente de datos (incluir en el repo) |
| `public/index.html` | Entrada Stlite para Vercel |
| `vercel.json` | Configuración de build y salida |
