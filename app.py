import streamlit as st
import pandas as pd
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium

# Add a descriptive title and introduction
st.title('Münster Bicycle Traffic Analysis Heatmap')
st.write('Explore the normalized daily bicycle counts across different stations in Münster, filtered by precipitation levels. The heatmap intensity and marker popups reflect the normalized counts, providing insights into how weather might influence ridership.')

# Load the preprocessed data (assuming the CSV is in the same directory as the app script)
try:
    df = pd.read_csv('filtered_bicycle_data.csv')
    # Ensure 'Datum' is datetime if needed for future features, though not strictly necessary for this heatmap
    df['Datum'] = pd.to_datetime(df['Datum'])
except FileNotFoundError:
    st.error("Error: 'filtered_bicycle_data.csv' not found. Please make sure the data file is in the same directory as the app script.")
    st.stop() # Stop the app if data is not found

# Get the maximum precipitation value from the data for the slider
max_precipitation = float(df['Niederschlag_mm'].max())

# Create a slider for precipitation filtering
selected_precipitation = st.slider(
    "Maximum Precipitation (mm)",
    min_value=0.0,
    max_value=max_precipitation,
    value=max_precipitation,  # Default to include all data initially
    step=0.1,  # Adjust step size as needed
    format="%.1f mm" # Add units to the slider
)

# Filter the data based on the selected precipitation level
filtered_df = df[df['Niederschlag_mm'] <= selected_precipitation].copy() # Use .copy() to avoid SettingWithCopyWarning

# Determine central coordinates for Münster
munster_coords = (51.9616, 7.6284)

# Create a Folium map centered on Münster
m = folium.Map(location=munster_coords, zoom_start=13, tiles='OpenStreetMap') # Changed zoom and added tiles

# Prepare data for HeatMap and markers
if not filtered_df.empty:
    # Heatmap data: list of lists [[lat, lon, weight], ...]
    heatmap_data = filtered_df[['lat', 'lon', 'normalized_count']].values.tolist()

    # Add HeatMap layer
    # Adjust radius and blur for better visualization
    HeatMap(heatmap_data, radius=15, blur=10).add_to(m)

    # Add markers with popups for each station in the filtered data
    # To avoid too many markers on the map for daily data, we can consider adding markers only for unique station locations
    # For simplicity here, we'll add a marker for each row in the filtered data, which might result in many markers if not aggregated
    # A better approach for many data points would be to aggregate filtered_df by station before adding markers
    station_locations = filtered_df.drop_duplicates(subset=['Station', 'lon', 'lat']) # Get unique station locations for markers

    for index, row in station_locations.iterrows():
        # Create the popup content - you might want to aggregate info for the popup if showing daily data
        # For this example, we'll just show the station name and average normalized count for the filtered data
        avg_normalized_count = filtered_df[filtered_df['Station'] == row['Station']]['normalized_count'].mean()
        popup_content = f"""
        <b>Station:</b> {row['Station']}<br>
        <b>Average Normalized Count (filtered):</b> {avg_normalized_count:.2f}
        """
        folium.Marker(
            location=[row['lat'], row['lon']],
            popup=popup_content
        ).add_to(m)
else:
    st.write("No data available for the selected precipitation range.")


# Display the map in Streamlit
st_folium(m, width=700, height=500)

# Optional: Add a section to display the filtered data
st.subheader("Filtered Data Preview")
st.write(filtered_df.head())
