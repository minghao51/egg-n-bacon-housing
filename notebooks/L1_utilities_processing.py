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
# # procesing all utilities with additional latlon and discard extra info

# %%
import sys

# import polars as pl
import geopandas as gpd
import pandas as pd
from bs4 import BeautifulSoup

# Add src directory to path for imports
import pathlib
sys.path.append(str(pathlib.Path(__file__).parent.parent / 'src'))

import json
import os

from dotenv import load_dotenv
load_dotenv()

# %% [markdown]
# ## OneMap
# %% [markdown]
# Create one map header
# %%
import requests

from data_helpers import load_parquet, save_parquet

# Try to use existing token from .env
access_token = os.environ.get('ONEMAP_TOKEN')

if access_token:
    # Decode JWT to check expiration
    try:
        import base64
        import time
        parts = access_token.split('.')
        if len(parts) == 3:
            payload = parts[1]
            payload += '=' * (4 - len(payload) % 4)
            decoded = base64.b64decode(payload)
            token_data = json.loads(decoded)

            current_time = time.time()
            if token_data.get('exp', 0) > current_time:
                print(f"✅ Using existing OneMap token from .env")
                print(f"   Token expires in: {(token_data.get('exp') - current_time) / 3600:.1f} hours")
                headers = {"Authorization": f"{access_token}"}
            else:
                print("⚠️  Token in .env has expired")
                access_token = None
        else:
            print("⚠️  Invalid token format")
            access_token = None
    except Exception as e:
        print(f"⚠️  Error decoding token: {e}")
        access_token = None

# Fallback: try to get new token (if email/password are configured)
if not access_token:
    print("Attempting to get new OneMap token...")
    url = "https://www.onemap.gov.sg/api/auth/post/getToken"

    payload = {
        "email": os.environ.get('ONEMAP_EMAIL'),
        "password": os.environ.get('ONEMAP_EMAIL_PASSWORD')
    }

    response = requests.request("POST", url, json=payload)
    print(f"API Response Status: {response.status_code}")

    if response.status_code == 200:
        response_data = json.loads(response.text)
        access_token = response_data.get('access_token')
        if access_token:
            print("✅ Successfully obtained new OneMap token")
            headers = {"Authorization": f"{access_token}"}
        else:
            print(f"❌ No access_token in response: {response.text}")
            raise KeyError("access_token not found in API response")
    else:
        print(f"❌ Failed to get token: {response.text}")
        raise Exception(f"Token request failed with status {response.status_code}")

# %% [markdown]
# # School

# %%
# config
school_query_onemap = False

# %%
import json
from random import uniform
from time import sleep

import requests
from tqdm import tqdm


def extract_df_data(school_df, search_cols, initial_backoff, max_retries, max_backoff, headers):
    """
    Extracts data from OneMap API for each search_cols in a pandas DataFrame.

    Args:
        school_df (pandas.DataFrame): DataFrame containing a column named 'postal_code'.
        initial_backoff (float): Initial delay for exponential backoff in seconds.
        max_retries (int): Maximum number of retries for failed requests.
        headers (dict): Dictionary containing headers for API requests.

    Returns:
        list: List of DataFrames containing extracted data for each successful request.
    """

    df_list = []
    for search_string in tqdm(school_df[search_cols], desc="Extracting Data"):
        retries = 0
        success = False
        backoff = initial_backoff

        while not success and retries < max_retries:
            try:
                url = f"https://www.onemap.gov.sg/api/common/elastic/search?searchVal={search_string}&returnGeom=Y&getAddrDetails=Y&pageNum=1"
                response = requests.get(url, headers=headers)
                # print(f"{search_string}")
                response.raise_for_status()  # Raise an exception for HTTP errors
                data = json.loads(response.text)
                _df = pd.DataFrame(data['results']).iloc[0:1]
                _df['NameAddress'] = search_string
                df_list.append(_df)
                success = True

            except:
                # print(f"No results found for postal code {search_string}. Retry.")
                retries += 1
                backoff = min(backoff * 2, max_backoff)  # Exponential backoff
                delay = backoff + uniform(0, 1)  # Add jitter to the delay
                print(
                    f"Request failed for {search_string}. Retrying in {delay:.2f} seconds. (Retry {retries}/{max_retries})")
                sleep(delay)

        if not success:
            print(
                f"Failed to retrieve data for {search_string} after {max_retries} retries.")

    return df_list


