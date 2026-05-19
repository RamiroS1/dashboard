# Dashboard — Matriz de santos

Análisis exploratorio de la matriz de santos con mapas, KPIs y gráficos Plotly.

## Desarrollo local (Streamlit)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Despliegue en Vercel (recomendado)

El sitio en producción es **HTML + Plotly.js** (carga en pocos segundos). No usa Python en el navegador.

1. Conecta el repo en [Vercel](https://vercel.com).
2. Framework: **Other** (usa `vercel.json`).
3. Tras cada deploy, `public/` sirve `index.html` y `data/santos.json`.

### Actualizar datos del Excel

```bash
python scripts/export_data.py   # genera data/santos.json
git add data/santos.json
git commit -m "Update santos data"
git push
```

## Estructura

| Ruta | Uso |
|------|-----|
| `streamlit_app.py` | App Streamlit para desarrollo local |
| `public/index.html` | Dashboard web en Vercel |
| `public/assets/dashboard.js` | Lógica y gráficos |
| `data/santos.json` | Datos exportados del Excel |
| `scripts/export_data.py` | Excel → JSON |
