import requests
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

# ============================================================
# NASA POWER RAINFALL TEST
# ============================================================

# OKI approximate center
LATITUDE = -3.33
LONGITUDE = 105.50

# Get last 30 days
END_DATE = datetime.utcnow().date()
START_DATE = END_DATE - timedelta(days=30)

url = (
    "https://power.larc.nasa.gov/api/temporal/daily/point"
    f"?parameters=PRECTOTCORR"
    f"&community=AG"
    f"&longitude={LONGITUDE}"
    f"&latitude={LATITUDE}"
    f"&start={START_DATE.strftime('%Y%m%d')}"
    f"&end={END_DATE.strftime('%Y%m%d')}"
    f"&format=JSON"
)

print("=" * 60)
print("NASA POWER RAINFALL TEST")
print("=" * 60)

print(f"Location : {LATITUDE}, {LONGITUDE}")
print(f"Period   : {START_DATE} → {END_DATE}")
print("Requesting NASA POWER...")

response = requests.get(url, timeout=60)
response.raise_for_status()

data = response.json()

rainfall = data["properties"]["parameter"]["PRECTOTCORR"]

df = pd.DataFrame(
    list(rainfall.items()),
    columns=["DATE", "RAINFALL_MM"]
)

df["DATE"] = pd.to_datetime(df["DATE"])
df["RAINFALL_MM"] = pd.to_numeric(
    df["RAINFALL_MM"],
    errors="coerce"
)

# Calculate rolling rainfall
df["RAINFALL_7D_MM"] = (
    df["RAINFALL_MM"]
    .rolling(7, min_periods=1)
    .sum()
)

df["RAINFALL_30D_MM"] = (
    df["RAINFALL_MM"]
    .rolling(30, min_periods=1)
    .sum()
)

# Output
output_dir = Path("data/v2/processed")
output_dir.mkdir(parents=True, exist_ok=True)

output_file = output_dir / "OKI_NASA_POWER_rainfall.csv"

df.to_csv(output_file, index=False)

print()
print("=" * 60)
print("SUCCESS")
print("=" * 60)

print(df.tail(10))

print()
print(f"Saved to: {output_file}")
print(f"Records : {len(df)}")
