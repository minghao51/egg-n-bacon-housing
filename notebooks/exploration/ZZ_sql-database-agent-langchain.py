# Databricks notebook source
# MAGIC %md # Use Langchain to interact with a SQL database
# MAGIC
# MAGIC The following code showcases an example of the Databricks SQL Agent. With the Databricks SQL agent any Databricks users can interact with a specified schema in Databrick Unity Catalog and generate insights on their data.
# MAGIC
# MAGIC ## Requirements
# MAGIC
# MAGIC - To use this notebook, please provide your OpenAI API Token.
# MAGIC - Databricks Runtime 13.3 ML and above

# COMMAND ----------

# https://docs.databricks.com/_extras/notebooks/source/machine-learning/large-language-models/sql-database-agent-langchain.html

# COMMAND ----------

# MAGIC %md ### Imports
# MAGIC
# MAGIC Databricks recommends the latest version of `langchain` and the `databricks-sql-connector`.

# COMMAND ----------

# MAGIC %pip install --upgrade langchain databricks-sql-connector
# MAGIC %pip install --upgrade langchain-databricks langchain
# MAGIC %pip install langchain-community

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

# import os
# os.environ["OPENAI_API_KEY"] = ""

# COMMAND ----------

# MAGIC %md ### SQL Database Agent
# MAGIC
# MAGIC This is an example of how to interact with a certain schema in Unity Catalog. Please note that the agent can't create new tables or delete tables. It can only query tables.
# MAGIC
# MAGIC The database instance is created within:
# MAGIC ```
# MAGIC db = SQLDatabase.from_databricks(catalog="...", schema="...")
# MAGIC ```
# MAGIC And the agent (and the required tools) are created by:
# MAGIC ```
# MAGIC toolkit = SQLDatabaseToolkit(db=db, llm=llm)
# MAGIC agent = create_sql_agent(llm=llm, toolkit=toolkit, **kwargs)
# MAGIC ```

# COMMAND ----------

from langchain.agents import create_sql_agent
from langchain.agents.agent_toolkits import SQLDatabaseToolkit
from langchain.sql_database import SQLDatabase
from langchain_community.llms import Databricks

db = SQLDatabase.from_databricks(catalog="samples", schema="nyctaxi")

# llm = OpenAI(temperature=.7)
# llm = Databricks(endpoint_name="dbrx1", model_kwargs={"temperature": 0.1, "max_tokens": 100})
llm = Databricks(endpoint_name="dbrx1", extra_params={"temperature": 0.1, "max_tokens": 200})
# llm("How are you?")

toolkit = SQLDatabaseToolkit(db=db, llm=llm)
agent = create_sql_agent(llm=llm, toolkit=toolkit, verbose=True)

# COMMAND ----------

# agent.run("What is the longest trip distance and how long did it take?")
agent.invoke("What is the longest trip distance and how long did it take?")
