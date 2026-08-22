from folium.plugins import HeatMap
import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from streamlit_folium import st_folium
from pathlib import Path


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Hotspot Monitoring & Early Warning System",
    page_icon="🔥",
    layout="wide",
)


# ============================================================
# BASE DIRECTORY
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

PROCESSED_DIR = (
    BASE_DIR
    / "data"
    / "v2"
    / "processed"
)

BOUNDARIES_DIR = (
    BASE_DIR
    / "boundaries"
)


# ============================================================
# AREA CONFIGURATION
# ============================================================

AREA_CONFIG = {

    "OKI": {
        "display_name": "Ogan Komering Ilir",

        "spatial_file":
            PROCESSED_DIR
            / "OKI_NASA_FIRMS_spatial_analysis.csv",

        "event_file":
            PROCESSED_DIR
            / "OKI_NASA_FIRMS_fire_events.csv",

        "rainfall_file":
            PROCESSED_DIR
            / "OKI_fire_events_rainfall.csv",

        "boundary_type": "file",

        "boundary_file":
            BOUNDARIES_DIR
            / "OKI"
            / "OKI.shp",
    },


    "Teluk Bintuni": {
        "display_name": "Teluk Bintuni",

        "spatial_file":
            PROCESSED_DIR
            / "Teluk_Bintuni_NASA_FIRMS_spatial_analysis.csv",

        "event_file":
            PROCESSED_DIR
            / "Teluk_Bintuni_NASA_FIRMS_fire_events.csv",

        # Optional.
        # Dashboard will work even if this file
        # does not exist yet.
        "rainfall_file":
            PROCESSED_DIR
            / "Teluk_Bintuni_fire_events_rainfall.csv",

        "boundary_type": "file",

        "boundary_file":
            BOUNDARIES_DIR
            / "Teluk_Bintuni"
            / "Teluk_Bintuni.shp",
    },
}


# ============================================================
# TITLE
# ============================================================

st.title(
    "Hotspot Monitoring & Early Warning System"
)


# ============================================================
# AREA SELECTOR
# ============================================================

st.subheader("📍 Monitoring Area")

selected_area = st.selectbox(
    "Select Monitoring Area",
    list(AREA_CONFIG.keys()),
)


config = AREA_CONFIG[selected_area]


# ============================================================
# FILE CHECK
# ============================================================

SPATIAL_FILE = config["spatial_file"]
EVENT_FILE = config["event_file"]
RAINFALL_FILE = config["rainfall_file"]


if not SPATIAL_FILE.exists():

    st.error(
        f"Spatial data belum tersedia untuk "
        f"{selected_area}.\n\n"
        f"File yang dicari:\n"
        f"{SPATIAL_FILE}"
    )

    st.stop()


if not EVENT_FILE.exists():

    st.error(
        f"Fire Event data belum tersedia untuk "
        f"{selected_area}.\n\n"
        f"File yang dicari:\n"
        f"{EVENT_FILE}"
    )

    st.stop()


# ============================================================
# LOAD DATA
# ============================================================

@st.cache_data
def load_csv(path):

    return pd.read_csv(path)


events = load_csv(EVENT_FILE)

detections = load_csv(SPATIAL_FILE)


# ============================================================
# RAINFALL
# ============================================================

if RAINFALL_FILE.exists():

    rainfall = load_csv(
        RAINFALL_FILE
    )

else:

    rainfall = pd.DataFrame()


# ============================================================
# NORMALIZE EVENT ID
# ============================================================

if "FIRE_EVENT_ID" in events.columns:

    events["FIRE_EVENT_ID"] = (
        events["FIRE_EVENT_ID"]
        .astype(str)
    )


if not rainfall.empty:

    if "FIRE_EVENT_ID" in rainfall.columns:

        rainfall["FIRE_EVENT_ID"] = (
            rainfall["FIRE_EVENT_ID"]
            .astype(str)
        )


# ============================================================
# MERGE RAINFALL
# ============================================================

