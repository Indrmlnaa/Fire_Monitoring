from folium.plugins import HeatMap
import streamlit as st
import pandas as pd
import geopandas as gpd
import folium

from streamlit_folium import st_folium


# ============================================================
# CONFIG
# ============================================================

SPATIAL_FILE = "data/v2/processed/OKI_NASA_FIRMS_spatial_analysis.csv"

EVENT_FILE = "data/v2/processed/OKI_NASA_FIRMS_fire_events.csv"

RAINFALL_FILE = "data/v2/processed/OKI_fire_events_rainfall.csv"

BOUNDARY_FILE = "boundaries/OKI/OKI.shp"


st.set_page_config(
    page_title="OKI Fire Monitoring",
    page_icon="🔥",
    layout="wide"
)


# ============================================================
# LOAD DATA
# ============================================================

events = pd.read_csv(EVENT_FILE)

detections = pd.read_csv(SPATIAL_FILE)

rainfall = pd.read_csv(RAINFALL_FILE)

# Merge rainfall information into fire events
events = events.merge(
    rainfall[
        [
            "FIRE_EVENT_ID",
            "RAINFALL_1D_MM",
            "RAINFALL_7D_MM",
            "RAINFALL_30D_MM",
            "RAINFALL_STATUS"
        ]
    ],
    on="FIRE_EVENT_ID",
    how="left"
)

oki = gpd.read_file(BOUNDARY_FILE)

oki = oki.to_crs("EPSG:4326")


# ============================================================
# TITLE
# ============================================================

st.title("🔥 OKI Fire & Environment Monitoring System")

st.caption(
    "NASA FIRMS Satellite Fire Monitoring | "
    "Ogan Komering Ilir | 6–10 August 2026"
)


# ============================================================
# KPI
# ============================================================

total_detections = len(detections)

total_events = len(events)

high = len(
    events[events["PRIORITY"] == "HIGH"]
)

monitoring = len(
    events[events["PRIORITY"] == "MONITORING"]
)

low = len(
    events[events["PRIORITY"] == "LOW"]
)


c1, c2, c3, c4, c5 = st.columns(5)

c1.metric(
    "🛰️ Satellite Detections",
    f"{total_detections:,}"
)

c2.metric(
    "🔥 Fire Events",
    total_events
)

c3.metric(
    "🔴 High",
    high
)

c4.metric(
    "🟠 Monitoring",
    monitoring
)

c5.metric(
    "🟢 Low",
    low
)


st.divider()


# ============================================================
# FILTER
# ============================================================

st.subheader("🎛️ Monitoring Filter")

c1, c2, c3 = st.columns(3)

with c1:

    dates = sorted(
        events["EVENT_DATE"].unique()
    )

    selected_date = st.selectbox(
        "Monitoring Date",
        ["All"] + dates
    )


with c2:

    selected_priority = st.selectbox(
        "Priority",
        [
            "All",
            "HIGH",
            "MONITORING",
            "LOW"
        ]
    )


with c3:

    sensors = sorted(
        detections["sensor"]
        .dropna()
        .unique()
    )

    selected_sensor = st.selectbox(
        "Satellite Sensor",
        ["All"] + sensors
    )


# ------------------------------------------------------------
# FILTER FIRE EVENTS
# ------------------------------------------------------------

filtered_events = events.copy()


if selected_date != "All":

    filtered_events = filtered_events[
        filtered_events["EVENT_DATE"]
        == selected_date
    ]


if selected_priority != "All":

    filtered_events = filtered_events[
        filtered_events["PRIORITY"]
        == selected_priority
    ]


# ------------------------------------------------------------
# FILTER SATELLITE DETECTIONS
# ------------------------------------------------------------

filtered_detections = detections.copy()


filtered_detections = filtered_detections[
    filtered_detections["INSIDE_AREA"] == "YES"
]


if selected_date != "All":

    filtered_detections = filtered_detections[
        filtered_detections["acq_date"]
        == selected_date
    ]


if selected_sensor != "All":

    filtered_detections = filtered_detections[
        filtered_detections["sensor"]
        == selected_sensor
    ]
# ============================================================
# MAP
# ============================================================

st.subheader("🗺️ Fire Monitoring Map")


center = [
    events["LATITUDE"].mean(),
    events["LONGITUDE"].mean()
]


m = folium.Map(
    location=center,
    zoom_start=9,
    tiles="CartoDB positron"
)


# ============================================================
# BOUNDARY
# ============================================================

folium.GeoJson(
    oki.to_json(),
    name="OKI Boundary",
    style_function=lambda x: {
        "fillColor": "#3388ff",
        "fillOpacity": 0.05,
        "color": "blue",
        "weight": 3
    }
).add_to(m)



# ============================================================
# RAW SATELLITE DETECTIONS
# ============================================================

detection_group = folium.FeatureGroup(
    name="🛰️ Satellite Detections",
    show=False
)


for _, row in filtered_detections.iterrows():

    folium.CircleMarker(

        location=[
            row["latitude"],
            row["longitude"]
        ],

        radius=3,

        color="black",

        fill=True,

        fill_opacity=0.6,

        popup=folium.Popup(
            f"""
            <b>Satellite Detection</b><br>
            Sensor: {row['sensor']}<br>
            Date: {row['acq_date']}<br>
            FRP: {row['frp']} MW<br>
            Confidence: {row['confidence']}
            """,
            max_width=300
        )

    ).add_to(detection_group)


detection_group.add_to(m)


# ============================================================
# HEATMAP
# ============================================================

heat_group = folium.FeatureGroup(
    name="🔥 Hotspot Heatmap",
    show=False
)


heat_data = [

    [
        row["latitude"],
        row["longitude"],
        row["frp"]
    ]

    for _, row
    in filtered_detections.iterrows()

]