# %%
import json

import requests

# Define maximum retries and initial/maximum backoff times
max_retries = 3
initial_backoff = 1  # seconds
max_backoff = 32  # seconds


# %%
def get_school_data_from_onemap(school_df):
    """
    Retrieves school data from OneMap API for each postal code in the 'postal_code' column of the provided DataFrame.

    Args:
        school_df (pd.DataFrame): DataFrame containing a 'postal_code' column.

    Returns:
        pd.DataFrame: DataFrame containing school data, including 'name', 'lat', 'lon', etc.
    """
    df_list = extract_df_data(school_df,
                              search_cols='postal_code',
                              initial_backoff=initial_backoff,
                              max_retries=max_retries,
                              max_backoff=max_backoff,
                              headers=headers)
    if df_list:  # Check if any data was retrieved
        df_school = pd.concat(df_list).rename({
            'SEARCHVAL': 'name',
            'LATITUDE': 'lat',
            'LONGITUDE': 'lon',
            'POSTAL': 'postal',
            'ADDRESS': 'address'
        }, axis=1)
        df_school = df_school[['name', 'lat', 'lon', 'postal', 'address']]
        df_school['type'] = 'school'
        df_school['address'] = [i.lower() for i in df_school['address']]
        df_school['name'] = [i.lower() for i in df_school['name']]
    else:
        print("No school data retrieved from OneMap API.")

    return df_school


# %%
if school_query_onemap:
    school = pd.read_csv(
        "../data/raw_data/csv/datagov/Generalinformationofschools.csv")
    school_df = get_school_data_from_onemap(school)
    save_parquet(school_df, "L1_school_queried", source="onemap API")

else:
    # Read from parquet file if not querying OneMap API
    try:
        school_df = load_parquet("L1_school_queried")
        print("School data read from parquet file.")
    except ValueError:
        print("School data not found in metadata. Please ensure it exists or query OneMap API.")

# %% [markdown]
# # Mall

# %%
# config
mall_query_onemap = False

# %%
if mall_query_onemap:
    mall = load_parquet("raw_wiki_shopping_mall")
    df_list = extract_df_data(mall,
                              search_cols='shopping_mall',
                              initial_backoff=initial_backoff,
                              max_retries=max_retries,
                              max_backoff=max_backoff,
                              headers=headers)
    if df_list:  # Check if any data was retrieved
        df_mall = pd.concat(df_list).rename({
            'SEARCHVAL': 'name',
            'LATITUDE': 'lat',
            'LONGITUDE': 'lon',
            'POSTAL': 'postal',
            'ADDRESS': 'address'
        }, axis=1)
        df_mall = df_mall[['name', 'lat', 'lon', 'postal', 'address']]
        df_mall['type'] = 'mall'
        df_mall['address'] = [i.lower() for i in df_mall['address']]
        df_mall['name'] = [i.lower() for i in df_mall['name']]

        save_parquet(df_mall, "L1_mall_queried", source="onemap API")
else:
    df_mall = load_parquet("L1_mall_queried")

# %% [markdown]
# # Kindergardens, gym, hawker

# %%
import pandas as pd


def extract_html_name(html_str: str, name_search) -> str:
    """
    Extracts the name from an HTML string.

    Args:
        html_str (str): The HTML string to parse.

    Returns:
        str: The extracted name.
    """
    soup = BeautifulSoup(html_str, 'html.parser')
    name_cell = soup.find('th', string=name_search).find_next('td')
    name = name_cell.text.strip()
    return name