if not rainfall.empty:

    rain_cols = [
        "FIRE_EVENT_ID",
        "RAINFALL_1D_MM",
        "RAINFALL_7D_MM",
        "RAINFALL_30D_MM",
        "RAINFALL_STATUS",
    ]

    rain_cols = [
        c
        for c in rain_cols
        if c in rainfall.columns
    ]

    if (
        "FIRE_EVENT_ID" in rain_cols
        and "FIRE_EVENT_ID" in events.columns
    ):

        events = events.merge(
            rainfall[rain_cols],
            on="FIRE_EVENT_ID",
            how="left",
        )


# ============================================================
# ENSURE RAINFALL COLUMNS
# ============================================================

for col in [
    "RAINFALL_1D_MM",
    "RAINFALL_7D_MM",
    "RAINFALL_30D_MM",
]:

    if col not in events.columns:

        events[col] = pd.NA

    events[col] = pd.to_numeric(
        events[col],
        errors="coerce",
    )


# ============================================================
# LOAD BOUNDARY
# ============================================================

@st.cache_data
def load_boundary(
    area_name,
    config
):

    # --------------------------------------------------------
    # OKI
    # --------------------------------------------------------

    if config["boundary_type"] == "file":

        boundary = gpd.read_file(
            config["boundary_file"]
        )

        return boundary.to_crs(
            "EPSG:4326"
        )


    # --------------------------------------------------------
    # TELUK BINTUNI
    # --------------------------------------------------------

    boundary_folder = Path(
        config["boundary_folder"]
    )

    shp_files = list(
        boundary_folder.glob("*.shp")
    )

    if not shp_files:

        raise FileNotFoundError(
            "Tidak ditemukan shapefile "
            f"Indonesia di:\n"
            f"{boundary_folder}"
        )


    # --------------------------------------------------------
    # FIND SHAPEFILE
    # --------------------------------------------------------

    boundary = gpd.read_file(
        shp_files[0]
    )


    # --------------------------------------------------------
    # CHECK COLUMN
    # --------------------------------------------------------

    column = config[
        "boundary_column"
    ]

    value = config[
        "boundary_value"
    ]


    if column not in boundary.columns:

        raise RuntimeError(
            f"Kolom '{column}' "
            "tidak ditemukan.\n\n"
            f"Kolom tersedia:\n"
            f"{list(boundary.columns)}"
        )


    # --------------------------------------------------------
    # FILTER
    # --------------------------------------------------------

    boundary = boundary[
        boundary[column]
        .astype(str)
        .str.strip()
        .str.lower()
        ==
        value.lower()
    ].copy()


    if boundary.empty:

        raise RuntimeError(
            f"Boundary '{value}' "
            f"tidak ditemukan."
        )


    return boundary.to_crs(
        "EPSG:4326"
    )


try:

    boundary = load_boundary(
        selected_area,
        config,
    )

except Exception as e:

    st.error(
        f"Gagal memuat boundary "
        f"{selected_area}:\n\n{e}"
    )

    st.stop()


# ============================================================
# TITLE / PERIOD
# ============================================================

dates_dt = pd.to_datetime(
    events["EVENT_DATE"],
    errors="coerce",
).dropna()


period = (
    "Current monitoring period"
)


if not dates_dt.empty:

    period = (
        f"{dates_dt.min():%d %b %Y}"
        f" – "
        f"{dates_dt.max():%d %b %Y}"
    )


st.caption(
    "Satellite-Based Hotspot Detection & "
    "Spatial Analysis"
    f" | Area: {config['display_name']}"
    f" | {period}"
)


# ============================================================
# RAINFALL STATUS
# ============================================================

if RAINFALL_FILE.exists():

    rainfall_status = (
        "Rainfall data available"
    )

else:

    rainfall_status = (
        "Rainfall data not available "
        "for this area yet"
    )


st.caption(
    f"🌧️ {rainfall_status}"
)


# ============================================================
# KPI
# ============================================================

total_detections = len(
    detections
)

total_events = len(
    events
)

high = len(
    events[
        events["PRIORITY"]
        == "HIGH"
    ]
)

monitoring = len(
    events[
        events["PRIORITY"]
        == "MONITORING"
    ]
)

low = len(
    events[
        events["PRIORITY"]
        == "LOW"
    ]
)


c1, c2, c3, c4, c5 = (
    st.columns(5)
)


