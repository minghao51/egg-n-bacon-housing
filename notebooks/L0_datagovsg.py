# ---
# This is a test comment to verify jupytext sync
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.19.0
# ---

# %%
# import polars as pl
import json

# Test comment for jupytext sync verification
# Add src directory to path for imports
import pathlib
import re
import sys

import pandas as pd
import requests

sys.path.append(str(pathlib.Path(__file__).parent.parent / 'src'))

from data_helpers import save_parquet

# %% [markdown]
# # Custom scripts
# - scripts to retrive additional page with consideration for total records

# %%
def fetch_data(url: str, dataset_id: str) -> pd.DataFrame:
    """
    Fetches data from the Data.gov.sg API and returns a concatenated DataFrame.

    Args:
        url (str): The base URL for the API request.
        dataset_id (str): The ID of the dataset to fetch.

    Returns:
        pd.DataFrame: A concatenated DataFrame containing the fetched data.
    """
    _response_agg = []  # Initialize an empty list to store the DataFrames
    offset_value = 0  # Initialize the offset value
    total_records = 0  # Initialize the total records count

    while True:
        try:
            # Send a GET request to the API
            response = requests.get(url+dataset_id)
            response_text = json.loads(response.text)

            # Append the fetched data to the list
            _response_agg.append(pd.DataFrame.from_dict(response_text['result']['records']))

            # Check if there's a next page
            if 'next' not in response_text['result']['_links'].keys():
                break

            # Update the URL for the next page
            url = 'https://data.gov.sg' + response_text['result']['_links']['next']

            # Update the offset value and total records count
            match = re.search(r'offset=(\d+)', url)
            offset_value = int(match.group(1))
            total_records = response_text['result']['total']
            # print(total_records)

            # Break if the offset value exceeds the total records count
            if offset_value > total_records:
                break
        except Exception as e:
            print(f"Error: {e}")
            break

    # Concatenate the DataFrames
    if len(_response_agg) == 0:
        print(f"Warning: No data fetched for dataset {dataset_id}")
        return pd.DataFrame()  # Return empty DataFrame

    df = pd.concat(_response_agg, ignore_index=True)

    return df


# %% [markdown]
# # Data Gov Sg data

# %% [markdown]
# ## Private Residential Property Transactions in Rest of Central Region, Quarterly
# ### New Launch/Resale/SubSale Counts
# - https://data.gov.sg/datasets/d_5785799d63a9da091f4e0b456291eeb8/view

# %%
property_transasctions = fetch_data(
    url="https://data.gov.sg/api/action/datastore_search?resource_id=",
    dataset_id="d_5785799d63a9da091f4e0b456291eeb8"
    )
if not property_transasctions.empty:
    save_parquet(property_transasctions, "raw_datagov_general_sale", source="data.gov.sg API")

# %% [markdown]
# ### Private Residential Property Rental Index , (Base Quarter 2009-Q1 = 100), Quarterly
# - https://data.gov.sg/datasets/d_8e4c50283fb7052a391dfb746a05c853/view

# %%
rental_index = fetch_data(
    url="https://data.gov.sg/api/action/datastore_search?resource_id=",
    dataset_id="d_8e4c50283fb7052a391dfb746a05c853"
    )
if not rental_index.empty:
    save_parquet(rental_index, "raw_datagov_rental_index", source="data.gov.sg API")

# %% [markdown]
# ### Private Residential Property Price Index (Base Quarter 2009-Q1 = 100), Quarterly
# - https://data.gov.sg/datasets/d_97f8a2e995022d311c6c68cfda6d034c/view

# %%
price_index = fetch_data(
    url="https://data.gov.sg/api/action/datastore_search?resource_id=",
    dataset_id="d_97f8a2e995022d311c6c68cfda6d034c"
    )
if not price_index.empty:
    save_parquet(price_index, "raw_datagov_price_index", source="data.gov.sg API")

# %% [markdown]
# ### Median Annual Value and Property Tax By Type of Private Residential Property
# - Median Annual Value and Property Tax
# - https://data.gov.sg/datasets/d_774a81df45dca33112e59207e6dae1af/view

# %%
median_val_property_tax = fetch_data(
    url="https://data.gov.sg/api/action/datastore_search?resource_id=",
    dataset_id="d_774a81df45dca33112e59207e6dae1af"
    )
if not median_val_property_tax.empty:
    save_parquet(median_val_property_tax, "raw_datagov_median_price_via_property_type", source="data.gov.sg API")

# %% [markdown]
# ### Private Residential Property Transactions in the Whole of Singapore, Quarterly
# - Private Residential Property Transactions
# - https://data.gov.sg/datasets/d_7c69c943d5f0d89d6a9a773d2b51f337/view

# %%
private_residential_transactions_whole = fetch_data(
    url="https://data.gov.sg/api/action/datastore_search?resource_id=",
    dataset_id="d_7c69c943d5f0d89d6a9a773d2b51f337"
    )
if not private_residential_transactions_whole.empty:
    save_parquet(private_residential_transactions_whole, "raw_datagov_private_transactions_property_type", source="data.gov.sg API")

# %% [markdown]
# ## Resale Flat Prices
# - https://data.gov.sg/collections/189/view
# - download manually, just converting it here

# %%
csv_base_path = pathlib.Path(__file__).parent.parent / 'data' / 'raw_data' / 'csv'
resale_prices_path = csv_base_path / 'ResaleFlatPrices'

