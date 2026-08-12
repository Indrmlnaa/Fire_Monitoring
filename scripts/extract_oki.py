import geopandas as gpd
import os

# ============================================================
# INPUT
# ============================================================

INPUT_FILE = r"boundaries\Indonesia\[LapakGIS.com] Batas_Kabupaten_BIG_PPBW_V1.shp"

# ============================================================
# OUTPUT
# ============================================================

OUTPUT_DIR = r"boundaries\OKI"
OUTPUT_FILE = os.path.join(
    OUTPUT_DIR,
    "OKI.shp"
)

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)

# ============================================================
# LOAD INDONESIA BOUNDARY
# ============================================================

print()
print("========================================")
print("LOADING INDONESIA BOUNDARY")
print("========================================")

gdf = gpd.read_file(INPUT_FILE)

print("Total wilayah:", len(gdf))

# ============================================================
# SEARCH OKI
# ============================================================

target = "Ogan Komering Ilir"

oki = gdf[
    gdf["WADMKK"].astype(str).str.strip().str.lower()
    == target.lower()
].copy()

# ============================================================
# CHECK RESULT
# ============================================================

print()
print("========================================")
print("SEARCH RESULT")
print("========================================")

print("Target:", target)
print("Found:", len(oki))

if len(oki) == 0:

    print()
    print("❌ OKI tidak ditemukan.")

    print()
    print("Contoh nama wilayah Sumatera Selatan:")

    print(
        gdf[
            gdf["WADMPR"]
            .astype(str)
            .str.contains(
                "Sumatera Selatan",
                case=False,
                na=False
            )
        ][
            ["WADMKK", "WADMPR"]
        ]
        .to_string(index=False)
    )

    raise SystemExit


# ============================================================
# SAVE OKI
# ============================================================

oki.to_file(
    OUTPUT_FILE,
    driver="ESRI Shapefile"
)

print()
print("========================================")
print("OKI EXTRACTION SUCCESS")
print("========================================")

print("Wilayah:", oki["WADMKK"].iloc[0])
print("Provinsi:", oki["WADMPR"].iloc[0])

print()
print("Output:")
print(OUTPUT_FILE)