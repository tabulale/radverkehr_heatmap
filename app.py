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
    df["Niederschlag_group"] = df["Niederschlag_group"].astype(str)
    df["Monat"] = df["Monat"].astype(str)
    return df

df = load_data()
st.caption("📄 Dateien im Ordner: " + ", ".join(sorted(os.listdir("."))))
st.caption(f"⚙️ Geladen: {df.shape[0]} Zeilen, {df['Station'].nunique()} Stationen")
st.caption("🔑 Spalten: " + ", ".join(df.columns))

# -------------------------------
# Sidebar Filter
# -------------------------------
st.sidebar.title("Filter")
regen_opts = ["Alle"] + sorted(df["Niederschlag_group"].dropna().unique().tolist())
regen_kategorie = st.sidebar.selectbox("Niederschlagskategorie", regen_opts, index=0)

monate_order = ["January","February","March","April","May","June",
                "July","August","September","October","November","December"]
monate_opts = sorted(df["Monat"].dropna().unique().tolist(),
                     key=lambda m: monate_order.index(m) if m in monate_order else 99)
monate_sel = st.sidebar.multiselect("Monat", monate_opts, default=monate_opts)

stationen_opts = sorted(df["Station"].dropna().unique().tolist())
stationen_sel = st.sidebar.multiselect("Station(en)", stationen_opts, default=stationen_opts)

# -------------------------------
# Filter anwenden
# -------------------------------
df_filtered = df.copy()
if regen_kategorie != "Alle":
    df_filtered = df_filtered[df_filtered["Niederschlag_group"] == regen_kategorie]
if monate_sel:
    df_filtered = df_filtered[df_filtered["Monat"].isin(monate_sel)]
if stationen_sel:
    df_filtered = df_filtered[df_filtered["Station"].isin(stationen_sel)]

st.title("🚲 Fahrradbewegung in Münster in Abhängigkeit vom Wetter")
st.write(f"Anzahl angezeigter Datenpunkte (Zeilen nach Filter): {len(df_filtered)}")

# -------------------------------
# EIN Punkt pro Station
# Intensität = Anteil der Zähldaten im aktuellen Filter
#    = (Summe Zaehldaten im Filter) / (Stations-Gesamtsumme über gewählte Monate)
# -------------------------------

# 1) Stations-Gesamtsummen (unabhängig von Regen, aber nur gewählte Monate/Stationen)
df_totals = (
    df[(df["Monat"].isin(monate_sel)) & (df["Station"].isin(stationen_sel))]
    .groupby(["Station", "lat", "lon"], as_index=False)["Zaehldaten"]
    .sum()
    .rename(columns={"Zaehldaten": "Zaehldaten_total"})
)

# 2) Summe im aktuellen Filter (mit Regenkategorie)
df_subset = (
    df_filtered
    .groupby(["Station", "lat", "lon"], as_index=False)["Zaehldaten"]
    .sum()
    .rename(columns={"Zaehldaten": "Zaehldaten_subset"})
)

# 3) Mergen + Anteil berechnen (0..1)
df_map = df_totals.merge(df_subset, on=["Station","lat","lon"], how="left")
df_map["Zaehldaten_subset"] = df_map["Zaehldaten_subset"].fillna(0)
df_map["intensity"] = (df_map["Zaehldaten_subset"] / df_map["Zaehldaten_total"]).clip(0, 1)

st.caption(f"🧮 Punkte auf Karte (1 pro Station): {len(df_map)}")

# 4) Karte rendern
m = folium.Map(location=[51.96, 7.62], zoom_start=12)

# Heatmap (Gewicht = intensity)
heat_data = df_map[["lat","lon","intensity"]].dropna().values.tolist()
if heat_data:
    HeatMap(heat_data, radius=15, blur=12, max_zoom=13).add_to(m)
    
else:
    st.warning("⚠️ Keine Heatmap-Daten für die aktuelle Filterwahl gefunden.")

# Marker (Radius aus intensity, gedeckelt & gut skalierend)
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
            f"Gefilterte Summe: {int(row['Zaehldaten_subset'])}<br>"
            f"Stations-Gesamt (Monate gewählt): {int(row['Zaehldaten_total'])}<br>"
            f"Anteil im Filter: {intensity:.1%}",
            max_width=320
        )
    ).add_to(m)

st_folium(m, width=1000, height=600)