def parse_datagov_geojson(path: str, data_type: str, name_search: str = 'NAME') -> pd.DataFrame:
    """
    Parses a GeoJSON file and extracts relevant data.

    Args:
        path (str): The file path to the GeoJSON file.
        data_type (str): The type of data (e.g., "kindergardens").

    Returns:
        pd.DataFrame: A DataFrame with the extracted data.
    """
    df = gpd.read_file(path)
    df = df.to_crs('4326')
    df["lat"] = df['geometry'].y
    df["lon"] = df['geometry'].x
    df['type'] = data_type
    df['name'] = [extract_html_name(i, name_search) for i in df['Description']]
    return pd.DataFrame(df[['name', 'type', 'lat', 'lon']])


# %%
kindergarden_df = parse_datagov_geojson(
    "../data/raw_data/csv/datagov/Kindergartens.geojson", "kindergarden")

# %%
gym_df = parse_datagov_geojson(
    "../data/raw_data/csv/datagov/GymsSGGEOJSON.geojson", "gym")

# %%
hawker_df = parse_datagov_geojson(
    "../data/raw_data/csv/datagov/HawkerCentresGEOJSON.geojson", "hawker")

# %%
water_activities_df = parse_datagov_geojson(
    "../data/raw_data/csv/datagov/WaterActivitiesSG.geojson", "water_activities")

# %%
supermarket_df = parse_datagov_geojson(
    "../data/raw_data/csv/datagov/SupermarketsGEOJSON.geojson", "supermarket", "LIC_NAME")

# %%
preschool_df = parse_datagov_geojson(
    "../data/raw_data/csv/datagov/PreSchoolsLocation.geojson", "preschool", "CENTRE_NAME")

# %% [markdown]
# # park

# %%
df = gpd.read_file(
    "../data/raw_data/csv/datagov/NParksParksandNatureReserves.geojson")
df = df.set_crs(crs='epsg:4326')
df = df.to_crs(crs=3857)
df['lon'] = df.centroid.x
df['lat'] = df.centroid.y
df['type'] = 'park'
df['name'] = [extract_html_name(i, 'NAME') for i in df['Description']]
park_df = df[['name', 'type', 'lon', 'lat', 'geometry']]
park_df.to_file("../data/L1/park.geojson", driver='GeoJSON')

# %%
df = gpd.read_file(
    "../data/raw_data/csv/datagov/MasterPlan2019SDCPParkConnectorLinelayerGEOJSON.geojson")
park_connector_df = df.drop('Description', axis=1)
park_connector_df.to_file(
    "../data/L1/park_connector.geojson", driver='GeoJSON')

# %%
waterbody_df = gpd.read_file(
    "../data/raw_data/csv/datagov/MasterPlan2019SDCPWaterbodylayerKML.kml")
waterbody_df = waterbody_df.to_crs('3857')
waterbody_df['area_m'] = waterbody_df.geometry.area
waterbody_df = waterbody_df[waterbody_df['area_m'] >= 4000].reset_index()
waterbody_df = waterbody_df[['Name', 'geometry', 'area_m']]
save_parquet(waterbody_df, "L1_waterbody", source="datagov geojson")
waterbody_df.to_file("../data/L1/waterbody.geojson", driver='GeoJSON')

# %% [markdown]
# # Concat

# %%
df_combined = pd.concat([
    school_df[['name', 'type', 'lat', 'lon']],
    df_mall[['name', 'type', 'lat', 'lon']],
    kindergarden_df,
    gym_df,
    hawker_df,
    kindergarden_df,
    water_activities_df,
    supermarket_df,
    preschool_df
])

# %%
df_combined['lat'] = df_combined['lat'].astype('float')
df_combined['lon'] = df_combined['lon'].astype('float')

# %%
df_combined['type'].value_counts()

# %%
save_parquet(df_combined, "L1_amenity", source="L1 utilities processing")
