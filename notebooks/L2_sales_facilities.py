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

# %%
import sys

import geopandas as gpd
import h3
import numpy as np
import pandas as pd
from shapely.geometry import Polygon

# Add src directory to path for imports
import pathlib
sys.path.append(str(pathlib.Path(__file__).parent.parent / 'src'))

import json
import os

from dotenv import load_dotenv
load_dotenv()

# %% [markdown]
# # OneMap
# %%
import requests

from data_helpers import load_parquet, save_parquet

# Try to use existing token from .env
access_token = os.environ.get('ONEMAP_TOKEN')

if access_token:
    # Decode JWT to check expiration
    try:
        parts = access_token.split('.')
        if len(parts) == 3:
            import base64
            import time
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
# # Data Input

# %%
# planning area
data_base_path = pathlib.Path(__file__).parent.parent / 'data'
planning_area_path = data_base_path / "raw_data" / "onemap_planning_area_polygon.shp"

if planning_area_path.exists():
    planning_area_gpd = gpd.read_file(planning_area_path)
else:
    print(f"Warning: {planning_area_path} not found. Skipping planning area data.")
    planning_area_gpd = None

# transactions
condo_df = load_parquet("L1_housing_condo_transaction")
ec_df = load_parquet("L1_housing_ec_transaction")
hdb_df = load_parquet("L1_housing_hdb_transaction")

# processsed data
unique_df = load_parquet("L2_housing_unique_searched")
amenity_df = load_parquet("L1_amenity")

# filter for only first result from onemap then
unique_df = unique_df.loc[unique_df['search_result'] == 0]
unique_df = unique_df.rename({'LATITUDE': 'lat', 'LONGITUDE': 'lon'}, axis=1)
unique_df['lat'] = unique_df['lat'].astype(float)
unique_df['lon'] = unique_df['lon'].astype(float)

# unique name for ec, condo and hdb
condo_df['unique_name'] = condo_df['Project Name'] + \
    ' ' + condo_df['Street Name']
ec_df['unique_name'] = ec_df['Project Name'] + ' ' + ec_df['Street Name']
hdb_df['unique_name'] = hdb_df['block'] + ' ' + hdb_df['street_name']

# %%
# unique_df

# %%
# geojson
park_path = data_base_path / "L1" / "park.geojson"
park_connector_path = data_base_path / "L1" / "park_connector.geojson"
waterbody_path = data_base_path / "L1" / "waterbody.geojson"

if park_path.exists():
    park_df = gpd.read_file(park_path)
else:
    print(f"Warning: {park_path} not found. Skipping park data.")
    park_df = None

if park_connector_path.exists():
    park_connecter_df = gpd.read_file(park_connector_path)
else:
    print(f"Warning: {park_connector_path} not found. Skipping park connector data.")
    park_connecter_df = None

if waterbody_path.exists():
    waterbody_df = gpd.read_file(waterbody_path)
else:
    print(f"Warning: {waterbody_path} not found. Skipping waterbody data.")
    waterbody_df = None

# %%
sqm_2_sqrt = 10.764


# %% [markdown]
# # Casting

# %%
# ameneties_h12grid = [h3.latlng_to_cell(x,y, 13)  for x,y in zip(amenity_df['lat'], amenity_df['lon'])]

# %%
def generate_h3_grid_cell(lat, lon, resolution=8):
    """Generate H3 grid cell from lat/lon coordinates."""
    return h3.latlng_to_cell(lat, lon, resolution)


def generate_grid_disk(cell, k=5):
    """Generate H3 grid disk from a cell."""
    return h3.grid_disk(cell, k)


def generate_polygon_from_cells(cells):
    """Generate Shapely Polygon from H3 cells."""
    return Polygon(h3.cells_to_geo(cells)['coordinates'][0])


def generate_polygons(unique_df):
    """
    Generate polygons from unique_df's lat/lon coordinates.

    Parameters:
    unique_df (pandas.DataFrame): DataFrame containing 'lat' and 'lon' columns.

    Returns:
    list[shapely.Polygon]: List of polygons.
    """
    return [
        generate_polygon_from_cells(generate_grid_disk(
            generate_h3_grid_cell(lat, lon), 3))
        for lat, lon in zip(unique_df['lat'], unique_df['lon'])
    ]


# %% [markdown]
# # Data Processing Prep

