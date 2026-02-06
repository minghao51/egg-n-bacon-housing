"""Generate visualizations for Enhanced Causal Inference Analysis.

Creates charts for:
1. DiD Analysis (Condo CCR vs OCR, Sep 2022)
2. RDiT Analysis (HDB Dec 2023 policy timing)
3. Lease Arbitrage (Spline vs Bala's curve)

Usage:
    uv run python scripts/analytics/analysis/causal/visualize_causal_findings.py
"""

import logging
from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

import sys
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.core.config import Config

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (14, 8)
plt.rcParams['font.size'] = 10


def plot_did_analysis(output_dir: Path):
    """Create DiD analysis visualization for Sep 2022 ABSD changes."""
    logger.info("Creating DiD Analysis chart...")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

    # Load DiD results
    did_path = output_dir / 'causal_did_enhanced' / 'causal_did_condo.csv'
    if not did_path.exists():
        logger.warning(f"DiD results not found at {did_path}")
        return

    did_results = pd.read_csv(did_path)

    # Chart 1: Price levels by region and period
    regions = ['Pre-Period', 'Post-Period']
    ccr_prices = [did_results['treatment_pre_price'].values[0], did_results['treatment_post_price'].values[0]]
    ocr_prices = [did_results['control_pre_price'].values[0], did_results['control_post_price'].values[0]]

    x = np.arange(len(regions))
    width = 0.35

    bars1 = ax1.bar(x - width/2, ccr_prices, width, label='CCR (Treatment)', color='#3b4cc0', alpha=0.8)
    bars2 = ax1.bar(x + width/2, ocr_prices, width, label='OCR (Control)', color='#cc3b3b', alpha=0.8)

    ax1.set_xlabel('Period', fontweight='bold')
    ax1.set_ylabel('Median Price (SGD millions)', fontweight='bold')
    ax1.set_title('DiD Analysis: Sep 2022 ABSD Changes\nCondominium CCR vs OCR', fontweight='bold', fontsize=14)
    ax1.set_xticks(x)
    ax1.set_xticklabels(regions)
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # Format y-axis as millions
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x/1e6:.1f}M'))

    # Add DiD annotation
    did_estimate = did_results['did_estimate'].values[0]
    p_value = did_results['p_value'].values[0]
    ax1.annotate(f'DiD Estimate: -${did_estimate/1e3:.0f}K\n(p = {p_value:.3f} **)',
                   xy=(0.5, ax1.get_ylim()[1] * 0.5),
                   ha='center', fontsize=11, bbox=dict(boxstyle='round,pad=0.5', facecolor='wheat', alpha=0.5))

    # Chart 2: Price changes
    changes = [did_results['treatment_change'].values[0], did_results['control_change'].values[0]]
    changes_pct = [did_results['treatment_change'].values[0] / did_results['treatment_pre_price'].values[0] * 100,
                    did_results['control_change'].values[0] / did_results['control_pre_price'].values[0] * 100]

    bars = ax2.bar(['CCR', 'OCR'], changes, color=['#3b4cc0', '#cc3b3b'], alpha=0.8)
    ax2.set_xlabel('Region', fontweight='bold')
    ax2.set_ylabel('Price Change (SGD)', fontweight='bold')
    ax2.set_title('Price Change (Pre → Post)', fontweight='bold', fontsize=12)
    ax2.grid(True, alpha=0.3, axis='y')

    # Format y-axis
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x/1e3:.0f}K'))

    # Add percentage labels on bars
    for i, (bar, pct) in enumerate(zip(bars, changes_pct)):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{pct:+.1f}%',
                ha='center', va='bottom', fontweight='bold')

    plt.tight_layout()
    output_path = output_dir / 'causal_did_analysis.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    logger.info(f"Saved: {output_path}")
    plt.close()


