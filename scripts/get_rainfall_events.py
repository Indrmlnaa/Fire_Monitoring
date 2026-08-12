import requests
import pandas as pd
from pathlib import Path
from datetime import timedelta

# ============================================================
# RAINFALL PER FIRE EVENT - NASA POWER
# ============================================================

INPUT_FILE = Path(
    "data/v2/processed/OKI_NASA_FIRMS_fire_events.csv"
)

OUTPUT_FILE = Path(
    "data/v2/processed/OKI_fire_events_rainfall.csv"
)

print("=" * 60)
print("RAINFALL PER FIRE EVENT - NASA POWER")
print("=" * 60)

# ============================================================
# LOAD FIRE EVENTS
# ============================================================

if not INPUT_FILE.exists():
    raise FileNotFoundError(
        f"Input file tidak ditemukan: {INPUT_FILE}"
    )

df = pd.read_csv(INPUT_FILE)

print(f"Fire events loaded: {len(df)}")
print("Columns:")
print(df.columns.tolist())

if df.empty:
    raise RuntimeError("Fire event file kosong.")

# ============================================================
# FIND COLUMNS
# ============================================================

def find_column(possible_names):
    for name in possible_names:
        if name in df.columns:
            return name
    return None


lat_col = find_column([
    "latitude",
    "LATITUDE",
    "lat",
    "LAT"
])

lon_col = find_column([
    "longitude",
    "LONGITUDE",
    "lon",
    "LON"
])

date_col = find_column([
    "date",
    "DATE",
    "acq_date",
    "ACQ_DATE",
    "event_date",
    "EVENT_DATE"
])

if lat_col is None:
    raise RuntimeError(
        f"Kolom latitude tidak ditemukan. "
        f"Kolom tersedia: {df.columns.tolist()}"
    )

if lon_col is None:
    raise RuntimeError(
        f"Kolom longitude tidak ditemukan. "
        f"Kolom tersedia: {df.columns.tolist()}"
    )

if date_col is None:
    raise RuntimeError(
        f"Kolom tanggal tidak ditemukan. "
        f"Kolom tersedia: {df.columns.tolist()}"
    )

print()
print(f"Latitude column : {lat_col}")
print(f"Longitude column: {lon_col}")
print(f"Date column     : {date_col}")

# ============================================================
# CLEAN DATA
# ============================================================

df[lat_col] = pd.to_numeric(
    df[lat_col],
    errors="coerce"
)

df[lon_col] = pd.to_numeric(
    df[lon_col],
    errors="coerce"
)

df[date_col] = pd.to_datetime(
    df[date_col],
    errors="coerce"
)

df = df.dropna(
    subset=[
        lat_col,
        lon_col,
        date_col
    ]
).copy()

print(f"Valid fire events: {len(df)}")

# ============================================================
# NASA POWER
# ============================================================

def get_rainfall(lat, lon, event_date):

    event_date = pd.Timestamp(event_date)

    start_date = event_date - timedelta(days=29)
    end_date = event_date

    url = (
        "https://power.larc.nasa.gov/api/temporal/daily/point"
        "?parameters=PRECTOTCORR"
        "&community=AG"
        f"&longitude={lon}"
        f"&latitude={lat}"
        f"&start={start_date.strftime('%Y%m%d')}"
        f"&end={end_date.strftime('%Y%m%d')}"
        "&format=JSON"
    )

    response = requests.get(
        url,
        timeout=60
    )

    response.raise_for_status()

    data = response.json()

    rainfall = (
        data["properties"]
        ["parameter"]
        ["PRECTOTCORR"]
    )

    rain_df = pd.DataFrame(
        [
            {
                "DATE": pd.to_datetime(date_string),
                "RAINFALL_MM": max(float(value), 0.0)
            }
            for date_string, value in rainfall.items()
        ]
    )

    if rain_df.empty:
        return 0.0, 0.0, 0.0

    rain_df = rain_df.sort_values("DATE")

    # ========================================================
    # RAINFALL 1 DAY
    # ========================================================

    rain_1d = rain_df.loc[
        rain_df["DATE"] == event_date,
        "RAINFALL_MM"
    ].sum()

    # ========================================================
    # RAINFALL 7 DAYS
    # ========================================================

    rain_7d_start = (
        event_date - timedelta(days=6)
    )

    rain_7d = rain_df.loc[
        rain_df["DATE"].between(
            rain_7d_start,
            event_date
        ),
        "RAINFALL_MM"
    ].sum()

    # ========================================================
    # RAINFALL 30 DAYS
    # ========================================================

    rain_30d_start = (
        event_date - timedelta(days=29)
    )

    rain_30d = rain_df.loc[
        rain_df["DATE"].between(
            rain_30d_start,
            event_date
        ),
        "RAINFALL_MM"
    ].sum()

    return (
        round(float(rain_1d), 2),
        round(float(rain_7d), 2),
        round(float(rain_30d), 2)
    )


