#!/usr/bin/env python3
"""
Refresh OneMap API token.

This script attempts to get a new OneMap access token using the credentials
in your .env file and updates the .env file with the new token.
"""
import os
import json
import requests
from dotenv import load_dotenv
from pathlib import Path

# Load current .env
load_dotenv()

url = "https://www.onemap.gov.sg/api/auth/post/getToken"
email = os.environ.get('ONEMAP_EMAIL')
password = os.environ.get('ONEMAP_EMAIL_PASSWORD')

print("=" * 60)
print("OneMap Token Refresh")
print("=" * 60)
print(f"Email: {email}")
print(f"Password: {'SET' if password else 'NOT SET'}")
print("=" * 60)

if not email or not password:
    print("\n❌ ERROR: ONEMAP_EMAIL or ONEMAP_EMAIL_PASSWORD not set in .env")
    print("\nPlease add these to your .env file:")
    print("ONEMAP_EMAIL=your_email@example.com")
    print("ONEMAP_EMAIL_PASSWORD=your_password")
    exit(1)

print("\nRequesting new token from OneMap API...")

payload = {"email": email, "password": password}
response = requests.post(url, json=payload)

print(f"\nAPI Response Status: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    new_token = data.get('access_token')

    print("\n✅ SUCCESS! Got new token")
    print(f"Token (first 50 chars): {new_token[:50]}...")

    # Update .env file
    env_path = Path(".env")
    env_content = env_path.read_text()

    # Replace the token line
    lines = env_content.split('\n')
    for i, line in enumerate(lines):
        if line.startswith('ONEMAP_TOKEN='):
            lines[i] = f"ONEMAP_TOKEN={new_token}"
            break

    env_path.write_text('\n'.join(lines))
    print("\n✅ Updated .env file with new token")
    print("\nYou can now run the pipeline:")
    print("  uv run python scripts/run_pipeline.py --stage L1 --parallel")

elif response.status_code == 400:
    error_data = response.json()
    error_msg = error_data.get('error', 'Unknown error')
    print(f"\n❌ Authentication Failed")
    print(f"\nError: {error_msg}")
    print("\nThis means:")
    print("  1. The email/password combination is incorrect")
    print("  2. OR the OneMap account needs to be verified")
    print("\nTo fix:")
    print("  1. Visit https://www.onemap.gov.sg/")
    print("  2. Try logging in with your credentials")
    print("  3. If you can't login, reset your password")
    print("  4. Update the .env file with correct credentials")
    print(f"\nCurrent email in .env: {email}")
else:
    print(f"\n❌ Unexpected Error")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")

print("=" * 60)