c1.metric(
    "🛰️ Satellite Detections",
    f"{total_detections:,}",
)

c2.metric(
    "🔥 Fire Events",
    total_events,
)

c3.metric(
    "🔴 High",
    high,
)

c4.metric(
    "🟠 Monitoring",
    monitoring,
)

c5.metric(
    "🟢 Low",
    low,
)


st.divider()


# ============================================================
# FILTER
# ============================================================

st.subheader(
    "🎛️ Monitoring Filter"
)


c1, c2, c3 = (
    st.columns(3)
)


with c1:

    dates = sorted(
        events[
            "EVENT_DATE"
        ]
        .dropna()
        .astype(str)
        .unique()
    )


    selected_date = st.selectbox(
        "Monitoring Date",
        ["All"] + dates,
    )


with c2:

    selected_priority = (
        st.selectbox(
            "Priority",
            [
                "All",
                "HIGH",
                "MONITORING",
                "LOW",
            ],
        )
    )


with c3:

    sensors = sorted(
        detections[
            "sensor"
        ]
        .dropna()
        .astype(str)
        .unique()
    )


    selected_sensor = (
        st.selectbox(
            "Satellite Sensor",
            ["All"] + sensors,
        )
    )


# ============================================================
# FILTER EVENTS
# ============================================================

filtered_events = (
    events.copy()
)


if selected_date != "All":

    filtered_events = (
        filtered_events[
            filtered_events[
                "EVENT_DATE"
            ].astype(str)
            == selected_date
        ]
    )


if selected_priority != "All":

    filtered_events = (
        filtered_events[
            filtered_events[
                "PRIORITY"
            ]
            == selected_priority
        ]
    )


# ============================================================
# FILTER DETECTIONS
# ============================================================

filtered_detections = (
    detections.copy()
)


filtered_detections = (
    filtered_detections[
        filtered_detections[
            "INSIDE_AREA"
        ]
        == "YES"
    ]
)


if selected_date != "All":

    filtered_detections = (
        filtered_detections[
            filtered_detections[
                "acq_date"
            ].astype(str)
            == selected_date
        ]
    )


if selected_sensor != "All":

    filtered_detections = (
        filtered_detections[
            filtered_detections[
                "sensor"
            ].astype(str)
            == selected_sensor
        ]
    )


# ============================================================
# MAP
# ============================================================

st.subheader(
    "🗺️ Fire Monitoring Map"
)


if not events.empty:

    center = [
        events[
            "LATITUDE"
        ].mean(),

        events[
            "LONGITUDE"
        ].mean(),
    ]

else:

    center = [
        boundary.geometry
        .centroid
        .y.mean(),

        boundary.geometry
        .centroid
        .x.mean(),
    ]


m = folium.Map(
    location=center,
    zoom_start=9,
    tiles=None,
)


# ============================================================
# BASE MAPS
# ============================================================

folium.TileLayer(
    tiles="CartoDB positron",
    name="🗺️ Light Map",
    overlay=False,
    control=True,
    show=True,
).add_to(m)


folium.TileLayer(
    tiles=(
        "https://server.arcgisonline.com/"
        "ArcGIS/rest/services/"
        "World_Imagery/MapServer/tile/"
        "{z}/{y}/{x}"
    ),
    attr="Esri World Imagery",
    name="🛰️ Satellite",
    overlay=False,
    control=True,
    show=False,
).add_to(m)


folium.TileLayer(
    tiles=(
        "https://{s}.tile.opentopomap.org/"
        "{z}/{x}/{y}.png"
    ),
    attr="OpenTopoMap",
    name="⛰️ Terrain",
    overlay=False,
    control=True,
    show=False,
).add_to(m)


# ============================================================
# BOUNDARY
# ============================================================

folium.GeoJson(
    boundary.to_json(),
    name=f"{config['display_name']} Boundary",

    style_function=lambda x: {
        "fillColor": "#3388ff",
        "fillOpacity": 0.05,
        "color": "blue",
        "weight": 3,
    },

).add_to(m)


# ============================================================
# RAW SATELLITE DETECTIONS
# ============================================================

detection_group = (
    folium.FeatureGroup(
        name="🛰️ Satellite Detections",
        show=False,
    )
)


