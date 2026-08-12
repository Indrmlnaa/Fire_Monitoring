import pandas as pd

INPUT_FILE = r"data\processed\OKI_NASA_FIRMS_fire_events.csv"

events = pd.read_csv(INPUT_FILE)

print()
print("========================================")
print("OKI FIRE EVENT SUMMARY")
print("========================================")

print("Total fire events:", len(events))

print()
print("Events per date:")
print(
    events["EVENT_DATE"]
    .value_counts()
    .sort_index()
)

print()
print("Priority:")
print(
    events["PRIORITY"]
    .value_counts()
)

print()
print("Detection count:")
print(
    events["DETECTION_COUNT"]
    .describe()
)

print()
print("Top 10 Fire Events:")
print(
    events.sort_values(
        ["PRIORITY", "DETECTION_COUNT"],
        ascending=[True, False]
    )
    .head(10)
    .to_string(index=False)
)

print()
print("========================================")
print("SUMMARY COMPLETE")
print("========================================")