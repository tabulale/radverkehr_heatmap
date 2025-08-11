import streamlit as st
import pandas as pd
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium
import os

st.set_page_config(layout="wide")

# -------------------------------
# Daten laden (nur Parquet!)
# -------------------------------
@st.cache_data
def load_data():
    df = pd.read_parquet("df_months_long.parquet")
    # Strings sicherstellen (für Filter)
    if "Niederschlag_group" in df.columns:
        df["Niederschlag_group"] = df["Niederschlag_group"].astype(str)
    if "Monat" in df.columns:
        df["Monat"] = df["Monat"].astype(str)
    return df

df = load_data()

# Kurze Meta-Infos
st.caption("📄 Dateien im Ordner: " + ", ".join(sorted(os.listdir("."))))
st.caption(f"⚙️ Geladen: {df.shape[0]} Zeilen, {df['Station'].nunique()} Stationen")
st.caption("🔑 Spalten: " + ", ".join(df.columns))

# -------------------------------
# Sidebar Filter
# -------------------------------
st.sidebar.title("Filter")

# Niederschlagskategorie
if "Niederschlag_group" in df.columns:
    regen_opts = ["Alle"] + sorted(df["Niederschlag_group"].dropna().unique().tolist())
else:
    regen_opts = ["Alle"]
regen_kategorie = st.sidebar.selectbox("Niederschlagskategorie", regen_opts, index=0)

# Monate
monate_order = ["January","February","March","April","May","June",
                "July","August","September","October","November","December"]
if "Monat" in df.columns:
    monate_opts = sorted(
        df["Monat"].dropna().unique().tolist(),
        key=lambda m: monate_order.index(m) if m in monate_order else 99
    )
else:
    monate_opts = []
monate_sel = st.sidebar.multiselect("Monat", monate_opts, default=monate_opts)

# Stationen
stationen_opts = sorted(df["Station"].dropna().unique().tolist())
stationen_sel = st.sidebar.multiselect("Station(en)", stationen_opts, default=stationen_opts)

# Metrik-Umschalter: Roh vs. normalisiert (falls vorhanden)
# Versuche übliche Spaltennamen zu erkennen
norm_kandidaten = [c for c in df.columns if c.lower() in {"zaehldaten_norm","zaehldaten_normalisiert","zaehldaten_normalized","normalized_counts"}]
metriken = {"Rohdaten": "Zaehldaten"}
if norm_kandidaten:
    metriken["Normalisiert"] = norm_kandidaten[0]
metr_wahl = st.sidebar.radio("Metrik", list(metriken.keys()), horizontal=True)
metr_col = metriken[metr_wahl]

# -------------------------------
# Filter anwenden
# -------------------------------
df_filtered = df.copy()

if regen_kategorie != "Alle" and "Niederschlag_group" in df.columns:
    df_filtered = df_filtered[df_filtered["Niederschlag_group"] == regen_kategorie]
if monate_sel and "Monat" in df.columns:
    df_filtered = df_filtered[df_filtered["Monat"].isin(monate_sel)]
if stationen_sel:
    df_filtered = df_filtered[df_filtered["Station"].isin(stationen_sel)]

st.title("🚲 Fahrradbewegung in Münster in Abhängigkeit vom Wetter")
st.write(f"Anzahl angezeigter Datenpunkte (Zeilen nach Filter): {len(df_filtered)}")

# Falls keine Stationen gewählt: freundlich abbrechen
if not stationen_sel:
    st.info("Bitte mindestens eine Station auswählen.")
    st.stop()

# -------------------------------
# EIN Punkt pro Station
# Intensität = Anteil der gewählten Metrik im aktuellen Filter
#    = (Summe im Filter) / (Stations-Gesamtsumme über gewählte Monate)
# -------------------------------

# --- EINMALIG: Eindeutige Stations-Koordinaten bestimmen ---
stations_lookup = (
    df.dropna(subset=["Station","lat","lon"])
      .sort_values(["Station"])
      .drop_duplicates(subset=["Station"])[["Station","lat","lon"]]
)

