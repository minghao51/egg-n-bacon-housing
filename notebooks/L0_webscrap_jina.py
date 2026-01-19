# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.19.0
#   kernelspec:
#     display_name: py311cv
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Web Scraping and Data Retrieval using Jina.ai and Python Tenacity
#
# ## Overview
#
# Key Pipelines
#
# - URL Processing: Clean and process lists of URLs using Python
# - Neural Search: Utilize (Jina AI)'s neural search framework for efficient property data retrieval
# - Exponential Backoff: Implement retry logic with Tenacity for robust error handling
#
# # Requirements
#
# - Jina.ai account with API credentials (in .env)
#

# %%
# import pandas as pd
# import numpy as np
import os

from dotenv import load_dotenv

# Load the environment variables from .env file
load_dotenv()

# %%
# os.environ['JINA_AI']

# %%
urls_list = [
    "[1] https://www.ura.gov.sg/Corporate/Property/Residential/Buying-Property",
    "[2] https://quickcredit.com.sg/things-to-consider-when-buying-a-house-in-singapore/",
    "[3] https://www.rently.sg/blog/what-to-know-before-buying-rental-property-key-considerations",
    "[4] https://www.mingproperty.sg/property-buying-considerations/",
    "[5] https://sghomeinvestment.com/buying-a-property-in-singapore-factors-to-consider/",
    "[6] https://darrenong.sg/blog/a-complete-guide-to-buy-a-property-in-singapore/",
    "[7] https://www.singsaver.com.sg/blog/how-to-buy-a-house-in-singapore",
    "[8] https://www.odintax.com/resources/buying-a-house-in-singapore/",
    "[1] https://darrenong.sg/blog/a-complete-guide-to-buy-a-property-in-singapore/",
    "[2] https://quickcredit.com.sg/things-to-consider-when-buying-a-house-in-singapore/",
    "[3] https://www.wisemove.sg/post/types-of-housing-in-singapore",
    "[4] https://sghomeinvestment.com/buying-a-property-in-singapore-factors-to-consider/",
    "[5] https://www.99.co/singapore/insider/a-general-guide-to-types-of-housing-in-singapore/",
    "[6] https://plbinsights.com/understanding-the-different-property-types-in-singapore/",
    "[7] https://www.redbrick.sg/blog/what-are-the-different-types-of-private-and-landed-property-in-singapore/",
    "[8] https://www.singstat.gov.sg/-/media/files/standards_and_classifications/sctd.ashx",
    "[1] https://jaysonang.com/2024/08/29/5-key-factors-that-affect-singapores-property-prices/",
    "[2] https://quickcredit.com.sg/things-to-consider-when-buying-a-house-in-singapore/",
    "[3] https://www.mingproperty.sg/property-buying-considerations/",
    "[4] https://www.neezanizam.com/property-nuggets/4-essential-factors-to-consider-before-buying-property",
    "[5] https://www.singsaver.com.sg/blog/how-to-buy-a-house-in-singapore",
    "[6] https://www.rently.sg/blog/what-to-know-before-buying-rental-property-key-considerations",
    "[7] https://sghomeinvestment.com/buying-a-property-in-singapore-factors-to-consider/",
    "[8] https://darrenong.sg/blog/a-complete-guide-to-buy-a-property-in-singapore/",
    "[1] https://8-atbt.com.sg",
    "[2] https://8at-bt.com.sg",
    "[3] https://propertyreviewsg.com/8-at-bt-factsheet/",
    "[4] https://propertyreviewsg.com/8-at-bt/",
    "[5] https://stackedhomes.com/editorial/8bt-condo-review/",
    "[6] https://www.bukitsembawang.sg/8atbt",
    "[7] https://plbinsights.com/understanding-the-different-property-types-in-singapore/",
    "[8] https://darrenong.sg/blog/a-complete-guide-to-buy-a-property-in-singapore/",
    "[1] https://sghomeinvestment.com/8bt-condo-review-capitalise-on-beauty-worlds-transformation/",
    "[2] https://stackedhomes.com/editorial/should-you-buy-8bt-a-pricing-review-comparison-with-the-reserve-residences-and-the-linq-beauty-world/",
    "[3] https://primior.com/importance-of-accessibility-how-location-affects-property-value/",
    "[4] https://stackedhomes.com/editorial/8bt-condo-review/",
    "[5] https://8at-bt.com.sg",
    "[6] https://propertyreviewsg.com/8-at-bt/",
    "[7] https://www.newlaunchesreview.com/8bt/",
    "[8] https://8-atbt.com.sg",
    "[1] https://darrenong.sg/blog/a-complete-guide-to-buy-a-property-in-singapore/",
    "[2] https://quickcredit.com.sg/things-to-consider-when-buying-a-house-in-singapore/",
    "[3] https://www.wisemove.sg/post/types-of-housing-in-singapore",
    "[4] https://sghomeinvestment.com/buying-a-property-in-singapore-factors-to-consider/",
    "[5] https://www.99.co/singapore/insider/a-general-guide-to-types-of-housing-in-singapore/",
    "[6] https://plbinsights.com/understanding-the-different-property-types-in-singapore/",
    "[7] https://www.redbrick.sg/blog/what-are-the-different-types-of-private-and-landed-property-in-singapore/",
    "[8] https://www.singstat.gov.sg/-/media/files/standards_and_classifications/sctd.ashx",
    "[1] https://jaysonang.com/2024/08/29/5-key-factors-that-affect-singapores-property-prices/",
    "[2] https://quickcredit.com.sg/things-to-consider-when-buying-a-house-in-singapore/",
    "[3] https://www.mingproperty.sg/property-buying-considerations/",
    "[4] https://www.neezanizam.com/property-nuggets/4-essential-factors-to-consider-before-buying-property",
    "[5] https://www.singsaver.com.sg/blog/how-to-buy-a-house-in-singapore",
    "[6] https://www.rently.sg/blog/what-to-know-before-bbuying-rental-property-key-considerations",
    "[7] https://sghomeinvestment.com/buying-a-property-in-singapore-factors-to-consider/",
    "[8] https://darrenong.sg/blog/a-complete-guide-to-buy-a-property-in-singapore/",
]


