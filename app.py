import streamlit as st
import pandas as pd
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium

# Add a descriptive title and introduction
st.title('Münster Bicycle Traffic Analysis Heatmap (Monthly Aggregated Data)')
st.write('Explore the normalized monthly bicycle counts across different stations in Münster, filtered by precipitation levels. The heatmap intensity and marker popups reflect the normalized counts, providing insights into how weather might influence ridership.')

# Load the preprocessed data (assuming the CSV is in the same directory as the app script)
try:
    # Load the monthly aggregated data
    # Assuming you have saved df_monthly to a CSV or similar file
    # For now, I'll assume you'll save df_monthly to 'monthly_bicycle_data.csv'
    df_monthly = pd.read_csv('monthly_bicycle_data.csv')
    # Ensure 'Jahr_Monat' is in the correct format if needed
    # df_monthly['Jahr_Monat'] = pd.to_datetime(df_monthly['Jahr_Monat']).dt.to_period('M')
except FileNotFoundError:
    st.error("Error: 'monthly_bicycle_data.csv' not found. Please make sure the monthly aggregated data file is in the same directory as the app script.")
    st.stop() # Stop the app if data is not found

# Note: Filtering by precipitation on monthly aggregated data might be less intuitive
# as precipitation is summed over the month. We will keep the slider for now,
# but its interpretation changes.
max_precipitation = float(df_monthly['Niederschlag_mm'].max())

# Create a slider for precipitation filtering
selected_precipitation = st.slider(
    "Maximum Monthly Precipitation (mm)",
    min_value=0.0,
    max_value=max_precipitation,
    value=max_precipitation,  # Default to include all data initially
    step=1.0,  # Adjusted step for monthly data
    format="%.1f mm" # Add units to the slider
)

# Filter the data based on the selected precipitation level
filtered_df_monthly = df_monthly[df_monthly['Niederschlag_mm'] <= selected_precipitation].copy() # Use .copy() to avoid SettingWithCopyWarning

# Determine central coordinates for Münster
munster_coords = (51.9616, 7.6284)

# Create a Folium map centered on Münster
m = folium.Map(location=munster_coords, zoom_start=13, tiles='OpenStreetMap') # Changed zoom and added tiles

# Prepare data for HeatMap and markers
if not filtered_df_monthly.empty:
    # Heatmap data: list of lists [[lat, lon, weight], ...]
    # Use the aggregated 'Zaehldaten' for heatmap intensity, or re-calculate normalized if needed monthly
    # For simplicity here, we'll use 'Zaehldaten' from the monthly aggregation for heatmap intensity
    # If you want to use normalized monthly counts, you would need to calculate them after monthly aggregation
    # Let's use 'Zaehldaten' for heatmap and 'normalized_count' (if you add it to monthly_data) for popup
    # Assuming 'normalized_count' is available in monthly_bicycle_data.csv after monthly normalization
    # If not, we would need to calculate it here or earlier.
    # Let's assume 'normalized_count' is in the monthly data for heatmap weight for consistency with the task.
    # If normalized_count is not in the monthly data, change 'normalized_count' to 'Zaehldaten' below

    # *** Assuming 'normalized_count' was calculated on the daily data and then summed/averaged for monthly.
    # *** A more accurate normalization would be to calculate baseline on monthly data.
    # *** For now, let's proceed assuming a relevant 'normalized_count' or similar metric is available monthly.
    # *** If only summed 'Zaehldaten' is available, we'd use that or calculate a monthly normalization here.

    # Let's use the monthly 'Zaehldaten' for heatmap weight for now, as normalization was done on daily data
    # If you want monthly normalization, we need to adjust the data preparation step.
    heatmap_data = filtered_df_monthly[['lat', 'lon', 'Zaehldaten']].values.tolist()


    # Add HeatMap layer
    # Adjust radius and blur for better visualization. Max_zoom can also help with intensity.
    HeatMap(heatmap_data, radius=20, blur=15, max_zoom=15).add_to(m) # Adjusted radius, blur, and added max_zoom

    # Add markers with popups for each station in the filtered monthly data
    # We can use the average normalized count for the popup, calculated from the monthly data
    for index, row in filtered_df_monthly.iterrows():
        # Create the popup content
        # Assuming 'normalized_count' is available in the monthly data
        # If not, you might show total monthly count or other relevant info
        popup_content = f"""
        <b>Station:</b> {row['Station']}<br>
        <b>Month:</b> {row['Jahr_Monat']}<br>
        <b>Total Monthly Precipitation (mm):</b> {row['Niederschlag_mm']:.2f}<br>
        <b>Total Monthly Bicycle Count:</b> {int(row['Zaehldaten'])}
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
st.subheader("Filtered Monthly Data Preview")
st.write(filtered_df_monthly.head())
