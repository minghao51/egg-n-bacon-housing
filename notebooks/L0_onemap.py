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
# # To Ingest OneMap data via api
# - require .evn setup with onemap api

# %%
import os

from dotenv import load_dotenv

# Load the environment variables from .env file
load_dotenv()

# Now you can access the environment variable just like before

# %% [markdown]
# ## References
# - https://www.onemap.gov.sg/apidocs/apidocs

# %%
import json
import sys

import geopandas as gpd
import pandas as pd
import requests
from shapely.geometry import shape

# Add src directory to path for imports
sys.path.append('../src')

from data_helpers import save_parquet

# %% [markdown]
# # Acquiring token
# - Need to setup valid email and password in .env file

# %%

url = "https://www.onemap.gov.sg/api/auth/post/getToken"

payload = {
        "email": os.environ['ONEMAP_EMAIL'],
        "password": os.environ['ONEMAP_EMAIL_PASSWORD']
      }

response = requests.request("POST", url, json=payload)
access_token = json.loads(response.text)['access_token']
headers = {"Authorization": f"{access_token}"}

# %% [markdown]
# # One Map

# %% [markdown]
# # planning area polygon

# %%
year = "2024"
url = f"https://www.onemap.gov.sg/api/public/popapi/getAllPlanningarea?year={year}"
response = requests.request("GET", url, headers=headers)
print(response.text)


df = pd.DataFrame(json.loads(response.text)['SearchResults'])
df['geojson'] = [json.loads(i) for i in df['geojson']]
df['geometry'] = df['geojson'].apply(shape)
df = gpd.GeoDataFrame(df).set_geometry('geometry')
df = df.drop('geojson', axis=1)

df.to_file('../data/raw_data/onemap_planning_area_polygon.shp')
df.to_file('../data/raw_data/onemap_planning_area_polygon.geojson', driver='GeoJSON')

# %%
df = df.drop('geojson', axis=1)

# %% [markdown]
# # Names of planning area

# %%
import requests

url = "https://www.onemap.gov.sg/api/public/popapi/getPlanningareaNames?year=2023"
response = requests.request("GET", url, headers=headers)
df = pd.DataFrame(json.loads(response.text))
save_parquet(df, "raw_onemap_planning_area_names", source="onemap API")

# %%
planning_area_name_list = df['pln_area_n'].unique()

# %% [markdown]
# ## Work Income for household (monthly)
# - social economy for each planning area
# - would require additional query for each planning area

# %%
# Initialize an empty list to store the DataFrames
df_list = []

# Iterate through the planning_area_name_list
for i in planning_area_name_list:
    print(i)
    url = f"https://www.onemap.gov.sg/api/public/popapi/getHouseholdMonthlyIncomeWork?planningArea={i}&year=2020"
    response = requests.request("GET", url, headers=headers)
    try:
        df = pd.DataFrame(json.loads(response.text))
        # Append the DataFrame to the list
        df_list.append(df)
    except:
        print(f'failed to get for {i}')


# Concatenate the DataFrames in the list
df_concatenated = pd.concat(df_list, ignore_index=True)
save_parquet(df_concatenated, "raw_onemap_household_income", source="onemap API")

# %% [markdown]
# # Potential usage for realtime query

# %% [markdown]
# ## Planning Area Query
# - reverse query from lat long to planning area

# %%
import requests

url = "https://www.onemap.gov.sg/api/public/popapi/getPlanningarea?latitude=1.3&longitude=103.8&year=2019"

# headers = {"Authorization": "**********************"}

response = requests.request("GET", url, headers=headers)

print(response.text)

# %% [markdown]
# ## Age Data

# %%
import requests

url = "https://www.onemap.gov.sg/api/public/popapi/getPopulationAgeGroup?planningArea=Bedok&year=2020&gender=female"

headers = {"Authorization": "**********************"}

response = requests.request("GET", url, headers=headers)

print(response.text)

# %% [markdown]
# ## Dwelling type household data

# %%
import requests

url = "https://www.onemap.gov.sg/api/public/popapi/getTypeOfDwellingHousehold?planningArea=Bedok&year=202"

headers = {"Authorization": "**********************"}

response = requests.request("GET", url, headers=headers)

print(response.text)

# %%
val='31, punggol field'
url = f"https://www.onemap.gov.sg/api/common/elastic/search?searchVal={val}&returnGeom=Y&getAddrDetails=Y&pageNum=1"

response = requests.request("GET", url, headers=headers) #headers=headers

print(json.loads(response.text))
# print(response.text)