# --- 1) Stations-Gesamtsummen (nur Monate/Stationen-Filter; Regen egal) ---
mask_total = df["Station"].isin(stationen_sel)
if "Monat" in df.columns and monate_sel:
    mask_total &= df["Monat"].isin(monate_sel)

df_totals = (
    df[mask_total]
      .groupby("Station", as_index=False)[metr_col]
      .sum()
      .rename(columns={metr_col: "Zaehldaten_total"})
)

# --- 2) Summe im aktuellen Filter (inkl. Regenkategorie) ---
df_subset = (
    df_filtered
      .groupby("Station", as_index=False)[metr_col]
      .sum()
      .rename(columns={metr_col: "Zaehldaten_subset"})
)

# --- 3) Mergen + einmalige Koordinaten anfügen ---
df_map = (
    df_totals
      .merge(df_subset, on="Station", how="left")
      .merge(stations_lookup, on="Station", how="left")
)

# Fehlende Werte & Division-by-zero absichern
df_map["Zaehldaten_subset"] = df_map["Zaehldaten_subset"].fillna(0)
df_map["Zaehldaten_total"] = df_map["Zaehldaten_total"].fillna(0)
df_map["Zaehldaten_total"] = df_map["Zaehldaten_total"].replace(0, pd.NA)

df_map["intensity"] = (df_map["Zaehldaten_subset"] / df_map["Zaehldaten_total"]).clip(0, 1)
df_map["intensity"] = df_map["intensity"].fillna(0)

st.caption(f"🧮 Punkte auf Karte (1 pro Station): {len(df_map)}")

# Kleine Summary oben
sum_subset = int(df_map["Zaehldaten_subset"].sum())
sum_total = int(df_map["Zaehldaten_total"].fillna(0).sum())
anteil = (sum_subset / sum_total * 100) if sum_total > 0 else 0
st.success(f"Σ {metr_wahl}: {sum_subset:,} im aktuellen Filter · Anteil {anteil:.1f}% der gewählten Monate/Stationen".replace(",", "."))

# -------------------------------
# 4) Karte rendern
# -------------------------------
if df_map.dropna(subset=["lat","lon"]).empty:
    st.warning("Keine Koordinaten für die gewählten Stationen gefunden.")
    st.stop()

# Karte automatisch zentrieren
center = [df_map["lat"].mean(), df_map["lon"].mean()]
m = folium.Map(location=center, zoom_start=12)

# Heatmap: 1 Punkt je Station, Gewicht = intensity
heat_data = df_map[["lat","lon","intensity"]].dropna().values.tolist()
if heat_data:
    HeatMap(heat_data, radius=15, blur=12, max_zoom=13).add_to(m)
else:
    st.warning("⚠️ Keine Heatmap-Daten für die aktuelle Filterwahl gefunden.")

# Marker je Station
for _, row in df_map.dropna(subset=["lat","lon"]).iterrows():
    intensity = float(row["intensity"])
    radius = 4 + 18 * intensity  # 4..22 px

    folium.CircleMarker(
        location=[row["lat"], row["lon"]],
        radius=radius,
        color='blue',
        fill=True,
        fill_opacity=0.6,
        popup=folium.Popup(
            f"<b>{row['Station']}</b><br>"
            f"{metr_wahl} im Filter: {int(row['Zaehldaten_subset'])}<br>"
            f"{metr_wahl} gesamt (Monate gewählt): {int(row['Zaehldaten_total']) if pd.notna(row['Zaehldaten_total']) else 0}<br>"
            f"Anteil im Filter: {intensity:.1%}",
            max_width=320
        )
    ).add_to(m)

st_folium(m, width=1000, height=600)

# -------------------------------
# (Optional) Debug-Panel
# -------------------------------
with st.expander("Debug: Koordinaten-Varianten je Station"):
    st.write(
        df.groupby("Station")[["lat","lon"]]
          .nunique()
          .rename(columns={"lat":"lat_nuniq","lon":"lon_nuniq"})
          .sort_values("lat_nuniq", ascending=False)
          .head(20)
    )
