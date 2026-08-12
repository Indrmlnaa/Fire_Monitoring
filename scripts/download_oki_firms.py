import requests
import pandas as pd
import geopandas as gpd
import os
from io import StringIO


# ============================================================
# CONFIGURATION
# ============================================================

MAP_KEY = "0e32951e5111df9052f4525862db9134"

BOUNDARY_FILE = r"boundaries\OKI\OKI.shp"

START_DATE = "2026-08-06"
DAY_RANGE = 5

OUTPUT_DIR = r"data\raw"

SENSORS = [
    "MODIS_NRT",
    "VIIRS_SNPP_NRT",
    "VIIRS_NOAA20_NRT",
    "VIIRS_NOAA21_NRT"
]


# ============================================================
# CREATE OUTPUT FOLDER
# ============================================================

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


# ============================================================
# LOAD OKI
# ============================================================

print()
print("========================================")
print("LOADING OKI BOUNDARY")
print("========================================")

oki = gpd.read_file(
    BOUNDARY_FILE
)

print(
    "Wilayah:",
    oki["WADMKK"].iloc[0]
)

print(
    "Provinsi:",
    oki["WADMPR"].iloc[0]
)

print(
    "CRS:",
    oki.crs
)


# ============================================================
# ENSURE WGS84
# ============================================================

if oki.crs is None:

    raise ValueError(
        "Boundary tidak memiliki CRS."
    )

oki = oki.to_crs(
    "EPSG:4326"
)


# ============================================================
# GET BOUNDING BOX
# ============================================================

minx, miny, maxx, maxy = oki.total_bounds


# Small margin around OKI
margin = 0.05

west = minx - margin
south = miny - margin
east = maxx + margin
north = maxy + margin


area = (
    f"{west},{south},{east},{north}"
)


print()
print("========================================")
print("NASA FIRMS AREA")
print("========================================")

print(
    "West :", west
)

print(
    "South:", south
)

print(
    "East :", east
)

print(
    "North:", north
)


# ============================================================
# DOWNLOAD FUNCTION
# ============================================================

def download_sensor(sensor):

    print()
    print("========================================")
    print(
        "Downloading:",
        sensor
    )
    print("========================================")


    url = (
        "https://firms.modaps.eosdis.nasa.gov/"
        "api/area/csv/"
        f"{MAP_KEY}/"
        f"{sensor}/"
        f"{area}/"
        f"{DAY_RANGE}/"
        f"{START_DATE}"
    )


    try:

        response = requests.get(
            url,
            timeout=120
        )


        print(
            "HTTP Status:",
            response.status_code
        )


        if response.status_code != 200:

            print(
                "❌ NASA FIRMS ERROR"
            )

            print(
                response.text[:500]
            )

            return pd.DataFrame()


        if not response.text.strip():

            print(
                "Tidak ada data."
            )

            return pd.DataFrame()


        df = pd.read_csv(
            StringIO(
                response.text
            )
        )


        if df.empty:

            print(
                "Tidak ada hotspot."
            )

            return pd.DataFrame()


        # Add sensor
        df["sensor"] = sensor


        print(
            "Hotspot ditemukan:",
            len(df)
        )


        # Save individual sensor
        output_file = os.path.join(
            OUTPUT_DIR,
            f"OKI_{sensor}_5days.csv"
        )


        df.to_csv(
            output_file,
            index=False
        )


        print(
            "Saved:",
            output_file
        )


        return df


    except Exception as e:

        print(
            "❌ ERROR:",
            e
        )

        return pd.DataFrame()


# ============================================================
# DOWNLOAD ALL SENSORS
# ============================================================

all_data = []


for sensor in SENSORS:

    df = download_sensor(
        sensor
    )


    if not df.empty:

        all_data.append(
            df
        )


# ============================================================
# COMBINE
# ============================================================

print()
print("========================================")
print("COMBINING DATA")
print("========================================")


if all_data:

    combined = pd.concat(
        all_data,
        ignore_index=True
    )


    output_file = os.path.join(
        OUTPUT_DIR,
        "OKI_NASA_FIRMS_5days_raw.csv"
    )


    combined.to_csv(
        output_file,
        index=False
    )


    print()
    print(
        "Total records:",
        len(combined)
    )


    print()
    print(
        "Hotspot per sensor:"
    )

    print(
        combined[
            "sensor"
        ].value_counts()
    )


    print()
    print(
        "Hotspot per date:"
    )

    print(
        combined[
            "acq_date"
        ].value_counts()
        .sort_index()
    )


    print()
    print(
        "Output:"
    )

    print(
        output_file
    )


else:

    print(
        "Tidak ada hotspot."
    )


print()
print("========================================")
print("OKI FIRMS DOWNLOAD SELESAI")
print("========================================")