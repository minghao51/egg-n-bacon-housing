#!/usr/bin/env python3
"""Scrape URA rental statistics by project from e-service.

This script scrapes quarterly rental statistics for non-landed private
residential properties from URA's e-service.

Usage:
    uv run python scripts/data/download/scrape_ura_rental_stats.py
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.core.config import Config
from scripts.core.network_check import check_local_file_exists, require_network

logger = logging.getLogger(__name__)

OUTPUT_PATH = Config.PIPELINE_DIR / "L1" / "ura_rental_stats_by_project.parquet"

QUARTERS = [
    "2025Q4", "2025Q3", "2025Q2", "2025Q1",
    "2024Q4", "2024Q3", "2024Q2", "2024Q1",
    "2023Q4", "2023Q3", "2023Q2", "2023Q1",
    "2022Q4", "2022Q3", "2022Q2", "2022Q1",
    "2021Q4", "2021Q3", "2021Q2", "2021Q1",
    "2020Q4", "2020Q3", "2020Q2", "2020Q1",
    "2019Q4", "2019Q3", "2019Q2", "2019Q1",
    "2018Q4", "2018Q3", "2018Q2", "2018Q1",
    "2017Q4", "2017Q3", "2017Q2", "2017Q1",
    "2016Q4", "2016Q3",
]


def setup_browser():
    """Initialize Playwright browser."""
    from playwright.sync_api import sync_playwright

    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    )
    page = context.new_page()
    return playwright, browser, page


def close_browser(playwright, browser):
    """Close browser and playwright."""
    browser.close()
    playwright.stop()


def scrape_quarter(page, quarter: str) -> pd.DataFrame:
    """Scrape rental statistics for a single quarter."""
    from playwright.sync_api import TimeoutError

    url = "https://eservice.ura.gov.sg/property-market-information/pmiResidentialRentalStatisticsForNonLanded"
    page.goto(url, wait_until="networkidle", timeout=60000)

    page.wait_for_timeout(3000)

    try:
        page.wait_for_selector("select", state="visible", timeout=10000)

        page.select_option("select", quarter)

        page.wait_for_timeout(1500)

        page.click("button:has-text('Search')")

        page.wait_for_timeout(3000)

        table = page.locator("table").last
        if not table.is_visible():
            logger.warning(f"No table found for {quarter}")
            return pd.DataFrame()

        rows = table.locator("tr").all()
        if len(rows) < 2:
            logger.warning(f"No data for {quarter}")
            return pd.DataFrame()

        data = []
        for row in rows[1:]:
            cols = row.locator("td").all()
            if len(cols) >= 4:
                try:
                    project_name = cols[0].inner_text().strip()
                    district = cols[1].inner_text().strip()
                    median_rent = cols[2].inner_text().strip()
                    contracts = cols[3].inner_text().strip()

                    if project_name and project_name != "":
                        data.append({
                            "project_name": project_name,
                            "postal_district": int(district) if district.isdigit() else None,
                            "quarter": quarter,
                            "property_type": "Non-Landed",
                            "median_rent_psf": float(median_rent.replace(",", "")) if median_rent.replace(",", "").replace(".", "").isdigit() else None,
                            "no_of_contracts": int(contracts) if contracts.isdigit() else 0,
                            "created_at": datetime.now()
                        })
                except (ValueError, IndexError) as e:
                    logger.debug(f"Error parsing row: {e}")
                    continue

        logger.info(f"  {quarter}: {len(data)} projects")
        return pd.DataFrame(data)

    except TimeoutError as e:
        logger.error(f"Timeout scraping {quarter}: {e}")
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"Error scraping {quarter}: {e}")
        return pd.DataFrame()


def scrape_all_quarters(max_quarters: int = None) -> pd.DataFrame:
    """Scrape rental statistics for all quarters."""
    quarters_to_scrape = QUARTERS[:max_quarters] if max_quarters else QUARTERS

    all_data = []
    playwright, browser, page = setup_browser()

    try:
        for i, quarter in enumerate(quarters_to_scrape):
            logger.info(f"Scraping {quarter} ({i+1}/{len(quarters_to_scrape)})...")

            df = scrape_quarter(page, quarter)
            if not df.empty:
                all_data.append(df)

            if i < len(quarters_to_scrape) - 1:
                import time
                time.sleep(2)

    except Exception as e:
        logger.error(f"Scraping failed: {e}")
    finally:
        close_browser(playwright, browser)

    if all_data:
        return pd.concat(all_data, ignore_index=True)
    return pd.DataFrame()


def save_results(df: pd.DataFrame) -> bool:
    """Save scraped data to parquet."""
    if df.empty:
        logger.warning("No data to save")
        return False

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUTPUT_PATH, compression="snappy", index=False)
    logger.info(f"Saved {len(df)} records to {OUTPUT_PATH}")
    return True


def main():
    """Main execution."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Scrape URA rental statistics")
    parser.add_argument("--quarters", type=int, help="Limit number of quarters to scrape")
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("URA Rental Statistics Scraper")
    logger.info("=" * 60)

    if check_local_file_exists(OUTPUT_PATH):
        logger.info(f"Local file already exists: {OUTPUT_PATH}")
        logger.info("Skipping scrape. To re-scrape, delete the local file first.")
        return

    if not require_network():
        logger.error("Network unavailable. Cannot scrape data. Exiting.")
        return

    df = scrape_all_quarters(max_quarters=args.quarters)

    if not df.empty:
        save_results(df)

        logger.info("\nSummary:")
        logger.info(f"  Total projects: {df['project_name'].nunique()}")
        logger.info(f"  Total quarters: {df['quarter'].nunique()}")
        logger.info(f"  Date range: {df['quarter'].min()} to {df['quarter'].max()}")
        logger.info(f"  Districts: {df['postal_district'].nunique()}")
    else:
        logger.error("No data scraped")

    logger.info("=" * 60)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    main()
