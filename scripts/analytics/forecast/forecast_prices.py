#!/usr/bin/env python3
"""
Forecast Housing Prices Using Prophet

This script creates 6-month and 1-year price forecasts for Singapore HDB
properties by planning area using Facebook Prophet time-series models.

Author: Automated Pipeline
Date: 2026-01-24
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

import pandas as pd
import numpy as np
from prophet import Prophet
from datetime import datetime, timedelta


@dataclass
class ForecastResult:
    """Container for forecast results."""
    planning_area: str
    property_type: str
    target: str
    forecast_horizon: str
    forecast_date: str
    predicted_value: float
    confidence_lower: float
    confidence_upper: float
    trend_pct: float
    model_r2: float
    last_training_date: str


def load_price_data(property_type: str = 'HDB') -> pd.DataFrame:
    """Load price data for forecasting."""
    
    if property_type == 'HDB':
        path = Path('data/parquets/L1/housing_hdb_transaction.parquet')
    else:
        path = Path('data/parquets/L1/housing_condo_transaction.parquet')
    
    df = pd.read_parquet(path)
    
    # Ensure month is datetime
    df['month'] = pd.to_datetime(df['month'])
    
    return df


def prepare_prophet_data(
    df: pd.DataFrame,
    planning_area: str,
    price_column: str = 'resale_price'
) -> pd.DataFrame:
    """Prepare data for Prophet model.

    Prophet requires columns named 'ds' (date) and 'y' (value).
    """
    # Filter by planning area
    area_df = df[df['planning_area'] == planning_area].copy()
    
    if len(area_df) < 12:
        return None  # Not enough data
    
    # Aggregate by month
    monthly = area_df.groupby('month')[price_column].median().reset_index()
    monthly.columns = ['ds', 'y']
    monthly = monthly.sort_values('ds')
    
    return monthly


def train_prophet_model(
    data: pd.DataFrame,
    planning_area: str,
    yearly_seasonality: bool = True,
    weekly_seasonality: bool = False
) -> Tuple[Prophet, float]:
    """Train Prophet model and return model with R² score."""
    
    model = Prophet(
        yearly_seasonality=yearly_seasonality,
        weekly_seasonality=weekly_seasonality,
        changepoint_prior_scale=0.05,  # Regularization
        seasonality_prior_scale=0.1
    )
    
    # Fit model
    model.fit(data)
    
    # Calculate R² on training data (in-sample)
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
    
    # Create future dates
    future = model.make_future_dataframe(
        periods=horizon_months * 30,  # Approximate days
        freq='D'
    )
    
    # Filter to only include dates after last training date
    future = future[future['ds'] > last_date]
    
    # Predict
    forecast = model.predict(future)
    
    # Aggregate to monthly
    forecast['ds'] = pd.to_datetime(forecast['ds']).dt.to_period('M').dt.to_timestamp()
    monthly_forecast = forecast.groupby('ds').agg({
        'yhat': 'mean',
        'yhat_lower': 'mean',
        'yhat_upper': 'mean'
    }).reset_index()
    
    return monthly_forecast


def calculate_trend_pct(
    last_actual: float,
    forecast_value: float
) -> float:
    """Calculate percentage change from last actual to forecast."""
    if last_actual <= 0:
        return np.nan
    return ((forecast_value - last_actual) / last_actual) * 100


def forecast_planning_area(
    df: pd.DataFrame,
    planning_area: str,
    price_column: str = 'resale_price',
    horizons: List[int] = [6, 12]  # months
) -> List[ForecastResult]:
    """Generate forecasts for a single planning area."""
    
    # Prepare Prophet data
    prophet_data = prepare_prophet_data(df, planning_area, price_column)
    
    if prophet_data is None or len(prophet_data) < 24:
        return []
    
    # Train model
    model, r2 = train_prophet_model(prophet_data, planning_area)
    
    # Get last actual value
    last_actual = prophet_data['y'].iloc[-1]
    last_date = prophet_data['ds'].max()
    
    results = []
    
    for horizon in horizons:
        # Generate forecast
        forecast_df = generate_forecast(model, horizon, last_date)
        
        if len(forecast_df) == 0:
            continue
        
        # Get final forecast value
        final_forecast = forecast_df.iloc[-1]
        
        # Calculate trend
        trend_pct = calculate_trend_pct(last_actual, final_forecast['yhat'])
        
        result = ForecastResult(
            planning_area=planning_area,
            property_type='HDB',
            target='median_price',
            forecast_horizon=f'{horizon}m',
            forecast_date=final_forecast['ds'].strftime('%Y-%m-%d'),
            predicted_value=round(final_forecast['yhat'], 2),
            confidence_lower=round(final_forecast['yhat_lower'], 2),
            confidence_upper=round(final_forecast['yhat_upper'], 2),
            trend_pct=round(trend_pct, 2),
            model_r2=round(r2, 4),
            last_training_date=last_date.strftime('%Y-%m-%d')
        )
        
        results.append(result)
    
    return results


def forecast_all_planning_areas(
    property_type: str = 'HDB',
    horizons: List[int] = [6, 12]
) -> Tuple[List[ForecastResult], pd.DataFrame]:
    """Generate forecasts for all planning areas."""
    
    print(f"Loading {property_type} price data...")
    df = load_price_data(property_type)
    
    # Get unique planning areas with sufficient data
    pa_counts = df.groupby('planning_area').size()
    valid_pas = pa_counts[pa_counts >= 100].index.tolist()
    
    print(f"Found {len(valid_pas)} planning areas with sufficient data")
    
    all_results = []
    failed_areas = []
    
    for i, pa in enumerate(valid_pas):
        print(f"  [{i+1}/{len(valid_pas)}] Forecasting {pa}...", end=' ')
        
        try:
            results = forecast_planning_area(
                df, pa,
                price_column='resale_price' if property_type == 'HDB' else 'Transacted Price ($)',
                horizons=horizons
            )
            
            if results:
                all_results.extend(results)
                print(f"OK (R²={results[0].model_r2:.3f})")
            else:
                print("Insufficient data")
                failed_areas.append(pa)
                
        except Exception as e:
            print(f"FAILED: {e}")
            failed_areas.append(pa)
    
    # Convert to DataFrame
    results_df = pd.DataFrame([r.__dict__ for r in all_results])
    
    print(f"\n{'='*60}")
    print(f"Forecasting complete: {len(results_df)} forecasts generated")
    print(f"Failed areas: {len(failed_areas)}")
    
    return all_results, results_df


def generate_summary(results_df: pd.DataFrame) -> None:
    """Generate summary statistics for forecasts."""
    
    print(f"\n{'='*60}")
    print("Forecast Summary")
    print(f"{'='*60}")
    
    # 6-month forecasts
    df_6m = results_df[results_df['forecast_horizon'] == '6m']
    print(f"\n6-Month Forecasts ({len(df_6m)} areas):")
    print(f"  Mean predicted change: {df_6m['trend_pct'].mean():.2f}%")
    print(f"  Range: {df_6m['trend_pct'].min():.2f}% to {df_6m['trend_pct'].max():.2f}%")
    print(f"  Average model R²: {df_6m['model_r2'].mean():.3f}")
    
    # Top gainers
    print(f"\n  Top 5 Expected Gainers:")
    top_gainers = df_6m.nlargest(5, 'trend_pct')[['planning_area', 'predicted_value', 'trend_pct']]
    for _, row in top_gainers.iterrows():
        print(f"    {row['planning_area']}: +{row['trend_pct']:.1f}% to ${row['predicted_value']:,.0f}")
    
    # 12-month forecasts
    df_12m = results_df[results_df['forecast_horizon'] == '12m']
    print(f"\n12-Month Forecasts ({len(df_12m)} areas):")
    print(f"  Mean predicted change: {df_12m['trend_pct'].mean():.2f}%")
    print(f"  Range: {df_12m['trend_pct'].min():.2f}% to {df_12m['trend_pct'].max():.2f}%")
    print(f"  Average model R²: {df_12m['model_r2'].mean():.3f}")
    
    # Top gainers
    print(f"\n  Top 5 Expected Gainers:")
    top_gainers = df_12m.nlargest(5, 'trend_pct')[['planning_area', 'predicted_value', 'trend_pct']]
    for _, row in top_gainers.iterrows():
        print(f"    {row['planning_area']}: +{row['trend_pct']:.1f}% to ${row['predicted_value']:,.0f}")


def main():
    """Main execution function."""
    
    output_dir = Path('data/forecasts')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("="*60)
    print("Housing Price Forecasting Pipeline")
    print("="*60)
    
    # Generate forecasts for HDB
    print("\n[1/1] Forecasting HDB prices...")
    results, results_df = forecast_all_planning_areas(
        property_type='HDB',
        horizons=[6, 12]
    )
    
    # Generate summary
    generate_summary(results_df)
    
    # Save results
    output_path = output_dir / 'hdb_price_forecasts.parquet'
    results_df.to_parquet(output_path, index=False)
    print(f"\nSaved forecasts to: {output_path}")
    
    # Also save as CSV for easy inspection
    csv_path = output_dir / 'hdb_price_forecasts.csv'
    results_df.to_csv(csv_path, index=False)
    print(f"Saved CSV to: {csv_path}")
    
    print("\n" + "="*60)
    print("Forecasting complete!")
    print("="*60)
    
    return results, results_df


if __name__ == '__main__':
    main()
