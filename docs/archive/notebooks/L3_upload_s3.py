# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.19.0
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %%
# from bs4 import BeautifulSoup
import sys

# Add src directory to path for imports
sys.path.append('../src')

from data_helpers import load_parquet

# %%
load_parquet("L3_property")

# %%
import boto3
from botocore.exceptions import NoCredentialsError


def upload_files_to_s3(file_list, local_path, bucket_name, s3_path):
    """
    Upload a list of files to an S3 bucket.
    
    Args:
    file_list (list): List of file names to upload.
    local_path (str): Local directory path where files are stored.
    bucket_name (str): Name of the S3 bucket.
    s3_path (str): Path within the S3 bucket to store files.
    
    Returns:
    None
    """
    # Initialize a session using Amazon S3
    s3 = boto3.client('s3')

    for file_name in file_list:
        local_file_path = f"{local_path}{file_name}"
        s3_file_path = f"{s3_path}{file_name}"

        try:
            s3.upload_file(local_file_path, bucket_name, s3_file_path)
            print(f"Upload Successful: {file_name}")
        except FileNotFoundError:
            print(f"File not found: {local_file_path}")
        except NoCredentialsError:
            print("AWS credentials not available")
            break
        except Exception as e:
            print(f"An error occurred while uploading {file_name}: {str(e)}")

# Configuration
l3_file_list = [
    'private_property_facilities.parquet',
    'property_listing_sales.parquet',
    'property_nearby_facilities.parquet',
    'property_transactions_sales.parquet',
    'property.parquet'
]
l3_path = '../data/L3/'
bucket_name = 'public-git-data'
s3_path = 'public/'

# Upload files
upload_files_to_s3(l3_file_list, l3_path, bucket_name, s3_path)

# %%
for file_name in l3_file_list:
    print(f"https://{bucket_name}.s3.amazonaws.com/{path_name}{file_name}")

# %%
import os

from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_KEY')
supabase = create_client(supabase_url, supabase_key)

def upload_to_supabase(df, table_name):
    """
    Upload a DataFrame to Supabase.

    Args:
    df (pandas.DataFrame): DataFrame to upload.
    table_name (str): Name of the table in Supabase.

    Returns:
    None
    """
    try:
        # Convert DataFrame to list of dictionaries
        data = df.to_dict('records')

        # Upload data to Supabase
        response = supabase.table(table_name).insert(data).execute()

        print(f"Successfully uploaded {len(data)} rows to {table_name}")
    except Exception as e:
        print(f"An error occurred while uploading to {table_name}: {str(e)}")

# Configuration
l3_dataset_list = [
    'L3_private_property_facilities',
    'L3_property_listing_sales',
    'L3_property_nearby_facilities',
    'L3_property_transactions_sales',
    'L3_property'
]

# Upload each dataset to Supabase
for dataset_name in l3_dataset_list:
    # Load the dataset
    df = load_parquet(dataset_name)

    # Generate table name (remove L3_ prefix and replace underscores with hyphens)
    table_name = dataset_name.replace('L3_', '').replace('_', '-')

    # Upload to Supabase
    upload_to_supabase(df, table_name)

print("All datasets have been uploaded to Supabase.")