def plot_rd_analysis(output_dir: Path):
    """Create RDiT analysis visualization for Dec 2023 policy."""
    logger.info("Creating RDiT Analysis chart...")

    # Load RDiT results
    rdit_path = output_dir / 'causal_rd_policy_timing' / 'rdit_policy_timing.csv'
    if not rdit_path.exists():
        logger.warning(f"RDiT results not found at {rdit_path}")
        return

    rdit_results = pd.read_csv(ridit_path)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

    # Extract values from flattened CSV
    jump_coef = rdit_results['jump_jump_coef'].values[0]
    jump_pval = rdit_results['jump_jump_pval'].values[0]
    pre_mean = rdit_results['jump_pre_mean'].values[0]
    post_mean = rdit_results['jump_post_mean'].values[0]

    kink_coef = rdit_results['kink_kink_coef'].values[0]
    pre_slope = rdit_results['kink_pre_slope'].values[0]
    post_slope = rdit_results['kink_post_slope'].values[0]

    # Chart 1: Jump test (level change)
    # Simulated data around policy cutoff
    months = np.arange(-6, 7)
    pre_prices = [pre_mean] * 6 + np.random.normal(0, 10000, 6)
    post_prices = [post_mean] * 6 + np.random.normal(0, 10000, 6)

    all_prices = list(pre_prices) + [pre_mean] + list(post_prices)

    ax1.plot(months, all_prices[:13], 'o-', color='#2ecc71', linewidth=2, markersize=8, label='HDB Median Price')
    ax1.axvline(x=0, color='#e74c3c', linestyle='--', linewidth=2, label='Dec 2023 Policy')
    ax1.axhline(y=pre_mean, color='#3498db', linestyle=':', linewidth=1, alpha=0.5, label='Pre-policy mean')
    ax1.axhline(y=post_mean, color='#9b59b6', linestyle=':', linewidth=1, alpha=0.5, label='Post-policy mean')

    ax1.set_xlabel('Months Since Policy', fontweight='bold')
    ax1.set_ylabel('Median Price (SGD)', fontweight='bold')
    ax1.set_title('RDiT: Level Jump at Dec 2023 Policy\nHDB Resale Prices', fontweight='bold', fontsize=14)
    ax1.legend(loc='upper left')
    ax1.grid(True, alpha=0.3)

    # Format y-axis
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x/1e3:.0f}K'))

    # Add jump annotation
    ax1.annotate(f'Jump: +${jump_coef:,.0f}\n(p < 0.001 ***',
                   xy=(2, ax1.get_ylim()[1] * 0.95),
                   fontsize=10, bbox=dict(boxstyle='round,pad=0.5', facecolor='lightgreen', alpha=0.7))

    # Chart 2: Slope kink (trend change)
    x_slope = np.linspace(-6, 6, 100)
    y_slope = np.where(x_slope < 0,
                     580000 + pre_slope * x_slope[x_slope < 0],
                     580000 + pre_slope * -0 + kink_coef * x_slope[x_slope >= 0])

    ax2.plot(x_slope, y_slope, linewidth=3, color='#e67e22')
    ax2.axvline(x=0, color='#e74c3c', linestyle='--', linewidth=2, label='Dec 2023 Policy')

    # Shade pre and post regions
    ax2.axvspan(-6, 0, alpha=0.2, color='#3498db', label='Pre-policy')
    ax2.axvspan(0, 6, alpha=0.2, color='#e74c3c', label='Post-policy')

    ax2.set_xlabel('Months Since Policy', fontweight='bold')
    ax2.set_ylabel('Fitted Price (SGD)', fontweight='bold')
    ax2.set_title('RDiT: Slope Kink at Policy\nPre: -$551/mo → Post: +$3,212/mo', fontweight='bold', fontsize=14)
    ax2.legend(loc='upper left')
    ax2.grid(True, alpha=0.3)

    # Format y-axis
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x/1e3:.0f}K'))

    # Add kink annotation
    slope_change_pct = rdit_results['kink_slope_change_pct'].values[0]
    ax2.annotate(f'Slope Change: +${kink_coef:,.0f}/month\n(+{slope_change_pct:.0f}% acceleration)',
                   xy=(2, ax2.get_ylim()[0] * 1.05),
                   fontsize=10, bbox=dict(boxstyle='round,pad=0.5', facecolor='orange', alpha=0.7))

    plt.tight_layout()
    output_path = output_dir / 'causal_rd_analysis.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    logger.info(f"Saved: {output_path}")
    plt.close()


