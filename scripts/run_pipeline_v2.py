import os
import time
import requests
import pandas as pd
import geopandas as gpd
import numpy as np

from pathlib import Path
from sklearn.cluster import DBSCAN


# ============================================================
# CONFIG — CUKUP UBAH BAGIAN INI
# ============================================================

MAP_KEY = os.environ["0e32951e5111df9052f4525862db9134"]

AREA_NAME = "OKI"

BOUNDARY_FILE = (
    r"boundaries\OKI\OKI.shp"
)

from datetime import date, timedelta

END_DATE = date.today()
START_DATE = END_DATE - timedelta(days=4)

END_DATE = END_DATE.strftime("%Y-%m-%d")
START_DATE = START_DATE.strftime("%Y-%m-%d")

SENSORS = [
    "MODIS_NRT",
    "VIIRS_SNPP_NRT",
    "VIIRS_NOAA20_NRT",
    "VIIRS_NOAA21_NRT"
]

CLUSTER_DISTANCE_KM = 2.0


# ============================================================
# FOLDER
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

RAW_DIR = BASE_DIR / "data" / "v2" / "raw"

PROCESSED_DIR = BASE_DIR / "data" / "v2" / "processed"

RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# NASA FIRMS API
# ============================================================

FIRMS_URL = (
    "https://firms.modaps.eosdis.nasa.gov/"
    "api/area/csv/"
    "{map_key}/{sensor}/{west},{south},{east},{north}/"
    "{days}"
)


# ============================================================
# LOAD BOUNDARY
# ============================================================

print("=" * 60)
print(f"LOADING {AREA_NAME.upper()} BOUNDARY")
print("=" * 60)

boundary = gpd.read_file(
    BASE_DIR / BOUNDARY_FILE
)

boundary = boundary.to_crs("EPSG:4326")

print("CRS:", boundary.crs)
print("Records:", len(boundary))


# ============================================================
# GET BOUNDING BOX
# ============================================================

minx, miny, maxx, maxy = boundary.total_bounds

west = minx
south = miny
east = maxx
north = maxy

print("\nNASA FIRMS AREA")
print("West :", west)
print("South:", south)
print("East :", east)
print("North:", north)


# ============================================================
# DOWNLOAD FIRMS
# ============================================================

all_data = []

days = (
    pd.to_datetime(END_DATE)
    - pd.to_datetime(START_DATE)
).days + 1


for sensor in SENSORS:

    print("\n" + "=" * 60)
    print(f"DOWNLOADING: {sensor}")
    print("=" * 60)

    url = FIRMS_URL.format(
        map_key=MAP_KEY,
        sensor=sensor,
        west=west,
        south=south,
        east=east,
        north=north,
        days=days
    )

    try:

        response = requests.get(
            url,
            timeout=60
        )

        print(
            "HTTP Status:",
            response.status_code
        )

        if response.status_code != 200:

            print(
                "Download failed:",
                response.text[:300]
            )

            continue


        from io import StringIO

        df = pd.read_csv(
            StringIO(response.text)
        )


        if df.empty:

            print("Tidak ada hotspot.")

            continue


        df["sensor"] = sensor

        df["acq_date"] = pd.to_datetime(
            df["acq_date"]
        ).dt.strftime("%Y-%m-%d")


        # Filter exact date range
        df = df[
            (df["acq_date"] >= START_DATE)
            &
            (df["acq_date"] <= END_DATE)
        ]


        print(
            "Hotspot ditemukan:",
            len(df)
        )


        output_file = (
            RAW_DIR
            / f"{AREA_NAME}_{sensor}_{days}days.csv"
        )

        df.to_csv(
            output_file,
            index=False
        )

        print(
            "Saved:",
            output_file
        )

        all_data.append(df)


    except Exception as e:

        print(
            "ERROR:",
            e
        )


# ============================================================
# COMBINE
# ============================================================

print("\n" + "=" * 60)
print("COMBINING DATA")
print("=" * 60)


if not all_data:

    raise RuntimeError(
        "Tidak ada data NASA FIRMS yang berhasil didownload."
    )


firms = pd.concat(
    all_data,
    ignore_index=True
)


print(
    "Total records:",
    len(firms)
)


print("\nHotspot per sensor:")

print(
    firms["sensor"].value_counts()
)


print("\nHotspot per date:")

print(
    firms["acq_date"].value_counts().sort_index()
)


raw_combined = (
    RAW_DIR
    / f"{AREA_NAME}_NASA_FIRMS_{days}days_raw.csv"
)


firms.to_csv(
    raw_combined,
    index=False
)


print(
    "\nOutput:",
    raw_combined
)


# ============================================================
# SPATIAL ANALYSIS
# ============================================================

print("\n" + "=" * 60)
print("SPATIAL ANALYSIS")
print("=" * 60)


geometry = gpd.points_from_xy(
    firms["longitude"],
    firms["latitude"]
)


points = gpd.GeoDataFrame(
    firms,
    geometry=geometry,
    crs="EPSG:4326"
)


# Spatial join
points["INSIDE_AREA"] = "NO"


joined = gpd.sjoin(
    points,
    boundary,
    how="left",
    predicate="within"
)


points.loc[
    joined.index[joined.index_right.notna()],
    "INSIDE_AREA"
] = "YES"


# ============================================================
# DISTANCE TO BOUNDARY — OUTSIDE ONLY
# ============================================================

points["DISTANCE_BOUNDARY_KM"] = np.nan

outside_mask = points["INSIDE_AREA"] == "NO"

