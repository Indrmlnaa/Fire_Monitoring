import os
import requests
import pandas as pd
import geopandas as gpd
import numpy as np

from pathlib import Path
from datetime import date, timedelta
from io import StringIO
from sklearn.cluster import DBSCAN


# ============================================================
# CONFIG
# ============================================================

MAP_KEY = os.environ["FIRMS_MAP_KEY"]


# ============================================================
# MONITORING AREAS
# ============================================================

AREAS = [
    {
        "name": "OKI",
        "boundary_file": "boundaries/OKI/OKI.shp",
        "use_indonesia_boundary": False
    },

    {
        "name": "Teluk_Bintuni",
        "boundary_file": "boundaries/Teluk_Bintuni/Teluk_Bintuni.shp",
        "use_indonesia_boundary": False
    }
]


# ============================================================
# ROLLING WINDOW
# ============================================================
#
# Today + previous 4 days = 5 days
#
# Example:
#
# 2026-08-15
# ↓
# 11, 12, 13, 14, 15
#
# Tomorrow:
# ↓
# 12, 13, 14, 15, 16
#
# ============================================================

END_DATE_OBJ = date.today()

START_DATE_OBJ = (
    END_DATE_OBJ
    - timedelta(days=4)
)

END_DATE = (
    END_DATE_OBJ.strftime("%Y-%m-%d")
)

START_DATE = (
    START_DATE_OBJ.strftime("%Y-%m-%d")
)


# ============================================================
# NASA FIRMS SENSORS
# ============================================================

SENSORS = [
    "MODIS_NRT",
    "VIIRS_SNPP_NRT",
    "VIIRS_NOAA20_NRT",
    "VIIRS_NOAA21_NRT"
]


# ============================================================
# SPATIAL CLUSTERING
# ============================================================

CLUSTER_DISTANCE_KM = 2.0


# ============================================================
# BASE FOLDER
# ============================================================

BASE_DIR = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)


RAW_DIR = (
    BASE_DIR
    / "data"
    / "v2"
    / "raw"
)


PROCESSED_DIR = (
    BASE_DIR
    / "data"
    / "v2"
    / "processed"
)


RAW_DIR.mkdir(
    parents=True,
    exist_ok=True
)


PROCESSED_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# NASA FIRMS API
# ============================================================

FIRMS_URL = (
    "https://firms.modaps.eosdis.nasa.gov/"
    "api/area/csv/"
    "{map_key}/{sensor}/"
    "{west},{south},{east},{north}/"
    "{days}"
)


# ============================================================
# NUMBER OF DAYS
# ============================================================

days = (
    pd.to_datetime(END_DATE)
    - pd.to_datetime(START_DATE)
).days + 1


# ============================================================
# LOAD BOUNDARY
# ============================================================

