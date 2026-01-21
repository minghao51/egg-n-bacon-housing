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
import pathlib
sys.path.append(str(pathlib.Path(__file__).parent.parent / 'src'))

from data_helpers import save_parquet

url = "https://en.wikipedia.org/wiki/List_of_shopping_malls_in_Singapore"

# Add User-Agent header to avoid being blocked
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

response = requests.get(url, headers=headers)

print(f"Response status: {response.status_code}")

soup = BeautifulSoup(response.content, "html.parser")
div_col_elements = soup.find_all('div', class_='div-col')

print(f"Found {len(div_col_elements)} div-col elements")

shopping_mall_list = []
for div_col in div_col_elements:
    li_elements = div_col.find_all('li')
    for li in li_elements:
        text = li.text.strip()
        if text:  # Only add non-empty text
            shopping_mall_list.append(text)

print(f"Scraped {len(shopping_mall_list)} shopping malls")
shopping_mall_list[:10]  # Show first 10

# %%
shopping_mall_df = pd.DataFrame(shopping_mall_list, columns=['shopping_mall'])

print(f"Created DataFrame with {len(shopping_mall_df)} rows")

if not shopping_mall_df.empty:
    save_parquet(shopping_mall_df, "raw_wiki_shopping_mall", source="wikipedia.org")
    print("✅ Saved shopping mall data")
else:
    print("⚠️  No shopping mall data to save")
