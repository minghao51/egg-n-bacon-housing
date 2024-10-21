# Databricks notebook source
# MAGIC %md
# MAGIC # Read data from s3 to upload to databricks catalog
# MAGIC - Required to be run in databricks env

# COMMAND ----------

parquet_list = ["https://public-git-data.s3.amazonaws.com/public/private_property_facilities.parquet",
"https://public-git-data.s3.amazonaws.com/public/property_listing_sales.parquet",
"https://public-git-data.s3.amazonaws.com/public/property_nearby_facilities.parquet",
"https://public-git-data.s3.amazonaws.com/public/property_transactions_sales.parquet",
"https://public-git-data.s3.amazonaws.com/public/property.parquet"]

# COMMAND ----------

import os

file_names = [os.path.basename(url).split('.')[0] for url in parquet_list]
file_names

# COMMAND ----------

import pandas as pd

for url, name in zip(parquet_list, file_names):
    print(name)
    df_pandas = pd.read_parquet(url)
    df = spark.createDataFrame(df_pandas)
    df.write.saveAsTable(f"default.{name}")
