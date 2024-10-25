# Databricks notebook source
# MAGIC %md # Use LangChain to interact with Spark DataFrames
# MAGIC
# MAGIC The following code showcases an example of the Spark DataFrame Agent.
# MAGIC
# MAGIC ## Requirements
# MAGIC
# MAGIC - To use this notebook, please provide your OpenAI API Token.
# MAGIC - Databricks Runtime 13.3 ML and above
# MAGIC

# COMMAND ----------

# MAGIC %md ## Install libraries
# MAGIC
# MAGIC Databricks recommends the latest version of `langchain` and the `databricks-sql-connector`.
# MAGIC

# COMMAND ----------

# MAGIC %pip install --upgrade langchain databricks-sql-connector
# MAGIC %pip install langchain-community
# MAGIC %pip install langchain_experimental
# MAGIC %pip install mlflow

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

# import os
# os.environ["OPENAI_API_KEY"] = ""

# COMMAND ----------

# MAGIC %md ## Spark DataFrame Agent
# MAGIC
# MAGIC The Spark DataFrame agent allows you to interact with a spark dataframe as needed. You simply call `create_spark_dataframe_agent` with an LLM and the dataframe in question.

# COMMAND ----------

from langchain.llms import OpenAI
# from langchain.agents import create_spark_dataframe_agent
from langchain_experimental.agents import create_spark_dataframe_agent

df = spark.read.csv("/databricks-datasets/COVID/coronavirusdataset/Region.csv", header=True, inferSchema=True)
display(df)

# COMMAND ----------

from langchain_community.llms import Databricks

# llm = OpenAI(temperature=0)
llm = Databricks(endpoint_name="dbrx1", extra_params={"temperature": 0.1, "max_tokens": 100})

agent = create_spark_dataframe_agent(llm=llm, df=df, verbose=True, allow_dangerous_code=True)

# COMMAND ----------

agent.run("How many rows are there?")