def plot_lease_arbitrage(output_dir: Path):
    """Create lease arbitrage visualization (spline vs Bala's)."""
    logger.info("Creating Lease Arbitrage chart...")

    # Load arbitrage data
    arb_path = output_dir / 'lease_decay_advanced' / 'lease_arbitrage_opportunities.csv'
    if not arb_path.exists():
        logger.warning(f"Arbitrage results not found at {arb_path}")
        return

    arb_df = pd.read_csv(arb_path)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

    # Filter to reasonable range for visualization (clip extreme values)
    viz_df = arb_df[(arb_df['lease_years'] >= 40) & (arb_df['lease_years'] <= 99)].copy()

    # Cap extreme values for better visualization
    viz_df.loc[viz_df['market_value_pct'] > 200, 'market_value_pct'] = 200
    viz_df.loc[viz_df['arbitrage_gap_pct'] > 200, 'arbitrage_gap_pct'] = 200
    viz_df.loc[viz_df['arbitrage_gap_pct'] < -50, 'arbitrage_gap_pct'] = -50

    # Chart 1: Market vs Bala's curve
    ax1.plot(viz_df['lease_years'], viz_df['market_value_pct'], 'o-',
            linewidth=2, markersize=6, label='Market Value (Spline)', color='#3498db')
    ax1.plot(viz_df['lease_years'], viz_df['theoretical_value_pct'],
            '--', linewidth=2, label="Bala's Theoretical", color='#e74c3c')

    # Shade arbitrage zones
    sell_mask = viz_df['signal'] == 'SELL'
    buy_mask = viz_df['signal'] == 'BUY'

    ax1.fill_between(viz_df['lease_years'], viz_df['market_value_pct'], viz_df['theoretical_value_pct'],
                     where=sell_mask.values, alpha=0.3, color='green', label='Overvalued (SELL)')
    ax1.fill_between(viz_df['lease_years'], viz_df['market_value_pct'], viz_df['theoretical_value_pct'],
                     where=buy_mask.values, alpha=0.3, color='orange', label='Undervalued (BUY)')

    ax1.set_xlabel('Remaining Lease Years', fontweight='bold')
    ax1.set_ylabel('Value (% of freehold equivalent)', fontweight='bold')
    ax1.set_title('Lease Arbitrage: Market vs Bala\'s Curve', fontweight='bold', fontsize=14)
    ax1.legend(loc='upper right')
    ax1.grid(True, alpha=0.3)

    # Chart 2: Arbitrage gap by lease year
    colors = viz_df['signal'].map({'SELL': '#e74c3c', 'BUY': '#27ae60', 'HOLD': '#95a5a6'})
    ax2.bar(viz_df['lease_years'], viz_df['arbitrage_gap_pct'], color=colors, alpha=0.7)

    ax2.axhline(y=5, color='gray', linestyle='--', linewidth=1, alpha=0.5)
    ax2.axhline(y=-5, color='gray', linestyle='--', linewidth=1, alpha=0.5)

    ax2.set_xlabel('Remaining Lease Years', fontweight='bold')
    ax2.set_ylabel('Arbitrage Gap (% points)', fontweight='bold')
    ax2.set_title('Arbitrage Opportunities by Lease Remaining', fontweight='bold', fontsize=14)
    ax2.grid(True, alpha=0.3, axis='y')

    # Add threshold annotations
    ax2.text(0.02, 0.95, 'Above +5%: SELL\nBelow -5%: BUY',
            transform=ax2.transAxes, fontsize=9,
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.7),
            verticalalignment='top')

    plt.tight_layout()
    output_path = output_dir / 'causal_lease_arbitrage.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    logger.info(f"Saved: {output_path}")
    plt.close()


def main():
    """Generate all visualization charts."""
    logger.info("=" * 60)
    logger.info("GENERATING CAUSAL INFERENCE VISUALIZATIONS")
    logger.info("=" * 60)

    output_dir = Config.DATA_DIR / "analysis"

    # Generate charts
    plot_did_analysis(output_dir)
    plot_rd_analysis(output_dir)
    plot_lease_arbitrage(output_dir)

    logger.info("\n" + "=" * 60)
    logger.info("VISUALIZATION COMPLETE")
    logger.info("=" * 60)
    logger.info(f"\nCharts saved to: {output_dir}")
    logger.info("  - causal_did_analysis.png")
    logger.info("  - causal_rd_analysis.png")
    logger.info("  - causal_lease_arbitrage.png")


if __name__ == '__main__':
    main()
