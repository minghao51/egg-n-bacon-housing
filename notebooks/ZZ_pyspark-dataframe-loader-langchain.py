# Databricks notebook source
# MAGIC %md # PySpark DataFrame Loader and MLFlow in Langchain
# MAGIC
# MAGIC This notebook showcases the integration between PySpark and Langchain and includes how to:
# MAGIC 1. Create a Langchain document loader from a PySpark Dataframe
# MAGIC 2. Create a Langchain RetrievalQA instance using that document loader
# MAGIC 3. Use Mlflow to save the RetrievalQA example
# MAGIC
# MAGIC
# MAGIC ### Requirements
# MAGIC
# MAGIC - Databricks Runtime 13.3 ML and above
# MAGIC - MLflow 2.5 and above

# COMMAND ----------

# Cant seems to run this with the serverless
# EnvironmentError: Failed to set environment metadata. The Spark session may be unavailable, please try again or contact Databricks support.

# COMMAND ----------

# MAGIC %md ### Imports

# COMMAND ----------

# MAGIC %pip install --upgrade langchain faiss-cpu mlflow
# MAGIC %pip install langchain-community
# MAGIC # For GPU clusters use the following 
# MAGIC # %pip install --upgrade langchain faiss-gpu mlflow

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %md ### Creating a RetrievalQA chain with PySpark-based document loading

# COMMAND ----------

# MAGIC %md Let's use the Wikipedia datasets within `/databricks-datasets/`. In the following cell, please add your OpenAI API Key

# COMMAND ----------

import os

# os.environ["OPENAI_API_KEY"] = ""

# COMMAND ----------

number_of_articles = 20

wikipedia_dataframe = spark.read.parquet("databricks-datasets/wikipedia-datasets/data-001/en_wikipedia/articles-only-parquet/*").limit(number_of_articles)
display(wikipedia_dataframe)

# COMMAND ----------

# MAGIC %md The following lines are all that is needed for loading data from a PySpark Dataframe into Langchain 

# COMMAND ----------

from langchain.document_loaders import PySparkDataFrameLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

loader = PySparkDataFrameLoader(spark, wikipedia_dataframe, page_content_column="text")
documents = loader.load()

text_splitter = RecursiveCharacterTextSplitter(chunk_size=3000, chunk_overlap=0)
texts = text_splitter.split_documents(documents)
print(f"Number of documents: {len(texts)}")

# COMMAND ----------

# MAGIC %md ### Create a FAISS vector store using HuggingfaceEmbeddings
# MAGIC
# MAGIC This FAISS vector store is the intermediate step to ensure you can log the model with MLflow.

# COMMAND ----------

from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import FAISS

embeddings = OpenAIEmbeddings()
db = FAISS.from_documents(texts, embeddings)

# COMMAND ----------

# MAGIC %md ### Create a RetrievalQA chain

# COMMAND ----------

from langchain.chains import RetrievalQA
from langchain import OpenAI

retrieval_qa = RetrievalQA.from_chain_type(llm=OpenAI(), chain_type="stuff", retriever=db.as_retriever())

# COMMAND ----------

# MAGIC %md ### Query the RetrievalQA chain

# COMMAND ----------

query = "Who is Harrison Schmitt"
result = retrieval_qa({"query": query})
print("Result:", result["result"])

# COMMAND ----------

# MAGIC %md ### Logging the chain with Mlflow

# COMMAND ----------

import mlflow

persist_directory = "langchain/faiss_index"
db.save_local(persist_directory)

def load_retriever(persist_directory):
  embeddings = OpenAIEmbeddings()
  db = FAISS.load_local(persist_directory, embeddings)
  return db.as_retriever()

# Log the RetrievalQA chain
with mlflow.start_run() as mlflow_run:
  logged_model = mlflow.langchain.log_model(
    retrieval_qa,
    "retrieval_qa_chain",
    loader_fn=load_retriever,
    persist_dir=persist_directory,
  )

# COMMAND ----------

# MAGIC %md ### Loading the chain using MLFlow
# MAGIC
# MAGIC

# COMMAND ----------

model_uri = f"runs:/{ mlflow_run.info.run_id }/retrieval_qa_chain"

loaded_pyfunc_model = mlflow.pyfunc.load_model(model_uri)
langchain_input = {"query": "Who is Harrison Schmitt"}
loaded_pyfunc_model.predict([langchain_input])