# %%
polygon_list = generate_polygons(unique_df)
unique_gdf = gpd.GeoDataFrame(unique_df, geometry=polygon_list)
unique_gdf = unique_gdf.drop('search_result', axis=1)
unique_gdf = unique_gdf.set_crs('EPSG:4326')

# %%
# checks

# len(unique_gdf['SEARCHVAL'].unique())

# unique_tmp = unique_gdf.copy()
# unique_tmp['SEARCHVAL'] = unique_tmp['SEARCHVAL'].str.lower()
# unique_tmp.columns = unique_tmp.columns.str.lower()
# mask = unique_tmp['searchval'].str.contains('prive', case=False, na=False)
# unique_tmp[mask]

# %%
amenity_gdf = gpd.GeoDataFrame(
    amenity_df,
    geometry=gpd.points_from_xy(amenity_df.lon, amenity_df.lat),
    crs="EPSG:4326"  # Coordinate Reference System
)

# %%
# Comment
# some properties contain a list of postcode instead of a single
# 828816, 828817 etc are all prive, punggol

# %% [markdown]
# ## Properties vs Amenity

# %%
unique_gdf = unique_gdf.to_crs(crs=3857)
amenity_gdf = amenity_gdf.to_crs(crs=3857)

# create copy of geometry
amenity_gdf['amenity_centroid'] = amenity_gdf.geometry


# sjoin
unique_joined = (
    unique_gdf[['SEARCHVAL', 'POSTAL', 'geometry']].drop_duplicates()
    .sjoin(amenity_gdf[['type', 'name', 'geometry', 'amenity_centroid']].drop_duplicates())
    .drop('index_right', axis=1)
)

unique_gdf = unique_gdf.to_crs(crs='EPSG:4326')
amenity_gdf = amenity_gdf.to_crs(crs='EPSG:4326')

# unique_joined = unique_joined.to_crs(crs=3857)
unique_joined["polygon_centroid"] = unique_joined["geometry"].centroid
# unique_joined = unique_joined.to_crs('EPSG:4326')

# add distance calculation
unique_joined['distance'] = unique_joined['polygon_centroid'].distance(
    unique_joined['amenity_centroid'])

# %%
unique_joined['SEARCHVAL'] = unique_joined['SEARCHVAL'].str.lower()
unique_joined.columns = unique_joined.columns.str.lower()

# %%
# len(unique_joined['searchval'].unique())
# some properties are missing, or they dont have anything nearby....

# %% [markdown]
# ## Properties vs Planning area

# %%
planning_area_gpd = planning_area_gpd.set_crs(crs='EPSG:4326')
planning_area_gpd = planning_area_gpd.rename(
    {'pln_area_n': 'planning_area'}, axis=1)

# centroid
unique_gdf = unique_gdf.to_crs(crs=3857)
unique_gdf["geometry"] = unique_gdf["geometry"].centroid
unique_gdf = unique_gdf.to_crs(crs='EPSG:4326')

unique_gdf = (
    unique_gdf
    .sjoin(planning_area_gpd, how='left', predicate='within')  # d
    .drop('index_right', axis=1)
)

# %% [markdown]
# # Post processing

# %%

# Function to extract commencing year and calculate years left


def extract_lease_info(lease_info):
    # Extract the number of years and the commencing year
    if lease_info == 'freehold' or lease_info == 'Freehold':
        return None, 'freehold'
    else:
        years = int(lease_info.split(' ')[0])
        commencing_year = int(lease_info.split(' ')[-1])

    # Calculate the remaining years
    # current_year = datetime.now().year
    # years_left = years - (current_year - commencing_year)

    return commencing_year, 'leasehold'


# %%
def extract_two_digits(string):
    """Extracts the first two digits from a string of the format "a to b".

    Args:
        string: The input string.

    Returns:
        The first two digits extracted from the string.
    """

    # Split the string into two parts based on "to"
    digits_parts = string.split(" to ")

    return (digits_parts[0], digits_parts[1])


# %% [markdown]
# ## Transactions

# %%
private_df = pd.concat([condo_df, ec_df])
private_df.columns = (private_df.columns
                      # Replace text in brackets with underscore
                      .str.replace(r'\((.*?)\)', r'_\1', regex=True)
                      # Remove the last bracket
                      .str.replace(r'\)$', '', regex=True)
                      # Remove special characters
                      .str.replace(r'[^a-zA-Z0-9_]', '', regex=True)
                      .str.replace(r'_$', '', regex=True)
                      .str.lower()
                      )


