#!/usr/bin/env python
"""
Guide to running the real data pipeline with actual API calls.

This script will help you run the L0 → L1 → L2 notebooks with real data.
"""

import sys
import subprocess
from pathlib import Path

def check_env_setup():
    """Check if .env is configured."""
    print("=" * 60)
    print("STEP 1: Check Environment Setup")
    print("=" * 60)
    print()

    env_file = Path(".env")
    if not env_file.exists():
        print("❌ .env file not found!")
        print("   Please run: cp .env.example .env")
        print("   Then edit .env with your API keys")
        return False

    print("✅ .env file found")

    # Check if API keys are set
    with open(env_file) as f:
        content = f.read()

    required_keys = {
        "ONEMAP_EMAIL": False,
        "GOOGLE_API_KEY": False
    }

    for key in required_keys:
        if key in content and len(content.split(key + "=")[1].strip()) > 10:
            required_keys[key] = True

    all_set = all(required_keys.values())

    if not all_set:
        print("\n⚠️  The following API keys need to be set in .env:")
        for key, set_flag in required_keys.items():
            status = "✅" if set_flag else "❌"
            print(f"   {status} {key}")
        print()
        print("Please edit .env and add your API keys:")
        print("1. ONEMAP_EMAIL - Register at https://www.onemap.gov.sg/apidocs/register")
        print("2. ONEMAP_EMAIL_PASSWORD - Your OneMap password")
        print("3. GOOGLE_API_KEY - Get from https://makersuite.google.com/app/apikey")
        print()
        response = input("Press Enter once you've added the API keys (or 'q' to quit): ")
        if response.lower() == 'q':
            return False
    else:
        print("✅ All required API keys are set")

    print()
    return True


def run_l0_notebooks():
    """Run L0 data collection notebooks."""
    print("=" * 60)
    print("STEP 2: Run L0 Data Collection Notebooks")
    print("=" * 60)
    print()

    notebooks = [
        ("L0_datagovsg.ipynb", "Collect data from data.gov.sg API"),
        ("L0_onemap.ipynb", "Collect data from OneMap API"),
        ("L0_wiki.ipynb", "Scrape Wikipedia for shopping malls"),
    ]

    print("This will collect raw data from external APIs:")
    for i, (nb, desc) in enumerate(notebooks, 1):
        print(f"{i}. {nb}")
        print(f"   {desc}")

    print()
    response = input("Run L0 notebooks now? (y/n): ")

    if response.lower() == 'y':
        for nb, desc in notebooks:
            print(f"\n{'=' * 60}")
            print(f"Running {nb}...")
            print(f"{'=' * 60}")
            print(f"Description: {desc}")
            print()

            # Run the paired .py file
            py_file = Path("notebooks") / nb.replace(".ipynb", ".py")
            if py_file.exists():
                result = subprocess.run(
                    ["uv", "run", "python", str(py_file)],
                    capture_output=False
                )
                if result.returncode == 0:
                    print(f"✅ {nb} completed")
                else:
                    print(f"❌ {nb} failed")
                    return False
            else:
                print(f"⚠️  {py_file} not found, skipping")

        print()
        print("✅ L0 data collection complete!")
        return True
    else:
        print("Skipping L0 notebooks")
        return True


def run_l1_notebooks():
    """Run L1 data processing notebooks."""
    print("\n" + "=" * 60)
    print("STEP 3: Run L1 Data Processing Notebooks")
    print("=" * 60)
    print()

    notebooks = [
        ("L1_ura_transactions_processing.ipynb", "Process URA transaction data"),
        ("L1_utilities_processing.ipynb", "Process utilities and amenities data"),
    ]

    print("This will process and clean the raw data:")
    for i, (nb, desc) in enumerate(notebooks, 1):
        print(f"{i}. {nb}")
        print(f"   {desc}")

    print()
    response = input("Run L1 notebooks now? (y/n): ")

    if response.lower() == 'y':
        for nb, desc in notebooks:
            print(f"\n{'=' * 60}")
            print(f"Running {nb}...")
            print(f"{'=' * 60}")
            print(f"Description: {desc}")
            print()

            py_file = Path("notebooks") / nb.replace(".ipynb", ".py")
            if py_file.exists():
                result = subprocess.run(
                    ["uv", "run", "python", str(py_file)],
                    capture_output=False
                )
                if result.returncode == 0:
                    print(f"✅ {nb} completed")
                else:
                    print(f"❌ {nb} failed")
                    return False
            else:
                print(f"⚠️  {py_file} not found, skipping")

        print()
        print("✅ L1 data processing complete!")
        return True
    else:
        print("Skipping L1 notebooks")
        return True