for _, row in (
    filtered_detections.iterrows()
):

    confidence = (
        row["confidence"]
        if "confidence"
        in row
        else "N/A"
    )

    frp = (
        row["frp"]
        if "frp"
        in row
        else "N/A"
    )


    folium.CircleMarker(

        location=[
            row["latitude"],
            row["longitude"],
        ],

        radius=3,

        color="black",

        fill=True,

        fill_opacity=0.6,

        popup=folium.Popup(

            f"""
            <b>Satellite Detection</b><br>
            Area: {config['display_name']}<br>
            Sensor: {row['sensor']}<br>
            Date: {row['acq_date']}<br>
            FRP: {frp} MW<br>
            Confidence: {confidence}
            """,

            max_width=300,
        ),

    ).add_to(
        detection_group
    )


detection_group.add_to(m)


# ============================================================
# HEATMAP
# ============================================================

heat_group = (
    folium.FeatureGroup(
        name="🔥 Hotspot Heatmap",
        show=False,
    )
)


heat_data = [
    [
        row["latitude"],
        row["longitude"],
        row["frp"],
    ]

    for _, row
    in filtered_detections.iterrows()
]


if heat_data:

    HeatMap(
        heat_data,
        radius=18,
        blur=15,
        min_opacity=0.3,
    ).add_to(
        heat_group
    )


heat_group.add_to(m)


# ============================================================
# FIRE EVENTS
# ============================================================

event_group = (
    folium.FeatureGroup(
        name="🔥 Fire Events",
        show=True,
    )
)


for _, row in (
    filtered_events.iterrows()
):

    priority = (
        row["PRIORITY"]
    )


    if priority == "HIGH":

        marker_color = "red"

    elif priority == "MONITORING":

        marker_color = "orange"

    else:

        marker_color = "green"


    def rain_text(value):

        if pd.notna(value):

            return (
                f"{value:.2f} mm"
            )

        return "N/A"


    popup = f"""
    <b>{row['FIRE_EVENT_ID']}</b><br><br>

    <b>Area:</b>
    {config['display_name']}<br>

    <b>Date:</b>
    {row['EVENT_DATE']}<br>

    <b>Priority:</b>
    {priority}<br>

    <b>Detections:</b>
    {row['DETECTION_COUNT']}<br>

    <b>Detected By:</b><br>
    {row['DETECTED_BY']}<br><br>

    <b>Maximum FRP:</b>
    {row['MAX_FRP_MW']} MW<br><br>

    <b>🌧️ Rainfall Context</b><br>

    1 Day:
    {rain_text(row['RAINFALL_1D_MM'])}<br>

    7 Days:
    {rain_text(row['RAINFALL_7D_MM'])}<br>

    30 Days:
    {rain_text(row['RAINFALL_30D_MM'])}
    """


    folium.CircleMarker(

        location=[
            row["LATITUDE"],
            row["LONGITUDE"],
        ],

        radius=8,

        color=marker_color,

        fill=True,

        fill_color=marker_color,

        fill_opacity=0.8,

        popup=folium.Popup(
            popup,
            max_width=350,
        ),

    ).add_to(
        event_group
    )


event_group.add_to(m)


folium.LayerControl().add_to(m)


st_folium(
    m,
    width=None,
    height=650,
)


# ============================================================
# CHARTS
# ============================================================

st.divider()

st.subheader(
    "📊 Fire Event Analysis"
)


c1, c2 = (
    st.columns(2)
)


with c1:

    st.markdown(
        "### Fire Events by Date"
    )


    daily = (
        events
        .groupby(
            "EVENT_DATE"
        )
        .size()
        .reset_index(
            name="Fire Events"
        )
        .set_index(
            "EVENT_DATE"
        )
    )


    st.bar_chart(
        daily
    )


with c2:

    st.markdown(
        "### Fire Events by Priority"
    )


    priority_chart = (
        events
        .groupby(
            "PRIORITY"
        )
        .size()
        .reset_index(
            name="Fire Events"
        )
        .set_index(
            "PRIORITY"
        )
    )


    st.bar_chart(
        priority_chart
    )