def load_area_boundary(area_config):

    area_name = area_config["name"]

    print("\n")
    print("=" * 60)
    print(
        f"LOADING {area_name.upper()} BOUNDARY"
    )
    print("=" * 60)

    # --------------------------------------------------------
    # NORMAL BOUNDARY FILE
    # --------------------------------------------------------

    if not area_config.get(
        "use_indonesia_boundary",
        False
    ):

        boundary_path = (
            BASE_DIR
            / area_config["boundary_file"]
        )

        if not boundary_path.exists():

            raise FileNotFoundError(
                f"Boundary tidak ditemukan: "
                f"{boundary_path}"
            )

        boundary = gpd.read_file(
            boundary_path
        )

    # --------------------------------------------------------
    # INDONESIA MASTER BOUNDARY
    # --------------------------------------------------------

    else:

        boundary_dir = (
            BASE_DIR
            / area_config["boundary_file"]
        )

        if not boundary_dir.exists():

            raise FileNotFoundError(
                f"Folder boundary Indonesia "
                f"tidak ditemukan: "
                f"{boundary_dir}"
            )

        # ----------------------------------------------------
        # FIND SHAPEFILE
        # ----------------------------------------------------

        shp_files = list(
            boundary_dir.glob("*.shp")
        )

        if not shp_files:

            raise FileNotFoundError(
                "Tidak ditemukan file .shp "
                f"di {boundary_dir}"
            )

        print(
            "Indonesia shapefile:"
        )

        for shp in shp_files:

            print(
                " -",
                shp.name
            )

        # ----------------------------------------------------
        # READ FIRST SHAPEFILE
        # ----------------------------------------------------

        indonesia = gpd.read_file(
            shp_files[0]
        )

        print(
            "Indonesia records:",
            len(indonesia)
        )

        # ----------------------------------------------------
        # CHECK COLUMN
        # ----------------------------------------------------

        column = (
            area_config[
                "boundary_column"
            ]
        )

        value = (
            area_config[
                "boundary_value"
            ]
        )

        if column not in indonesia.columns:

            raise RuntimeError(
                f"Kolom {column} "
                "tidak ditemukan.\n"
                f"Columns tersedia: "
                f"{list(indonesia.columns)}"
            )

        # ----------------------------------------------------
        # FILTER TELUK BINTUNI
        # ----------------------------------------------------

        boundary = indonesia[
            indonesia[column]
            .astype(str)
            .str.strip()
            .str.lower()
            ==
            value.lower()
        ].copy()

        if boundary.empty:

            raise RuntimeError(
                f"Boundary "
                f"'{value}' "
                f"tidak ditemukan "
                f"pada kolom {column}."
            )

        print(
            f"Filtered {value}:",
            len(boundary),
            "polygon"
        )

    # ========================================================
    # CRS
    # ========================================================

    if boundary.crs is None:

        print(
            "CRS tidak tersedia. "
            "Menggunakan EPSG:4326."
        )

        boundary = boundary.set_crs(
            "EPSG:4326"
        )

    else:

        boundary = boundary.to_crs(
            "EPSG:4326"
        )

    print(
        "CRS:",
        boundary.crs
    )

    print(
        "Records:",
        len(boundary)
    )

    return boundary


# ============================================================
# PROCESS ONE AREA
# ============================================================

