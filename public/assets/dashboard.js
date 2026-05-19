const MAP_COLORSCALE = [
  [0, "#0f0720"],
  [0.2, "#3b0764"],
  [0.45, "#7c3aed"],
  [0.7, "#c084fc"],
  [1, "#fae8ff"],
];

const PLOT_CFG = { responsive: true, scrollZoom: true, displayModeBar: true };
const LAYOUT_BASE = {
  paper_bgcolor: "rgba(0,0,0,0)",
  plot_bgcolor: "rgba(0,0,0,0)",
  font: { color: "#e4e4e7", family: "Inter, system-ui, sans-serif" },
};

let payload = null;
let rawRecords = [];

function num(v) {
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

function mean(arr) {
  const xs = arr.filter((x) => x != null && Number.isFinite(x));
  if (!xs.length) return null;
  return xs.reduce((a, b) => a + b, 0) / xs.length;
}

function unique(arr) {
  return [...new Set(arr)];
}

function filterRecords(records, f) {
  return records.filter((r) => {
    if (!f.countries.has(r["País"])) return false;
    const y = num(r["Año nacimiento"]);
    if (y == null || y < f.yearMin || y > f.yearMax) return false;
    const t = num(r["Total"]) ?? 0;
    if (t < f.minTotal) return false;
    return true;
  });
}

function getFilters() {
  const sel = document.getElementById("filter-countries");
  const countries = new Set(
    [...sel.selectedOptions].map((o) => o.value)
  );
  return {
    countries,
    yearMin: Number(document.getElementById("year-min").value),
    yearMax: Number(document.getElementById("year-max").value),
    minTotal: Number(document.getElementById("min-total").value),
    mapType: document.getElementById("map-type").value,
    lon: Number(document.getElementById("map-lon").value),
    lat: Number(document.getElementById("map-lat").value),
    saint: document.getElementById("saint-pick").value,
  };
}

function themeScores(df, meta) {
  const rows = [];
  for (const [theme, cols] of meta.themeGroups) {
    const present = cols.filter((c) => df[0] && c in df[0]);
    if (!present.length) continue;
    let anyCount = 0;
    let sumMarks = 0;
    let nMarks = 0;
    for (const r of df) {
      const vals = present.map((c) => num(r[c]) || 0);
      if (vals.some((v) => v > 0)) anyCount++;
      for (const v of vals) {
        sumMarks += v;
        nMarks++;
      }
    }
    rows.push({
      Tema: theme,
      pctAny: (anyCount / df.length) * 100,
      intensity: nMarks ? (sumMarks / nMarks) * 100 : 0,
    });
  }
  return rows;
}

function corrMatrix(records, cols) {
  const n = cols.length;
  const data = cols.map((c) =>
    records.map((r) => num(r[c]) || 0)
  );
  const z = Array.from({ length: n }, () => Array(n).fill(0));
  for (let i = 0; i < n; i++) {
    for (let j = 0; j < n; j++) {
      const xi = data[i];
      const xj = data[j];
      const mi = mean(xi);
      const mj = mean(xj);
      let nume = 0;
      let di = 0;
      let dj = 0;
      for (let k = 0; k < xi.length; k++) {
        const a = xi[k] - mi;
        const b = xj[k] - mj;
        nume += a * b;
        di += a * a;
        dj += b * b;
      }
      z[i][j] = di && dj ? nume / Math.sqrt(di * dj) : 0;
    }
  }
  return { z, cols };
}

function aggregateMap(df, meta) {
  const byIso = {};
  const paísPorIso = {};
  for (const r of df) {
    const iso = r.iso3;
    if (!iso) continue;
    byIso[iso] = (byIso[iso] || 0) + 1;
    if (!paísPorIso[iso]) paísPorIso[iso] = r["País"];
  }
  return { byIso, paísPorIso, meta };
}

function buildMap(df, f, meta) {
  const { byIso, paísPorIso } = aggregateMap(df, meta);
  const isos = Object.keys(byIso);
  if (!isos.length) {
    return {
      data: [],
      layout: {
        ...LAYOUT_BASE,
        annotations: [
          {
            text: "Sin datos geográficos en la selección",
            showarrow: false,
            xref: "paper",
            yref: "paper",
            x: 0.5,
            y: 0.5,
            font: { size: 16, color: "#a1a1aa" },
          },
        ],
        height: 500,
      },
    };
  }

  const locations = isos;
  const z = locations.map((iso) => byIso[iso]);
  const text = locations.map((iso) => paísPorIso[iso]);
  const mx = Math.max(...z);

  const lonB = [];
  const latB = [];
  const bubbleText = [];
  const bubbleSize = [];
  for (const iso of isos) {
    const c = meta.iso3Centroid[iso];
    if (!c) continue;
    const n = byIso[iso];
    lonB.push(c[0]);
    latB.push(c[1]);
    bubbleText.push(`${paísPorIso[iso]} · ${n} santo${n !== 1 ? "s" : ""}`);
    bubbleSize.push(18 + (n / mx) * 46);
  }

  const isGlobe = f.mapType === "globe";
  const geoBase = {
    showocean: true,
    oceancolor: "#050814",
    showlakes: true,
    lakecolor: "#070d18",
    showcountries: true,
    countrycolor: "rgba(148,163,184,0.28)",
    countrywidth: 0.6,
    coastlinecolor: "rgba(186, 230, 253, 0.35)",
    coastlinewidth: 0.8,
    landcolor: "#141419",
    bgcolor: "#030508",
    showframe: false,
    resolution: 110,
    projection: {
      type: isGlobe ? "orthographic" : "natural earth",
      rotation: { lon: f.lon, lat: f.lat },
      scale: isGlobe ? 1.14 : 1.05,
    },
  };

  return {
    data: [
      {
        type: "choropleth",
        locations,
        z,
        locationmode: "ISO-3",
        colorscale: MAP_COLORSCALE,
        text,
        hovertemplate: "<b>%{text}</b><br>Santos: %{z}<extra></extra>",
        marker: { line: { color: "rgba(248,250,252,0.35)", width: 0.75 } },
        colorbar: {
          title: { text: "Santos", font: { size: 13 } },
          thickness: 18,
          len: 0.72,
          tickfont: { size: 11 },
          bgcolor: "rgba(15,15,20,0.85)",
          bordercolor: "rgba(148,163,184,0.35)",
          borderwidth: 1,
        },
      },
      {
        type: "scattergeo",
        lon: lonB,
        lat: latB,
        text: bubbleText,
        mode: "markers",
        marker: {
          size: bubbleSize,
          color: "#f0abfc",
          line: { color: "rgba(255,255,255,0.92)", width: 2.5 },
          opacity: 0.96,
          sizemode: "diameter",
        },
        hovertemplate: "<b>%{text}</b><extra></extra>",
        showlegend: false,
      },
    ],
    layout: {
      ...LAYOUT_BASE,
      geo: geoBase,
      margin: { l: 0, r: 0, t: 56, b: 8 },
      height: isGlobe ? 540 : 500,
      title: {
        text: `<b>Distribución geográfica</b><br><sup>${
          isGlobe
            ? "Globo ortográfico: arrastra para rotar · rueda para acercar"
            : "Mapa plano: arrastra y zoom con la rueda"
        }</sup>`,
        font: { size: 18 },
        x: 0.02,
        xanchor: "left",
      },
    },
  };
}

function plot(id, fig) {
  const el = document.getElementById(id);
  if (!el) return;
  Plotly.react(el, fig.data, fig.layout, PLOT_CFG);
}

function renderKpis(df) {
  const countries = unique(df.map((r) => r["País"])).length;
  document.getElementById("kpi-n").textContent = df.length;
  document.getElementById("kpi-countries").textContent = countries;
  document.getElementById("kpi-age").textContent =
    mean(df.map((r) => num(r["Edad"])))?.toFixed(1) ?? "—";
  document.getElementById("kpi-year").textContent =
    mean(df.map((r) => num(r["Año nacimiento"])))?.toFixed(0) ?? "—";
  document.getElementById("kpi-total").textContent =
    mean(df.map((r) => num(r["Total"])))?.toFixed(2) ?? "—";
}

function renderCharts(df, f, meta) {
  if (!df.length) {
    document.getElementById("empty-msg").classList.remove("hidden");
    ["chart-map", "chart-bar", "chart-hist", "chart-radar", "chart-theme", "chart-scatter", "chart-corr"].forEach(
      (id) => {
        const el = document.getElementById(id);
        if (el) Plotly.purge(el);
      }
    );
    return;
  }
  document.getElementById("empty-msg").classList.add("hidden");

  plot("chart-map", buildMap(df, f, meta));

  const byCountry = {};
  for (const r of df) {
    byCountry[r["País"]] = (byCountry[r["País"]] || 0) + 1;
  }
  const top = Object.entries(byCountry)
    .sort((a, b) => a[1] - b[1])
    .slice(-15);
  plot("chart-bar", {
    data: [
      {
        type: "bar",
        orientation: "h",
        x: top.map((t) => t[1]),
        y: top.map((t) => t[0]),
        marker: {
          color: top.map((t) => t[1]),
          colorscale: [[0, "#3b0764"], [1, "#fae8ff"]],
        },
      },
    ],
    layout: {
      ...LAYOUT_BASE,
      title: "Top países en la selección",
      margin: { l: 10, r: 10, t: 50, b: 10 },
      xaxis: { gridcolor: "#27272a", title: "Cantidad" },
      yaxis: { gridcolor: "#27272a", categoryorder: "total ascending" },
      showlegend: false,
    },
  });

  const years = df.map((r) => num(r["Año nacimiento"])).filter((y) => y != null);
  plot("chart-hist", {
    data: [{ type: "histogram", x: years, marker: { color: "#8b5cf6" }, nbinsx: 30 }],
    layout: {
      ...LAYOUT_BASE,
      title: "Distribución por año de nacimiento",
      bargap: 0.15,
      xaxis: { gridcolor: "#27272a" },
      yaxis: { gridcolor: "#27272a", title: "Santos" },
      margin: { l: 50, r: 20, t: 50, b: 40 },
    },
  });

  const scores = [];
  const labels = [];
  for (const [theme, cols] of meta.themeGroups) {
    const present = cols.filter((c) => df[0] && c in df[0]);
    if (!present.length) continue;
    let anyCount = 0;
    for (const r of df) {
      if (present.some((c) => (num(r[c]) || 0) > 0)) anyCount++;
    }
    scores.push((anyCount / df.length) * 100);
    labels.push(theme);
  }
  if (scores.length) {
    plot("chart-radar", {
      data: [
        {
          type: "scatterpolar",
          r: [...scores, scores[0]],
          theta: [...labels, labels[0]],
          fill: "toself",
          fillcolor: "rgba(124, 58, 237, 0.35)",
          line: { color: "#a78bfa", width: 2 },
        },
      ],
      layout: {
        ...LAYOUT_BASE,
        polar: {
          radialaxis: { visible: true, range: [0, 100], gridcolor: "#3f3f46", linecolor: "#52525b" },
          angularaxis: { linecolor: "#52525b" },
          bgcolor: "rgba(0,0,0,0)",
        },
        title: "Presencia temática en la muestra (% de santos)",
        showlegend: false,
        margin: { l: 60, r: 60, t: 60, b: 40 },
      },
    });
  }

  const ts = themeScores(df, meta).sort((a, b) => a.intensity - b.intensity);
  plot("chart-theme", {
    data: [
      {
        type: "bar",
        orientation: "h",
        x: ts.map((t) => t.intensity),
        y: ts.map((t) => t.Tema),
        marker: {
          color: ts.map((t) => t.intensity),
          colorscale: [[0, "#312e81"], [1, "#c4b5fd"]],
        },
        hovertemplate: "%{y}<br>Intensidad: %{x:.1f}%<extra></extra>",
      },
    ],
    layout: {
      ...LAYOUT_BASE,
      title: "Intensidad media por tema",
      margin: { l: 10, r: 10, t: 50, b: 10 },
      xaxis: { gridcolor: "#27272a" },
      yaxis: { gridcolor: "#27272a" },
      showlegend: false,
    },
  });

  const countries = unique(df.map((r) => r["País"]));
  const palette = [
    "#ef4444", "#f97316", "#eab308", "#22c55e", "#06b6d4", "#3b82f6", "#8b5cf6", "#ec4899",
  ];
  plot("chart-scatter", {
    data: countries.map((país, i) => {
      const pts = df.filter((r) => r["País"] === país);
      return {
        type: "scatter",
        mode: "markers",
        name: país,
        x: pts.map((r) => num(r["Año nacimiento"])),
        y: pts.map((r) => num(r["Total"])),
        text: pts.map((r) => r["Nombre"]),
        marker: { color: palette[i % palette.length] },
        hovertemplate: "%{text}<br>Año: %{x}<br>Total: %{y}<extra></extra>",
      };
    }),
    layout: {
      ...LAYOUT_BASE,
      title: "Puntuación Total vs año de nacimiento",
      xaxis: { gridcolor: "#27272a" },
      yaxis: { gridcolor: "#27272a" },
      legend: { orientation: "v", yanchor: "top", y: 1, x: 1.02 },
      margin: { l: 50, r: 120, t: 50, b: 40 },
    },
  });

  const { z, cols } = corrMatrix(df, meta.dimensionCols);
  plot("chart-corr", {
    data: [
      {
        type: "heatmap",
        z,
        x: cols,
        y: cols,
        zmin: -1,
        zmax: 1,
        colorscale: [
          [0, "#1e103f"],
          [0.5, "#3b0764"],
          [1, "#f5d0fe"],
        ],
      },
    ],
    layout: {
      ...LAYOUT_BASE,
      title: "Correlación entre subdimensiones (0/1)",
      font: { color: "#e4e4e7", size: 10 },
      margin: { l: 10, r: 10, t: 50, b: 10 },
      xaxis: { side: "bottom", tickangle: -45 },
    },
  });
}

function renderSaint(df, name, meta) {
  const el = document.getElementById("saint-detail");
  const row = df.find((r) => r["Nombre"] === name);
  if (!row) {
    el.innerHTML = "<p class='empty'>Selecciona una figura</p>";
    return;
  }
  const marks = [];
  for (const [theme, cols] of meta.themeGroups) {
    const hit = cols.filter((c) => (num(row[c]) || 0) > 0);
    if (hit.length) marks.push(`<li><strong>${theme}:</strong> ${hit.join(", ")}</li>`);
  }
  el.innerHTML = `
    <h3>${row["Nombre"]} — ${row["Ciudad"] || ""}, <em>${row["País"] || ""}</em></h3>
    <div class="kpis" style="margin:0.75rem 0">
      <div class="kpi"><div class="label">Nacimiento</div><div class="value">${fmt(row["Año nacimiento"])}</div></div>
      <div class="kpi"><div class="label">Defunción</div><div class="value">${fmt(row["Año defunción"])}</div></div>
      <div class="kpi"><div class="label">Edad</div><div class="value">${fmt(row["Edad"])}</div></div>
      <div class="kpi"><div class="label">Total</div><div class="value">${fmt(row["Total"])}</div></div>
    </div>
    <div class="grid">
      <div>
        <p><strong>Problema central</strong><br>${esc(row["Problema central"])}</p>
        <p><strong>Decisión clave</strong><br>${esc(row["Decisión clave"])}</p>
      </div>
      <div>
        <p><em>Situación:</em> ${esc(row["Situación humana"])}</p>
        <p><em>Virtud:</em> ${esc(row["Virtud principal"])}</p>
        <p><em>Frase:</em> ${esc(row["Frase corta"])}</p>
      </div>
    </div>
    ${marks.length ? `<p><strong>Dimensiones marcadas</strong></p><ul>${marks.join("")}</ul>` : "<p><em>Sin marcas en dimensiones.</em></p>"}
  `;
}

function fmt(v) {
  const n = num(v);
  return n != null ? String(Math.round(n)) : "—";
}

function esc(s) {
  if (s == null || s === "") return "—";
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function renderTable(df) {
  const cols = [
    "Nombre",
    "Ciudad",
    "País",
    "Año nacimiento",
    "Año defunción",
    "Edad",
    "Total",
    "Problema central",
    "Decisión clave",
  ];
  const sorted = [...df].sort((a, b) =>
    (a["País"] || "").localeCompare(b["País"] || "") ||
    (a["Nombre"] || "").localeCompare(b["Nombre"] || "")
  );
  const head = cols.map((c) => `<th>${c}</th>`).join("");
  const body = sorted
    .map(
      (r) =>
        `<tr>${cols.map((c) => `<td>${esc(r[c])}</td>`).join("")}</tr>`
    )
    .join("");
  document.getElementById("data-table").innerHTML = `<table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`;
}

function updateSaintOptions(df) {
  const sel = document.getElementById("saint-pick");
  const prev = sel.value;
  const names = [...df].map((r) => r["Nombre"]).sort();
  sel.innerHTML = names
    .map((n) => {
      const safe = String(n).replace(/&/g, "&amp;").replace(/"/g, "&quot;");
      return `<option value="${safe}">${esc(n)}</option>`;
    })
    .join("");
  if (names.includes(prev)) sel.value = prev;
  else if (names.length) sel.value = names[0];
}

function render() {
  const f = getFilters();
  const df = filterRecords(rawRecords, f);
  const meta = payload.meta;

  renderKpis(df);
  renderCharts(df, f, meta);
  updateSaintOptions(df);
  renderSaint(df, document.getElementById("saint-pick").value, meta);
  renderTable(df);
}

function bindControls(years, countries, maxTotal) {
  const sel = document.getElementById("filter-countries");
  sel.innerHTML = countries
    .map((c) => `<option value="${esc(c)}" selected>${esc(c)}</option>`)
    .join("");

  document.getElementById("year-min").min = years.min;
  document.getElementById("year-min").max = years.max;
  document.getElementById("year-min").value = years.min;
  document.getElementById("year-max").min = years.min;
  document.getElementById("year-max").max = years.max;
  document.getElementById("year-max").value = years.max;
  document.getElementById("year-min-label").textContent = years.min;
  document.getElementById("year-max-label").textContent = years.max;

  const mt = document.getElementById("min-total");
  mt.min = 0;
  mt.max = maxTotal;
  mt.value = 0;
  document.getElementById("min-total-label").textContent = "0";

  ["filter-countries", "year-min", "year-max", "min-total", "map-type", "map-lon", "map-lat", "saint-pick"].forEach(
    (id) => document.getElementById(id).addEventListener("change", render)
  );
  document.getElementById("year-min").addEventListener("input", (e) => {
    document.getElementById("year-min-label").textContent = e.target.value;
    render();
  });
  document.getElementById("year-max").addEventListener("input", (e) => {
    document.getElementById("year-max-label").textContent = e.target.value;
    render();
  });
  document.getElementById("min-total").addEventListener("input", (e) => {
    document.getElementById("min-total-label").textContent = e.target.value;
    render();
  });
  document.getElementById("map-type").addEventListener("change", (e) => {
    const globe = e.target.value === "globe";
    document.getElementById("map-lat").value = globe ? 24 : 18;
    render();
  });
}

async function init() {
  try {
    const res = await fetch("./data/santos.json");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    payload = await res.json();
    rawRecords = payload.records;

    const years = rawRecords.map((r) => num(r["Año nacimiento"])).filter((y) => y != null);
    const countries = [...new Set(rawRecords.map((r) => r["País"]))].sort();
    const maxTotal = Math.max(...rawRecords.map((r) => num(r["Total"]) || 0));

    document.getElementById("data-source").textContent = payload.meta.source;
    bindControls(
      { min: Math.min(...years), max: Math.max(...years) },
      countries,
      maxTotal
    );
    render();
  } catch (err) {
    document.querySelector(".main").innerHTML = `<div class="empty">Error al cargar datos: ${esc(err.message)}</div>`;
  } finally {
    document.getElementById("loader").classList.add("hidden");
  }
}

function waitForPlotly() {
  if (typeof Plotly === "undefined") {
    setTimeout(waitForPlotly, 50);
    return;
  }
  init();
}

waitForPlotly();
