import streamlit as st
import pandas as pd
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium

st.set_page_config(layout="wide")

# 🔹 Daten laden
@st.cache_data
def load_data():
    df = pd.read_csv("df_heatmap_ready.csv", parse_dates=["Datum"])
    return df

df = load_data()

# 🔹 Koordinaten laden
stations_coords = pd.read_csv("stations_coords.csv")

# 🔹 Sidebar – Filterauswahl
st.sidebar.title("Filter")
regen_kategorie = st.sidebar.selectbox(
    "Wähle Niederschlagskategorie",
    ["Alle", "Kein Regen (0 mm)", "Leichter Regen (0–1 mm)", "Mäßiger Regen (1–5 mm)", "Starker Regen (>5 mm)"]
)

# 🔹 Regen-Filterlogik
if regen_kategorie == "Kein Regen (0 mm)":
    df_filtered = df[df['Niederschlag_mm'] == 0]
elif regen_kategorie == "Leichter Regen (0–1 mm)":
    df_filtered = df[(df['Niederschlag_mm'] > 0) & (df['Niederschlag_mm'] <= 1)]
elif regen_kategorie == "Mäßiger Regen (1–5 mm)":
    df_filtered = df[(df['Niederschlag_mm'] > 1) & (df['Niederschlag_mm'] <= 5)]
elif regen_kategorie == "Starker Regen (>5 mm)":
    df_filtered = df[df['Niederschlag_mm'] > 5]
else:
    df_filtered = df.copy()

# 🔹 Titel & Info
st.title("🚲 Fahrradbewegung in Münster in Abhängigkeit vom Wetter")
st.write(f"Anzahl angezeigter Datenpunkte: {len(df_filtered)}")

# 🔹 Karte initialisieren
m = folium.Map(location=[51.96, 7.62], zoom_start=12)

# 🔹 Marker setzen
for _, row in df_filtered.iterrows():
    if pd.notna(row['lat']) and pd.notna(row['lon']):
        folium.CircleMarker(
            location=[row['lat'], row['lon']],
            radius=max(row['Zaehldaten'] / 1000, 2),  # min. Radius = 2
            color='blue',
            fill=True,
            fill_opacity=0.6,
            popup=folium.Popup(
                f"<b>{row['Station']}</b><br>{int(row['Zaehldaten'])} Fahrräder<br>{row['Datum'].date()}<br>{row['Niederschlag_mm']} mm Regen",
                max_width=300
            )
        ).add_to(m)

# 🔹 Karte anzeigen
st_folium(m, width=1000, height=600)
