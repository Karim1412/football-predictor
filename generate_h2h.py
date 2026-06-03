"""
Run this in Colab AFTER your feature engineering cells.
It generates h2h_data.json covering ALL team pairs from your dataset.

Cell to add in Colab:
    !python generate_h2h.py
    # Then download h2h_data.json and place it in football_predictor/models/
"""
import pandas as pd
import json
from collections import defaultdict

print("Loading dataset...")
df = pd.read_csv("featured_football_2026.csv", parse_dates=["Date"])
df = df.sort_values("Date").reset_index(drop=True)

# Keep only needed cols
needed = ["Date","League","Season","HomeTeam","AwayTeam","FTHG","FTAG","Result"]
df = df[[c for c in needed if c in df.columns]].dropna(subset=["HomeTeam","AwayTeam","FTHG","FTAG"])
df["FTHG"] = df["FTHG"].astype(int)
df["FTAG"] = df["FTAG"].astype(int)

print(f"Total matches: {len(df):,}")
print(f"Date range: {df.Date.min().date()} → {df.Date.max().date()}")

# Build H2H dict: key = "TeamA|TeamB" (sorted alphabetically)
h2h = defaultdict(list)

for _, row in df.iterrows():
    ht, at = row.HomeTeam, row.AwayTeam
    key = "|".join(sorted([ht, at]))
    h2h[key].append({
        "date":  row.Date.strftime("%b %d, %Y"),
        "home":  ht,
        "away":  at,
        "hs":    int(row.FTHG),
        "as":    int(row.FTAG),
        "league": str(row.get("League",""))
    })

# Keep last 8 matches per pair (most recent first)
h2h_trimmed = {}
for key, matches in h2h.items():
    h2h_trimmed[key] = matches[-8:]  # already sorted by date

print(f"H2H pairs: {len(h2h_trimmed):,}")

# Also build team list with their last known league
teams = {}
for _, row in df.sort_values("Date").iterrows():
    teams[row.HomeTeam] = str(row.get("League",""))
    teams[row.AwayTeam] = str(row.get("League",""))

output = {
    "h2h": h2h_trimmed,
    "teams": teams,
    "generated": pd.Timestamp.now().strftime("%Y-%m-%d"),
    "total_matches": len(df),
    "date_range": f"{df.Date.min().date()} to {df.Date.max().date()}"
}

with open("h2h_data.json","w") as f:
    json.dump(output, f, separators=(",",":"))

import os
size_kb = os.path.getsize("h2h_data.json")/1024
print(f"\n✓ h2h_data.json saved ({size_kb:.0f} KB)")
print(f"  Teams: {len(teams)}")
print(f"  H2H pairs: {len(h2h_trimmed)}")
print("\nDownload h2h_data.json from the Files panel and place it in:")
print("  football_predictor/models/h2h_data.json")
