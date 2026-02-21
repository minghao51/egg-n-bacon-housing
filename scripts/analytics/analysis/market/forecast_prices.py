#!/usr/bin/env python3
"""Price forecasting using ARIMA."""

import logging
import sys
from pathlib import Path

import pandas as pd
from statsmodels.tsa.arima.model import ARIMA

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.core.data_helpers import load_parquet, save_parquet

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def main():
    """Forecast prices by planning area using ARIMA."""
    logger.info("🚀 Starting price forecasting")

    df = load_parquet("L3_housing_unified")

    df["month"] = pd.to_datetime(df["month"], errors="coerce")
    df = df.dropna(subset=["month", "planning_area", "price_psf"])

    areas = df["planning_area"].dropna().unique()
    logger.info(f"Forecasting for {len(areas)} planning areas")

    forecasts = []

    for area in list(areas)[:20]:
        area_data = df[df["planning_area"] == area].sort_values("month")

        if len(area_data) < 12:
            continue

        ts = area_data.groupby("month")["price_psf"].median()
        ts = ts.asfreq("MS")
        ts = ts.ffill()

        try:
            model = ARIMA(ts, order=(1, 1, 1))
            model_fit = model.fit()

            forecast = model_fit.forecast(steps=6)

            forecasts.append({
                "planning_area": area,
                "forecast_6m_price_psf": float(forecast.iloc[-1]),
                "last_price_psf": float(ts.iloc[-1]),
                "projected_growth_pct": (forecast.iloc[-1] / ts.iloc[-1] - 1) * 100
            })

        except Exception as e:
            logger.warning(f"  Could not forecast {area}: {e}")

    forecast_df = pd.DataFrame(forecasts)

    if len(forecast_df) > 0:
        save_parquet(forecast_df, "L4_price_forecasts", source="ARIMA models")
        logger.info(f"✅ Saved forecasts for {len(forecast_df)} areas")

        top_growth = forecast_df.nlargest(5, "projected_growth_pct")
        logger.info("\nTop 5 Areas for Price Growth (6-month forecast):")
        for _, row in top_growth.iterrows():
            logger.info(f"  {row['planning_area']}: +{row['projected_growth_pct']:.1f}%")

        print({
            "key_findings": [
                f"Forecasted prices for {len(forecast_df)} planning areas",
                f"Top growth area: {top_growth.iloc[0]['planning_area']} (+{top_growth.iloc[0]['projected_growth_pct']:.1f}%)",
                "Used ARIMA(1,1,1) model with 6-month horizon"
            ],
            "outputs": ["L4_price_forecasts.parquet"],
        })
    else:
        logger.warning("No forecasts generated")


if __name__ == "__main__":
    main()
