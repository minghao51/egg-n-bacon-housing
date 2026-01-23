# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.19.0
#   kernelspec:
#     display_name: demo
#     language: python
#     name: python3
# ---

# %%
"""
L2 Sales Facilities Notebook

This notebook runs the L2 features pipeline which creates:
- Property table
- Private property facilities
- Nearby facilities
- Transaction sales
- Listing sales

Usage:
    Run all cells to execute the pipeline
    Or call: from src.pipeline.L2_features import run_l2_features_pipeline; run_l2_features_pipeline()
"""

# %%
import sys
from pathlib import Path

# Add src directory to path for imports
sys.path.append(str(Path(__file__).parent.parent / 'src'))

# %%
from src.pipeline.L2_features import run_l2_features_pipeline

# %%
# Run the L2 features pipeline
results = run_l2_features_pipeline()

# %%
# Display results summary
print(f"\n✅ Pipeline completed successfully!")
print(f"Property records: {len(results['property_df']):,}")
print(f"Facility records: {len(results['private_facilities']):,}")
print(f"Nearby records: {len(results['nearby_df']):,}")
print(f"Transaction sales: {len(results['transaction_sales']):,}")
print(f"Listing sales: {len(results['listing_sales']):,}")