private_df = private_df.drop(
    ['nettprice', 'numberofunits', 'typeofarea', 'typeofsale'], axis=1)

private_df[['lease_start_yr', 'hold_type']] = private_df['tenure'].apply(
    lambda x: pd.Series(extract_lease_info(x)))


# Convert the 'Date' column to datetime
private_df['saledate'] = pd.to_datetime(
    private_df['saledate'], format='%b-%y').dt.date

# private_df['area_sqft'] = private_df['area_sqft'].astype(float)

numerical_cast_dict = {'transactedprice': int,
                       'unitprice_psf': int, 'unitprice_psm': int, 'area_sqft': float}
# 'lease_start_yr':int

for key, val in numerical_cast_dict.items():
    private_df[key] = private_df[key].str.replace(',', '').astype(val)

private_df['propertytype'] = private_df['propertytype'].replace(
    'Apartment', 'Condominium')
private_df['property_type'] = 'Private'

cat_cast_list = ['marketsegment', 'propertytype', 'hold_type']
for col in cat_cast_list:
    private_df[col] = private_df[col].astype('category')

# Replace '-' with a meaningful category, if needed
private_df['floorlevel'] = private_df['floorlevel'].replace('-', 'Unknown')
# Fitler for the 3 odd records
private_df = private_df.loc[private_df['floorlevel'] != 'Unknown']
# Convert the 'Range' column to categorical
private_df['floorlevel'] = private_df['floorlevel'].astype('category')

private_df = private_df.rename(
    {'unique_name': 'property_index', 'projectname': 'project_name',
     'saledate': 'transaction_date', 'lease_start_yr': 'lease_commence_date',
     'floorlevel': 'floor_level', 'streetname': 'street_name',
     'propertytype': 'property_sub_type', 'transactedprice': 'resale_price'}, axis=1)

str_cast_list = ['project_name', 'street_name', 'property_index']
for col in str_cast_list:
    private_df[col] = private_df[col].astype('string')

private_df['area_sqft'] = pd.to_numeric(
    private_df['area_sqft'], errors='coerce')
# Fill NaN values in 'area_sqm' with calculated values from 'area_sqft'
private_df['area_sqm'] = private_df.apply(
    lambda row: row['area_sqft'] / 10.7639 if pd.isna(row['area_sqm']) else row['area_sqm'], axis=1)

private_df['lease_commence_date'] = private_df['lease_commence_date'].astype(
    'Int64')

private_df[['floor_low', 'floor_high']] = [
    extract_two_digits(i) for i in private_df['floor_level']]
private_df['property_sub_type'] = private_df['property_sub_type'].str.lower()

private_df = private_df.drop(
    ['tenure', 'marketsegment', 'postaldistrict', 'unitprice_psm'], axis=1)

# %%
# Column Renaming
hdb_df = hdb_df.rename(columns={
    'month': 'transaction_date',
    'unique_name': 'property_index',
    'floor_area_sqm': 'area_sqm',
    'storey_range': 'floor_level',
    'flat_type': 'property_sub_type',
    'block': 'project_name'
})

# String Lowercase Conversion
string_cols = ['floor_level', 'property_sub_type']
for col in string_cols:
    hdb_df[col] = hdb_df[col].str.lower()

# Numerical Data Type Conversion
numerical_cols = ['resale_price', 'area_sqm', 'remaining_lease_months', 'lease_commence_date']
hdb_df[numerical_cols] = hdb_df[numerical_cols].astype('int')

# Derived Columns
hdb_df['area_sqft'] = hdb_df['area_sqm'] * sqm_2_sqrt
hdb_df['transaction_date'] = pd.to_datetime(hdb_df['transaction_date'], format="%Y-%m").dt.date

# Categorical Data Type Conversion
categorical_cols = ['property_sub_type', 'flat_model', 'floor_level', 'town']
hdb_df[categorical_cols] = hdb_df[categorical_cols].astype('category')

# String Data Type Conversion
string_cols = ['street_name', 'property_index', 'project_name']
hdb_df[string_cols] = hdb_df[string_cols].astype('string')

# Add Constant Columns
hdb_df['property_type'] = 'HDB'
hdb_df['hold_type'] = 'leasehold'

# Extract Floor Levels (optional, assumes extract_two_digits function exists)
hdb_df[['floor_low', 'floor_high']] = [extract_two_digits(i) for i in hdb_df['floor_level']]

