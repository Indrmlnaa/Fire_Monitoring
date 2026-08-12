from folium.plugins import HeatMap
import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from streamlit_folium import st_folium

SPATIAL_FILE = "data/v2/processed/OKI_NASA_FIRMS_spatial_analysis.csv"
EVENT_FILE = "data/v2/processed/OKI_NASA_FIRMS_fire_events.csv"
RAINFALL_FILE = "data/v2/processed/OKI_fire_events_rainfall.csv"
BOUNDARY_FILE = "boundaries/OKI/OKI.shp"

st.set_page_config(page_title="Hotspot Monitoring & Early Warning System", page_icon="🔥", layout="wide")

# -------------------- LOAD DATA --------------------
events = pd.read_csv(EVENT_FILE)
detections = pd.read_csv(SPATIAL_FILE)
rainfall = pd.read_csv(RAINFALL_FILE)

events["FIRE_EVENT_ID"] = events["FIRE_EVENT_ID"].astype(str)
rainfall["FIRE_EVENT_ID"] = rainfall["FIRE_EVENT_ID"].astype(str)

rain_cols = [
    "FIRE_EVENT_ID", "RAINFALL_1D_MM", "RAINFALL_7D_MM",
    "RAINFALL_30D_MM", "RAINFALL_STATUS"
]
rain_cols = [c for c in rain_cols if c in rainfall.columns]
events = events.merge(rainfall[rain_cols], on="FIRE_EVENT_ID", how="left")

for col in ["RAINFALL_1D_MM", "RAINFALL_7D_MM", "RAINFALL_30D_MM"]:
    if col not in events.columns:
        events[col] = pd.NA
    events[col] = pd.to_numeric(events[col], errors="coerce")

oki = gpd.read_file(BOUNDARY_FILE).to_crs("EPSG:4326")

# -------------------- TITLE --------------------
st.title("Hotspot Monitoring & Early Warning System")
dates_dt = pd.to_datetime(events["EVENT_DATE"], errors="coerce").dropna()
period = "Current monitoring period"
if not dates_dt.empty:
    period = f"{dates_dt.min():%d %b %Y} – {dates_dt.max():%d %b %Y}"
st.caption(f"Satellite-Based Hotspot Detection & Spatial Analysis | {period}")

# -------------------- KPI --------------------
total_detections = len(detections)
total_events = len(events)
high = len(events[events["PRIORITY"] == "HIGH"])
monitoring = len(events[events["PRIORITY"] == "MONITORING"])
low = len(events[events["PRIORITY"] == "LOW"])

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("🛰️ Satellite Detections", f"{total_detections:,}")
c2.metric("🔥 Fire Events", total_events)
c3.metric("🔴 High", high)
c4.metric("🟠 Monitoring", monitoring)
c5.metric("🟢 Low", low)
st.divider()

# -------------------- FILTER --------------------
st.subheader("🎛️ Monitoring Filter")
c1, c2, c3 = st.columns(3)

with c1:
    dates = sorted(events["EVENT_DATE"].dropna().astype(str).unique())
    selected_date = st.selectbox("Monitoring Date", ["All"] + dates)
with c2:
    selected_priority = st.selectbox("Priority", ["All", "HIGH", "MONITORING", "LOW"])
with c3:
    sensors = sorted(detections["sensor"].dropna().astype(str).unique())
    selected_sensor = st.selectbox("Satellite Sensor", ["All"] + sensors)

filtered_events = events.copy()
if selected_date != "All":
    filtered_events = filtered_events[filtered_events["EVENT_DATE"].astype(str) == selected_date]
if selected_priority != "All":
    filtered_events = filtered_events[filtered_events["PRIORITY"] == selected_priority]

filtered_detections = detections.copy()
filtered_detections = filtered_detections[filtered_detections["INSIDE_AREA"] == "YES"]
if selected_date != "All":
    filtered_detections = filtered_detections[filtered_detections["acq_date"].astype(str) == selected_date]
