# Databricks notebook source
# MAGIC %md
# MAGIC # Databricks test query on Databricks serving model

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT ai_query(
# MAGIC     'dbrx1',
# MAGIC     'Describe Databricks SQL in 30 words.'
# MAGIC   ) AS summary
# MAGIC
# MAGIC   -- "Databricks SQL is a cloud-based platform for data analytics and machine learning, providing a unified workspace for collaborative data exploration, analysis, and visualization using SQL queries."
# MAGIC

# COMMAND ----------

# MAGIC %pip install openai
# MAGIC %pip install --upgrade typing_extensions

# COMMAND ----------

# MAGIC %restart_python

# COMMAND ----------

from openai import OpenAI
import os

# How to get your Databricks token: https://docs.databricks.com/en/dev-tools/auth/pat.html
# DATABRICKS_TOKEN = os.environ.get('DATABRICKS_TOKEN')
# Alternatively in a Databricks notebook you can use this:
DATABRICKS_TOKEN = dbutils.notebook.entry_point.getDbutils().notebook().getContext().apiToken().get()

client = OpenAI(
  api_key=DATABRICKS_TOKEN,
  base_url="https://dbc-0a534b63-c06b.cloud.databricks.com/serving-endpoints"
)

chat_completion = client.chat.completions.create(
  messages=[
  {
    "role": "system",
    "content": "You are an AI assistant"
  },
  {
    "role": "user",
    "content": "What are you"
  }
  ],
  model="dbrx1",
  max_tokens=256
)

print(chat_completion.choices[0].message.content)

# COMMAND ----------

# from openai import OpenAI
# # %pip install --upgrade typing_extensions
# import os

# # How to get your Databricks token: https://docs.databricks.com/en/dev-tools/auth/pat.html
# # DATABRICKS_TOKEN = os.environ.get('DATABRICKS_TOKEN')
# # Alternatively in a Databricks notebook you can use this:
# DATABRICKS_TOKEN = dbutils.notebook.entry_point.getDbutils().notebook().getContext().apiToken().get()

# # client = OpenAI(
# #   api_key=DATABRICKS_TOKEN,
# #   base_url="https://dbc-0a534b63-c06b.cloud.databricks.com/serving-endpoints/dbrx1/invocations"
# # )

# client = OpenAI(
#   api_key=DATABRICKS_TOKEN,
#   base_url="https://dbc-0a534b63-c06b.cloud.databricks.com/serving-endpoints"
# )
# completions = client.completions.create(
#   prompt='Write 3 reasons why you should train an AI model on domain specific data sets?',
#   model="dbrx1",
#   max_tokens=128
# )

# print(completions.choices[0].text)

# COMMAND ----------


