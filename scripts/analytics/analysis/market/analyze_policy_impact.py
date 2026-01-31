#!/usr/bin/env python3
"""
Analyze Policy Impact using Difference-in-Differences (DiD).

Estimates causal effects of policy interventions on housing markets.

Usage:
    uv run python scripts/analysis/analyze_policy_impact.py --help
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.core.config import Config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    import statsmodels.api as sm
    STATSMODELS_AVAILABLE = True
except ImportError:
    STATSMODELS_AVAILABLE = False
    logger.warning("statsmodels not available")


def load_transaction_data() -> pd.DataFrame:
    """Load HDB transaction data."""
    logger.info("Loading transaction data...")
    
    path = Config.PARQUETS_DIR / "L1" / "housing_hdb_transaction.parquet"
    if not path.exists():
        logger.error(f"Transaction data not found: {path}")
        return pd.DataFrame()
    
    df = pd.read_parquet(path)
    df['month'] = pd.to_datetime(df['month'], format='%Y-%m')
    df['year'] = df['month'].dt.year
    
    logger.info(f"Loaded {len(df):,} transaction records")
    return df


def define_regions(df: pd.DataFrame) -> pd.DataFrame:
    """Define treatment and control regions."""
    logger.info("Defining treatment/control regions...")
    
    central_towns = [
        'CENTRAL AREA', 'DOWNTOWN CORE', 'MARINA SOUTH', 'MUSEUM',
        'ORCHARD', 'RIVER VALLEY', 'ROCHOR', 'SINGAPORE RIVER',
        'SOUTHERN ISLANDS', 'STRAITS VIEW', 'BUKIT TIMAH', 'CHOA CHU KANG'
    ]
    
    if 'town' in df.columns:
        df['region'] = df['town'].apply(
            lambda x: 'CCR' if x.upper() in [t.upper() for t in central_towns] else 'OCR'
        )
    else:
        df['region'] = 'OCR'
    
    region_counts = df.groupby('region').size()
    logger.info(f"  CCR: {region_counts.get('CCR', 0):,} records")
    logger.info(f"  OCR: {region_counts.get('OCR', 0):,} records")
    
    return df


def run_did_analysis(
    df: pd.DataFrame,
    policy_date: str,
    treatment: str = 'CCR',
    control: str = 'OCR',
    pre_months: int = 12,
    post_months: int = 24
) -> dict:
    """Run Difference-in-Differences analysis."""
    logger.info(f"Running DiD analysis (policy: {policy_date})...")
    
    policy_dt = pd.to_datetime(policy_date)
    
    df = df[(df['month'] >= policy_dt - pd.DateOffset(months=pre_months)) &
            (df['month'] <= policy_dt + pd.DateOffset(months=post_months))]
    
    df['post'] = (df['month'] >= policy_dt).astype(int)
    df['treatment'] = (df['region'] == treatment).astype(int)
    df['did'] = df['post'] * df['treatment']
    
    treatment_data = df[df['region'] == treatment]
    control_data = df[df['region'] == control]
    
    pre_treatment = treatment_data[treatment_data['post'] == 0]['resale_price'].mean()
    post_treatment = treatment_data[treatment_data['post'] == 1]['resale_price'].mean()
    pre_control = control_data[control_data['post'] == 0]['resale_price'].mean()
    post_control = control_data[control_data['post'] == 1]['resale_price'].mean()
    
    did_estimate = (post_treatment - pre_treatment) - (post_control - pre_control)
    
    df_model = df[['resale_price', 'post', 'treatment', 'did']].dropna()
    
    X = df_model[['post', 'treatment', 'did']]
    X = sm.add_constant(X)
    y = df_model['resale_price']
    
    model = sm.OLS(y, X).fit()
    
    return {
        'did_estimate': did_estimate,
        'coefficient': model.params.get('did', did_estimate),
        'std_error': model.bse.get('did', 0),
        't_stat': model.tvalues.get('did', 0),
        'p_value': model.pvalues.get('did', 1),
        'r_squared': model.rsquared,
        'pre_treatment_treatment': pre_treatment,
        'post_treatment_treatment': post_treatment,
        'pre_treatment_control': pre_control,
        'post_treatment_control': post_control
    }


def summarize_results(result: dict, policy_date: str) -> list:
    """Generate key findings summary."""
    findings = []
    
    findings.append(f"Policy date: {policy_date}")
    findings.append(f"DiD estimate: ${result['did_estimate']:,.0f}")
    findings.append(f" Coefficient: ${result['coefficient']:,.0f}")
    findings.append(f" P-value: {result['p_value']:.4f}")
    
    if result['p_value'] < 0.01:
        significance = "Highly significant (p < 0.01)"
    elif result['p_value'] < 0.05:
        significance = "Significant (p < 0.05)"
    elif result['p_value'] < 0.1:
        significance = "Marginally significant (p < 0.1)"
    else:
        significance = "Not significant"
    
    findings.append(f"Significance: {significance}")
    findings.append(f" R-squared: {result['r_squared']:.4f}")
    
    treatment_change = ((result['post_treatment_treatment'] - result['pre_treatment_treatment']) 
                        / result['pre_treatment_treatment'] * 100)
    control_change = ((result['post_treatment_control'] - result['pre_treatment_control']) 
                      / result['pre_treatment_control'] * 100)
    
    findings.append(f"Treatment change: {treatment_change:.1f}%")
    findings.append(f"Control change: {control_change:.1f}%")
    
    return findings


def main():
    start_time = datetime.now()
    
    logger.info("="*60)
    logger.info("POLICY IMPACT ANALYSIS (Difference-in-Differences)")
    logger.info("="*60)
    
    if not STATSMODELS_AVAILABLE:
        logger.error("statsmodels not available")
        return
    
    policy_date = "2020-07-01"
    treatment = "CCR"
    control = "OCR"
    
    df = load_transaction_data()
    if df.empty:
        logger.error("No data available")
        return
    
    df = define_regions(df)
    
    result = run_did_analysis(df, policy_date, treatment, control)
    
    output_dir = Config.ANALYSIS_OUTPUT_DIR / "analyze_policy_impact"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    result_df = pd.DataFrame([result])
    result_df.to_csv(output_dir / "did_results.csv", index=False)
    logger.info(f"Saved: {output_dir / 'did_results.csv'}")
    
    findings = summarize_results(result, policy_date)
    for f in findings:
        logger.info(f"  {f}")
    
    duration = (datetime.now() - start_time).total_seconds()
    
    print(json.dumps({
        "script": "analyze_policy_impact",
        "status": "success",
        "key_findings": findings,
        "outputs": [str(output_dir / "did_results.csv")],
        "duration_seconds": round(duration, 2)
    }))
    
    logger.info("="*60)
    logger.info("Policy impact analysis complete!")
    logger.info("="*60)


if __name__ == "__main__":
    main()