def process_area(area_config):

    AREA_NAME = (
        area_config["name"]
    )

    print("\n\n")
    print("#" * 60)
    print(
        f"PROCESSING AREA: "
        f"{AREA_NAME}"
    )
    print("#" * 60)


    # ========================================================
    # LOAD BOUNDARY
    # ========================================================

    boundary = load_area_boundary(
        area_config
    )


    # ========================================================
    # GET BOUNDING BOX
    # ========================================================

    minx, miny, maxx, maxy = (
        boundary.total_bounds
    )

    west = minx
    south = miny
    east = maxx
    north = maxy


    print("\nNASA FIRMS AREA")

    print(
        "West :",
        west
    )

    print(
        "South:",
        south
    )

    print(
        "East :",
        east
    )

    print(
        "North:",
        north
    )


    print("\nDATE WINDOW")

    print(
        "Start :",
        START_DATE
    )

    print(
        "End   :",
        END_DATE
    )


    # ========================================================
    # DOWNLOAD FIRMS
    # ========================================================

    all_data = []


    for sensor in SENSORS:

        print("\n" + "=" * 60)

        print(
            f"{AREA_NAME} "
            f"- DOWNLOADING: "
            f"{sensor}"
        )

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
                    response.text[:500]
                )

                continue


            df = pd.read_csv(
                StringIO(
                    response.text
                )
            )


            if df.empty:

                print(
                    "Tidak ada hotspot."
                )

                continue


            # ------------------------------------------------
            # SENSOR
            # ------------------------------------------------

            df["sensor"] = sensor


            # ------------------------------------------------
            # DATE
            # ------------------------------------------------

            df["acq_date"] = (
                pd.to_datetime(
                    df["acq_date"],
                    errors="coerce"
                )
                .dt
                .strftime("%Y-%m-%d")
            )


            # ------------------------------------------------
            # EXACT DATE FILTER
            # ------------------------------------------------

            df = df[
                (df["acq_date"] >= START_DATE)
                &
                (df["acq_date"] <= END_DATE)
            ].copy()


            print(
                "Hotspot ditemukan:",
                len(df)
            )


            if df.empty:

                continue


            # ------------------------------------------------
            # SAVE SENSOR RAW
            # ------------------------------------------------

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


            all_data.append(
                df
            )


        except Exception as e:

            print(
                "ERROR:",
                repr(e)
            )


    # ========================================================
    # COMBINE
    # ========================================================

    print("\n" + "=" * 60)

    print(
        f"{AREA_NAME} - "
        "COMBINING DATA"
    )

    print("=" * 60)


    if not all_data:

        print(
            f"WARNING: "
            f"Tidak ada data FIRMS "
            f"untuk {AREA_NAME}."
        )

        return False


    firms = pd.concat(
        all_data,
        ignore_index=True
    )


    print(
        "Total records:",
        len(firms)
    )


    print(
        "\nHotspot per sensor:"
    )


    print(
        firms[
            "sensor"
        ].value_counts()
    )


    print(
        "\nHotspot per date:"
    )


    print(
        firms[
            "acq_date"
        ]
        .value_counts()
        .sort_index()
    )


    # ========================================================
    # SAVE COMBINED RAW
    # ========================================================

    raw_combined = (
        RAW_DIR
        / f"{AREA_NAME}_NASA_FIRMS_{days}days_raw.csv"
    )


    firms.to_csv(
        raw_combined,
        index=False
    )


    print(
        "\nRaw output:",
        raw_combined
    )


    # ========================================================
    # SPATIAL ANALYSIS
    # ========================================================

    print("\n" + "=" * 60)

    print(
        f"{AREA_NAME} - "
        "SPATIAL ANALYSIS"
    )

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


    # ========================================================
    # SPATIAL JOIN
    # ========================================================

    points[
        "INSIDE_AREA"
    ] = "NO"


    joined = gpd.sjoin(
        points,
        boundary,
        how="left",
        predicate="within"
    )


    points.loc[
        joined.index[
            joined.index_right.notna()
        ],
        "INSIDE_AREA"
    ] = "YES"


    # ========================================================
    # DISTANCE TO BOUNDARY
    # ========================================================

    points[
        "DISTANCE_BOUNDARY_KM"
    ] = np.nan


    outside_mask = (
        points[
            "INSIDE_AREA"
        ]
        == "NO"
    )


    if outside_mask.any():

        points_metric = (
            points.to_crs(
                "EPSG:3857"
            )
        )


        boundary_metric = (
            boundary.to_crs(
                "EPSG:3857"
            )
        )


        boundary_line = (
            boundary_metric
            .boundary
            .union_all()
        )


        points.loc[
            outside_mask,
            "DISTANCE_BOUNDARY_KM"
        ] = (
            points_metric.loc[
                outside_mask
            ]
            .geometry
            .distance(
                boundary_line
            )
            / 1000
        ).round(3)


    # ========================================================
    # PRIORITY
    # ========================================================

    points[
        "PRIORITY"
    ] = "MONITORING"


    # HIGH

    points.loc[
        (
            (
                points[
                    "INSIDE_AREA"
                ]
                == "YES"
            )
            &
            (
                points[
                    "frp"
                ]
                .fillna(0)
                >= 10
            )
        ),
        "PRIORITY"
    ] = "HIGH"


    # LOW

    points.loc[
        (
            (
                points[
                    "INSIDE_AREA"
                ]
                == "YES"
            )
            &
            (
                points[
                    "frp"
                ]
                .fillna(0)
                < 10
            )
        ),
        "PRIORITY"
    ] = "LOW"


    # OUTSIDE BUT CLOSE

    points.loc[
        (
            (
                points[
                    "INSIDE_AREA"
                ]
                == "NO"
            )
            &
            (
                points[
                    "DISTANCE_BOUNDARY_KM"
                ]
                <= 5
            )
        ),
        "PRIORITY"
    ] = "MONITORING"


    # ========================================================
    # SPATIAL OUTPUT
    # ========================================================

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
        "\nSpatial output:",
        spatial_output
    )


    print(
        "\nInside / Outside:"
    )


    print(
        points[
            "INSIDE_AREA"
        ].value_counts()
    )


    print(
        "\nInside per date:"
    )


    print(
        points[
            points[
                "INSIDE_AREA"
            ]
            == "YES"
        ][
            "acq_date"
        ]
        .value_counts()
        .sort_index()
    )


    # ========================================================
    # FIRE EVENT CLUSTERING
    # ========================================================

    print("\n" + "=" * 60)

    print(
        f"{AREA_NAME} - "
        "FIRE EVENT CLUSTERING"
    )

    print("=" * 60)


    inside = points[
        points[
            "INSIDE_AREA"
        ]
        == "YES"
    ].copy()


    print(
        "Inside detections:",
        len(inside)
    )


    # ========================================================
    # EVENT OUTPUT
    # ========================================================

    event_output = (
        PROCESSED_DIR
        / f"{AREA_NAME}_NASA_FIRMS_fire_events.csv"
    )


    # ========================================================
    # NO DETECTIONS
    # ========================================================

    if len(inside) == 0:

        print(
            "Tidak ada fire detection "
            "di dalam boundary."
        )


        empty_events = pd.DataFrame(
            columns=[
                "FIRE_EVENT_ID",
                "EVENT_DATE",
                "LATITUDE",
                "LONGITUDE",
                "DETECTION_COUNT",
                "DETECTED_BY",
                "MAX_FRP_MW",
                "PRIORITY"
            ]
        )


        empty_events.to_csv(
            event_output,
            index=False
        )


        return True


    # ========================================================
    # DBSCAN
    # ========================================================

    earth_radius_km = 6371.0088


    epsilon = (
        CLUSTER_DISTANCE_KM
        / earth_radius_km
    )


    inside[
        "CLUSTER"
    ] = -1


    cluster_counter = 0


    # ========================================================
    # CLUSTER EACH DATE SEPARATELY
    # ========================================================

    for event_date, daily_group in (
        inside.groupby(
            "acq_date",
            sort=True
        )
    ):

        print(
            f"\nClustering date: "
            f"{event_date}"
        )


        print(
            "Detections:",
            len(daily_group)
        )


        daily_indices = (
            daily_group.index
        )


        coords = np.radians(
            daily_group[
                [
                    "latitude",
                    "longitude"
                ]
            ].values
        )


        clustering = DBSCAN(

            eps=epsilon,

            min_samples=1,

            metric="haversine"

        ).fit(
            coords
        )


        labels = (
            clustering.labels_
        )


        daily_clusters = (
            len(
                np.unique(
                    labels
                )
            )
        )


        print(
            "Daily clusters:",
            daily_clusters
        )


        # ----------------------------------------------------
        # GLOBAL CLUSTER IDS
        # ----------------------------------------------------

        for original_label in (
            np.unique(labels)
        ):

            mask = (
                labels
                == original_label
            )


            inside.loc[
                daily_indices[mask],
                "CLUSTER"
            ] = cluster_counter


            cluster_counter += 1


    # ========================================================
    # BUILD EVENTS
    # ========================================================

    events = []


    for cluster_id, group in (
        inside.groupby(
            "CLUSTER"
        )
    ):

        detected_by = ", ".join(
            sorted(
                group[
                    "sensor"
                ]
                .dropna()
                .unique()
            )
        )


        max_frp = (
            group[
                "frp"
            ]
            .fillna(0)
            .max()
        )


        detection_count = (
            len(group)
        )


        lat = (
            group[
                "latitude"
            ]
            .mean()
        )


        lon = (
            group[
                "longitude"
            ]
            .mean()
        )


        event_date = (
            group[
                "acq_date"
            ]
            .mode()
            .iloc[0]
        )


        sensor_count = (
            group[
                "sensor"
            ]
            .nunique()
        )


        # ====================================================
        # EVENT PRIORITY
        # ====================================================

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

            "EVENT_DATE":
                event_date,

            "LATITUDE":
                round(
                    lat,
                    6
                ),

            "LONGITUDE":
                round(
                    lon,
                    6
                ),

            "DETECTION_COUNT":
                detection_count,

            "DETECTED_BY":
                detected_by,

            "MAX_FRP_MW":
                round(
                    max_frp,
                    2
                ),

            "PRIORITY":
                priority

        })


    # ========================================================
    # EVENTS DATAFRAME
    # ========================================================

    events_df = pd.DataFrame(
        events
    )


    # ========================================================
    # SORT
    # ========================================================

    events_df = (
        events_df
        .sort_values(
            [
                "EVENT_DATE",
                "DETECTION_COUNT"
            ],
            ascending=[
                True,
                False
            ]
        )
        .reset_index(
            drop=True
        )
    )


    # ========================================================
    # EVENT ID
    # ========================================================

    events_df.insert(

        0,

        "FIRE_EVENT_ID",

        [
            f"{AREA_NAME}_FE-{i:04d}"

            for i in range(
                1,
                len(events_df) + 1
            )
        ]
    )


    # ========================================================
    # SAVE EVENTS
    # ========================================================

    events_df.to_csv(
        event_output,
        index=False
    )


    print(
        "\nUnique fire events:",
        len(events_df)
    )


    print(
        "\nEvents per date:"
    )


    print(
        events_df[
            "EVENT_DATE"
        ]
        .value_counts()
        .sort_index()
    )


    print(
        "\nPriority:"
    )


    print(
        events_df[
            "PRIORITY"
        ]
        .value_counts()
    )


    print(
        "\nTop 10:"
    )


    print(
        events_df
        .sort_values(
            "DETECTION_COUNT",
            ascending=False
        )
        .head(10)
        .to_string(
            index=False
        )
    )


    print(
        "\nFire event output:",
        event_output
    )


    return True


