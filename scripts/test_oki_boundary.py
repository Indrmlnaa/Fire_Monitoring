import geopandas as gpd

OKI_FILE = r"boundaries\OKI\OKI.shp"

print()
print("========================================")
print("TEST OKI BOUNDARY")
print("========================================")

oki = gpd.read_file(OKI_FILE)

print("CRS:", oki.crs)
print("Jumlah polygon:", len(oki))

print()
print("Nama wilayah:")
print(oki["WADMKK"].iloc[0])

print("Provinsi:")
print(oki["WADMPR"].iloc[0])

# Bounding box
minx, miny, maxx, maxy = oki.total_bounds

print()
print("========================================")
print("BOUNDING BOX")
print("========================================")

print("West :", minx)
print("South:", miny)
print("East :", maxx)
print("North:", maxy)

print()
print("========================================")
print("TEST BERHASIL")
print("========================================")