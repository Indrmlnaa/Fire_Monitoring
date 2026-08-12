import pandas as pd
import geopandas as gpd
import os

# ============================================================
# CONFIGURATION
# ============================================================

FIRMS_FILE = r"data\raw\OKI_NASA_FIRMS_5days_raw.csv"
BOUNDARY_FILE = r"boundaries\OKI\OKI.shp"

OUTPUT_DIR = r"data\processed"

OUTPUT_FILE = os.path.join(
    OUTPUT_DIR,
    "OKI_NASA_FIRMS_spatial_analysis.csv"
)

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)

# ============================================================
# LOAD FIRMS DATA
# ============================================================

print()
print("========================================")
print("LOADING NASA FIRMS DATA")
print("========================================")

df = pd.read_csv(FIRMS_FILE)

print(
    "Total satellite detections:",
    len(df)
)

# ============================================================
# CREATE GEODATAFRAME
# ============================================================

hotspots = gpd.GeoDataFrame(
    df.copy(),
    geometry=gpd.points_from_xy(
        df["longitude"],
        df["latitude"]
    ),
    crs="EPSG:4326"
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

oki = oki.to_crs(
    "EPSG:4326"
)

print(
    "Boundary:",
    oki["WADMKK"].iloc[0]
)

# ============================================================
# SPATIAL JOIN
# ============================================================

print()
print("========================================")
print("SPATIAL ANALYSIS")
print("========================================")

joined = gpd.sjoin(
    hotspots,
    oki[["WADMKK", "WADMPR", "geometry"]],
    how="left",
    predicate="within"
)

# ============================================================
# INSIDE / OUTSIDE
# ============================================================

joined["INSIDE_OKI"] = joined[
    "WADMKK"
].notna().map({
    True: "YES",
    False: "NO"
})

# ============================================================
# DISTANCE TO OKI BOUNDARY
# ============================================================

print(
    "Calculating distance to boundary..."
)

# Project to metric CRS
hotspots_projected = hotspots.to_crs(
    "EPSG:32748"
)

oki_projected = oki.to_crs(
    "EPSG:32748"
)

boundary = oki_projected.geometry.boundary

hotspots_projected["DISTANCE_BOUNDARY_KM"] = (
    hotspots_projected.geometry
    .apply(
        lambda point:
        point.distance(
            boundary.unary_union
        ) / 1000
    )
)

joined["DISTANCE_BOUNDARY_KM"] = (
    hotspots_projected[
        "DISTANCE_BOUNDARY_KM"
    ].round(3).values
)

# ============================================================
# CLEAN COLUMNS
# ============================================================

drop_columns = [
    "geometry",
    "index_right",
    "WADMKK",
    "WADMPR"
]

for col in drop_columns:

    if col in joined.columns:

        joined = joined.drop(
            columns=col
        )

# ============================================================
# SAVE
# ============================================================

joined.to_csv(
    OUTPUT_FILE,
    index=False
)

# ============================================================
# SUMMARY
# ============================================================

print()
print("========================================")
print("SPATIAL ANALYSIS COMPLETE")
print("========================================")

print(
    "Total detections:",
    len(joined)
)

print()
print("Inside OKI:")

print(
    joined[
        "INSIDE_OKI"
    ].value_counts()
)

print()
print("Output:")

print(
    OUTPUT_FILE
)

print()
print("========================================")