def run_l2_notebooks():
    """Run L2 feature engineering notebooks."""
    print("\n" + "=" * 60)
    print("STEP 4: Run L2 Feature Engineering Notebooks")
    print("=" * 60)
    print()

    notebooks = [
        ("L2_sales_facilities.ipynb", "Engineer features and create final datasets"),
    ]

    print("This will create features for ML/analysis:")
    for i, (nb, desc) in enumerate(notebooks, 1):
        print(f"{i}. {nb}")
        print(f"   {desc}")

    print()
    response = input("Run L2 notebooks now? (y/n): ")

    if response.lower() == 'y':
        for nb, desc in notebooks:
            print(f"\n{'=' * 60}")
            print(f"Running {nb}...")
            print(f"{'=' * 60}")
            print(f"Description: {desc}")
            print()

            py_file = Path("notebooks") / nb.replace(".ipynb", ".py")
            if py_file.exists():
                result = subprocess.run(
                    ["uv", "run", "python", str(py_file)],
                    capture_output=False
                )
                if result.returncode == 0:
                    print(f"✅ {nb} completed")
                else:
                    print(f"❌ {nb} failed")
                    return False
            else:
                print(f"⚠️  {py_file} not found, skipping")

        print()
        print("✅ L2 feature engineering complete!")
        return True
    else:
        print("Skipping L2 notebooks")
        return True


def show_results():
    """Show pipeline results."""
    print("\n" + "=" * 60)
    print("PIPELINE RESULTS")
    print("=" * 60)
    print()

    try:
        from src.data_helpers import list_datasets
        import json

        datasets = list_datasets()

        if not datasets:
            print("⚠️  No datasets found. Pipeline may not have run yet.")
            return

        print(f"📊 Total datasets: {len(datasets)}")
        print()

        # Group by level
        l0_datasets = {k: v for k, v in datasets.items() if k.startswith("raw_")}
        l1_datasets = {k: v for k, v in datasets.items() if k.startswith("L1_")}
        l2_datasets = {k: v for k, v in datasets.items() if k.startswith("L2_") or k.startswith("L3_")}

        if l0_datasets:
            print("L0 (Raw Data):")
            for name, info in l0_datasets.items():
                print(f"  - {name}: {info['rows']} rows")

        if l1_datasets:
            print("\nL1 (Processed):")
            for name, info in l1_datasets.items():
                print(f"  - {name}: {info['rows']} rows")

        if l2_datasets:
            print("\nL2/L3 (Features):")
            for name, info in l2_datasets.items():
                print(f"  - {name}: {info['rows']} rows")

        print()
        print("✅ Pipeline complete!")

    except Exception as e:
        print(f"❌ Error loading results: {e}")


def main():
    """Main execution."""
    print("\n" + "=" * 60)
    print("🏠 REAL DATA PIPELINE EXECUTION")
    print("=" * 60)
    print()
    print("This guide will help you run the actual pipeline with API calls.")
    print()

    # Check environment
    if not check_env_setup():
        print("\n❌ Environment not configured. Exiting.")
        return 1

    # Ask if user wants to continue
    print("\n" + "=" * 60)
    print("READY TO RUN PIPELINE")
    print("=" * 60)
    print()
    print("The pipeline will:")
    print("1. L0: Collect data from data.gov.sg, OneMap, Wikipedia")
    print("2. L1: Process and clean the data")
    print("3. L2: Engineer features for analysis")
    print()
    print("⏱️  Estimated time: 10-30 minutes (depends on API rate limits)")
    print()

    response = input("Continue? (y/n): ")
    if response.lower() != 'y':
        print("Exiting...")
        return 0

    # Run pipeline
    success = True
    success = run_l0_notebooks() and success
    success = run_l1_notebooks() and success
    success = run_l2_notebooks() and success

    # Show results
    if success:
        show_results()

    print()
    print("=" * 60)
    print("Pipeline execution complete!")
    print("=" * 60)
    print()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