# ============================================================
# MAIN
# ============================================================

print("\n")
print("=" * 60)
print("FIRE MONITORING PIPELINE V2")
print("=" * 60)

print(
    "Period:",
    START_DATE,
    "to",
    END_DATE
)

print(
    "Areas:",
    ", ".join(
        area["name"]
        for area in AREAS
    )
)

print(
    "Sensors:",
    ", ".join(SENSORS)
)

print(
    "Cluster distance:",
    CLUSTER_DISTANCE_KM,
    "km"
)


# ============================================================
# PROCESS ALL AREAS
# ============================================================

results = {}


for area in AREAS:

    try:

        results[
            area["name"]
        ] = process_area(
            area
        )

    except Exception as e:

        print("\n")
        print(
            "!" * 60
        )

        print(
            f"AREA FAILED: "
            f"{area['name']}"
        )

        print(
            "ERROR:",
            repr(e)
        )

        print(
            "!" * 60
        )

        results[
            area["name"]
        ] = False


# ============================================================
# FINAL SUMMARY
# ============================================================

print("\n\n")

print("=" * 60)
print("PIPELINE V2 COMPLETE")
print("=" * 60)


print(
    "Period:",
    START_DATE,
    "to",
    END_DATE
)


print(
    "\nAREA STATUS:"
)


for area_name, status in (
    results.items()
):

    print(
        f"  {area_name}: "
        f"{'SUCCESS' if status else 'FAILED'}"
    )


print(
    "\nGenerated files:"
)


for file in sorted(
    PROCESSED_DIR.glob("*.csv")
):

    print(
        " -",
        file.name
    )


print("=" * 60)
