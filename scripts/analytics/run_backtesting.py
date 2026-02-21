# scripts/analytics/run_backtesting.py
"""
Run backtesting validation for VAR/ARIMAX forecasting system.
"""

import logging

from scripts.analytics.pipelines.cross_validate_timeseries import run_cross_validation
from scripts.analytics.pipelines.prepare_timeseries_data import run_preparation_pipeline
from scripts.core.config import Config

logger = logging.getLogger(__name__)


def main():
    """Run complete backtesting pipeline."""
    logger.info("=" * 80)
    logger.info("VAR Housing Appreciation - Backtesting & Validation")
    logger.info("=" * 80)

    # Step 1: Prepare time series data
    logger.info("\n" + "=" * 80)
    logger.info("STEP 1: Preparing Time Series Data")
    logger.info("=" * 80)

    try:
        regional_data, area_data = run_preparation_pipeline(
            start_date='2021-01',
            end_date='2026-02'
        )

        logger.info("\nTime series preparation complete!")
        logger.info(f"   Regional: {len(regional_data)} records, {len(regional_data['region'].unique())} regions")
        logger.info(f"   Area: {len(area_data)} records, {len(area_data['area'].unique())} areas")

    except Exception as e:
        logger.error(f"Time series preparation failed: {e}")
        return

    # Step 2: Run cross-validation
    logger.info("\n" + "=" * 80)
    logger.info("STEP 2: Running Cross-Validation")
    logger.info("=" * 80)

    try:
        cv_results = run_cross_validation(
            regional_data=regional_data,
            area_data=area_data,
            n_folds=5
        )

        # Log regional results
        logger.info("\n" + "-" * 80)
        logger.info("REGIONAL VAR MODEL RESULTS")
        logger.info("-" * 80)

        for region, results in cv_results['regional'].items():
            if 'mean_rmse' in results:
                logger.info(f"\n{region}:")
                logger.info(f"  RMSE: {results['mean_rmse']:.2f}%")
                logger.info(f"  MAE: {results['mean_mae']:.2f}%")
                logger.info(f"  Directional Accuracy: {results['mean_directional_accuracy']:.1f}%")

                # Check if meets success criteria
                if results['mean_directional_accuracy'] >= 70:
                    logger.info("  PASS: Meets 70% directional accuracy threshold")
                else:
                    logger.warning("  WARNING: Below 70% directional accuracy threshold")

        # Calculate overall statistics
        logger.info("\n" + "=" * 80)
        logger.info("BACKTESTING SUMMARY")
        logger.info("=" * 80)

        # Regional average
        regional_dir_acc = [r['mean_directional_accuracy'] for r in cv_results['regional'].values()]
        avg_regional_dir_acc = sum(regional_dir_acc) / len(regional_dir_acc) if regional_dir_acc else 0

        logger.info(f"\nRegional Models: {len(cv_results['regional'])} regions")
        logger.info(f"  Average Directional Accuracy: {avg_regional_dir_acc:.1f}%")

        # Success criteria check
        logger.info("\n" + "=" * 80)
        logger.info("SUCCESS CRITERIA VALIDATION")
        logger.info("=" * 80)

        criteria_met = []

        # RMSE < 5% for regional
        regional_rmse = [r['mean_rmse'] for r in cv_results['regional'].values()]
        avg_rmse = sum(regional_rmse) / len(regional_rmse) if regional_rmse else float('inf')

        if avg_rmse < 5:
            logger.info(f"PASS RMSE: {avg_rmse:.2f}% < 5%")
            criteria_met.append("RMSE")
        else:
            logger.warning(f"FAIL RMSE: {avg_rmse:.2f}% >= 5% (Target: < 5%)")

        # Directional accuracy > 70%
        if avg_regional_dir_acc > 70:
            logger.info(f"PASS Directional Accuracy: {avg_regional_dir_acc:.1f}% > 70%")
            criteria_met.append("Directional Accuracy")
        else:
            logger.warning(f"FAIL Directional Accuracy: {avg_regional_dir_acc:.1f}% <= 70% (Target: > 70%)")

        logger.info(f"\nCriteria Passed: {len(criteria_met)}/2")

        if len(criteria_met) == 2:
            logger.info("SUCCESS: All criteria met - System ready for production!")
        else:
            logger.warning("WARNING: Some criteria not met - consider model tuning")

        # Save results
        output_path = Config.ANALYSIS_OUTPUT_DIR / "var_backtesting_results.txt"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            f.write("VAR Housing Appreciation - Backtesting Results\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"Regional Models: {len(cv_results['regional'])} regions\n")
            f.write(f"Average RMSE: {avg_rmse:.2f}%\n")
            f.write(f"Average Directional Accuracy: {avg_regional_dir_acc:.1f}%\n")
            f.write(f"\nCriteria Passed: {len(criteria_met)}/2\n")

        logger.info(f"\nResults saved to {output_path}")

    except Exception as e:
        logger.error(f"Cross-validation failed: {e}", exc_info=True)
        return

    logger.info("\n" + "=" * 80)
    logger.info("Backtesting Complete!")
    logger.info("=" * 80)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    main()
