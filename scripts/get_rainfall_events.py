import requests
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

# ============================================================
# RAINFALL PER FIRE EVENT - NASA POWER
# ============================================================

INPUT_FILE = Path("data/v2/processed/OKI_NASA_FIRMS_fire_events.csv")
OUTPUT_FILE = Path("data/v2/processed/OKI_fire_events_rainfall.csv")

print("=" * 60)
print("RAINFALL PER FIRE EVENT")
print("=" * 60)

# ------------------------------------------------------------
# LOAD FIRE EVENTS
# ------------------------------------------------------------

if not INPUT_FILE.exists():
    raise FileNotFoundError(f"File tidak ditemukan: {INPUT_FILE}")

df = pd.read_csv(INPUT_FILE)

print(f"Fire events loaded: {len(df)}")
print("Columns:")
print(df.columns.tolist())

# ------------------------------------------------------------
# DETECT COLUMN NAMES
# ------------------------------------------------------------

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

if not lat_col:
    raise RuntimeError("Kolom latitude tidak ditemukan.")

if not lon_col:
    raise RuntimeError("Kolom longitude tidak ditemukan.")

if not date_col:
    raise RuntimeError("Kolom tanggal tidak ditemukan.")

print()
print(f"Latitude column : {lat_col}")
print(f"Longitude column: {lon_col}")
print(f"Date column     : {date_col}")

# ------------------------------------------------------------
# CLEAN DATA
# ------------------------------------------------------------

df[lat_col] = pd.to_numeric(df[lat_col], errors="coerce")
df[lon_col] = pd.to_numeric(df[lon_col], errors="coerce")
df[date_col] = pd.to_datetime(df[date_col], errors="coerce")

df = df.dropna(
    subset=[lat_col, lon_col, date_col]
).copy()

# ------------------------------------------------------------
# NASA POWER FUNCTION
# ------------------------------------------------------------

def get_rainfall(lat, lon, event_date):

    start_date = event_date - timedelta(days=30)
    end_date = event_date

    url = (
        "https://power.larc.nasa.gov/api/temporal/daily/point"
        f"?parameters=PRECTOTCORR"
        f"&community=AG"
        f"&longitude={lon}"
        f"&latitude={lat}"
        f"&start={start_date.strftime('%Y%m%d')}"
        f"&end={end_date.strftime('%Y%m%d')}"
        f"&format=JSON"
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

    rainfall_values = []

    for date_string, value in rainfall.items():

        try:
            value = float(value)

            # NASA POWER missing value
            if value < 0:
                value = 0.0

            rainfall_values.append({
                "DATE": pd.to_datetime(date_string),
                "RAINFALL_MM": value
            })

        except (ValueError, TypeError):
            continue

    rain_df = pd.DataFrame(rainfall_values)

    if rain_df.empty:
        return 0.0, 0.0, 0.0

    rain_df = rain_df.sort_values("DATE")

    # Rainfall on event date
    rain_1d = rain_df[
        rain_df["DATE"] == event_date
    ]["RAINFALL_MM"].sum()

    # Last 7 days including event date
    rain_7d = rain_df[
        rain_df["DATE"] >= event_date - timedelta(days=6)
    ]["RAINFALL_MM"].sum()

    # Last 30 days including event date
    rain_30d = rain_df[
        rain_df["DATE"] >= event_date - timedelta(days=29)
    ]["RAINFALL_MM"].sum()

    return (
        round(float(rain_1d), 2),
        round(float(rain_7d), 2),
        round(float(rain_30d), 2)
    )


# ------------------------------------------------------------
# PROCESS EVENTS
# ------------------------------------------------------------

results = []

for i, row in df.iterrows():

    event_id = row.get(
        "FIRE_EVENT_ID",
        row.get("fire_event_id", f"FE-{i+1:04d}")
    )

    lat = row[lat_col]
    lon = row[lon_col]
    event_date = row[date_col].date()

    print(
        f"[{i+1}/{len(df)}] "
        f"{event_id} | "
        f"{event_date} | "
        f"{lat:.5f}, {lon:.5f}"
    )

    try:

        rain_1d, rain_7d, rain_30d = get_rainfall(
            lat,
            lon,
            event_date
        )

        results.append({
            "FIRE_EVENT_ID": event_id,
            "EVENT_DATE": event_date,
            "LATITUDE": lat,
            "LONGITUDE": lon,
            "RAINFALL_1D_MM": rain_1d,
            "RAINFALL_7D_MM": rain_7d,
            "RAINFALL_30D_MM": rain_30d
        })

    except Exception as e:

        print(f"  ERROR: {e}")

        results.append({
            "FIRE_EVENT_ID": event_id,
            "EVENT_DATE": event_date,
            "LATITUDE": lat,
            "LONGITUDE": lon,
            "RAINFALL_1D_MM": None,
            "RAINFALL_7D_MM": None,
            "RAINFALL_30D_MM": None
        })


# ------------------------------------------------------------
# SAVE
# ------------------------------------------------------------

rainfall_df = pd.DataFrame(results)

OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True
)

rainfall_df.to_csv(
    OUTPUT_FILE,
    index=False
)

print()
print("=" * 60)
print("SUCCESS")
print("=" * 60)

print(f"Output: {OUTPUT_FILE}")
print(f"Records: {len(rainfall_df)}")

print()
print(rainfall_df.head(10).to_string(index=False))
