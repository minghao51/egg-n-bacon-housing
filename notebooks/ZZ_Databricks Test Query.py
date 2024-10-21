# Databricks notebook source
# MAGIC %md
# MAGIC # Databricks test query on Databricks serving model

# COMMAND ----------

# MAGIC %md
# MAGIC ## AI Query

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

# MAGIC %md
# MAGIC ## Raw OopenAI

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

# MAGIC %md ## VectorSearch

# COMMAND ----------

from langchain_databricks import DatabricksVectorSearch

vector_store = DatabricksVectorSearch(index_name="<YOUR_VECTOR_SEARCH_INDEX_NAME>")
retriever = vector_store.as_retriever(search_kwargs={"k": 5})
retriever.invoke("What is Databricks?")


# COMMAND ----------

# MAGIC %md ## ChatDatabricks

# COMMAND ----------

# MAGIC %pip install --upgrade langchain-databricks langchain

# COMMAND ----------

from langchain_databricks import ChatDatabricks

chat_model = ChatDatabricks(
    endpoint="dbrx1", #"databricks-meta-llama-3-1-70b-instruct"
    temperature=0.1,
    max_tokens=250,
)
chat_model.invoke("How to use Databricks?")


# COMMAND ----------


