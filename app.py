import streamlit as st
import pandas as pd
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium

st.set_page_config(layout="wide")

# -------------------------------
# Daten laden (nur Parquet!)
# -------------------------------
@st.cache_data
def load_data():
    df = pd.read_parquet("df_months_long.parquet")
    # Sicherheit: Kategorien als string
    df["Niederschlag_group"] = df["Niederschlag_group"].astype(str)
    df["Monat"] = df["Monat"].astype(str)
    return df

df = load_data()
st.caption(f"⚙️ Geladen: {df.shape[0]} Zeilen, {df['Station'].nunique()} Stationen")

# -------------------------------
# Sidebar Filter
# -------------------------------
st.sidebar.title("Filter")

regen_opts = ["Alle"] + sorted(df["Niederschlag_group"].dropna().unique().tolist())
regen_kategorie = st.sidebar.selectbox("Niederschlagskategorie", regen_opts, index=0)

monate_order = [
    "January","February","March","April","May","June",
    "July","August","September","October","November","December"
]
monate_opts = sorted(
    df["Monat"].dropna().unique().tolist(),
    key=lambda m: monate_order.index(m) if m in monate_order else 99
)
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
st.write(f"Anzahl angezeigter Datenpunkte: {len(df_filtered)}")

# -------------------------------
# Performance-Guard: zu viele Punkte verdichten
# -------------------------------
MAX_POINTS = 2000
if len(df_filtered) > MAX_POINTS:
    st.warning(f"⚠️ {len(df_filtered)} Punkte → Verdichtung pro Station")
    df_map = (
        df_filtered.groupby(["Station","lat","lon"], as_index=False)
        .agg({"Zaehldaten_norm": "sum", "Zaehldaten": "sum"})
    )
else:
    df_map = df_filtered.copy()

# -------------------------------
# Karte mit Heatmap + Marker
# -------------------------------
m = folium.Map(location=[51.96, 7.62], zoom_start=12)

# HeatMap: Intensität = normalisierte Zähldaten
heat_data = df_map[["lat", "lon", "Zaehldaten_norm"]].dropna().values.tolist()
if heat_data:
    HeatMap(heat_data, radius=20, max_zoom=13).add_to(m)
else:
    st.warning("⚠️ Keine Heatmap-Daten für die aktuelle Filterwahl gefunden.")

# Marker mit Popups
for _, row in df_map.dropna(subset=["lat","lon"]).iterrows():
    norm = float(row.get("Zaehldaten_norm", 0.0))
    radius = max(norm * 25, 3)
    folium.CircleMarker(
        location=[row["lat"], row["lon"]],
        radius=radius,
        color='blue',
        fill=True,
        fill_opacity=0.6,
        popup=folium.Popup(
            f"<b>{row['Station']}</b><br>"
            f"Monat: {row.get('Monat','-')}<br>"
            f"Wetter: {row.get('Niederschlag_group','-')}<br>"
            f"Zähldaten (absolut): {int(row['Zaehldaten'])}<br>"
            f"Zähldaten (normalisiert): {norm:.1%}",
            max_width=300
        )
    ).add_to(m)

st_folium(m, width=1000, height=600)
