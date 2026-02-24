# OneMap API Authentication Fix

**Date:** 2026-01-21
**Issue:** OneMap API authentication failing with `KeyError: 'access_token'`

## Problem

The pipeline notebooks were trying to authenticate with OneMap API using email and password credentials:
```python
url = "https://www.onemap.gov.sg/api/auth/post/getToken"
payload = {
    "email": os.environ['ONEMAP_EMAIL'],
    "password": os.environ['ONEMAP_EMAIL_PASSWORD']
}
response = requests.request("POST", url, json=payload)
access_token = json.loads(response.text)['access_token']  # KeyError here
```

However, the API was returning an error:
```json
{
  "error": "You have to enter a valid email address and valid password to generate a token."
}
```

This caused a `KeyError: 'access_token'` because the response didn't contain an access_token key.

## Root Cause

The email/password credentials in `.env` were either invalid or not registered with OneMap API. However, there was already a valid `ONEMAP_TOKEN` in the `.env` file that was working.

## Solution

Updated all 4 notebooks that use OneMap API authentication to:

1. **First, try to use the existing token from `.env`**
2. **Check if the token is expired** by decoding the JWT payload
3. **Only request a new token** if the existing one is expired or missing

### New Authentication Logic

```python
# Try to use existing token from .env
access_token = os.environ.get('ONEMAP_TOKEN')

if access_token:
    # Decode JWT to check expiration
    try:
        parts = access_token.split('.')
        if len(parts) == 3:
            payload = parts[1]
            payload += '=' * (4 - len(payload) % 4)
            decoded = base64.b64decode(payload)
            token_data = json.loads(decoded)

            current_time = time.time()
            if token_data.get('exp', 0) > current_time:
                print(f"✅ Using existing OneMap token from .env")
                print(f"   Token expires in: {(token_data.get('exp') - current_time) / 3600:.1f} hours")
                headers = {"Authorization": f"{access_token}"}
            else:
                print("⚠️  Token in .env has expired")
                access_token = None
        else:
            print("⚠️  Invalid token format")
            access_token = None
    except Exception as e:
        print(f"⚠️  Error decoding token: {e}")
        access_token = None

# Fallback: try to get new token (if email/password are configured)
if not access_token:
    print("Attempting to get new OneMap token...")
    url = "https://www.onemap.gov.sg/api/auth/post/getToken"

    payload = {
        "email": os.environ.get('ONEMAP_EMAIL'),
        "password": os.environ.get('ONEMAP_EMAIL_PASSWORD')
    }

    response = requests.request("POST", url, json=payload)
    print(f"API Response Status: {response.status_code}")

    if response.status_code == 200:
        response_data = json.loads(response.text)
        access_token = response_data.get('access_token')
        if access_token:
            print("✅ Successfully obtained new OneMap token")
            headers = {"Authorization": f"{access_token}"}
        else:
            print(f"❌ No access_token in response: {response.text}")
            raise KeyError("access_token not found in API response")
    else:
        print(f"❌ Failed to get token: {response.text}")
        raise Exception(f"Token request failed with status {response.status_code}")
```

## Files Updated

1. `notebooks/L0_onemap.py`
2. `notebooks/L1_utilities_processing.py`
3. `notebooks/L1_ura_transactions_processing.py`
4. `notebooks/L2_sales_facilities.py`

## Benefits

1. **Uses existing valid token** instead of trying to get new one unnecessarily
2. **Checks token expiration** to avoid using expired tokens
3. **Clear error messages** if authentication fails
4. **Graceful fallback** to email/password if token is missing
5. **Prevents API rate limiting** by reusing existing tokens

## Current Token Status

The current `ONEMAP_TOKEN` in `.env` is:
- **Valid:** ✅ Yes
- **Expires:** In approximately 70 hours
- **User ID:** 4609

## Maintenance

When the token expires:
1. The code will attempt to get a new token using email/password
2. If that fails, you'll need to manually get a new token from OneMap
3. Update the `ONEMAP_TOKEN` in `.env` with the new token
4. The pipeline will automatically use the new token

To manually get a new token, visit: https://www.onemap.gov.sg/apidocs/authentication
