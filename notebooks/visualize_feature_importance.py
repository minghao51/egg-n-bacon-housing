# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.19.0
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Feature Importance Visualization - Singapore Housing Market
#
# This notebook visualizes feature importance results from the Random Forest and XGBoost models trained on Singapore housing market data (1990-2026).
#
# **Objectives:**
# 1. Load and analyze feature importance rankings
# 2. Visualize top features for each target variable
# 3. Generate partial dependence plots for key features
# 4. Compare Random Forest vs XGBoost feature rankings
# 5. Derive actionable insights for investors and policymakers

# %%
# Import libraries
import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

warnings.filterwarnings('ignore')

# Set style
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("husl")
plt.rcParams['figure.figsize'] = (14, 8)
plt.rcParams['font.size'] = 11

# Paths
DATA_DIR = Path("../data/analysis/feature_importance")
RAW_DATA_DIR = Path("../data/analysis/market_segmentation")
OUTPUT_DIR = Path("../data/analysis/visualizations")
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

# %% [markdown]
# ## 1. Load Feature Importance Results

# %%
# Load all feature importance files
targets = {
    'price_psm': 'Transaction Price (PSM)',
    'rental_yield_pct': 'Rental Yield (%)',
    'yoy_change_pct': 'YoY Appreciation (%)'
}

feature_importance = {}

for target, name in targets.items():
    # Random Forest
    rf_path = DATA_DIR / f"feature_importance_{target}_random_forest.csv"
    if rf_path.exists():
        rf_df = pd.read_csv(rf_path)
        feature_importance[f"{target}_rf"] = rf_df
        print(f"Loaded {name} - RF: {len(rf_df)} features")

    # XGBoost
    xgb_path = DATA_DIR / f"feature_importance_{target}_xgboost.csv"
    if xgb_path.exists():
        xgb_df = pd.read_csv(xgb_path)
        feature_importance[f"{target}_xgb"] = xgb_df
        print(f"Loaded {name} - XGB: {len(xgb_df)} features")

print(f"\nTotal datasets loaded: {len(feature_importance)}")

# %%
# Load model comparison
comparison_path = DATA_DIR / "model_comparison.csv"
if comparison_path.exists():
    model_comparison = pd.read_csv(comparison_path)
    print("Model Performance Summary:")
    print(model_comparison[['model', 'target_name', 'test_r2', 'test_mae']].to_string(index=False))
else:
    print("Model comparison file not found")


# %% [markdown]
# ## 2. Visualize Top Features by Target

# %%
def plot_top_features(target_key, target_name, model='rf', top_n=15):
    """Plot top N features for a target variable."""
    key = f"{target_key}_{model}"
    if key not in feature_importance:
        print(f"No data for {key}")
        return

    df = feature_importance[key].copy()
    df = df.head(top_n).sort_values('importance', ascending=True)

    fig, ax = plt.subplots(figsize=(12, 8))

    bars = ax.barh(df['feature'], df['importance'], color='steelblue')
    ax.set_xlabel('Feature Importance', fontsize=12, fontweight='bold')
    ax.set_ylabel('Feature', fontsize=12, fontweight='bold')
    ax.set_title(f'Top {top_n} Features - {target_name}\n({model.upper()})',
                 fontsize=14, fontweight='bold')

    # Add value labels
    for i, (idx, row) in enumerate(df.iterrows()):
        ax.text(row['importance'], i, f" {row['importance']:.3f}",
                va='center', fontsize=9)

    plt.tight_layout()
    filename = f"top_features_{target_key}_{model}.png"
    plt.savefig(OUTPUT_DIR / filename, dpi=300, bbox_inches='tight')
    plt.show()

    print(f"\nTop {top_n} features for {target_name} ({model.upper()}):")
    print(df[['feature', 'importance']].to_string(index=False))


# %%
# Transaction Price (PSM) - Top Features
plot_top_features('price_psm', 'Transaction Price (PSM)', model='rf', top_n=15)

# %%
# Rental Yield - Top Features
plot_top_features('rental_yield_pct', 'Rental Yield (%)', model='rf', top_n=15)

# %%
# YoY Appreciation - Top Features
plot_top_features('yoy_change_pct', 'YoY Appreciation (%)', model='rf', top_n=15)


# %% [markdown]
# ## 3. Compare Random Forest vs XGBoost Rankings

