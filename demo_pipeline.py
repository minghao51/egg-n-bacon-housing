#!/usr/bin/env python
"""
Demo: Simulated L0 → L1 → L2 pipeline

This demonstrates how the data pipeline works without requiring external API calls.
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config import Config
from src.data_helpers import save_parquet, load_parquet, list_datasets


def demo_l0_data_collection():
    """Simulate L0: Collect raw data."""
    print("\n" + "=" * 60)
    print("L0: DATA COLLECTION (Simulated)")
    print("=" * 60)

    # Simulate collecting raw housing data
    raw_data = pd.DataFrame({
        "property_id": ["P001", "P002", "P003", "P004", "P005"],
        "address": ["123 Main St", "456 Oak Ave", "789 Pine Rd", "321 Elm St", "654 Maple Dr"],
        "type": ["condo", "hdb", "condo", "hdb", "condo"],
        "price_sgd": [1500000, 650000, 1200000, 580000, 950000],
        "floor_size_sqft": [1200, 900, 1100, 850, 1000],
        "year_built": [2010, 1995, 2015, 1998, 2012],
        "latitude": [1.3521, 1.3522, 1.3523, 1.3524, 1.3525],
        "longitude": [103.8198, 103.8199, 103.8200, 103.8201, 103.8202],
        "source": ["mock_api"] * 5
    })

    print(f"📥 Collected {len(raw_data)} raw property records")
    print(f"   Columns: {list(raw_data.columns)}")
    print(f"\n   Sample data:")
    print(raw_data.head(2).to_string(index=False))

    # Save raw data
    save_parquet(raw_data, "demo_raw_properties", source="mock_data.gov.sg")

    print(f"\n✅ Saved to: demo_raw_properties")
    return raw_data


def demo_l1_processing(raw_data):
    """Simulate L1: Process and clean data."""
    print("\n" + "=" * 60)
    print("L1: DATA PROCESSING")
    print("=" * 60)

    # Simulate data processing
    processed = raw_data.copy()

    # Calculate price per sqft
    processed["price_per_sqft"] = processed["price_sgd"] / processed["floor_size_sqft"]

    # Calculate property age
    current_year = 2025
    processed["property_age_years"] = current_year - processed["year_built"]

    # Standardize property type
    processed["property_type"] = processed["type"].str.upper()

    # Add quality flags
    processed["is_new"] = processed["property_age_years"] <= 5
    processed["is_affordable"] = processed["price_per_sqft"] < 1000

    # Select relevant columns
    processed = processed[[
        "property_id",
        "property_type",
        "price_sgd",
        "floor_size_sqft",
        "price_per_sqft",
        "property_age_years",
        "is_new",
        "is_affordable",
        "latitude",
        "longitude"
    ]]

    print(f"🔧 Processed {len(processed)} records")
    print(f"   Added columns: price_per_sqft, property_age_years, is_new, is_affordable")
    print(f"\n   Sample processed data:")
    print(processed.head(2).to_string(index=False))

    # Save processed data
    save_parquet(processed, "demo_L1_processed_properties", source="demo_raw_properties")

    print(f"\n✅ Saved to: demo_L1_processed_properties")
    return processed


def demo_l2_feature_engineering(processed_data):
    """Simulate L2: Feature engineering."""
    print("\n" + "=" * 60)
    print("L2: FEATURE ENGINEERING")
    print("=" * 60)

    # Simulate feature engineering
    features = processed_data.copy()

    # Distance features (simulated)
    np.random.seed(42)
    features["distance_to_mrt_km"] = np.random.uniform(0.1, 2.0, len(features))
    features["distance_to_cbd_km"] = np.random.uniform(5.0, 20.0, len(features))

    # Amenity counts (simulated)
    features["schools_within_1km"] = np.random.randint(0, 5, len(features))
    features["malls_within_1km"] = np.random.randint(0, 3, len(features))

    # Price category
    features["price_category"] = pd.cut(
        features["price_per_sqft"],
        bins=[0, 800, 1200, float('inf')],
        labels=["Low", "Medium", "High"]
    )

    # Calculate a simple score
    features["desirability_score"] = (
        (features["schools_within_1km"] * 10) +
        (features["malls_within_1km"] * 15) -
        (features["distance_to_mrt_km"] * 20) +
        (100 if features["is_new"].any() else 0)
    )

    print(f"⭐ Engineered features for {len(features)} records")
    print(f"   Added features:")
    print(f"   - distance_to_mrt_km")
    print(f"   - distance_to_cbd_km")
    print(f"   - schools_within_1km")
    print(f"   - malls_within_1km")
    print(f"   - price_category")
    print(f"   - desirability_score")

    print(f"\n   Sample feature data:")
    print(features[["property_id", "price_per_sqft", "distance_to_mrt_km", "desirability_score"]].head(2).to_string(index=False))

    # Save feature data
    save_parquet(features, "demo_L2_features", source="demo_L1_processed_properties")

    print(f"\n✅ Saved to: demo_L2_features")
    return features


def demo_l3_analysis(features_data):
    """Simulate L3: Analysis insights."""
    print("\n" + "=" * 60)
    print("L3: ANALYSIS & INSIGHTS")
    print("=" * 60)

    # Calculate some statistics
    avg_price_per_sqft = features_data["price_per_sqft"].mean()
    avg_desirability = features_data["desirability_score"].mean()
    high_desirability_count = len(features_data[features_data["desirability_score"] > 100])

    print(f"📊 Analysis Results:")
    print(f"   Average price per sqft: ${avg_price_per_sqft:.2f}")
    print(f"   Average desirability score: {avg_desirability:.1f}")
    print(f"   High desirability properties: {high_desirability_count} ({high_desirability_count/len(features_data)*100:.0f}%)")

    # Price category distribution
    print(f"\n   Price Category Distribution:")
    for category in ["Low", "Medium", "High"]:
        count = len(features_data[features_data["price_category"] == category])
        pct = count / len(features_data) * 100
        print(f"   - {category}: {count} ({pct:.0f}%)")

    return {
        "avg_price_per_sqft": avg_price_per_sqft,
        "avg_desirability": avg_desirability,
        "high_desirability_pct": high_desirability_count / len(features_data) * 100
    }


def main():
    """Run the complete pipeline demo."""
    print("\n" + "=" * 60)
    print("🏠 DEMO: COMPLETE DATA PIPELINE")
    print("=" * 60)
    print("\nThis demo simulates the full L0 → L1 → L2 → L3 pipeline")
    print("without requiring external API calls.\n")

    # L0: Collection
    raw_data = demo_l0_data_collection()

    # L1: Processing
    processed_data = demo_l1_processing(raw_data)

    # L2: Feature Engineering
    feature_data = demo_l2_feature_engineering(processed_data)

    # L3: Analysis
    insights = demo_l3_analysis(feature_data)

    # Final summary
    print("\n" + "=" * 60)
    print("PIPELINE SUMMARY")
    print("=" * 60)

    datasets = list_datasets()
    demo_datasets = {k: v for k, v in datasets.items() if k.startswith("demo_")}

    print(f"\n📁 Datasets Created:")
    for name, info in demo_datasets.items():
        print(f"   - {name}")
        print(f"     Rows: {info['rows']}")
        print(f"     Source: {info['source']}")

    print(f"\n✅ Pipeline Complete!")
    print(f"   Total datasets: {len(demo_datasets)}")
    print(f"   Total records processed: {len(feature_data)}")

    print(f"\n💡 To load these datasets later:")
    print(f"   from src.data_helpers import load_parquet")
    print(f"   df = load_parquet('demo_L2_features')")

    print("\n" + "=" * 60)
    print("Demo successful! 🎉")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
