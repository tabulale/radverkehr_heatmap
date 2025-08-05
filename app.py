import streamlit as st
import pandas as pd
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium

st.set_page_config(layout="wide")

@st.cache_data
def load_data():
    df = pd.read_csv("df_heatmap_ready.csv", parse_dates=["Datum"])
    return df

df = load_data()

st.sidebar.header("Filter")
min_rain = st.sidebar.slider("Mindestniederschlag (mm)", 0.0, 10.0, 0.0, 0.1)
date_range = st.sidebar.date_input("Datum auswählen", [df["Datum"].min(), df["Datum"].max()])

mask = (
    (df["Niederschlag_mm"] >= min_rain) &
    (df["Datum"] >= pd.to_datetime(date_range[0])) &
    (df["Datum"] <= pd.to_datetime(date_range[1]))
)
df_filtered = df[mask]

m = folium.Map(location=[51.96, 7.62], zoom_start=12)
heat_data = [[row["lat"], row["lon"], row["Zaehldaten"]] for idx, row in df_filtered.iterrows()]
HeatMap(heat_data, radius=15, max_zoom=13).add_to(m)

st.title("🚲 Fahrradbewegung in Münster in Abhängigkeit vom Wetter")
st.write(f"{len(df_filtered)} Datenpunkte ausgewählt")
st_folium(m, width=1000, height=600)

# Koordinaten laden
stations_coords = pd.read_csv("stations_coords.csv")