if outside_mask.any():

    points_metric = points.to_crs("EPSG:3857")

    boundary_metric = boundary.to_crs("EPSG:3857")

    boundary_line = boundary_metric.boundary.union_all()

    points.loc[
        outside_mask,
        "DISTANCE_BOUNDARY_KM"
    ] = (
        points_metric.loc[
            outside_mask
        ]
        .geometry
        .distance(boundary_line)
        / 1000
    ).round(3)
# ============================================================
# PRIORITY PER DETECTION
# ============================================================

points["PRIORITY"] = "MONITORING"


points.loc[
    (
        (points["INSIDE_AREA"] == "YES")
        &
        (
            points["frp"].fillna(0) >= 10
        )
    ),
    "PRIORITY"
] = "HIGH"


points.loc[
    (
        (points["INSIDE_AREA"] == "YES")
        &
        (
            points["frp"].fillna(0) < 10
        )
    ),
    "PRIORITY"
] = "LOW"


# Outside but close to boundary
points.loc[
    (
        (points["INSIDE_AREA"] == "NO")
        &
        (
            points["DISTANCE_BOUNDARY_KM"] <= 5
        )
    ),
    "PRIORITY"
] = "MONITORING"


# ============================================================
# SPATIAL OUTPUT
# ============================================================

spatial_output = (
    PROCESSED_DIR
    / f"{AREA_NAME}_NASA_FIRMS_spatial_analysis.csv"
)


points.drop(
    columns="geometry"
).to_csv(
    spatial_output,
    index=False
)


print(
    "Spatial output:",
    spatial_output
)


print("\nInside / Outside:")

print(
    points["INSIDE_AREA"].value_counts()
)


# ============================================================
# FIRE EVENT CLUSTERING
# ============================================================

print("\n" + "=" * 60)
print("FIRE EVENT CLUSTERING")
print("=" * 60)


inside = points[
    points["INSIDE_AREA"] == "YES"
].copy()


print(
    "Inside detections:",
    len(inside)
)


if len(inside) == 0:

    print(
        "Tidak ada fire detection di dalam boundary."
    )

else:

    # --------------------------------------------------------
    # DBSCAN
    # --------------------------------------------------------

    coords = np.radians(
        inside[
            ["latitude", "longitude"]
        ].values
    )


    earth_radius_km = 6371.0088


    epsilon = (
        CLUSTER_DISTANCE_KM
        / earth_radius_km
    )


    clustering = DBSCAN(
        eps=epsilon,
        min_samples=1,
        metric="haversine"
    ).fit(coords)


    inside["CLUSTER"] = (
        clustering.labels_
    )


    # --------------------------------------------------------
    # BUILD FIRE EVENTS
    # --------------------------------------------------------

    events = []


    for cluster_id, group in inside.groupby(
        "CLUSTER"
    ):

        detected_by = ", ".join(
            sorted(
                group["sensor"]
                .dropna()
                .unique()
            )
        )


        max_frp = (
            group["frp"]
            .fillna(0)
            .max()
        )


        detection_count = len(
            group
        )


        lat = group["latitude"].mean()

        lon = group["longitude"].mean()

        date = group["acq_date"].mode()[0]


        # ----------------------------------------------------
        # EVENT PRIORITY
        # ----------------------------------------------------

        sensor_count = (
            group["sensor"]
            .nunique()
        )


        if (
            detection_count >= 10
            or sensor_count >= 3
            or max_frp >= 30
        ):

            priority = "HIGH"

        elif (
            detection_count >= 3
            or sensor_count >= 2
            or max_frp >= 10
        ):

            priority = "MONITORING"

        else:

            priority = "LOW"


        events.append({
    "EVENT_DATE": date,
    "LATITUDE": round(lat, 6),
    "LONGITUDE": round(lon, 6),
    "DETECTION_COUNT": detection_count,
    "DETECTED_BY": detected_by,
    "MAX_FRP_MW": round(max_frp, 2),
    "PRIORITY": priority
})


    events_df = pd.DataFrame(
        events
    )


    # --------------------------------------------------------
    # EVENT ID
    # --------------------------------------------------------

    events_df = events_df.sort_values(
        [
            "EVENT_DATE",
            "DETECTION_COUNT"
        ],
        ascending=[
            True,
            False
        ]
    ).reset_index(
        drop=True
    )


    events_df.insert(
        0,
        "FIRE_EVENT_ID",
        [
            f"FE-{i:04d}"
            for i in range(
                1,
                len(events_df) + 1
            )
        ]
    )


    # --------------------------------------------------------
    # OUTPUT
    # --------------------------------------------------------

    event_output = (
        PROCESSED_DIR
        / f"{AREA_NAME}_NASA_FIRMS_fire_events.csv"
    )


    events_df.to_csv(
        event_output,
        index=False
    )


    print(
        "\nUnique fire events:",
        len(events_df)
    )


    print("\nPriority:")

    print(
        events_df[
            "PRIORITY"
        ].value_counts()
    )


    print("\nTop 10:")

    print(
        events_df.sort_values(
            "DETECTION_COUNT",
            ascending=False
        ).head(10).to_string(
            index=False
        )
    )


    print(
        "\nFire event output:",
        event_output
    )


# ============================================================
# FINAL SUMMARY
# ============================================================

print("\n")
print("=" * 60)
print("PIPELINE V2 COMPLETE")
print("=" * 60)

print(
    "Area:",
    AREA_NAME
)

print(
    "Period:",
    START_DATE,
    "to",
    END_DATE
)

print(
    "Satellite detections:",
    len(firms)
)

print(
    "Raw output:",
    raw_combined
)

print(
    "Spatial output:",
    spatial_output
)

if len(inside) > 0:

    print(
        "Fire event output:",
        event_output
    )

print("=" * 60)