# Drop Unnecessary Columns
hdb_df = hdb_df.drop(['remaining_lease_months', 'town', 'flat_model'], axis=1)

# Calculate Unit Price Per Square Foot
hdb_df['unitprice_psf'] = hdb_df['resale_price'] / hdb_df['area_sqft']

# %%
transaction_sales = pd.concat([hdb_df, private_df])

# %% [markdown]
# ## Property

# %%
# Create a copy of the unique_gdf
property_df = unique_gdf.copy()

# Convert column names to lowercase and rename 'nameaddress' to 'property_id'
property_df.columns = property_df.columns.str.lower()
property_df = property_df.rename({'nameaddress': 'property_id'}, axis=1)

# Convert specific columns to string data type
str_cast_list = ['property_id', 'blk_no', 'road_name', 'building', 'address']
property_df[str_cast_list] = property_df[str_cast_list].astype('string')

# Convert 'postal' to numeric, handling errors
property_df['postal'] = pd.to_numeric(property_df['postal'], errors='coerce')

# Convert 'postal' to Int64 data type
property_df['postal'] = property_df['postal'].astype('Int64')

# Select specific columns
property_df = property_df[['property_id', 'blk_no', 'road_name', 'building', 'address', 'postal', 'planning_area', 'property_type']]

# %%
import random

# Define facilities list
facilities = ['bbq', 'gym', 'tennis court', 'sky terrace', 'jacuzzi', 'swimming pool', 'yoga corner', 'pavilion', 'fitness corner']

# Filter private properties
private_properties = property_df[property_df['property_type'] == 'private'][['property_id']]

# Assign random facilities
private_properties['facilities'] = [random.sample(facilities, np.random.randint(5,7)) for i in  range(len(private_properties))]

# Explode facilities into separate rows
private_facilities = private_properties.explode('facilities').reset_index(drop=True)

# %% [markdown]
# ## Nearby

# %%
nearby_df = unique_joined.copy()
nearby_df = nearby_df.rename(
    {'searchval': 'property_index', 'distance': 'distance_m'}, axis=1)
nearby_df = nearby_df[['property_index', 'type', 'name', 'distance_m']]
nearby_df['distance_m'] = nearby_df['distance_m'].astype('int32')

# %% [markdown]
# # Sales/Listing Data
# - creation from transacted data

# %%
frac = 0.8
replace = True
hdb_sales = (hdb_df.sort_values('transaction_date', ascending=False).groupby(
    'property_index').first().sample(frac=frac, replace=replace))

private_sales = (private_df.sort_values('transaction_date', ascending=False).groupby(
    'property_index').first().sample(frac=frac, replace=replace))

# %%
listing_sales = pd.concat([hdb_sales, private_sales])

# adding room no
# sg rooms are typically of 10-30sqm area
listing_sales['room_no'] = [
    i[0] if 'room' in i else 0 for i in listing_sales['property_sub_type']]
listing_sales['room_no'] = [x if x != 0 else np.clip(int(
    y/np.random.randint(15, 25)/sqm_2_sqrt), a_min=1, a_max=6) for x, y in zip(listing_sales['room_no'], listing_sales['area_sqft'])]
listing_sales['room_no'] = listing_sales['room_no'].astype('int')
# adding bathroom
listing_sales['bathroom_no'] = [np.clip(int(
    x/np.random.randint(35, 45)/sqm_2_sqrt), a_min=1, a_max=4) for x in listing_sales['area_sqft']]
listing_sales['bathroom_no'] = listing_sales['bathroom_no'].astype('int')
# floor
listing_sales['floor'] = [int(np.random.randint(x, y)) for x, y in zip(
    listing_sales['floor_low'], listing_sales['floor_high'])]
listing_sales['floor'] = listing_sales['floor'].astype('int')

listing_sales = listing_sales.drop(
    ['floor_low', 'floor_high', 'floor_level'], axis=1)

# %%
listing_sales[:5]  # ['floor'].value_counts()

# %% [markdown]
# # Output

# %%
save_parquet(property_df, "L3_property", source="L2 sales facilities")
save_parquet(private_facilities, "L3_private_property_facilities", source="L2 sales facilities")
# added town to the property table
save_parquet(nearby_df, "L3_property_nearby_facilities", source="L2 sales facilities")
# TODO maybe add walking est/time too
save_parquet(transaction_sales, "L3_property_transactions_sales", source="L2 sales facilities")
save_parquet(listing_sales, "L3_property_listing_sales", source="L2 sales facilities")
