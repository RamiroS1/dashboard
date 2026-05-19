"""
Dashboard: Matriz de santos (Excel).

Local:  streamlit run app.py
Vercel: sitio estático con Stlite (ver public/index.html y vercel.json).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
XLSX_PATH = DATA_DIR / "Estructura genérica de santos - con datos.xlsx"
SHEET = "Matriz Santos"

COUNTRY_TO_ISO3 = {
    "Alemania": "DEU",
    "Argelia": "DZA",
    "Armenia": "ARM",
    "Bélgica": "BEL",
    "Colombia": "COL",
    "Croacia": "HRV",
    "Dinamarca": "DNK",
    "Egipto": "EGY",
    "El Salvador": "SLV",
    "España": "ESP",
    "Estados Unidos": "USA",
    "Francia": "FRA",
    "Hungría": "HUN",
    "Inglaterra": "GBR",
    "Israel": "ISR",
    "Italia": "ITA",
    "Macedonia del Norte": "MKD",
    "Perú": "PER",
    "Polonia": "POL",
    "Portugal": "PRT",
    "Reino Unido": "GBR",
    "Siria": "SYR",
    "Sudán": "SDN",
    "Suecia": "SWE",
    "Turquía": "TUR",
    "Túnez": "TUN",
}

# Centroides aproximados (lon, lat) para burbujas — mismo orden ISO-3 que Plotly
ISO3_CENTROID: dict[str, tuple[float, float]] = {
    "DEU": (10.45, 51.16),
    "DZA": (2.63, 28.16),
    "ARM": (44.93, 40.07),
    "BEL": (4.47, 50.50),
    "COL": (-74.30, 4.57),
    "HRV": (15.20, 45.10),
    "DNK": (9.50, 56.26),
    "EGY": (30.80, 26.82),
    "SLV": (-88.90, 13.79),
    "ESP": (-3.75, 40.46),
    "USA": (-98.58, 39.83),
    "FRA": (2.21, 46.23),
    "HUN": (19.50, 47.16),
    "GBR": (-3.44, 55.38),
    "ISR": (34.91, 31.95),
    "ITA": (12.57, 41.87),
    "MKD": (21.75, 41.61),
    "PER": (-75.02, -9.19),
    "POL": (19.40, 52.13),
    "PRT": (-8.22, 39.40),
    "SYR": (38.99, 34.80),
    "SDN": (29.89, 15.50),
    "SWE": (18.64, 60.13),
    "TUR": (35.24, 38.96),
    "TUN": (9.54, 33.89),
}

MAP_COLORSCALE: list[list[float | str]] = [
    [0.0, "#0f0720"],
    [0.2, "#3b0764"],
    [0.45, "#7c3aed"],
    [0.7, "#c084fc"],
    [1.0, "#fae8ff"],
]

THEME_GROUPS: list[tuple[str, list[str]]] = [
    ("Miedo y valentía", ["Miedo", "Valentía", "Confianza"]),
    ("Cansancio y esperanza", ["Cansancio", "Tristeza", "Esperanza"]),
    ("Búsqueda de propósito", ["Sentido de Vida", "Discernimiento", "Cambio de rumbo"]),
    ("Liderazgo y decisiones", ["Liderazgo", "Autoridad", "Decisiones difíciles"]),
    ("Conflictos y reconciliación", ["Conflicto", "Perdón", "Diálogo"]),
    ("Servicio y amor", ["Compasión", "Pobreza", "Comunidad"]),
    ("Conocimiento y creatividad", ["Educación", "Ciencia", "Sabiduría", "Enseñanza"]),
    ("Transformación personal", ["Conversión", "Humildad"]),
    ("Cuidado de personas y vida", ["Salud de las personas", "Cuidado de la naturaleza", "Cuidado de animales"]),
    ("Contemplación y espiritualidad", ["Oración", "Contemplación", "Interioridad"]),
]

DIMENSION_COLS = [c for _, cols in THEME_GROUPS for c in cols]


@st.cache_data(show_spinner=False)
def load_data() -> pd.DataFrame:
    if not XLSX_PATH.is_file():
        raise FileNotFoundError(f"No se encuentra el Excel: {XLSX_PATH}")
    df = pd.read_excel(XLSX_PATH, sheet_name=SHEET, header=1)
    df = df[df["Nombre"].notna()].copy()
    df["País"] = df["País"].astype(str).str.strip()
    df["iso3"] = df["País"].map(COUNTRY_TO_ISO3)
    missing_iso = df.loc[df["iso3"].isna() & df["País"].notna() & (df["País"] != "nan"), "País"].unique()
    if len(missing_iso):
        st.warning("Países sin código ISO para el mapa: " + ", ".join(sorted(missing_iso.astype(str))))
    for c in DIMENSION_COLS:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df["Año nacimiento"] = pd.to_numeric(df["Año nacimiento"], errors="coerce")
    df["Año defunción"] = pd.to_numeric(df["Año defunción"], errors="coerce")
    df["Edad"] = pd.to_numeric(df["Edad"], errors="coerce")
    df["Total"] = pd.to_numeric(df["Total"], errors="coerce")
    return df


def theme_scores(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for theme, cols in THEME_GROUPS:
        present = [c for c in cols if c in df.columns]
        if not present:
            continue
        sub = df[present]
        # Porcentaje de santos con marca (1) en al menos una dimensión del bloque, y media por dimensión
        pct_any = (sub.fillna(0).gt(0).any(axis=1)).mean() * 100
        mean_marked = sub.fillna(0).mean().mean() * 100
        rows.append({"Tema": theme, "% con alguna dimensión": pct_any, "Intensidad media (%)": mean_marked})
    return pd.DataFrame(rows)


def fig_map(
    df: pd.DataFrame,
    *,
    projection: str = "globe",
    lon_rotation: float = 14.0,
    lat_rotation: float = 22.0,
) -> go.Figure:
    agg = df.groupby("iso3", dropna=True).agg(santos=("Nombre", "count")).reset_index()
    agg = agg.dropna(subset=["iso3"])
    if agg.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="Sin datos geográficos en la selección",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=16, color="#a1a1aa"),
        )
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=40, b=0),
        )
        return fig

    país_por_iso = df.groupby("iso3")["País"].agg(lambda s: s.mode().iloc[0] if len(s.mode()) else s.iloc[0])
    agg["país"] = agg["iso3"].map(país_por_iso)

    choropleth = go.Choropleth(
        locations=agg["iso3"],
        z=agg["santos"],
        locationmode="ISO-3",
        colorscale=MAP_COLORSCALE,
        text=agg["país"],
        hovertemplate="<b>%{text}</b><br>Santos: %{z}<extra></extra>",
        marker_line_color="rgba(248, 250, 252, 0.35)",
        marker_line_width=0.75,
        colorbar=dict(
            title=dict(text="Santos", font=dict(size=13)),
            thickness=18,
            len=0.72,
            tickfont=dict(size=11),
            bgcolor="rgba(15,15,20,0.85)",
            bordercolor="rgba(148,163,184,0.35)",
            borderwidth=1,
        ),
    )

    lon_b: list[float] = []
    lat_b: list[float] = []
    bubble_text: list[str] = []
    bubble_size: list[float] = []
    mx = float(agg["santos"].max())
    for _, row in agg.iterrows():
        iso = str(row["iso3"])
        if iso not in ISO3_CENTROID:
            continue
        lo, la = ISO3_CENTROID[iso]
        lon_b.append(lo)
        lat_b.append(la)
        n_s = int(row["santos"])
        bubble_text.append(f"{row['país']} · {n_s} santo{'s' if n_s != 1 else ''}")
        bubble_size.append(18.0 + (n_s / mx) * 46.0)

    bubbles = go.Scattergeo(
        lon=lon_b,
        lat=lat_b,
        text=bubble_text,
        mode="markers",
        marker=dict(
            size=bubble_size,
            color="#f0abfc",
            line=dict(color="rgba(255,255,255,0.92)", width=2.5),
            opacity=0.96,
            sizemode="diameter",
        ),
        hovertemplate="<b>%{text}</b><extra></extra>",
        name="",
        showlegend=False,
    )

    fig = go.Figure(data=[choropleth, bubbles])

    is_globe = projection == "globe"
    fig.update_geos(
        projection_type="orthographic" if is_globe else "natural earth",
        projection_rotation=dict(lon=lon_rotation, lat=lat_rotation),
        showocean=True,
        oceancolor="#050814",
        showlakes=True,
        lakecolor="#070d18",
        showcountries=True,
        countrycolor="rgba(148,163,184,0.28)",
        countrywidth=0.6,
        coastlinecolor="rgba(186, 230, 253, 0.35)",
        coastlinewidth=0.8,
        landcolor="#141419",
        bgcolor="#030508",
        lonaxis_showgrid=True,
        lonaxis_gridcolor="rgba(71,85,105,0.25)",
        lataxis_showgrid=True,
        lataxis_gridcolor="rgba(71,85,105,0.25)",
        showframe=False,
        projection_scale=1.14 if is_globe else 1.05,
        resolution=110,
    )

    subtitle = (
        "Globo ortográfico: arrastra para rotar · rueda para acercar · doble clic reinicia la vista"
        if is_globe
        else "Proyección plana: arrastra y zoom con la rueda · doble clic reinicia"
    )

    fig.update_layout(
        margin=dict(l=0, r=0, t=56, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e4e4e7", family="Inter, system-ui, sans-serif"),
        title=dict(
            text=f"<b>Distribución geográfica</b><br><sup>{subtitle}</sup>",
            font=dict(size=18),
            x=0.02,
            xanchor="left",
        ),
        height=540 if is_globe else 500,
        uirevision="geo",
    )
    return fig


def fig_theme_radar(df: pd.DataFrame) -> go.Figure:
    scores = []
    labels = []
    for theme, cols in THEME_GROUPS:
        present = [c for c in cols if c in df.columns]
        if not present:
            continue
        sub = df[present].fillna(0)
        # % de santos que tienen al menos un “1” en el bloque
        v = (sub.gt(0).any(axis=1)).mean() * 100
        scores.append(v)
        labels.append(theme)
    fig = go.Figure(
        data=go.Scatterpolar(
            r=scores + [scores[0]],
            theta=labels + [labels[0]],
            fill="toself",
            fillcolor="rgba(124, 58, 237, 0.35)",
            line=dict(color="#a78bfa", width=2),
            name="% santos con huella en el tema",
        )
    )
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100], gridcolor="#3f3f46", linecolor="#52525b"),
            angularaxis=dict(linecolor="#52525b"),
            bgcolor="rgba(0,0,0,0)",
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e4e4e7"),
        title=dict(text="Presencia temática en la muestra (% de santos)", font=dict(size=18)),
        margin=dict(l=60, r=60, t=60, b=40),
        showlegend=False,
    )
    return fig


def main() -> None:
    st.set_page_config(
        page_title="Dashboard — Matriz de santos",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(
        """
        <style>
        div[data-testid="stMetric"] { background: linear-gradient(145deg, #1f1f28 0%, #18181f 100%); border: 1px solid #2d2d3a; border-radius: 12px; padding: 12px 16px; }
        h1 { letter-spacing: -0.02em; font-weight: 700 !important; }
        .block-container { padding-top: 1.5rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("Matriz de santos")
    st.caption(
        "Análisis exploratorio de dimensiones humanas y espirituales — datos del Excel "
        + f"`{XLSX_PATH.name}`"
    )

    try:
        df_raw = load_data()
    except FileNotFoundError as e:
        st.error(str(e))
        st.stop()

    countries = sorted(df_raw["País"].dropna().unique())
    y_min = int(df_raw["Año nacimiento"].min())
    y_max = int(df_raw["Año nacimiento"].max())

    with st.sidebar:
        st.header("Filtros")
        sel_countries = st.multiselect("País", countries, default=countries)
        yr = st.slider("Año de nacimiento", y_min, y_max, (y_min, y_max))
        min_total = st.slider("Puntuación Total mínima", 0, int(df_raw["Total"].max() or 10), 0)
        st.divider()
        st.markdown("**Qué muestra el tablero**")
        st.markdown(
            "- Mapa mundi con conteos por país.\n"
            "- KPIs y distribución temporal.\n"
            "- Temas del Excel agregados en radar y barras.\n"
            "- Tabla detalle y correlaciones entre dimensiones."
        )

    df = df_raw[
        df_raw["País"].isin(sel_countries)
        & df_raw["Año nacimiento"].between(yr[0], yr[1], inclusive="both")
        & (df_raw["Total"].fillna(0) >= min_total)
    ].copy()

    n = len(df)
    if n == 0:
        st.warning("Sin registros con los filtros actuales.")
        st.stop()

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Santos (filtrados)", n)
    with col2:
        st.metric("Países", df["País"].nunique())
    with col3:
        st.metric("Edad media (registrada)", f"{df['Edad'].mean():.1f} años")
    with col4:
        st.metric("Año nac. medio", f"{df['Año nacimiento'].mean():.0f}")
    with col5:
        st.metric("Puntuación Total media", f"{df['Total'].mean():.2f}")

    row_map = st.container()
    with row_map:
        st.subheader("Mapa mundial")
        cvm1, cvm2, cvm3 = st.columns([1.1, 1, 1])
        with cvm1:
            vista_mapa = st.selectbox(
                "Tipo de vista",
                ["Globo 3D (ortográfico)", "Mapa plano (Natural Earth)"],
                index=0,
                help="El globo se puede rotar con el ratón; la vista plana es cómoda para comparar países.",
            )
        usar_globo = vista_mapa.startswith("Globo")
        with cvm2:
            lon_map = st.slider(
                "Orientación · longitud",
                min_value=-180,
                max_value=180,
                value=14,
                step=2,
                help="Centra el mapa o el globo (este ↔ oeste).",
            )
        with cvm3:
            lat_map = st.slider(
                "Orientación · latitud",
                min_value=-55,
                max_value=72,
                value=24 if usar_globo else 18,
                step=2,
                help="Inclina la vista (norte ↔ sur).",
            )
        fig_m = fig_map(
            df,
            projection="globe" if usar_globo else "flat",
            lon_rotation=float(lon_map),
            lat_rotation=float(lat_map),
        )
        st.plotly_chart(
            fig_m,
            use_container_width=True,
            config={
                "scrollZoom": True,
                "displayModeBar": True,
                "modeBarButtonsToRemove": ["lasso2d", "select2d"],
            },
        )

    left, right = st.columns((1, 1))
    with left:
        pc = df["País"].value_counts().reset_index()
        pc.columns = ["País", "Santos"]
        fig_bar = px.bar(
            pc.head(15),
            x="Santos",
            y="País",
            orientation="h",
            color="Santos",
            color_continuous_scale=px.colors.sequential.Purples_r,
            labels={"Santos": "Cantidad"},
        )
        fig_bar.update_layout(
            title="Top países en la selección",
            yaxis=dict(categoryorder="total ascending", gridcolor="#27272a"),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#e4e4e7"),
            coloraxis_showscale=False,
            margin=dict(l=10, r=10, t=50, b=10),
            xaxis=dict(gridcolor="#27272a"),
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    with right:
        fig_hist = px.histogram(
            df,
            x="Año nacimiento",
            nbins=min(40, max(10, df["Año nacimiento"].nunique())),
            color_discrete_sequence=["#8b5cf6"],
        )
        fig_hist.update_layout(
            title="Distribución por siglo / año de nacimiento",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#e4e4e7"),
            bargap=0.15,
            xaxis=dict(gridcolor="#27272a"),
            yaxis=dict(gridcolor="#27272a", title="Santos"),
        )
        st.plotly_chart(fig_hist, use_container_width=True)

    st.subheader("Dimensiones temáticas")
    c1, c2 = st.columns((1, 1))
    with c1:
        st.plotly_chart(fig_theme_radar(df), use_container_width=True)
    with c2:
        ts = theme_scores(df)
        fig_th_bar = px.bar(
            ts.sort_values("Intensidad media (%)", ascending=True),
            x="Intensidad media (%)",
            y="Tema",
            orientation="h",
            color="Intensidad media (%)",
            color_continuous_scale=[[0, "#312e81"], [1, "#c4b5fd"]],
            hover_data=["% con alguna dimensión"],
        )
        fig_th_bar.update_layout(
            title="Intensidad media por tema (% sobre subdimensiones marcadas)",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#e4e4e7"),
            coloraxis_showscale=False,
            margin=dict(l=10, r=10, t=50, b=10),
            xaxis=dict(gridcolor="#27272a"),
            yaxis=dict(gridcolor="#27272a"),
        )
        st.plotly_chart(fig_th_bar, use_container_width=True)

    st.markdown(
        "**Interpretación:** cada celda del Excel marca presencia (1) de una dimensión en la vida del santo. "
        "El radar indica en qué proporción de santos aparece al menos una dimensión de ese bloque; "
        "la barra derecha promedia la densidad de marcas dentro del bloque."
    )

    st.subheader("Relación Total vs tiempo de vida y correlaciones entre dimensiones")
    u1, u2 = st.columns((1, 1))
    with u1:
        fig_sc = px.scatter(
            df,
            x="Año nacimiento",
            y="Total",
            color="País",
            hover_data=["Nombre", "Ciudad", "Edad"],
            color_discrete_sequence=px.colors.qualitative.Bold,
        )
        fig_sc.update_layout(
            title="Puntuación Total vs año de nacimiento",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#e4e4e7"),
            legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.02),
            xaxis=dict(gridcolor="#27272a"),
            yaxis=dict(gridcolor="#27272a"),
        )
        st.plotly_chart(fig_sc, use_container_width=True)

    with u2:
        sub = df[DIMENSION_COLS].fillna(0)
        corr = sub.corr()
        fig_hm = px.imshow(
            corr,
            color_continuous_scale=[[0, "#1e103f"], [0.5, "#3b0764"], [1, "#f5d0fe"]],
            zmin=-1,
            zmax=1,
            aspect="auto",
        )
        fig_hm.update_layout(
            title="Correlación entre subdimensiones (0/1)",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#e4e4e7", size=10),
            margin=dict(l=10, r=10, t=50, b=10),
            xaxis=dict(side="bottom", tickangle=-45),
        )
        st.plotly_chart(fig_hm, use_container_width=True)

    st.subheader("Explorador de santos")
    names = sorted(df["Nombre"].astype(str).tolist())
    pick = st.selectbox("Seleccionar figura", names)
    row = df.loc[df["Nombre"] == pick].iloc[0]
    st.markdown(f"**{row['Nombre']}** — {row.get('Ciudad', '')}, _{row.get('País', '')}_")
    kpi_cols = st.columns(4)
    with kpi_cols[0]:
        st.metric("Nacimiento", f"{row['Año nacimiento']:.0f}" if pd.notna(row["Año nacimiento"]) else "—")
    with kpi_cols[1]:
        st.metric("Defunción", f"{row['Año defunción']:.0f}" if pd.notna(row["Año defunción"]) else "—")
    with kpi_cols[2]:
        st.metric("Edad", f"{row['Edad']:.0f}" if pd.notna(row["Edad"]) else "—")
    with kpi_cols[3]:
        st.metric("Total", f"{row['Total']:.0f}" if pd.notna(row["Total"]) else "—")

    dcols = st.columns(2)
    with dcols[0]:
        st.markdown("**Problema central**")
        st.write(row.get("Problema central", "") or "—")
        st.markdown("**Decisión clave**")
        st.write(row.get("Decisión clave", "") or "—")
    with dcols[1]:
        st.markdown("**Situación humana / Virtud / Frase**")
        st.write(f"_Situación:_ {row.get('Situación humana', '') or '—'}")
        st.write(f"_Virtud:_ {row.get('Virtud principal', '') or '—'}")
        st.write(f"_Frase:_ {row.get('Frase corta', '') or '—'}")

    marks = []
    for theme, cols in THEME_GROUPS:
        hit = [c for c in cols if c in row.index and pd.notna(row[c]) and float(row[c]) > 0]
        if hit:
            marks.append((theme, ", ".join(hit)))
    if marks:
        st.markdown("**Dimensiones marcadas en la matriz**")
        for t, h in marks:
            st.markdown(f"- **{t}:** {h}")
    else:
        st.info("Sin marcas numéricas en dimensiones para esta figura.")

    st.subheader("Tabla filtrada")
    show_cols = [
        "Nombre",
        "Ciudad",
        "País",
        "Año nacimiento",
        "Año defunción",
        "Edad",
        "Total",
        "Problema central",
        "Decisión clave",
    ]
    st.dataframe(
        df[[c for c in show_cols if c in df.columns]].sort_values(["País", "Nombre"]),
        use_container_width=True,
        hide_index=True,
    )


main()
