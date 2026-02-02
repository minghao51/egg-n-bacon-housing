#!/usr/bin/env python3
"""
Refresh OneMap API token.

This script attempts to get a new OneMap access token using the credentials
in your .env file and updates the .env file with the new token.
"""
import os
import sys
from pathlib import Path

import requests

from scripts.core.script_base import setup_script_environment
from scripts.core.logging_config import setup_logging_from_env, get_logger


def refresh_onemap_token() -> bool:
    """
    Refresh the OneMap API token.

    Returns:
        True if successful, False otherwise
    """
    logger = get_logger(__name__)

    url = "https://www.onemap.gov.sg/api/auth/post/getToken"
    email = os.environ.get('ONEMAP_EMAIL')
    password = os.environ.get('ONEMAP_EMAIL_PASSWORD')

    logger.info("=" * 60)
    logger.info("OneMap Token Refresh")
    logger.info("=" * 60)
    logger.info(f"Email: {email}")
    logger.info(f"Password: {'SET' if password else 'NOT SET'}")
    logger.info("=" * 60)

    if not email or not password:
        logger.error("ONEMAP_EMAIL or ONEMAP_EMAIL_PASSWORD not set in .env")
        logger.info("Please add these to your .env file:")
        logger.info("  ONEMAP_EMAIL=your_email@example.com")
        logger.info("  ONEMAP_EMAIL_PASSWORD=your_password")
        return False

    logger.info("Requesting new token from OneMap API...")

    try:
        payload = {"email": email, "password": password}
        response = requests.post(url, json=payload, timeout=30)

        logger.info(f"API Response Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            new_token = data.get('access_token')

            logger.info("SUCCESS! Got new token")
            logger.info(f"Token (first 50 chars): {new_token[:50]}...")

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
            logger.info("Updated .env file with new token")
            logger.info("You can now run the pipeline:")
            logger.info("  uv run python scripts/run_pipeline.py --stage L1 --parallel")
            return True

        elif response.status_code == 400:
            error_data = response.json()
            error_msg = error_data.get('error', 'Unknown error')
            logger.error("Authentication Failed")
            logger.error(f"Error: {error_msg}")
            logger.info("This means:")
            logger.info("  1. The email/password combination is incorrect")
            logger.info("  2. OR the OneMap account needs to be verified")
            logger.info("To fix:")
            logger.info("  1. Visit https://www.onemap.gov.sg/")
            logger.info("  2. Try logging in with your credentials")
            logger.info("  3. If you can't login, reset your password")
            logger.info("  4. Update the .env file with correct credentials")
            logger.info(f"Current email in .env: {email}")
            return False
        else:
            logger.error(f"Unexpected Error")
            logger.error(f"Status: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
        return False
    finally:
        logger.info("=" * 60)


def main():
    """Main entry point."""
    # Setup environment and logging
    setup_script_environment()
    setup_logging_from_env()

    # Refresh token
    success = refresh_onemap_token()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
