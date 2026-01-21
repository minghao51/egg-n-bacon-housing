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
import pandas as pd
from dotenv import load_dotenv
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

# %%
llm = ChatGoogleGenerativeAI(model = 'gemini-1.5-flash-latest')
df = pd.read_csv('../data/listing_search_result.csv')

# %%
agent = create_pandas_dataframe_agent(llm, df, verbose=True, allow_dangerous_code=True)

# %%
agent.invoke('how many rows are there?')

# %%
agent.invoke('what is this dataset about?')

# %%
agent.invoke('what is the median number of bedrooms available at watertown?')
