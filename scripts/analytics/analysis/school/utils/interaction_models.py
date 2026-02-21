"""Segmentation and interaction effects analysis utilities."""

import logging
from pathlib import Path

import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
from sklearn.model_selection import train_test_split

logger = logging.getLogger(__name__)


class SegmentationAnalyzer:
    """Analyze heterogeneous treatment effects across market segments."""

    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)
        self.segment_results = {}

    def create_market_segments(self, df: pd.DataFrame):
        """
        Create 9 market segments: property_type × region.

        Regions: CCR (Core Central), RCR (Rest of Central), OCR (Outside Central)
        Derived from planning_area using URA definitions.
        """
        logger.info("Creating market segments...")

        # Define region mapping (simplified URA market segments)
        ccr_areas = [
            'DOWNTOWN CORE', 'NEWTON', 'ORCHARD', 'OUTRAM', 'RIVER VALLEY',
            'ROCHOR', 'SINGAPORE RIVER', 'MARINA EAST', 'MARINA SOUTH',
            'SOUTHERN ISLANDS', 'STRANGERS VIEW'
        ]

        rcr_areas = [
            'BISHAN', 'BUKIT MERAH', 'BUKIT TIMAH', 'GEYLANG', 'KALLANG',
            'NOVENA', 'QUEENSTOWN', 'TOA PAYOH', 'MARINE PARADE', 'MUSEUM',
            'TIONG BAHRU'
        ]

        # OCR is everything else
        def get_region(planning_area):
            if planning_area in ccr_areas:
                return 'CCR'
            elif planning_area in rcr_areas:
                return 'RCR'
            else:
                return 'OCR'

        df = df.copy()
        df['region'] = df['planning_area'].apply(get_region)

        # Create segment
        df['market_segment'] = df['property_type'] + '_' + df['region']

        segment_counts = df['market_segment'].value_counts()
        logger.info(f"  Created {len(segment_counts)} segments:")
        for segment, count in segment_counts.items():
            logger.info(f"    {segment}: {count:,} records")

        return df

    def create_interaction_features(self, df: pd.DataFrame):
        """
        Create explicit interaction terms for school quality × key features.
        """
        logger.info("Creating interaction features...")

        df = df.copy()

        # School quality × floor area
        if 'school_primary_quality_score' in df.columns and 'floor_area_sqm' in df.columns:
            df['school_x_area'] = df['school_primary_quality_score'] * df['floor_area_sqm']
            logger.info("  school_x_area: school_quality × floor_area")

        # School quality × MRT distance
        if 'school_primary_quality_score' in df.columns and 'dist_to_nearest_mrt' in df.columns:
            df['school_x_mrt'] = df['school_primary_quality_score'] * df['dist_to_nearest_mrt']
            logger.info("  school_x_mrt: school_quality × mrt_distance")

        # School quality × remaining lease
        if 'school_primary_quality_score' in df.columns and 'remaining_lease_months' in df.columns:
            df['school_x_lease'] = df['school_primary_quality_score'] * df['remaining_lease_months']
            logger.info("  school_x_lease: school_quality × remaining_lease")

        return df

    def run_segmented_models(
        self,
        df: pd.DataFrame,
        feature_cols: list,
        target_col: str = 'price_psf'
    ):
        """
        Run separate models for each market segment.

        Returns dict of results per segment.
        """
        logger.info("Running segmented models...")

        results = []

        for segment in df['market_segment'].unique():
            segment_df = df[df['market_segment'] == segment].copy()

            if len(segment_df) < 500:
                logger.warning(f"  Skipping {segment}: insufficient data ({len(segment_df)} records)")
                continue

            logger.info(f"  Segment: {segment} ({len(segment_df):,} records)")

            # Prepare data
            X = segment_df[feature_cols]
            y = segment_df[target_col]

            # Drop NaN
            segment_df = segment_df.dropna(subset=feature_cols + [target_col])
            X = segment_df[feature_cols]
            y = segment_df[target_col]

            # Split
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )

            # Fit OLS
            model = LinearRegression()
            model.fit(X_train, y_train)

            # Predict
            y_pred = model.predict(X_test)
            r2 = r2_score(y_test, y_pred)

            # Extract school coefficients
            school_coefs = []
            for i, feat in enumerate(feature_cols):
                if 'school' in feat.lower():
                    school_coefs.append({
                        'segment': segment,
                        'feature': feat,
                        'coefficient': model.coef_[i]
                    })

            results.append({
                'segment': segment,
                'n_train': len(X_train),
                'n_test': len(X_test),
                'r2': r2,
                'model': model,
                'school_coefs': school_coefs
            })

        self.segment_results['segmented'] = results
        return results

    def run_interaction_model(
        self,
        df: pd.DataFrame,
        base_features: list,
        target_col: str = 'price_psf'
    ):
        """
        Run pooled model with interaction terms.

        Model: Y = α + β₁·school + β₂·prop_type + β₃·region + β₄·(school×prop_type) + ...
        """
        logger.info("Running interaction model...")

        df = df.copy()

        # Create dummies for categorical variables
        df = pd.get_dummies(df, columns=['property_type', 'region'], drop_first=True)

        # Add interaction terms
        interaction_cols = []

        # School × property type
        if 'school_primary_quality_score' in df.columns:
            for col in df.columns:
                if col.startswith('property_type_'):
                    interaction_col = f'school_x_{col}'
                    df[interaction_col] = df['school_primary_quality_score'] * df[col]
                    interaction_cols.append(interaction_col)

            # School × region
            for col in df.columns:
                if col.startswith('region_'):
                    interaction_col = f'school_x_{col}'
                    df[interaction_col] = df['school_primary_quality_score'] * df[col]
                    interaction_cols.append(interaction_col)

        logger.info(f"  Created {len(interaction_cols)} interaction terms")

        # Prepare features
        feature_cols = base_features + interaction_cols
        feature_cols = [f for f in feature_cols if f in df.columns]

        # Drop NaN
        df = df.dropna(subset=feature_cols + [target_col])

        X = df[feature_cols]
        y = df[target_col]

        # Split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        # Fit OLS
        model = LinearRegression()
        model.fit(X_train, y_train)

        # Predict
        y_pred = model.predict(X_test)
        r2 = r2_score(y_test, y_pred)

        # Extract interaction coefficients
        interaction_coefs = []
        for i, feat in enumerate(feature_cols):
            if feat.startswith('school_x_'):
                interaction_coefs.append({
                    'feature': feat,
                    'coefficient': model.coef_[i],
                    'abs_coef': abs(model.coef_[i])
                })

        interaction_df = pd.DataFrame(interaction_coefs).sort_values('abs_coef', ascending=False)

        logger.info(f"  R²: {r2:.4f}")
        logger.info("  Top interactions:")
        for _, row in interaction_df.head(5).iterrows():
            logger.info(f"    {row['feature']}: {row['coefficient']:.4f}")

        result = {
            'model': model,
            'r2': r2,
            'n_train': len(X_train),
            'n_test': len(X_test),
            'interaction_coefs': interaction_df,
            'feature_cols': feature_cols
        }

        self.segment_results['interaction'] = result
        return result

    def save_segment_coefficients(self):
        """Save segment-specific school coefficients to CSV."""
        if 'segmented' not in self.segment_results:
            logger.warning("No segmented results to save")
            return None

        all_coefs = []
        for result in self.segment_results['segmented']:
            all_coefs.extend(result['school_coefs'])

        coef_df = pd.DataFrame(all_coefs)

        # Pivot for easier viewing
        pivot_df = coef_df.pivot(index='segment', columns='feature', values='coefficient')

        output_path = self.output_dir / "segment_coefficients.csv"
        pivot_df.to_csv(output_path)
        logger.info(f"Saved segment coefficients: {output_path}")

        return pivot_df

    def save_interaction_results(self):
        """Save interaction model results to CSV."""
        if 'interaction' not in self.segment_results:
            logger.warning("No interaction results to save")
            return None

        interaction_df = self.segment_results['interaction']['interaction_coefs']

        output_path = self.output_dir / "interaction_model_results.csv"
        interaction_df.to_csv(output_path, index=False)
        logger.info(f"Saved interaction results: {output_path}")

        return interaction_df

    def compare_r2_across_segments(self):
        """Compare model performance (R²) across segments."""
        if 'segmented' not in self.segment_results:
            logger.warning("No segmented results to compare")
            return None

        r2_data = []
        for result in self.segment_results['segmented']:
            r2_data.append({
                'segment': result['segment'],
                'r2': result['r2'],
                'n_test': result['n_test']
            })

        r2_df = pd.DataFrame(r2_data).sort_values('r2', ascending=False)

        output_path = self.output_dir / "segment_r2_comparison.csv"
        r2_df.to_csv(output_path, index=False)
        logger.info(f"Saved R² comparison: {output_path}")

        return r2_df
