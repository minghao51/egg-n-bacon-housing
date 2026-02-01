#!/usr/bin/env python3
"""
Forecast Rental Yields Using Prophet

This script creates 6-month and 1-year rental yield forecasts for Singapore
HDB properties by planning area using Facebook Prophet.

Author: Automated Pipeline
Date: 2026-01-24
"""

from pathlib import Path
from dataclasses import dataclass

import pandas as pd
import numpy as np
from prophet import Prophet


@dataclass
class YieldForecastResult:
    """Container for yield forecast results."""
    planning_area: str
    forecast_horizon: str
    forecast_date: str
    predicted_yield_pct: float
    confidence_lower: float
    confidence_upper: float
    trend_bps: float
    model_r2: float
    last_training_date: str


def load_rental_yield_data() -> pd.DataFrame:
    """Load rental yield data."""
    path = Path('data/pipeline/L2/rental_yield.parquet')
    df = pd.read_parquet(path)
    
    # Handle mixed date formats (monthly "2021-01" and quarterly "2021Q1")
    def parse_date(val):
        if pd.isna(val):
            return pd.NaT
        if isinstance(val, str):
            if 'Q' in val:
                # Quarterly format: "2021Q1" -> convert to end of quarter
                year, quarter = val.split('Q')
                month = int(quarter) * 3  # Q1->3, Q2->6, Q3->9, Q4->12
                return pd.to_datetime(f"{year}-{month:02d}-01")
            else:
                return pd.to_datetime(val)
        return pd.NaT
    
    df['month'] = df['month'].apply(parse_date)
    df = df.dropna(subset=['month'])
    return df


def prepare_prophet_data(
    df: pd.DataFrame,
    planning_area: str
) -> pd.DataFrame:
    """Prepare data for Prophet model."""
    area_df = df[df['town'] == planning_area].copy()
    
    if len(area_df) < 12:
        return None
    
    # Aggregate by month
    monthly = area_df.groupby('month')['rental_yield_pct'].mean().reset_index()
    monthly.columns = ['ds', 'y']
    monthly = monthly.sort_values('ds')
    monthly = monthly.dropna()
    
    return monthly


def train_prophet_model(
    data: pd.DataFrame
) -> tuple:
    """Train Prophet model and return model with R² score."""
    model = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=False,
        changepoint_prior_scale=0.05,
        seasonality_prior_scale=0.1
    )
    
    model.fit(data)
    
    # Calculate R²
    train_pred = model.predict(data[['ds']])
    ss_res = np.sum((data['y'] - train_pred['yhat']) ** 2)
    ss_tot = np.sum((data['y'] - data['y'].mean()) ** 2)
    r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
    
    return model, r2


def generate_forecast(
    model: Prophet,
    horizon_months: int,
    last_date: pd.Timestamp
) -> pd.DataFrame:
    """Generate forecast for specified horizon."""
    future = model.make_future_dataframe(
        periods=horizon_months * 30,
        freq='D'
    )
    
    future = future[future['ds'] > last_date]
    forecast = model.predict(future)
    
    forecast['ds'] = pd.to_datetime(forecast['ds']).dt.to_period('M').dt.to_timestamp()
    monthly_forecast = forecast.groupby('ds').agg({
        'yhat': 'mean',
        'yhat_lower': 'mean',
        'yhat_upper': 'mean'
    }).reset_index()
    
    return monthly_forecast


def calculate_trend_bps(
    last_actual: float,
    forecast_value: float
) -> float:
    """Calculate change in basis points."""
    return (forecast_value - last_actual) * 100  # Convert % to bps


def forecast_yields(
    planning_area: str,
    horizons: list = [6, 12]
) -> list:
    """Generate forecasts for a single planning area."""
    df = load_rental_yield_data()
    prophet_data = prepare_prophet_data(df, planning_area)
    
    if prophet_data is None or len(prophet_data) < 12:
        return []
    
    model, r2 = train_prophet_model(prophet_data)
    last_actual = prophet_data['y'].iloc[-1]
    last_date = prophet_data['ds'].max()
    
    results = []
    
    for horizon in horizons:
        forecast_df = generate_forecast(model, horizon, last_date)
        
        if len(forecast_df) == 0:
            continue
        
        final_forecast = forecast_df.iloc[-1]
        trend_bps = calculate_trend_bps(last_actual, final_forecast['yhat'])
        
        result = YieldForecastResult(
            planning_area=planning_area,
            forecast_horizon=f'{horizon}m',
            forecast_date=final_forecast['ds'].strftime('%Y-%m-%d'),
            predicted_yield_pct=round(final_forecast['yhat'], 3),
            confidence_lower=round(final_forecast['yhat_lower'], 3),
            confidence_upper=round(final_forecast['yhat_upper'], 3),
            trend_bps=round(trend_bps, 1),
            model_r2=round(r2, 4),
            last_training_date=last_date.strftime('%Y-%m-%d')
        )
        
        results.append(result)
    
    return results


def forecast_all_areas(horizons: list = [6, 12]) -> pd.DataFrame:
    """Generate forecasts for all planning areas with yield data."""
    
    print("Loading rental yield data...")
    df = load_rental_yield_data()
    
    valid_pas = df['town'].unique().tolist()
    print(f"Found {len(valid_pas)} planning areas with yield data")
    
    all_results = []
    
    for i, pa in enumerate(valid_pas):
        print(f"  [{i+1}/{len(valid_pas)}] Forecasting {pa}...", end=' ')
        
        try:
            results = forecast_yields(pa, horizons)
            
            if results:
                all_results.extend(results)
                print(f"OK (R²={results[0].model_r2:.3f})")
            else:
                print("Insufficient data")
        except Exception as e:
            print(f"FAILED: {e}")
    
    results_df = pd.DataFrame([r.__dict__ for r in all_results])
    
    print(f"\nForecasting complete: {len(results_df)} forecasts generated")
    
    return results_df


def main():
    """Main execution function."""
    
    output_dir = Path('data/forecasts')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("="*60)
    print("Rental Yield Forecasting Pipeline")
    print("="*60)
    
    results_df = forecast_all_areas(horizons=[6, 12])
    
    if len(results_df) > 0:
        # Summary
        print(f"\n{'='*60}")
        print("Yield Forecast Summary")
        print(f"{'='*60}")
        
        df_6m = results_df[results_df['forecast_horizon'] == '6m']
        print(f"\n6-Month Yield Forecasts ({len(df_6m)} areas):")
        print(f"  Mean yield: {df_6m['predicted_yield_pct'].mean():.2f}%")
        print(f"  Range: {df_6m['predicted_yield_pct'].min():.2f}% to {df_6m['predicted_yield_pct'].max():.2f}%")
        print(f"  Average trend: {df_6m['trend_bps'].mean():.0f} bps")
        
        # Save
        output_path = output_dir / 'hdb_yield_forecasts.parquet'
        results_df.to_parquet(output_path, index=False)
        print(f"\nSaved to: {output_path}")
        
        csv_path = output_dir / 'hdb_yield_forecasts.csv'
        results_df.to_csv(csv_path, index=False)
        print(f"Saved CSV to: {csv_path}")
    
    print("\n" + "="*60)
    print("Yield forecasting complete!")
    print("="*60)
    
    return results_df


if __name__ == '__main__':
    main()