if selected_sensor != "All":
    filtered_detections = filtered_detections[filtered_detections["sensor"].astype(str) == selected_sensor]

# -------------------- MAP --------------------
st.subheader("🗺️ Fire Monitoring Map")
center = [events["LATITUDE"].mean(), events["LONGITUDE"].mean()] if not events.empty else [-3.4, 105.2]

# Base map: Light / Satellite / Terrain
m = folium.Map(location=center, zoom_start=9, tiles=None)

folium.TileLayer(
    tiles="CartoDB positron",
    name="🗺️ Light Map",
    overlay=False,
    control=True,
    show=True,
).add_to(m)

folium.TileLayer(
    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attr="Esri World Imagery",
    name="🛰️ Satellite",
    overlay=False,
    control=True,
    show=False,
).add_to(m)

folium.TileLayer(
    tiles="https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
    attr="OpenTopoMap",
    name="⛰️ Terrain",
    overlay=False,
    control=True,
    show=False,
).add_to(m)

folium.GeoJson(
    oki.to_json(), name="OKI Boundary",
    style_function=lambda x: {"fillColor": "#3388ff", "fillOpacity": 0.05, "color": "blue", "weight": 3},
).add_to(m)

# Raw satellite detections
detection_group = folium.FeatureGroup(name="🛰️ Satellite Detections", show=False)
for _, row in filtered_detections.iterrows():
    folium.CircleMarker(
        location=[row["latitude"], row["longitude"]], radius=3,
        color="black", fill=True, fill_opacity=0.6,
        popup=folium.Popup(
            f"<b>Satellite Detection</b><br>Sensor: {row['sensor']}<br>"
            f"Date: {row['acq_date']}<br>FRP: {row['frp']} MW<br>Confidence: {row['confidence']}",
            max_width=300,
        ),
    ).add_to(detection_group)
detection_group.add_to(m)

# Heatmap
heat_group = folium.FeatureGroup(name="🔥 Hotspot Heatmap", show=False)
heat_data = [[row["latitude"], row["longitude"], row["frp"]] for _, row in filtered_detections.iterrows()]
if heat_data:
    HeatMap(heat_data, radius=18, blur=15, min_opacity=0.3).add_to(heat_group)
heat_group.add_to(m)

# Fire events
event_group = folium.FeatureGroup(name="🔥 Fire Events", show=True)
for _, row in filtered_events.iterrows():
    priority = row["PRIORITY"]
    marker_color = "red" if priority == "HIGH" else "orange" if priority == "MONITORING" else "green"

    def rain_text(value):
        return f"{value:.2f} mm" if pd.notna(value) else "N/A"

    popup = f"""
    <b>{row['FIRE_EVENT_ID']}</b><br><br>
    <b>Date:</b> {row['EVENT_DATE']}<br>
    <b>Priority:</b> {priority}<br>
    <b>Detections:</b> {row['DETECTION_COUNT']}<br>
    <b>Detected By:</b><br>{row['DETECTED_BY']}<br><br>
    <b>Maximum FRP:</b> {row['MAX_FRP_MW']} MW<br><br>
    <b>🌧️ Rainfall Context</b><br>
    1 Day: {rain_text(row['RAINFALL_1D_MM'])}<br>
    7 Days: {rain_text(row['RAINFALL_7D_MM'])}<br>
    30 Days: {rain_text(row['RAINFALL_30D_MM'])}
    """

    folium.CircleMarker(
        location=[row["LATITUDE"], row["LONGITUDE"]], radius=8,
        color=marker_color, fill=True, fill_color=marker_color, fill_opacity=0.8,
        popup=folium.Popup(popup, max_width=350),
    ).add_to(event_group)
event_group.add_to(m)

folium.LayerControl().add_to(m)
st_folium(m, width=None, height=650)

