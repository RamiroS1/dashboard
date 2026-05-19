#!/usr/bin/env python3
"""Exporta el Excel a JSON para el dashboard estático (Vercel)."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
XLSX_PATH = ROOT / "data" / "Estructura genérica de santos - con datos.xlsx"
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

ISO3_CENTROID = {
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

THEME_GROUPS = [
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

OUT_PATHS = [
    ROOT / "data" / "santos.json",
    ROOT / "public" / "data" / "santos.json",
]


def load_raw() -> pd.DataFrame:
    if not XLSX_PATH.is_file():
        raise FileNotFoundError(f"No se encuentra el Excel: {XLSX_PATH}")
    df = pd.read_excel(XLSX_PATH, sheet_name=SHEET, header=1)
    df = df[df["Nombre"].notna()].copy()
    df["País"] = df["País"].astype(str).str.strip()
    df["iso3"] = df["País"].map(COUNTRY_TO_ISO3)
    for c in DIMENSION_COLS:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    for col in ("Año nacimiento", "Año defunción", "Edad", "Total"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def to_records(df: pd.DataFrame) -> list[dict]:
    import math

    out = df.where(pd.notna(df), None).to_dict(orient="records")
    for row in out:
        for k, v in list(row.items()):
            if isinstance(v, float) and not math.isnan(v) and v == int(v):
                row[k] = int(v)
    return out


def main() -> None:
    df = load_raw()
    payload = {
        "meta": {
            "source": XLSX_PATH.name,
            "themeGroups": [[t, cols] for t, cols in THEME_GROUPS],
            "dimensionCols": DIMENSION_COLS,
            "countryToIso3": COUNTRY_TO_ISO3,
            "iso3Centroid": {k: list(v) for k, v in ISO3_CENTROID.items()},
        },
        "records": to_records(df),
    }
    text = json.dumps(payload, ensure_ascii=False)
    for path in OUT_PATHS:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        print(f"Escrito {path} ({len(text) // 1024} KB)")


if __name__ == "__main__":
    main()