# ============================================================
# RAINFALL SUMMARY
# ============================================================

st.divider()

st.subheader(
    "🌧️ Rainfall Context"
)


st.dataframe(

    filtered_events[
        [
            "FIRE_EVENT_ID",
            "EVENT_DATE",
            "RAINFALL_1D_MM",
            "RAINFALL_7D_MM",
            "RAINFALL_30D_MM",
        ]
    ],

    use_container_width=True,

    hide_index=True,
)


# ============================================================
# TOP 10
# ============================================================

st.divider()

st.subheader(
    "🔥 Top 10 Fire Events"
)


priority_order = {
    "HIGH": 1,
    "MONITORING": 2,
    "LOW": 3,
}


top10 = (
    filtered_events.copy()
)


top10[
    "PRIORITY_ORDER"
] = (
    top10[
        "PRIORITY"
    ]
    .map(priority_order)
)


top10 = (
    top10
    .sort_values(

        by=[
            "PRIORITY_ORDER",
            "DETECTION_COUNT",
            "MAX_FRP_MW",
        ],

        ascending=[
            True,
            False,
            False,
        ],
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
            "MAX_FRP_MW",
            "RAINFALL_1D_MM",
            "RAINFALL_7D_MM",
            "RAINFALL_30D_MM",
        ]
    ],

    use_container_width=True,

    hide_index=True,
)


# ============================================================
# EVENT DETAIL
# ============================================================

st.divider()

st.subheader(
    "🔎 Fire Event Detail"
)


event_ids = (
    filtered_events[
        "FIRE_EVENT_ID"
    ].tolist()
)


if event_ids:

    selected_event = (
        st.selectbox(
            "Select Fire Event",
            event_ids,
        )
    )


    detail = (
        filtered_events[
            filtered_events[
                "FIRE_EVENT_ID"
            ]
            == selected_event
        ]
        .iloc[0]
    )


    c1, c2, c3 = (
        st.columns(3)
    )


    with c1:

        st.metric(
            "Priority",
            detail["PRIORITY"],
        )

        st.metric(
            "Detection Count",
            detail[
                "DETECTION_COUNT"
            ],
        )

        st.metric(
            "Maximum FRP",
            f"{detail['MAX_FRP_MW']} MW",
        )


    with c2:

        st.metric(
            "Latitude",
            f"{detail['LATITUDE']:.6f}",
        )

        st.metric(
            "Longitude",
            f"{detail['LONGITUDE']:.6f}",
        )

        st.write(
            "**Detected By**"
        )

        st.write(
            detail["DETECTED_BY"]
        )


    with c3:

        st.write(
            "**Area**"
        )

        st.write(
            config["display_name"]
        )


        st.write(
            "**Event Date**"
        )

        st.write(
            detail["EVENT_DATE"]
        )


        st.write(
            "**🌧️ Rainfall Context**"
        )


        st.metric(

            "1 Day",

            (
                f"{detail['RAINFALL_1D_MM']:.2f} mm"
                if pd.notna(
                    detail[
                        "RAINFALL_1D_MM"
                    ]
                )
                else "N/A"
            ),
        )


        st.metric(

            "7 Days",

            (
                f"{detail['RAINFALL_7D_MM']:.2f} mm"
                if pd.notna(
                    detail[
                        "RAINFALL_7D_MM"
                    ]
                )
                else "N/A"
            ),
        )


        st.metric(

            "30 Days",

            (
                f"{detail['RAINFALL_30D_MM']:.2f} mm"
                if pd.notna(
                    detail[
                        "RAINFALL_30D_MM"
                    ]
                )
                else "N/A"
            ),
        )


else:

    st.info(
        "No fire event matches "
        "the selected filter."
    )


# ============================================================
# EVENT TABLE
# ============================================================

st.divider()

st.subheader(
    "🔥 Fire Event Records"
)


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
            "RAINFALL_30D_MM",
        ]
    ],

    use_container_width=True,

    hide_index=True,
)


# ============================================================
# FOOTER
# ============================================================

st.caption(
    "Data source: NASA FIRMS + NASA POWER | "
    f"Spatial analysis: "
    f"{config['display_name']} boundary"
)