# %%
def urls_cleaner(urls_list: list):
    # Initialize an empty list to store the URLs
    urls = []

    # Iterate over each string in the list
    for item in urls_list:
        # Split the string into two parts at the space character
        parts = item.split(" ")

        # The second part is the URL
        url = parts[1]

        # Add the URL to the list if it's not already there
        if url not in urls:
            urls.append(url)
    return urls


# Print the set of URLs
urls = urls_cleaner(urls_list)
urls = list(set(urls))
len(urls)

# %%
import requests
from tenacity import retry, stop_after_attempt, wait_exponential


def reader_url_jina(urls):
    # Use tenacity to retry failed requests with exponential backoff
    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def _fetch_url(url):
        """
        Fetch a URL and return the response text.

        Args:
        url (str): The URL to fetch.

        Returns:
        str: The response text.
        """
        base_url = "https://r.jina.ai/"
        headers = {"Authorization": os.environ["JINA_AI"]}
        response = requests.get(base_url + url, headers=headers)
        response.raise_for_status()  # Raise an exception for bad status codes
        return response.text

    response_text = []

    for item in urls:
        # Add the URL to the list if it's not already there
        response_text.append(_fetch_url(item))

    # Print the list of URLs
    return response_text


# %%
# import pprint


def extract_title_url(text) -> dict:
    """
    Extracts the title and URL from a formatted string.

    Args:
        text: The string containing title, URL, and other information.

    Returns:
        A dictionary containing the extracted title and URL, or None if not found.
    """
    lines = text.splitlines()
    result = {}

    for line in lines:
        if line.startswith("Title: "):
            result["title"] = line.replace("Title: ", "").strip()
        elif line.startswith("URL Source: "):
            result["url"] = line.replace("URL Source: ", "").strip()

    if "title" in result and "url" in result:
        return result
    else:
        return None


import re


def extract_all_url(text) -> dict:
    """
    Extracts the title and URL from a formatted string.

    Args:
        text: The string containing title, URL, and other information.

    Returns:
        A dictionary containing the extracted title and URL, or None if not found.
    """
    result = {}

    result["title"] = re.search(r"Title: (.*)", text).group(1).strip()
    result["url"] = re.search(r"URL Source: (.*)", text).group(1).strip()
    match = re.search(r"Published Time: (.*)", text)
    result["time"] = (
        re.search(r"Published Time: (.*)", text).group(1).strip() if match else ""
    )
    result["md"] = re.search(r"Markdown Content:(.*)", text, re.DOTALL).group(1).strip()

    if "title" in result and "url" in result:
        return result
    else:
        return None


# pprint.pprint(response_text[1])
# extract_title_url(response_text[1])

# %%
import openai

client = openai.OpenAI(
    base_url="https://api.groq.com/openai/v1", api_key=os.environ.get("GROQ")
)

