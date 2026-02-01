#!/usr/bin/env python3
"""Fix school distances to be in meters instead of radians."""

import pandas as pd
from scipy.spatial import cKDTree
from math import radians, cos, sin, asin, sqrt

def radians_to_meters(radians_val):
    return radians_val * 6371000

# Load property data
df = pd.read_parquet('data/pipeline/L3/housing_unified.parquet')

# Load schools
schools_df = pd.read_parquet('data/pipeline/raw_datagov_school_directory.parquet')

# Geocode schools
schools_df["latitude"] = None
schools_df["longitude"] = None

import requests
import time

for idx, row in schools_df.iterrows():
    postal_code = row.get("postal_code")
    if postal_code:
        try:
            url = "https://www.onemap.gov.sg/api/common/elastic/search"
            params = {"searchVal": str(postal_code).strip(), "returnGeom": "Y", "getAddrDetails": "Y", "pageNum": 1}
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            if data.get("found", 0) > 0:
                result = data["results"][0]
                schools_df.at[idx, "latitude"] = float(result["LATITUDE"])
                schools_df.at[idx, "longitude"] = float(result["LONGITUDE"])
        except Exception as e:
            pass
        time.sleep(0.1)

print(f"Geocoded {schools_df['latitude'].notna().sum()}/{len(schools_df)} schools")

# Build combined school tree
schools_geo = schools_df.dropna(subset=["latitude", "longitude"]).copy()
coords = list(zip(schools_geo["latitude"], schools_geo["longitude"]))
tree = cKDTree(coords)

print(f"Total schools in tree: {len(coords)}")

# Convert distances for PRIMARY
primary_schools = schools_geo[schools_geo["mainlevel_code"] == "PRIMARY"]
if len(primary_schools) > 0:
    primary_coords = list(zip(primary_schools["latitude"], primary_schools["longitude"]))
    primary_tree = cKDTree(primary_coords)
    
    # Get current distances (in radians)
    current_dists = df["nearest_school_PRIMARY_dist"].values
    
    # Re-calculate for a sample to verify
    sample_props = df.dropna(subset=["lat", "lon"]).head(100)
    new_dists_radians, _ = primary_tree.query(sample_props[["lat", "lon"]].values, k=1)
    new_dists_meters = [radians_to_meters(d) for d in new_dists_radians]
    
    print(f"Sample old distances (radians): {current_dists[:3]}")
    print(f"Sample new distances (meters): {new_dists_meters[:3]}")
    
    # Update all distances in dataframe
    properties_with_coords = df.dropna(subset=["lat", "lon"]).copy()
    all_dists_radians, _ = primary_tree.query(properties_with_coords[["lat", "lon"]].values, k=1)
    
    # Convert to meters and update
    for idx, (row_idx, row) in enumerate(properties_with_coords.iterrows()):
        df.at[row_idx, "nearest_school_PRIMARY_dist"] = radians_to_meters(all_dists_radians[idx])
    
    print(f"Updated {len(properties_with_coords)} PRIMARY distances to meters")

# Save updated dataframe
df.to_parquet('data/pipeline/L3/housing_unified.parquet', compression='snappy', index=False)
print("Saved updated data")