# ============================================================
# PROCESS FIRE EVENTS
# ============================================================

results = []

total = len(df)

for i, (_, row) in enumerate(df.iterrows(), start=1):

    event_id = row.get(
        "FIRE_EVENT_ID",
        row.get(
            "fire_event_id",
            f"FE-{i:04d}"
        )
    )

    lat = float(row[lat_col])
    lon = float(row[lon_col])

    event_date = pd.Timestamp(
        row[date_col]
    ).normalize()

    print(
        f"[{i}/{total}] "
        f"{event_id} | "
        f"{event_date.strftime('%Y-%m-%d')} | "
        f"{lat:.5f}, {lon:.5f}"
    )

    try:

        rain_1d, rain_7d, rain_30d = get_rainfall(
            lat,
            lon,
            event_date
        )

        print(
            f"    Rain 1D : {rain_1d:.2f} mm"
        )

        print(
            f"    Rain 7D : {rain_7d:.2f} mm"
        )

        print(
            f"    Rain 30D: {rain_30d:.2f} mm"
        )

        results.append({
            "FIRE_EVENT_ID": event_id,
            "EVENT_DATE": event_date.strftime("%Y-%m-%d"),
            "LATITUDE": lat,
            "LONGITUDE": lon,
            "RAINFALL_1D_MM": rain_1d,
            "RAINFALL_7D_MM": rain_7d,
            "RAINFALL_30D_MM": rain_30d,
            "RAINFALL_STATUS": "SUCCESS"
        })

    except Exception as e:

        print(
            f"    ERROR: {e}"
        )

        results.append({
            "FIRE_EVENT_ID": event_id,
            "EVENT_DATE": event_date.strftime("%Y-%m-%d"),
            "LATITUDE": lat,
            "LONGITUDE": lon,
            "RAINFALL_1D_MM": None,
            "RAINFALL_7D_MM": None,
            "RAINFALL_30D_MM": None,
            "RAINFALL_STATUS": "ERROR"
        })


# ============================================================
# SAVE OUTPUT
# ============================================================

rainfall_df = pd.DataFrame(results)

OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True
)

rainfall_df.to_csv(
    OUTPUT_FILE,
    index=False
)

# ============================================================
# SUMMARY
# ============================================================

success_count = (
    rainfall_df["RAINFALL_STATUS"]
    == "SUCCESS"
).sum()

error_count = (
    rainfall_df["RAINFALL_STATUS"]
    == "ERROR"
).sum()

print()
print("=" * 60)
print("RAINFALL PROCESS COMPLETED")
print("=" * 60)

print(f"Total events : {len(rainfall_df)}")
print(f"Success      : {success_count}")
print(f"Errors       : {error_count}")
print(f"Output       : {OUTPUT_FILE}")

print()
print("Preview:")

print(
    rainfall_df.head(10).to_string(
        index=False
    )
)