# Load all CSV files from ResaleFlatPrices folder
resale_files = list(resale_prices_path.glob('*.csv'))
print(f"Found {len(resale_files)} resale flat price files")

resale_dfs = []
for file in resale_files:
    print(f"Loading: {file.name}")
    df = pd.read_csv(file)
    resale_dfs.append(df)

# Combine all resale data
resale_flat_all = pd.concat(resale_dfs, ignore_index=True)
print(f"Total resale records: {len(resale_flat_all)}")

# Convert remaining_lease from text format (e.g., "61 years 04 months") to numeric months
def convert_lease_to_months(lease_str):
    """Convert lease string like '61 years 04 months' to total months"""
    if pd.isna(lease_str):
        return None

    if isinstance(lease_str, (int, float)):
        return int(lease_str)

    # Parse format like "61 years 04 months" or "60 years" or "05 months"
    import re
    lease_str = str(lease_str).lower()

    years_match = re.search(r'(\d+)\s*years?', lease_str)
    months_match = re.search(r'(\d+)\s*months?', lease_str)

    years = int(years_match.group(1)) if years_match else 0
    months = int(months_match.group(1)) if months_match else 0

    return years * 12 + months

if 'remaining_lease' in resale_flat_all.columns:
    print("Converting 'remaining_lease' from text to months...")
    resale_flat_all['remaining_lease_months'] = resale_flat_all['remaining_lease'].apply(convert_lease_to_months)
    # Keep original column as string for reference, add numeric version
    resale_flat_all['remaining_lease'] = resale_flat_all['remaining_lease'].astype(str)
    print(f"Converted {resale_flat_all['remaining_lease_months'].notna().sum()} lease values")

save_parquet(resale_flat_all, "raw_datagov_resale_flat_all", source="data.gov.sg CSV (all files)")

# %%
# resale_flat_df = fetch_data(
#     url="https://data.gov.sg/api/action/datastore_search?resource_id=",
#     dataset_id="d_8b84c4ee58e3cfc0ece0d773c8ca6abc"
#     )

# %%
# Note: resale_flat_df variable not defined - data already saved as resale_flat_all above
# save_parquet(resale_flat_df, "raw_datagov_resale_flat_price_2017onwards", source="data.gov.sg API")

# %%
# Note: response variable not defined - commented out
# response.json()

# %%
resale_flat_df_jan2015 = fetch_data(
    url="https://data.gov.sg/api/action/datastore_search?resource_id=",
    dataset_id="d_ea9ed51da2787afaf8e51f827c304208"
    )

if not resale_flat_df_jan2015.empty:
    save_parquet(resale_flat_df_jan2015, "raw_datagov_resale_flat_price_2015_2016_api", source="data.gov.sg API")

# %% [markdown]
# ## Private Residential Property Transactions in Outside Central Region, Quarterly
# - https://data.gov.sg/datasets/d_1a7823f3d31e7db4b426833833762bab/view

# %%
private_residential_transactions_outside_central = fetch_data(
    url="https://data.gov.sg/api/action/datastore_search?resource_id=",
    dataset_id="d_1a7823f3d31e7db4b426833833762bab"
    )

# %% [markdown]
# ## Private Residential Property Transactions in Core Central Region, Quarterly
# - https://data.gov.sg/datasets/d_c287c8be114bfa7d055b27ab2c87de83/view

# %%
private_residential_transactions_central = fetch_data(
    url="https://data.gov.sg/api/action/datastore_search?resource_id=",
    dataset_id="d_c287c8be114bfa7d055b27ab2c87de83"
    )

# %% [markdown]
# ## Demand for Rental and Sold Flats
# - https://data.gov.sg/datasets/d_4b4ee36346b27fe35c529588900340b2/view

# %%
demand_rental_sold_flats = fetch_data(
    url="https://data.gov.sg/api/action/datastore_search?resource_id=",
    dataset_id="d_4b4ee36346b27fe35c529588900340b2"
    )

# %% [markdown]
# ## Number of Sold and Rented HDB Residential Units
# - https://data.gov.sg/datasets/d_67966e5fd5dce14cf9fa5f0bc5164faf/view

# %%
sold_rented_hdb = fetch_data(
    url="https://data.gov.sg/api/action/datastore_search?resource_id=",
    dataset_id="d_67966e5fd5dce14cf9fa5f0bc5164faf"
    )

# %% [markdown]
# ## Price Range of HDB Flats Offered
# - https://data.gov.sg/datasets/d_2d493bdcc1d9a44828b6e71cb095b88d/view

# %%
price_range_hdb = fetch_data(
    url="https://data.gov.sg/api/action/datastore_search?resource_id=",
    dataset_id="d_2d493bdcc1d9a44828b6e71cb095b88d"
    )

# %% [markdown]
# ## HDB Resale Price Index (1Q2009 = 100), Quarterly
# - https://data.gov.sg/datasets/d_14f63e595975691e7c24a27ae4c07c79/view

# %%
price_index_hdb = fetch_data(
    url="https://data.gov.sg/api/action/datastore_search?resource_id=",
    dataset_id="d_14f63e595975691e7c24a27ae4c07c79"
    )

# %% [markdown]
# ## Renting Out of Flats 2024 (CSV)
# - https://data.gov.sg/datasets/d_c9f57187485a850908655db0e8cfe651/view

# %%
renting_flats = fetch_data(
    url="https://data.gov.sg/api/action/datastore_search?resource_id=",
    dataset_id="d_c9f57187485a850908655db0e8cfe651"
    )