if heat_data:

    HeatMap(
        heat_data,
        radius=18,
        blur=15,
        min_opacity=0.3
    ).add_to(heat_group)


heat_group.add_to(m)
# ============================================================
# FIRE EVENTS
# ============================================================

event_group = folium.FeatureGroup(
    name="🔥 Fire Events",
    show=True
)



for _, row in filtered_events.iterrows():

    priority = row["PRIORITY"]

    if priority == "HIGH":
        color = "red"
    elif priority == "MONITORING":
        color = "orange"
    else:
        color = "green"

    popup = f"""
    <b>{row['FIRE_EVENT_ID']}</b><br><br>
    <b>Date:</b> {row['EVENT_DATE']}<br>
    <b>Priority:</b> {priority}<br>
    <b>Detections:</b> {row['DETECTION_COUNT']}<br>
    <b>Detected By:</b><br>
    {row['DETECTED_BY']}<br><br>
    <b>Maximum FRP:</b> {row['MAX_FRP_MW']} MW<br><br>

    <b>🌧️ Rainfall Context</b><br>
    1 Day: {row['RAINFALL_1D_MM']:.2f} mm<br>
    7 Days: {row['RAINFALL_7D_MM']:.2f} mm<br>
    30 Days: {row['RAINFALL_30D_MM']:.2f} mm
    """

    folium.CircleMarker(
        location=[
            row["LATITUDE"],
            row["LONGITUDE"]
        ],
        radius=8,
        color=color,
        fill=True,
        fill_color=color,
        fill_opacity=0.8,
        popup=folium.Popup(
            popup,
            max_width=350
        )
    ).add_to(event_group)

event_group.add_to(m)


folium.LayerControl().add_to(m)


st_folium(
    m,
    width=None,
    height=650
)


# ============================================================
# CHARTS
# ============================================================

st.divider()

st.subheader("📊 Fire Event Analysis")


c1, c2 = st.columns(2)


with c1:

    st.markdown("### Fire Events by Date")

    daily = (
        events
        .groupby("EVENT_DATE")
        .size()
        .reset_index(name="Fire Events")
    )

    daily = daily.set_index("EVENT_DATE")

    st.bar_chart(
        daily
    )


with c2:

    st.markdown("### Fire Events by Priority")

    priority_chart = (
        events
        .groupby("PRIORITY")
        .size()
        .reset_index(name="Fire Events")
    )

    priority_chart = priority_chart.set_index(
        "PRIORITY"
    )

    st.bar_chart(
        priority_chart
    )

# ============================================================
# TOP 10 FIRE EVENTS
# ============================================================

st.divider()

st.subheader("🔥 Top 10 Fire Events")

priority_order = {
    "HIGH": 1,
    "MONITORING": 2,
    "LOW": 3
}

top10 = filtered_events.copy()

top10["PRIORITY_ORDER"] = (
    top10["PRIORITY"]
    .map(priority_order)
)

top10 = (
    top10
    .sort_values(
        by=[
            "PRIORITY_ORDER",
            "DETECTION_COUNT",
            "MAX_FRP_MW"
        ],
        ascending=[
            True,
            False,
            False
        ]
    )
    .head(10)
)

st.dataframe(
    top10[
        [
            "FIRE_EVENT_ID",
            "EVENT_DATE",
            "PRIORITY",
            "DETECTION_COUNT",
            "DETECTED_BY",
            "MAX_FRP_MW"
        ]
    ],
    use_container_width=True,
    hide_index=True
)
# ============================================================
# EVENT DETAIL
# ============================================================

st.subheader("🔎 Fire Event Detail")

event_ids = filtered_events["FIRE_EVENT_ID"].tolist()

if event_ids:

    selected_event = st.selectbox(
        "Select Fire Event",
        event_ids
    )

    detail = filtered_events[
        filtered_events["FIRE_EVENT_ID"] == selected_event
    ].iloc[0]

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric("Priority", detail["PRIORITY"])
        st.metric("Detection Count", detail["DETECTION_COUNT"])
        st.metric("Maximum FRP", f"{detail['MAX_FRP_MW']} MW")

    with c2:
        st.metric("Latitude", detail["LATITUDE"])
        st.metric("Longitude", detail["LONGITUDE"])
        

    with c3:
        st.write("**Event Date**")
        st.write(detail["EVENT_DATE"])
    
        st.write("**Detected By**")
        st.write(detail["DETECTED_BY"])
    
        st.write("**🌧️ Rainfall**")
    
        st.metric(
            "1 Day",
            f"{detail['RAINFALL_1D_MM']:.2f} mm"
        )
    
        st.metric(
            "7 Days",
            f"{detail['RAINFALL_7D_MM']:.2f} mm"
        )
    
        st.metric(
            "30 Days",
            f"{detail['RAINFALL_30D_MM']:.2f} mm"
        )
    
    else:
    st.info("No fire event matches the selected filter.")
# ============================================================
# EVENT TABLE
# ============================================================

st.divider()

st.subheader("🔥 Fire Event Records")

st.dataframe(

    filtered_events[
    [
        "FIRE_EVENT_ID",
        "EVENT_DATE",
        "LATITUDE",
        "LONGITUDE",
        "DETECTION_COUNT",
        "DETECTED_BY",
        "MAX_FRP_MW",
        "PRIORITY",
        "RAINFALL_1D_MM",
        "RAINFALL_7D_MM",
        "RAINFALL_30D_MM"
    ]
],

    use_container_width=True,

    hide_index=True
)


# ============================================================
# FOOTER
# ============================================================

st.caption(
    "Data source: NASA FIRMS | "
    "Spatial analysis: Ogan Komering Ilir boundary"
)
