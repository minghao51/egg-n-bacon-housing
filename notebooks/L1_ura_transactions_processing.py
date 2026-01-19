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

# Add src directory to path for imports
sys.path.append('../src')

from data_helpers import save_parquet

# %%
ec_list = [
    "URA_ResidentialTransaction_EC2020_20240917220317",
    "URA_ResidentialTransaction_EC2021_20240917220358",
    "URA_ResidentialTransaction_EC2022_20240917220420",
    "URA_ResidentialTransaction_EC2023_20240917220459",
    "URA_ResidentialTransaction_EC2024_20240917220523",
]

condo_list = [
    "URA_ResidentialTransaction_Conda2020_20240917220234",
    "URA_ResidentialTransaction_Conda2021_20240917220149",
    "URA_ResidentialTransaction_Conda2022_20240917220116",
    "URA_ResidentialTransaction_Conda2023_20240917215948",
    "URA_ResidentialTransaction_Condo2024_20240917215852",
]

hdb_list = [
    "ResaleFlatPricesBasedonRegistrationDateFromJan2015toDec2016",
    "ResaleflatpricesbasedonregistrationdatefromJan2017onwards",
]

# %%
ec_df = [pd.read_csv(f"../data/raw_data/csv/ura/{ec}.csv") for ec in ec_list]
ec_df = pd.concat(ec_df)
save_parquet(ec_df, "L1_housing_ec_transaction", source="URA CSV data")

# %%
condo_df = [
    pd.read_csv(f"../data/raw_data/csv/ura/{condo}.csv") for condo in condo_list
]
condo_df = pd.concat(condo_df)
condo_df['Area (SQM)'] = condo_df['Area (SQM)'].str.replace(
    ',', '').str.strip()
condo_df['Area (SQM)'] = pd.to_numeric(condo_df['Area (SQM)'], errors='coerce')
save_parquet(condo_df, "L1_housing_condo_transaction", source="URA CSV data")

# %%
import re

hdb_df = [pd.read_csv(f"../data/raw_data/csv/datagov/{hdb}.csv")
          for hdb in hdb_list]
hdb_df = pd.concat(hdb_df)


def standardize_lease_duration(lease):
    if isinstance(lease, int) or lease.isdigit():
        return int(lease) * 12  # assume months
    else:
        match = re.match(r'(\d+) years?\s*', lease)  # (\d+) months?
        if match:
            years = int(match.group(1))
            # months = int(match.group(2)) if match.group(2) else 0
            return years * 12  # + months
        else:
            return None  # or raise an exception


hdb_df['remaining_lease_months'] = hdb_df['remaining_lease'].apply(
    standardize_lease_duration)
hdb_df.drop('remaining_lease', axis=1, inplace=True)
save_parquet(hdb_df, "L1_housing_hdb_transaction", source="data.gov.sg CSV data")

# %% [markdown]
# # Combining to idenfity all unique condo and flats

# %%
condo_df['property_type'] = 'private'
ec_df['property_type'] = 'private'
hdb_df['property_type'] = 'hdb'


housing_df = pd.concat(
    [
        condo_df[["Project Name", "Street Name",
                  "property_type"]].drop_duplicates(),
        ec_df[["Project Name", "Street Name", 'property_type']].drop_duplicates(),
        hdb_df[["block", "street_name", 'property_type']].drop_duplicates(),
    ],
    ignore_index=True,
)

NameAddress_list = ["Project Name", "Street Name",
                    "block", "street_name"]
for i in NameAddress_list:
    housing_df[i] = housing_df[i].fillna("")
housing_df["NameAddress"] = housing_df[NameAddress_list].agg(" ".join, axis=1)
housing_df["NameAddress"] = [i.strip() for i in housing_df["NameAddress"]]

# %%
for search_string in housing_df['NameAddress'][:10]:
    print(search_string)

# %% [markdown]
# # OneMap Setup

# %%
import json
import os

import requests

url = "https://www.onemap.gov.sg/api/auth/post/getToken"

payload = {
    "email": os.environ['ONEMAP_EMAIL'],
    "password": os.environ['ONEMAP_EMAIL_PASSWORD']
}

response = requests.request("POST", url, json=payload)
access_token = json.loads(response.text)['access_token']
headers = {"Authorization": f"{access_token}"}

# %% [markdown]
# # Search for X, Y and other data on OneMap
# - this will take a while
# - with exponential backoff and limit to failure

# %%
import json

import pandas as pd
import requests
from tenacity import retry, wait_exponential

df_list = []
max_retries = 3
initial_backoff = 1  # seconds
max_backoff = 32  # seconds


@retry(wait=wait_exponential(multiplier=1, min=initial_backoff, max=max_backoff))
def fetch_data(search_string):
  url = f"https://www.onemap.gov.sg/api/common/elastic/search?searchVal={search_string}&returnGeom=Y&getAddrDetails=Y&pageNum=1"
  response = requests.get(url, headers=headers)
  response.raise_for_status()
  return pd.DataFrame(json.loads(response.text)['results']).reset_index().rename(
      {'index': 'search_result'}, axis=1)


failed_searches = []
for search_string in housing_df['NameAddress']:
  try:
    _df = fetch_data(search_string)
    _df['NameAddress'] = search_string
    df_list.append(_df)
  except requests.RequestException:
    failed_searches.append(search_string)
    print(f"Request failed for {search_string}. Skipping.")

if failed_searches:
  print(f"Failed to retrieve data for the following addresses after {max_retries} retries: {', '.join(failed_searches)}")

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
