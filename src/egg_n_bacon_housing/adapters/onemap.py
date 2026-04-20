"""OneMap API adapter for geocoding and authentication.

This module provides:
- OneMap API token management and authentication
- Geocoding helpers specific to OneMap API
- Retry logic with exponential backoff

OneMap is Singapore's official geospatial data service.
"""

import base64
import json
import logging
import os
import time
from urllib.parse import quote

import pandas as pd
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from egg_n_bacon_housing.config import settings
from egg_n_bacon_housing.utils.cache import cached_call

logger = logging.getLogger(__name__)


def setup_onemap_headers() -> dict[str, str]:
    """Setup OneMap API authentication headers.

    Returns:
        Dict with Authorization header containing valid JWT token

    Raises:
        Exception: If token cannot be obtained or is invalid
    """
    access_token = os.environ.get("ONEMAP_TOKEN")

    if access_token:
        try:
            parts = access_token.split(".")
            if len(parts) == 3:
                payload = parts[1]
                payload += "=" * (4 - len(payload) % 4)
                decoded = base64.b64decode(payload)
                token_data = json.loads(decoded)

                current_time = time.time()
                if token_data.get("exp", 0) > current_time:
                    print("✅ Using existing OneMap token from .env")
                    print(
                        f"   Token expires in: {(token_data.get('exp') - current_time) / 3600:.1f} hours"
                    )
                    return {"Authorization": f"{access_token}"}
                else:
                    print("⚠️  Token in .env has expired")
                    access_token = None
            else:
                print("⚠️  Invalid token format")
                access_token = None
        except Exception as e:
            print(f"⚠️  Error decoding token: {e}")
            access_token = None

    if not access_token:
        print("Attempting to get new OneMap token...")
        url = "https://www.onemap.gov.sg/api/auth/post/getToken"
        payload = {
            "email": os.environ.get("ONEMAP_EMAIL"),
            "password": os.environ.get("ONEMAP_EMAIL_PASSWORD"),
        }

        response = requests.request("POST", url, json=payload)
        print(f"API Response Status: {response.status_code}")

        if response.status_code == 200:
            response_data = json.loads(response.text)
            access_token = response_data.get("access_token")
            if access_token:
                print("✅ Successfully obtained new OneMap token")
                return {"Authorization": f"{access_token}"}
            else:
                print(f"❌ No access_token in response: {response.text}")
                raise KeyError("access_token not found in API response")
        else:
            print(f"❌ Failed to get token: {response.text}")
            raise Exception(f"Token request failed with status {response.status_code}")


initial_backoff = 1
max_backoff = 32


@retry(
    wait=wait_exponential(multiplier=1, min=initial_backoff, max=max_backoff),
    stop=stop_after_attempt(3),
    before_sleep=lambda retry_state: logger.warning(
        f"Retrying OneMap API ({retry_state.attempt_number}/3) after error: {retry_state.outcome.exception()}"
    ),
)
def fetch_data(search_string: str, headers: dict[str, str], timeout: int = 30) -> pd.DataFrame:
    """Fetch geocoding data from OneMap API for a given address.

    Args:
        search_string: Address to search for
        headers: Authentication headers from setup_onemap_headers()
        timeout: Request timeout in seconds (default: 30)

    Returns:
        DataFrame with search results including coordinates

    Raises:
        requests.RequestException: If API call fails after retries
        requests.Timeout: If request times out
    """
    encoded_search = quote(search_string, safe="")
    url = f"https://www.onemap.gov.sg/api/common/elastic/search?searchVal={encoded_search}&returnGeom=Y&getAddrDetails=Y&pageNum=1"
    response = requests.get(url, headers=headers, timeout=timeout)
    response.raise_for_status()
    return (
        pd.DataFrame(json.loads(response.text)["results"])
        .reset_index()
        .rename({"index": "search_result"}, axis=1)
    )


def fetch_data_cached(
    search_string: str, headers: dict[str, str], timeout: int = 30
) -> pd.DataFrame:
    """Fetch geocoding data from OneMap API with caching support.

    Args:
        search_string: Address to search for
        headers: Authentication headers from setup_onemap_headers()
        timeout: Request timeout in seconds (default: 30)

    Returns:
        DataFrame with search results including coordinates

    Raises:
        requests.RequestException: If API call fails after retries
        requests.Timeout: If request times out
    """
    cache_id = f"onemap_search:{search_string}"

    def _fetch_from_api():
        return fetch_data(search_string, headers, timeout)

    return cached_call(cache_id, _fetch_from_api, duration_hours=settings.geocoding.timeout_seconds)
