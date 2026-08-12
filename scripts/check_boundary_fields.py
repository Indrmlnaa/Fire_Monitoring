import geopandas as gpd

SHP_FILE = r"boundaries\Indonesia\[LapakGIS.com] Batas_Kabupaten_BIG_PPBW_V1.shp"

print("Loading Indonesia boundary...")

gdf = gpd.read_file(SHP_FILE)

print()
print("========================================")
print("COLUMNS")
print("========================================")

print(gdf.columns.tolist())

print()
print("========================================")
print("JUMLAH KABUPATEN")
print("========================================")

print(len(gdf))

print()
print("========================================")
print("ATRIBUT TANPA GEOMETRY")
print("========================================")

# Tampilkan hanya kolom atribut
attribute_columns = [
    col for col in gdf.columns
    if col != "geometry"
]

print(
    gdf[attribute_columns]
    .head(10)
    .to_string(index=False)
)