# -------------------- CHARTS --------------------
st.divider()
st.subheader("📊 Fire Event Analysis")
c1, c2 = st.columns(2)
with c1:
    st.markdown("### Fire Events by Date")
    daily = events.groupby("EVENT_DATE").size().reset_index(name="Fire Events").set_index("EVENT_DATE")
    st.bar_chart(daily)
with c2:
    st.markdown("### Fire Events by Priority")
    priority_chart = events.groupby("PRIORITY").size().reset_index(name="Fire Events").set_index("PRIORITY")
    st.bar_chart(priority_chart)

# -------------------- RAINFALL SUMMARY --------------------
st.divider()
st.subheader("🌧️ Rainfall Context")
st.dataframe(
    filtered_events[["FIRE_EVENT_ID", "EVENT_DATE", "RAINFALL_1D_MM", "RAINFALL_7D_MM", "RAINFALL_30D_MM"]],
    use_container_width=True, hide_index=True,
)

# -------------------- TOP 10 --------------------
st.divider()
st.subheader("🔥 Top 10 Fire Events")
priority_order = {"HIGH": 1, "MONITORING": 2, "LOW": 3}
top10 = filtered_events.copy()
top10["PRIORITY_ORDER"] = top10["PRIORITY"].map(priority_order)
top10 = top10.sort_values(
    by=["PRIORITY_ORDER", "DETECTION_COUNT", "MAX_FRP_MW"],
    ascending=[True, False, False],
).head(10)
st.dataframe(
    top10[["FIRE_EVENT_ID", "EVENT_DATE", "PRIORITY", "DETECTION_COUNT", "DETECTED_BY", "MAX_FRP_MW", "RAINFALL_1D_MM", "RAINFALL_7D_MM", "RAINFALL_30D_MM"]],
    use_container_width=True, hide_index=True,
)

# -------------------- EVENT DETAIL --------------------
st.divider()
st.subheader("🔎 Fire Event Detail")
event_ids = filtered_events["FIRE_EVENT_ID"].tolist()
if event_ids:
    selected_event = st.selectbox("Select Fire Event", event_ids)
    detail = filtered_events[filtered_events["FIRE_EVENT_ID"] == selected_event].iloc[0]

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Priority", detail["PRIORITY"])
        st.metric("Detection Count", detail["DETECTION_COUNT"])
        st.metric("Maximum FRP", f"{detail['MAX_FRP_MW']} MW")
    with c2:
        st.metric("Latitude", f"{detail['LATITUDE']:.6f}")
        st.metric("Longitude", f"{detail['LONGITUDE']:.6f}")
        st.write("**Detected By**")
        st.write(detail["DETECTED_BY"])
    with c3:
        st.write("**Event Date**")
        st.write(detail["EVENT_DATE"])
        st.write("**🌧️ Rainfall Context**")
        st.metric("1 Day", f"{detail['RAINFALL_1D_MM']:.2f} mm" if pd.notna(detail["RAINFALL_1D_MM"]) else "N/A")
        st.metric("7 Days", f"{detail['RAINFALL_7D_MM']:.2f} mm" if pd.notna(detail["RAINFALL_7D_MM"]) else "N/A")
        st.metric("30 Days", f"{detail['RAINFALL_30D_MM']:.2f} mm" if pd.notna(detail["RAINFALL_30D_MM"]) else "N/A")
else:
    st.info("No fire event matches the selected filter.")

# -------------------- EVENT TABLE --------------------
st.divider()
st.subheader("🔥 Fire Event Records")
st.dataframe(
    filtered_events[[
        "FIRE_EVENT_ID", "EVENT_DATE", "LATITUDE", "LONGITUDE",
        "DETECTION_COUNT", "DETECTED_BY", "MAX_FRP_MW", "PRIORITY",
        "RAINFALL_1D_MM", "RAINFALL_7D_MM", "RAINFALL_30D_MM",
    ]],
    use_container_width=True, hide_index=True,
)

st.caption("Data source: NASA FIRMS + NASA POWER | Spatial analysis: Ogan Komering Ilir boundary")