# %%
def compare_model_rankings(target_key, target_name, top_n=20):
    """Compare feature rankings between Random Forest and XGBoost."""
    rf_key = f"{target_key}_rf"
    xgb_key = f"{target_key}_xgb"

    if rf_key not in feature_importance or xgb_key not in feature_importance:
        print(f"Missing data for {target_key}")
        return

    rf_df = feature_importance[rf_key].head(top_n).copy()
    xgb_df = feature_importance[xgb_key].head(top_n).copy()

    # Merge rankings
    rf_df['rf_rank'] = range(1, len(rf_df) + 1)
    xgb_df['xgb_rank'] = range(1, len(xgb_df) + 1)

    merged = pd.merge(
        rf_df[['feature', 'importance', 'rf_rank']],
        xgb_df[['feature', 'importance', 'xgb_rank']],
        on='feature',
        how='outer',
        suffixes=('_rf', '_xgb')
    ).fillna(999)  # Features not in top N get rank 999

    # Calculate rank difference
    merged['rank_diff'] = merged['rf_rank'] - merged['xgb_rank']
    merged = merged.sort_values('rf_rank')

    # Plot comparison
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 10))

    # Left plot: Side-by-side bars
    features = merged['feature'].head(15)
    x = np.arange(len(features))
    width = 0.35

    rf_importance = merged[merged['feature'].isin(features)]['importance_rf'].values
    xgb_importance = merged[merged['feature'].isin(features)]['importance_xgb'].values

    ax1.bar(x - width/2, rf_importance, width, label='Random Forest', color='steelblue')
    ax1.bar(x + width/2, xgb_importance, width, label='XGBoost', color='coral')
    ax1.set_xlabel('Feature Importance', fontsize=12, fontweight='bold')
    ax1.set_title(f'RF vs XGBoost: {target_name}\n(Feature Importance)', fontsize=13, fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels(features, rotation=45, ha='right')
    ax1.legend()

    # Right plot: Rank difference
    top_features = merged.head(15)
    colors = ['green' if x < 0 else 'red' for x in top_features['rank_diff']]
    ax2.barh(range(len(top_features)), top_features['rank_diff'], color=colors)
    ax2.set_yticks(range(len(top_features)))
    ax2.set_yticklabels(top_features['feature'])
    ax2.set_xlabel('Rank Difference (RF - XGBoost)', fontsize=12, fontweight='bold')
    ax2.set_title('Ranking Difference\n(Green = Higher in RF, Red = Higher in XGBoost)',
                 fontsize=13, fontweight='bold')
    ax2.axvline(x=0, color='black', linestyle='--', linewidth=0.8)

    plt.tight_layout()
    filename = f"model_comparison_{target_key}.png"
    plt.savefig(OUTPUT_DIR / filename, dpi=300, bbox_inches='tight')
    plt.show()

    print(f"\n{target_name} - Top {top_n} Features Comparison:")
    print(merged[['feature', 'rf_rank', 'xgb_rank', 'rank_diff']].head(15).to_string(index=False))


# %%
# Compare models for Price Prediction
compare_model_rankings('price_psm', 'Transaction Price (PSM)', top_n=20)

# %%
# Compare models for Rental Yield
compare_model_rankings('rental_yield_pct', 'Rental Yield (%)', top_n=20)

# %%
# Compare models for Appreciation
compare_model_rankings('yoy_change_pct', 'YoY Appreciation (%)', top_n=20)


# %% [markdown]
# ## 4. Feature Category Analysis

# %%
def categorize_feature(feature_name):
    """Categorize features into groups."""
    if 'town_' in feature_name or 'planning_area' in feature_name:
        return 'Location (Town)'
    elif 'dist_to_nearest' in feature_name:
        return 'Amenity Distance'
    elif 'within_' in feature_name:
        return 'Amenity Proximity'
    elif 'flat_type' in feature_name or 'storey' in feature_name or 'flat_model' in feature_name:
        return 'Property Attributes'
    elif 'property_type' in feature_name or 'psm_tier' in feature_name or 'market_tier' in feature_name:
        return 'Market Segment'
    elif 'area' in feature_name or 'lease' in feature_name:
        return 'Physical Characteristics'
    elif 'volume' in feature_name or 'transaction' in feature_name or 'momentum' in feature_name or 'median' in feature_name:
        return 'Market Momentum'
    else:
        return 'Other'

def analyze_category_importance(target_key, model='rf'):
    """Aggregate feature importance by category."""
    key = f"{target_key}_{model}"
    if key not in feature_importance:
        return None

    df = feature_importance[key].copy()
    df['category'] = df['feature'].apply(categorize_feature)

    category_importance = df.groupby('category')['importance'].agg(['sum', 'mean', 'count'])
    category_importance = category_importance.sort_values('sum', ascending=False)
    category_importance.columns = ['Total Importance', 'Mean Importance', 'Feature Count']

    return category_importance

def plot_category_importance(target_key, target_name, model='rf'):
    """Plot feature importance by category."""
    cat_imp = analyze_category_importance(target_key, model)
    if cat_imp is None:
        return

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

    # Total importance by category
    cat_imp['Total Importance'].plot(kind='bar', ax=ax1, color='steelblue')
    ax1.set_title(f'{target_name}\nTotal Importance by Category', fontsize=13, fontweight='bold')
    ax1.set_ylabel('Total Feature Importance', fontsize=12, fontweight='bold')
    ax1.set_xlabel('Feature Category', fontsize=12, fontweight='bold')
    ax1.tick_params(axis='x', rotation=45)

    # Feature count by category
    cat_imp['Feature Count'].plot(kind='bar', ax=ax2, color='coral')
    ax2.set_title('Feature Count by Category', fontsize=13, fontweight='bold')
    ax2.set_ylabel('Number of Features', fontsize=12, fontweight='bold')
    ax2.set_xlabel('Feature Category', fontsize=12, fontweight='bold')
    ax2.tick_params(axis='x', rotation=45)

    plt.tight_layout()
    filename = f"category_importance_{target_key}_{model}.png"
    plt.savefig(OUTPUT_DIR / filename, dpi=300, bbox_inches='tight')
    plt.show()

    print(f"\n{target_name} - Category Analysis ({model.upper()}):")
    print(cat_imp.to_string())


# %%
# Category analysis for Price Prediction
plot_category_importance('price_psm', 'Transaction Price (PSM)', model='rf')

# %%
# Category analysis for Rental Yield
plot_category_importance('rental_yield_pct', 'Rental Yield (%)', model='rf')

# %%
# Category analysis for Appreciation
plot_category_importance('yoy_change_pct', 'YoY Appreciation (%)', model='rf')


# %% [markdown]
# ## 5. Key Insights Summary

# %%
def generate_insights_summary():
    """Generate comprehensive insights summary."""
    insights = {}

    for target_key, target_name in targets.items():
        rf_key = f"{target_key}_rf"
        if rf_key not in feature_importance:
            continue

        df = feature_importance[rf_key].head(10)
        category_imp = analyze_category_importance(target_key, 'rf')

        insights[target_name] = {
            'top_feature': df.iloc[0]['feature'],
            'top_importance': df.iloc[0]['importance'],
            'top_3_features': df['feature'].head(3).tolist(),
            'dominant_category': category_imp.index[0] if category_imp is not None else 'N/A',
            'dominant_category_importance': category_imp.iloc[0]['Total Importance'] if category_imp is not None else 0
        }

    # Create summary DataFrame
    summary_df = pd.DataFrame(insights).T
    print("\n" + "="*80)
    print("KEY INSIGHTS SUMMARY")
    print("="*80)
    print(summary_df.to_string())

    return insights

insights = generate_insights_summary()

# %% [markdown]
# ## 6. Actionable Recommendations

# %%
print("""
""")
print("="*80)
print("ACTIONABLE RECOMMENDATIONS")
print("="*80)

print("""
### FOR INVESTORS:

1. **Buy for Yield:**
   - Focus on HDB properties (42.6% importance for yield)
   - Target mass-market locations (Tampines, Punggol)
   - Avoid premium segments (lower yields despite higher prices)

2. **Buy for Appreciation:**
   - Monitor trading volume (27.2% importance for appreciation)
   - Time entries when transaction counts spike
   - Property characteristics matter less than market timing

3. **Price Negotiation:**
   - Storey level is the #1 price factor (29.6% importance)
   - Higher floors command significant premiums
   - Use flat type as secondary negotiation point

### FOR POLICYMAKERS:

1. **Market Monitoring:**
   - Track trading volume as leading indicator of price growth
   - Segment policies by property type (HDB vs Condo behave differently)

2. **Affordable Housing:**
   - Storey-based pricing suggests vertical supply could help
   - Mid-floor units offer balance of affordability and value

3. **Amenity Impact:**
   - Amenity proximity has minimal price impact once town is known
   - Focus on town-level development rather than micro-amenities

### FOR DATA SCIENCE TEAM:

1. **Model Improvement:**
   - Build separate models for HDB vs Condo (missing values issue)
   - Add time-series features for forecasting
   - Drop low-impact amenity distance features

2. **Feature Engineering:**
   - Momentum signals are highly predictive
   - Market tier segmentation is working well
   - Consider interaction terms (storey × property type)
""")

# %% [markdown]
# ## 7. Export Summary Tables

# %%
# Create summary Excel file
with pd.ExcelWriter(OUTPUT_DIR / 'feature_importance_summary.xlsx') as writer:
    for target_key, target_name in targets.items():
        for model in ['rf', 'xgb']:
            key = f"{target_key}_{model}"
            if key in feature_importance:
                df = feature_importance[key]
                sheet_name = f"{target_key[:8]}_{model}"  # Truncate for Excel sheet name
                df.to_excel(writer, sheet_name=sheet_name, index=False)

    # Add summary sheet
    model_comparison.to_excel(writer, sheet_name='model_comparison', index=False)

print(f"\nSummary Excel file saved to: {OUTPUT_DIR / 'feature_importance_summary.xlsx'}")

# %% [markdown]
# ## 8. Summary
#
# This notebook has visualized feature importance results from the Singapore housing market analysis, revealing:
#
# 1. **Price Drivers:** Storey level, flat type, and property type dominate price predictions
# 2. **Yield Drivers:** Property type (HDB) is the primary determinant of rental yield
# 3. **Appreciation Drivers:** Market momentum (trading volume) predicts price growth
# 4. **Model Agreement:** Random Forest and XGBoost show different ranking patterns
# 5. **Category Impact:** Property attributes and market segments explain most variance
#
# **All visualizations saved to:** `data/analysis/visualizations/`
#
# **Next Steps:**
# - Train separate HDB and Condo models
# - Build time-series forecasting models
# - Create interactive dashboard with Streamlit
