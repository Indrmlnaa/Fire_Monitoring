import pandas as pd
import numpy as np
from sklearn.cluster import DBSCAN
import os

INPUT_FILE = r"data\processed\OKI_NASA_FIRMS_spatial_analysis.csv"
OUTPUT_FILE = r"data\processed\OKI_NASA_FIRMS_fire_events.csv"

# Parameter clustering
DISTANCE_KM = 2.0
TIME_WINDOW_DAYS = 1

# Load data
df = pd.read_csv(INPUT_FILE)

# Hanya hotspot yang benar-benar berada di OKI
df = df[df["INSIDE_OKI"] == "YES"].copy()

df["acq_date"] = pd.to_datetime(df["acq_date"])

print()
print("========================================")
print("FIRE EVENT CLUSTERING")
print("========================================")
print("Inside OKI detections:", len(df))

if df.empty:
    print("Tidak ada detection di dalam OKI.")
    raise SystemExit

# ------------------------------------------------------------
# CLUSTER PER HARI
# ------------------------------------------------------------

events = []
event_counter = 1

for date, group in df.groupby("acq_date"):

    group = group.copy()

    coords = np.radians(
        group[["latitude", "longitude"]].values
    )

    # 2 km radius
    eps = DISTANCE_KM / 6371.0088

    clustering = DBSCAN(
        eps=eps,
        min_samples=1,
        metric="haversine"
    )

    labels = clustering.fit_predict(coords)

    group["cluster"] = labels

    for cluster_id, cluster in group.groupby("cluster"):

        lat = cluster["latitude"].mean()
        lon = cluster["longitude"].mean()

        sensors = sorted(
            cluster["sensor"]
            .dropna()
            .unique()
        )

        max_frp = cluster["frp"].max()

        distance_boundary = cluster[
            "DISTANCE_BOUNDARY_KM"
        ].min()

        detection_count = len(cluster)

        # Priority sederhana
        if max_frp >= 50 or detection_count >= 5:
            priority = "HIGH"
        elif max_frp >= 10 or detection_count >= 2:
            priority = "MONITORING"
        else:
            priority = "LOW"

        events.append({
            "FIRE_EVENT_ID":
                f"FE-{event_counter:04d}",

            "EVENT_DATE":
                date.strftime("%Y-%m-%d"),

            "LATITUDE":
                round(lat, 6),

            "LONGITUDE":
                round(lon, 6),

            "DETECTION_COUNT":
                detection_count,

            "DETECTED_BY":
                ", ".join(sensors),

            "MAX_FRP_MW":
                round(max_frp, 2),

            "DISTANCE_BOUNDARY_KM":
                round(distance_boundary, 3),

            "PRIORITY":
                priority
        })

        event_counter += 1

# ------------------------------------------------------------
# OUTPUT
# ------------------------------------------------------------

events_df = pd.DataFrame(events)

events_df.to_csv(
    OUTPUT_FILE,
    index=False
)

print()
print("========================================")
print("FIRE EVENT CLUSTERING COMPLETE")
print("========================================")

print(
    "Satellite detections:",
    len(df)
)

print(
    "Unique fire events:",
    len(events_df)
)

print()
print("Priority:")
print(
    events_df["PRIORITY"].value_counts()
)

print()
print("Output:")
print(OUTPUT_FILE)

print()
print(
    events_df.head(20).to_string(index=False)
)