# %%
# extract the from the title and url in the response_text, craft a descriptive and concise name that is at indicative of "source domain -  title via llm"



def llm_extract_name(
    title_url_dict: dict[str, str],
    client: openai.OpenAI = client,
    model: str = "llama-3.1-8b-instant",
) -> str:
    """
    Extract a suitable name from a dictionary of title and URL.

    Args:
    - title_url_dict (Dict[str, str]): A dictionary containing the title and URL.

    Returns:
    - str: A suitable name extracted from the title and URL.
    """

    # Extract the title and URL from the dictionary
    title = title_url_dict["title"]
    url = title_url_dict["url"]

    # Prepare the input text
    prompt = f"Craft a concise and descriptive name from the following title and URL: '{title}' - '{url}', make sure it follow the format domain (without https and .com) - title. Return a single most indicative name without any other extra info or extra words"

    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ],
    )

    # Return the response text as the extracted name
    return completion.choices[0].message.content



# %% [markdown]
# # Main pipeline
#

# %%
urls_markdown = reader_url_jina(urls)
url_list_dict = [extract_all_url(i) for i in urls_markdown]
filenames_list = [llm_extract_name(i) for i in url_list_dict]

markdown_list = [i["md"] for i in url_list_dict]

# %%
filenames_list = [llm_extract_name(i) for i in url_list_dict]

# %%


def save_dict_to_markdown(data, file_path):
    """
    Save a dictionary to a Markdown file with front matter.

    Args:
        data (dict): Dictionary containing URL, title, time, and Markdown content.
        file_path (str): Path to the Markdown file.

    Example:
        data = {
            'url': 'https://example.com',
            'title': 'Example Title',
            'time': '2024-09-09T21:00:57+08:00',
            'markdown_content': '# Example Markdown Content'
        }
        save_dict_to_markdown(data, 'example.md')
    """

    # Create front matter
    # front_matter = yaml.dump(
    #     {"url": data["url"], "title": data["title"], "time": data.get("time")}
    # )
    front_matter = f"# {data['title']}\n"

    # Create Markdown content
    markdown_content = data['md'] #"\n\n---\n\n" +

    # Save to file
    with open(file_path, "w") as f:
        f.write(front_matter + markdown_content)


# %%
save_path = "data/raw_documents"

# Save each Markdown file
dirname = os.path.dirname(os.getcwd())
for markdown_full, filename in zip(url_list_dict, filenames_list):
    file_path = os.path.join(dirname, save_path, f"{filename}.md")
    save_dict_to_markdown(markdown_full, file_path)

# %%
import polars as pl

df = pl.DataFrame(url_list_dict)
df = df.drop('md')

df_filename = pl.DataFrame(filenames_list)
df_filename.columns = ['file_name']

df_all = pl.concat([df_filename, df], how="horizontal")

df_all.write_csv(dirname+"/data/raw_documents/master_index.csv")

# %% [markdown]
# # Extract exploration

# %%
import glob


def list_files_in_directory(path):
    """
    This function reads the files from a given directory into a list.

    Args:
        path (str): The path to the directory from which files are to be read.

    Returns:
        list: A list of filenames in the given directory.
    """
    try:
        # Use glob to get a list of all files in the directory
        return glob.glob(os.path.join(path, "*.*"))

    except FileNotFoundError:
        print(f"Directory not found: {path}")
        return []

    except NotADirectoryError:
        print(f"Not a directory: {path}")
        return []


# %%
# Load Markdown file
def load_markdown(file_path):
    with open(file_path) as f:
        markdown_text = f.read()
    return markdown_text


# # Extract front matter and content
# def extract_front_matter(markdown_text):
#     lines = markdown_text.splitlines()
#     front_matter = {}
#     content = []
#     in_front_matter = True
#     for line in lines:
#         if line == "---":
#             in_front_matter = False
#         elif in_front_matter:
#             key, value = line.split(":")
#             front_matter[key.strip()] = value.strip()
#         else:
#             content.append(line)
#     return front_matter, "\n".join(content)

# %%
import os

dirname = os.path.dirname(os.getcwd())
list_files_in_directory(dirname + "/data/raw_documents")

# %%
load_markdown(r"/home/howt/work/egg-n-bacon-housing/data/raw_documents/propertyreviewsg - 8@BT.md")

# %%
extract_front_matter(r"/home/howt/work/egg-n-bacon-housing/data/raw_documents/propertyreviewsg - 8@BT.md")
