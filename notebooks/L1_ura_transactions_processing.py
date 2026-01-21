# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.19.0
#   kernelspec:
#     display_name: demo
#     language: python
#     name: python3
# ---

# %% [markdown]
# # procesing all housing with additional latlon and discard extra info

# %%
import sys
import pandas as pd
import pathlib
import os
from dotenv import load_dotenv

# Add src directory to path for imports
sys.path.append(str(pathlib.Path(__file__).parent.parent / 'src'))

load_dotenv()

from data_helpers import save_parquet
from geocoding import load_ura_files, extract_unique_addresses, setup_onemap_headers, fetch_data

# %%
# Load all URA and HDB transaction files using shared function
csv_base_path = pathlib.Path(__file__).parent.parent / 'data' / 'raw_data' / 'csv'
ec_df, condo_df, residential_df, hdb_df = load_ura_files(csv_base_path)

# Save individual transaction datasets
save_parquet(ec_df, "L1_housing_ec_transaction", source="URA CSV data")
save_parquet(condo_df, "L1_housing_condo_transaction", source="URA CSV data")
save_parquet(residential_df, "L1_housing_residential_transaction", source="URA CSV data")
save_parquet(hdb_df, "L1_housing_hdb_transaction", source="data.gov.sg CSV data")

# %% [markdown]
# # Combining to idenfity all unique condo and flats

# %%
# Extract unique addresses using shared function
housing_df = extract_unique_addresses(ec_df, condo_df, residential_df, hdb_df)

# Display first 10 addresses
for search_string in housing_df['NameAddress'][:10]:
    print(search_string)

# %% [markdown]
# # OneMap Setup

# %%
# Setup OneMap authentication using shared function
headers = setup_onemap_headers()

# %% [markdown]
# # Search for X, Y and other data on OneMap
# - this will take a while
# - with exponential backoff and limit to failure

# %%
import pandas as pd
import requests

df_list = []
failed_searches = []
total_addresses = len(housing_df['NameAddress'])
print(f"Starting geocoding for {total_addresses} unique addresses...")
print("This may take 30+ minutes due to API rate limiting")

for i, search_string in enumerate(housing_df['NameAddress'], 1):
  try:
    # Use fetch_data from shared geocoding module
    _df = fetch_data(search_string, headers)
    _df['NameAddress'] = search_string
    df_list.append(_df)

    # Print progress every 50 addresses
    if i % 50 == 0:
      print(f"Progress: {i}/{total_addresses} addresses ({i/total_addresses*100:.1f}%)")

  except requests.RequestException:
    failed_searches.append(search_string)
    print(f"❌ Request failed for {search_string}. Skipping.")

print(f"✅ Completed geocoding: {len(df_list)}/{total_addresses} successful")

if failed_searches:
  print(f"⚠️  Failed to retrieve data for {len(failed_searches)} addresses")

# %%
# import time
# import random

# for search_string in housing_df['NameAddress']:
#     retries = 0
#     success = False
#     backoff = initial_backoff

#     while not success and retries < max_retries:
#         try:
#             url = f"https://www.onemap.gov.sg/api/common/elastic/search?searchVal={search_string}&returnGeom=Y&getAddrDetails=Y&pageNum=1"
#             response = requests.request("GET", url, headers=headers)
#             response.raise_for_status()  # Raise an exception for HTTP errors

#             _df = pd.DataFrame(json.loads(response.text)['results']).reset_index().rename(
#                 {'index': 'search_result'}, axis=1)
#             _df['NameAddress'] = search_string
#             df_list.append(_df)

#             success = True

#         except requests.RequestException as e:
#             retries += 1
#             backoff = min(backoff * 2, max_backoff)  # Exponential backoff
#             # Add some jitter to the delay
#             delay = backoff + random.uniform(0, 1)
#             print(
#                 f"Request failed for {search_string}. Retrying in {delay:.2f} seconds. (Retry {retries}/{max_retries})")
#             time.sleep(delay)

#     if not success:
#         print(
#             f"Failed to retrieve data for {search_string} after {max_retries} retries.")

# %%
# Concatenate the dataframes
df_housing_searched = pd.concat(df_list)

# Save the full dataset
save_parquet(df_housing_searched, "L2_housing_unique_full_searched", source="L1 transaction data")

# Filter for search_result == 0 and reset index
df_housing_searched_selected = df_housing_searched[df_housing_searched['search_result'] == 0].reset_index(drop=True)

# Add the 'property_type' column
df_housing_searched_selected['property_type'] = housing_df['property_type']

# Save the filtered dataset
save_parquet(df_housing_searched_selected, "L2_housing_unique_searched", source="L2 housing data")
