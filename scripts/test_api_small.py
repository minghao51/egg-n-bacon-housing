#!/usr/bin/env python3
"""
Quick test to verify OneMap API is working with a small sample.

This tests:
1. Authentication setup
2. API connectivity
3. Successful response parsing
4. Error handling

Usage:
    uv run python scripts/test_api_small.py
"""

import sys
import pathlib
from datetime import datetime

# Add src directory to path
sys.path.append(str(pathlib.Path(__file__).parent.parent / 'src'))

from geocoding import setup_onemap_headers, fetch_data, load_ura_files, extract_unique_addresses


def main():
    """Test OneMap API with a small sample of addresses."""
    print("=" * 80)
    print("🧪 OneMap API Connectivity Test")
    print("=" * 80)
    print()

    # Setup authentication
    print("1️⃣  Testing OneMap authentication...")
    try:
        headers = setup_onemap_headers()
        print("   ✅ Authentication successful")
        print()
    except Exception as e:
        print(f"   ❌ Authentication failed: {e}")
        return False

    # Load a small sample of addresses
    print("2️⃣  Loading sample addresses...")
    try:
        csv_base_path = pathlib.Path(__file__).parent.parent / 'data' / 'raw_data' / 'csv'
        ec_df, condo_df, residential_df, hdb_df = load_ura_files(csv_base_path)
        housing_df = extract_unique_addresses(ec_df, condo_df, residential_df, hdb_df)

        # Test with first 10 addresses
        test_df = housing_df.head(10)
        print(f"   ✅ Loaded {len(test_df)} test addresses")
        print()
    except Exception as e:
        print(f"   ❌ Failed to load addresses: {e}")
        return False

    # Test API calls
    print("3️⃣  Testing API calls...")
    print(f"   Processing {len(test_df)} addresses...")
    print()

    success_count = 0
    fail_count = 0

    for i, row in test_df.iterrows():
        search_string = row['NameAddress']

        try:
            print(f"   [{i+1}/{len(test_df)}] Testing: {search_string[:60]}...")

            # Add timeout to test
            import requests
            from tenacity import retry, wait_exponential

            url = f"https://www.onemap.gov.sg/api/common/elastic/search?searchVal={search_string}&returnGeom=Y&getAddrDetails=Y&pageNum=1"

            # Set timeout
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            data = response.json()

            if 'results' in data and len(data['results']) > 0:
                print(f"      ✅ Found {len(data['results'])} result(s)")
                success_count += 1
            else:
                print(f"      ⚠️  No results found")
                success_count += 1  # API call succeeded, just no results

        except requests.exceptions.Timeout:
            print(f"      ❌ TIMEOUT after 10 seconds")
            fail_count += 1
        except requests.RequestException as e:
            print(f"      ❌ Request failed: {e}")
            fail_count += 1
        except Exception as e:
            print(f"      ❌ Unexpected error: {e}")
            fail_count += 1

        # Small delay between requests
        import time
        time.sleep(1)

    # Summary
    print()
    print("=" * 80)
    print("📊 Test Results Summary")
    print("=" * 80)
    print(f"Total tested: {len(test_df)} addresses")
    print(f"✅ Successful: {success_count} ({success_count/len(test_df)*100:.1f}%)")
    print(f"❌ Failed: {fail_count} ({fail_count/len(test_df)*100:.1f}%)")
    print()

    if fail_count == 0:
        print("🎉 All tests passed! OneMap API is working correctly.")
        print()
        print("✅ Ready to resume geocoding:")
        print("   uv run python scripts/geocode_addresses.py")
        return True
    else:
        print("⚠️  Some tests failed. Check errors above.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
