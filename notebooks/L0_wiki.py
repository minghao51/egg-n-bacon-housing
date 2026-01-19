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
# # Scrapping data from wiki for list of shopping mall

# %% [markdown]
# via beautiful soup

# %%
import sys

import pandas as pd
import requests
from bs4 import BeautifulSoup

# Add src directory to path for imports
sys.path.append('../src')

from data_helpers import save_parquet

url = "https://en.wikipedia.org/wiki/List_of_shopping_malls_in_Singapore"
response = requests.get(url)

soup = BeautifulSoup(response.content, "html.parser")
div_col_elements = soup.find_all('div', class_='div-col')
shopping_mall_list = []
for div_col in div_col_elements:
    li_elements = div_col.find_all('li')
    for li in li_elements:
        text = li.text.strip()
        shopping_mall_list.append(text)

shopping_mall_list

# %%
shopping_mall_df = pd.DataFrame(shopping_mall_list, columns=['shopping_mall'])

# %%
save_parquet(shopping_mall_df, "raw_wiki_shopping_mall", source="wikipedia.org")
