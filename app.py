import streamlit as st
import pandas as pd
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium
import os

st.set_page_config(layout="wide")
st.caption("🧩 Code-Version: v2.4 (Dummy-Koordinate erkennen + Missing-Report)")

# -------------------------------
# Daten laden (nur Parquet!)
# -------------------------------
@st.cache_data
def load_data():
    df = pd.read_parquet("df_months_long.parquet")

    # Grund-Cleaning
    for c in ["Niederschlag_group","Monat","Station"]:
        if c in df.columns:
            df[c] = df[c].astype(str)
    df["Station"] = df["Station"].astype(str).str.strip().str.replace(r"\s+", " ", regex=True)

    # lat/lon sauber und numerisch
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
    # etwas runden, um winzige Fluktuationen zu glätten
    df["lat"] = df["lat"].round(6)
    df["lon"] = df["lon"].round(6)

    # --- WICHTIG: Dominante (wahrscheinliche) Dummy-Koordinate erkennen ---
    # Wir zählen Paare (lat, lon) und nehmen das häufigste Paar als Dummy,
    # wenn es "ungewöhnlich" häufig ist (hier >30% aller Zeilen).
    pair_counts = (
        df.dropna(subset=["lat","lon"])
          .value_counts(subset=["lat","lon"])
          .reset_index(name="n")
          .sort_values("n", ascending=False)
    )
    if not pair_counts.empty and pair_counts.loc[0, "n"] > 0.30 * len(df):
        dummy_lat = pair_counts.loc[0, "lat"]
        dummy_lon = pair_counts.loc[0, "lon"]
        df["is_dummy_coord"] = (df["lat"].eq(dummy_lat) & df["lon"].eq(dummy_lon))
        # Dummy-Koordinaten als fehlend markieren
        df.loc[df["is_dummy_coord"], ["lat","lon"]] = pd.NA
    else:
        df["is_dummy_coord"] = False

    return df

df = load_data()

# Meta
st.caption("📄 Dateien im Ordner: " + ", ".join(sorted(os.listdir("."))))
st.caption(f"⚙️ Geladen: {df.shape[0]} Zeilen, {df['Station'].nunique()} Stationen")
st.caption("🔑 Spalten: " + ", ".join(df.columns))

# -------------------------------
# Sidebar Filter
# -------------------------------
st.sidebar.title("Filter")

regen_opts = ["Alle"] + sorted(df["Niederschlag_group"].dropna().unique().tolist()) \
    if "Niederschlag_group" in df.columns else ["Alle"]
regen_kategorie = st.sidebar.selectbox("Niederschlagskategorie", regen_opts, index=0)

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

stationen_opts = sorted(df["Station"].dropna().unique().tolist())
stationen_sel = st.sidebar.multiselect("Station(en)", stationen_opts, default=stationen_opts)

# Metrik-Umschalter
norm_candidates = [c for c in df.columns if c.lower() in {
    "zaehldaten_norm","zaehldaten_normalisiert","zaehldaten_normalized","normalized_counts"
}]
metriken = {"Rohdaten": "Zaehldaten"}
if norm_candidates:
    metriken["Normalisiert"] = norm_candidates[0]
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

if not stationen_sel:
    st.info("Bitte mindestens eine Station auswählen.")
    st.stop()

# -------------------------------
# EIN Punkt pro Station (mit Koordinaten-Check)
# -------------------------------

# Koordinaten-Lookup NUR aus gültigen (nicht-dummy) Koordinaten
stations_lookup = (
    df.dropna(subset=["Station","lat","lon"])
      .sort_values("Station")
      .drop_duplicates(subset=["Station"])[["Station","lat","lon"]]
)

# 1) Totals (Monate/Stationen-Filter)
mask_total = df["Station"].isin(stationen_sel)
if "Monat" in df.columns and monate_sel:
    mask_total &= df["Monat"].isin(monate_sel)

df_totals = (
    df[mask_total]
      .groupby("Station", as_index=False)[metr_col]
      .sum()
      .rename(columns={metr_col: "Zaehldaten_total"})
)

# 2) Subset (inkl. Regen)
df_subset = (
    df_filtered
      .groupby("Station", as_index=False)[metr_col]
      .sum()
      .rename(columns={metr_col: "Zaehldaten_subset"})
)

# 3) Merge + Intensität
df_map = (
    df_totals
      .merge(df_subset, on="Station", how="left")
      .merge(stations_lookup, on="Station", how="left")
)

df_map["Zaehldaten_subset"] = df_map["Zaehldaten_subset"].fillna(0)
df_map["Zaehldaten_total"]  = df_map["Zaehldaten_total"].fillna(0)
denom = df_map["Zaehldaten_total"].replace(0, pd.NA)
df_map["intensity"] = (df_map["Zaehldaten_subset"] / denom).fillna(0).clip(0, 1)

# Erwartete vs. vorhandene Punkte
expected = len(set(stationen_sel) & set(stations_lookup["Station"]))
st.caption(f"🧮 Punkte auf Karte (Zeilen df_map): {len(df_map)} · Erwartet ≈ {expected}")

# Summary
sum_subset = int(df_map["Zaehldaten_subset"].sum())
sum_total  = int(df_map["Zaehldaten_total"].sum())
anteil = (sum_subset / sum_total * 100) if sum_total > 0 else 0
st.success(f"Σ {metr_wahl}: {sum_subset:,} im aktuellen Filter · Anteil {anteil:.1f}%".replace(",", "."))

# -------------------------------
# Karte
# -------------------------------
valid_map = df_map.dropna(subset=["lat","lon"])
missing_coords = sorted(set(df_map["Station"]) - set(valid_map["Station"]))

if valid_map.empty:
    st.warning("Keine gültigen Koordinaten gefunden. Bitte Koordinaten im Datensatz prüfen.")
    st.stop()

center = [valid_map["lat"].mean(), valid_map["lon"].mean()]
m = folium.Map(location=center, zoom_start=12)

heat_data = valid_map[["lat","lon","intensity"]].values.tolist()
if heat_data:
    HeatMap(heat_data, radius=15, blur=12, max_zoom=13).add_to(m)

for _, row in valid_map.iterrows():
    intensity = float(row["intensity"])
    radius = 4 + 18 * intensity
    folium.CircleMarker(
        location=[row["lat"], row["lon"]],
        radius=radius,
        color='blue',
        fill=True,
        fill_opacity=0.6,
        popup=folium.Popup(
            f"<b>{row['Station']}</b><br>"
            f"{metr_wahl} im Filter: {int(row['Zaehldaten_subset'])}<br>"
            f"{metr_wahl} gesamt (Monate gewählt): {int(row['Zaehldaten_total'])}<br>"
            f"Anteil im Filter: {intensity:.1%}",
            max_width=320
        )
    ).add_to(m)

st_folium(m, width=1000, height=600)

# -------------------------------
# Debug / Datenqualität
# -------------------------------
with st.expander("Datenqualität: Koordinaten"):
    st.write("Eindeutige Stationen mit gültigen Koordinaten:", valid_map["Station"].nunique())
    st.write("Stationen ohne gültige Koordinaten (bitte im Parquet korrigieren):", missing_coords)
    st.dataframe(valid_map[["Station","lat","lon","Zaehldaten_subset","Zaehldaten_total","intensity"]].sort_values("Station"))
