#!/usr/bin/env python3
"""Calculate school features - optimized using KDTree for nearest search."""

import json
import logging
import threading
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from egg_n_bacon_housing.utils.geocoding import Geocoder
from egg_n_bacon_housing.utils.runtime import SchoolReference

SCHOOL_LEVELS = ["PRIMARY", "SECONDARY (S1-S5)", "JUNIOR COLLEGE"]

#: Columns emitted by :func:`calculate_school_quality_features` on every call.
QUALITY_FEATURE_COLUMNS = (
    "nearest_top_primary_school_dist",
    "nearest_top_secondary_school_dist",
    "school_accessibility_score",
)

#: Methodology weight for the overall blend (secondary-weighted, see
#: data/manual/csv/school_scoring_methodology.md "Aggregate School Features").
_PRIMARY_BLEND_WEIGHT = 0.4
_SECONDARY_BLEND_WEIGHT = 0.6

#: Distance decay: half-value at 500m, negligible at 2km (methodology).
_ACCESSIBILITY_DECAY_RANGE_M = 2000.0

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SchoolReferenceRepository:
    """School tiers rooted at immutable bronze and manual directories."""

    bronze_dir: Path
    data_dir: Path
    _lock: threading.RLock = field(
        default_factory=threading.RLock, init=False, repr=False, compare=False
    )
    _tiers_cache: tuple[pd.DataFrame, pd.DataFrame] | None = field(
        default=None, init=False, repr=False
    )

    def load_json(self, filename: str) -> dict | None:
        config_path = self.bronze_dir / "external" / filename
        if config_path.exists():
            try:
                with open(config_path) as f:
                    data = json.load(f)
                return data if isinstance(data, dict) else None
            except (OSError, json.JSONDecodeError, TypeError):
                logger.warning("Invalid school reference file: %s", config_path)
                return None
        logger.warning("Reference data file not found: %s", config_path)
        return None

    def load_school_tiers(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        with self._lock:
            if self._tiers_cache is None:
                object.__setattr__(self, "_tiers_cache", self._load_school_tiers())
            assert self._tiers_cache is not None
            return self._tiers_cache[0].copy(deep=True), self._tiers_cache[1].copy(deep=True)

    def _load_school_tiers(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        primary_tiers = pd.DataFrame()
        secondary_tiers = pd.DataFrame()
        json_data = self.load_json("school_tiers.json")
        if json_data:
            if "primary" in json_data:
                primary_tiers = pd.DataFrame(json_data["primary"])
                logger.info("Loaded %s primary school tiers from JSON", len(primary_tiers))
            if "secondary" in json_data:
                secondary_tiers = pd.DataFrame(json_data["secondary"])
                logger.info("Loaded %s secondary school tiers from JSON", len(secondary_tiers))
            return primary_tiers, secondary_tiers

        csv_dir = self.data_dir / "manual" / "csv"
        primary_path = csv_dir / "school_tiers_primary.csv"
        secondary_path = csv_dir / "school_tiers_secondary.csv"
        if primary_path.exists():
            primary_tiers = pd.read_csv(primary_path)
            logger.info("Loaded %s primary school tiers from CSV", len(primary_tiers))
        else:
            logger.warning("Primary school tiers not found: %s", primary_path)
        if secondary_path.exists():
            secondary_tiers = pd.read_csv(secondary_path)
            logger.info("Loaded %s secondary school tiers from CSV", len(secondary_tiers))
        else:
            logger.warning("Secondary school tiers not found: %s", secondary_path)
        return primary_tiers, secondary_tiers


def _repository(repository: SchoolReferenceRepository) -> SchoolReferenceRepository:
    return repository


def _load_reference_data(filename: str, repository: SchoolReferenceRepository) -> dict | None:
    """Load JSON reference data from an explicitly injected repository.

    Args:
        filename: Name of JSON file in data/01_bronze/external/

    Returns:
        Parsed JSON data or None if not found
    """
    return _repository(repository).load_json(filename)


def load_school_tiers(
    repository: SchoolReference,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load school tier data from JSON with CSV fallback.

    Returns:
        Tuple of (primary_tiers, secondary_tiers) DataFrames
    """
    return repository.load_school_tiers()


def _school_key(series: pd.Series) -> pd.Series:
    """Normalized school-name join key (tier CSVs and the MOE directory
    both use uppercase names; normalize defensively)."""
    return series.astype("string").str.strip().str.upper()


def _yes_no(series: pd.Series) -> pd.Series:
    """Yes/No column to float indicator (anything non-"Yes" is 0)."""
    return (series.astype("string").str.strip().str.lower() == "yes").astype(float)


def _tier_terms(tier: pd.Series) -> pd.Series:
    """tier_1/2/3 indicator terms (3.0 / 2.0 / 1.0 per methodology weights)."""
    tier_num = pd.to_numeric(tier, errors="coerce")
    return (tier_num == 1) * 3.0 + (tier_num == 2) * 2.0 + (tier_num == 3) * 1.0


def _popularity_score(series: pd.Series) -> pd.Series:
    """Phase 2B popularity ratio / 3, capped at 1.0.

    ``"High"`` markers carry no numeric ratio; the methodology caps the
    score at 1.0 anyway, so map them to the cap rather than dropping the
    signal. Other non-numeric values score 0.
    """
    normalized = series.astype("string").str.strip().str.lower()
    numeric = pd.to_numeric(series, errors="coerce") / 3.0
    numeric = numeric.clip(lower=0.0, upper=1.0)
    numeric = numeric.where(~(normalized == "high"), 1.0)
    return numeric.fillna(0.0)


def _cutoff_quality(series: pd.Series) -> pd.Series:
    """IP cut-off quality: (10 - midpoint) / 6 * 1.5, clipped at [0, 1.5].

    Cut-offs are PSLE aggregate ranges like ``"4-6"``; the midpoint of the
    range is used. Unparseable values score 0.
    """
    text = series.astype("string").str.strip()
    parts = text.str.extract(r"^(\d+)\s*-\s*(\d+)$")
    midpoint = (
        pd.to_numeric(parts[0], errors="coerce") + pd.to_numeric(parts[1], errors="coerce")
    ) / 2.0
    single = pd.to_numeric(text, errors="coerce")
    midpoint = midpoint.fillna(single)
    return ((10.0 - midpoint) / 6.0 * 1.5).clip(lower=0.0, upper=1.5).fillna(0.0)


def _quality_formula(terms: pd.Series) -> pd.Series:
    """terms + MIN(1.0, sum_of_terms) base bonus, clipped to the 0-10 scale.

    The methodology's ``MIN(1.0, sum_all_weights)`` is read literally as a
    participation bonus equal to the applied weighted terms capped at 1.0.
    """
    return (terms + terms.clip(upper=1.0)).clip(lower=0.0, upper=10.0)


def calculate_school_quality_scores(
    primary_tiers: pd.DataFrame, secondary_tiers: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compute 0-10 school quality scores per the published methodology.

    Implements the primary and secondary formulas from
    ``data/manual/csv/school_scoring_methodology.md``. Deviations from the
    literal formulas, all forced by the available data:

    - ``academic_awards`` is 0 for every school — the ``awards`` column is
      descriptive text ("Premier girls school"), not a count.
    - ``popularity_p2b`` markers of ``"High"`` map to the capped max (1.0);
      other non-numeric values score 0.
    - IP cut-off ranges use their midpoint.

    Returns:
        Tuple of (primary, secondary) frames with ``school_name``
        (normalized join key) and ``quality_score``; empty-in → empty-out
        with the same columns.
    """
    if primary_tiers.empty:
        primary = pd.DataFrame(columns=["school_name", "quality_score"])
    else:
        terms = (
            _yes_no(primary_tiers["gep"]) * 2.5
            + _yes_no(primary_tiers["sap"]) * 2.0
            + _tier_terms(primary_tiers["tier"])
            + _popularity_score(primary_tiers["popularity_p2b"]) * 0.5
        )
        primary = pd.DataFrame(
            {
                "school_name": _school_key(primary_tiers["school_name"]),
                "quality_score": _quality_formula(terms),
            }
        )

    if secondary_tiers.empty:
        secondary = pd.DataFrame(columns=["school_name", "quality_score"])
    else:
        # No award-count data exists in the source CSV — see docstring.
        terms = (
            _yes_no(secondary_tiers["ip"]) * 3.0
            + _yes_no(secondary_tiers["sap"]) * 2.0
            + _yes_no(secondary_tiers["autonomous"]) * 1.5
            + _tier_terms(secondary_tiers["tier"])
            + _cutoff_quality(secondary_tiers["ip_cutoff_2026"])
        )
        secondary = pd.DataFrame(
            {
                "school_name": _school_key(secondary_tiers["school_name"]),
                "quality_score": _quality_formula(terms),
            }
        )

    return primary, secondary


def _nearest_with_metadata(
    unique_coords: pd.DataFrame,
    candidates: pd.DataFrame,
    value_columns: list[str],
) -> dict[str, pd.Series]:
    """Per-unique-coordinate nearest candidate values via KD-tree.

    ``candidates`` needs ``latitude``/``longitude`` plus ``value_columns``;
    returned Series are indexed like ``unique_coords``.
    """
    tree = cKDTree(np.radians(candidates[["latitude", "longitude"]].to_numpy(dtype=float)))
    _chord, nearest_idx = tree.query(
        np.radians(unique_coords[["lat", "lon"]].to_numpy(dtype=float)), k=1
    )
    nearest = candidates.iloc[nearest_idx]
    out: dict[str, pd.Series] = {}
    for col in value_columns:
        values = nearest[col].to_numpy()
        out[col] = pd.Series(
            values, index=unique_coords.index, dtype=object if values.dtype == object else None
        )
    # Haversine distance to the chosen nearest candidate.
    out["__dist_m"] = pd.Series(
        _haversine_metres(
            unique_coords["lat"].to_numpy(dtype=float),
            unique_coords["lon"].to_numpy(dtype=float),
            pd.to_numeric(nearest["latitude"], errors="coerce").to_numpy(dtype=float),
            pd.to_numeric(nearest["longitude"], errors="coerce").to_numpy(dtype=float),
        ),
        index=unique_coords.index,
    )
    return out


def _map_back(
    properties_df: pd.DataFrame, unique_coords: pd.DataFrame, column: str, values: pd.Series
) -> None:
    """Assign unique-location ``values`` back onto every property row (1:many)."""
    lookup_index = pd.MultiIndex.from_frame(unique_coords[["lat", "lon"]])
    target_index = pd.MultiIndex.from_frame(properties_df[["lat", "lon"]])
    lookup = pd.Series(values.to_numpy(), index=lookup_index)
    properties_df[column] = lookup.reindex(target_index).to_numpy()


def _resolve_tier(pool_keys: pd.Series, tiers: pd.DataFrame, scores: pd.DataFrame) -> pd.DataFrame:
    """Resolve each directory school name to tier quality + tier-1 flag.

    Exact normalized-name match first. Fallback: longest prefix match, which
    handles the two known MOE-directory naming drifts (tier "NANYANG GIRLS'
    HIGH" vs directory "NANYANG GIRLS' HIGH SCHOOL"; tier "RAFFLES GIRLS'
    SCHOOL" vs directory "RAFFLES GIRLS' SCHOOL (SECONDARY)"). Unresolved
    schools score 0 and are never tier-1.
    """
    score_map = dict(zip(scores["school_name"], scores["quality_score"], strict=True))
    tier_num = (
        pd.to_numeric(tiers["tier"], errors="coerce")
        if "tier" in tiers.columns
        else pd.Series(dtype=float)
    )
    tier1_keys = (
        set(_school_key(tiers.loc[tier_num == 1, "school_name"])) if not tier_num.empty else set()
    )

    def _resolve(key: str) -> tuple[float, bool]:
        if key in score_map:
            return float(score_map[key]), key in tier1_keys
        candidates = [t for t in score_map if t.startswith(key) or key.startswith(t)]
        if candidates:
            best = max(candidates, key=len)
            return float(score_map[best]), best in tier1_keys
        return 0.0, False

    resolved = pool_keys.map(_resolve)
    return pd.DataFrame(
        {
            "quality": [r[0] for r in resolved],
            "is_tier1": [r[1] for r in resolved],
        },
        index=pool_keys.index,
    )


def calculate_school_quality_features(
    properties_df: pd.DataFrame,
    schools_df: pd.DataFrame,
    primary_tiers: pd.DataFrame,
    secondary_tiers: pd.DataFrame,
) -> pd.DataFrame:
    """Add tier-weighted school quality features to a property DataFrame.

    Adds the three :data:`QUALITY_FEATURE_COLUMNS` per the methodology:

    - ``nearest_top_primary_school_dist`` / ``nearest_top_secondary_school_dist``
      — haversine metres to the nearest tier-1 school of that level (NA
      when no tier-1 school of the level has coordinates).
    - ``school_accessibility_score`` — 0.4 * primary + 0.6 * secondary blend
      of per-level scores ``max(0, 1 - d/2000) * (1 + q/10) * q/10``, where
      d is the distance to the nearest school of the level and q its
      quality score (0 when the school is not in the tier tables). A level
      with no geocoded schools contributes 0.

    The secondary pool spans all MOE level codes admitting at S1 —
    ``SECONDARY (S1-S5)``, ``SECONDARY (S1-S4)`` (girls' schools), and
    ``MIXED LEVEL (S1-JC2)`` (6-year IP schools like Raffles Institution) —
    since the tier tables classify IP schools as secondary. Directory-name
    to tier-name matching is exact first, then longest-prefix (MOE appends
    "SCHOOL"/"(SECONDARY)" to some names).

    Args:
        properties_df: DataFrame with ``lat``/``lon`` columns.
        schools_df: School directory with ``school_name``, ``latitude``,
            ``longitude``, ``mainlevel_code``.
        primary_tiers / secondary_tiers: Raw tier frames from
            :class:`SchoolReferenceRepository` (CSV/JSON columns).

    Returns:
        DataFrame with the quality columns added (always present; NA where
        not computable).
    """
    properties_df = properties_df.copy().reset_index(drop=True)
    for col in QUALITY_FEATURE_COLUMNS:
        properties_df[col] = pd.NA

    if not {"latitude", "longitude", "school_name", "mainlevel_code"}.issubset(schools_df.columns):
        logger.warning(
            "School directory lacks coordinate/name columns — school quality features stay NA"
        )
        return properties_df
    schools_geo = schools_df.dropna(subset=["latitude", "longitude"]).copy()
    if schools_geo.empty:
        logger.warning("No geocoded schools available — school quality features stay NA")
        return properties_df
    schools_geo["_key"] = _school_key(schools_geo["school_name"])

    primary_scores, secondary_scores = calculate_school_quality_scores(
        primary_tiers, secondary_tiers
    )

    props_with_coords = properties_df[properties_df["lat"].notna() & properties_df["lon"].notna()]
    if props_with_coords.empty:
        logger.warning("No property coordinates available — school quality features stay NA")
        return properties_df
    unique_coords = props_with_coords[["lat", "lon"]].drop_duplicates().reset_index(drop=True)

    level_scores: dict[str, pd.Series] = {}
    level_specs = {
        "PRIMARY": ("nearest_top_primary_school_dist", primary_tiers, primary_scores),
        "SECONDARY (S1-S5)": (
            "nearest_top_secondary_school_dist",
            secondary_tiers,
            secondary_scores,
        ),
    }
    for level, (top_col, tiers, scores) in level_specs.items():
        if level == "SECONDARY (S1-S5)":
            # Secondary pool spans the MOE level codes that admit at S1:
            # standalone secondaries, S1-S4 girls' schools, and 6-year IP
            # schools (RI, Hwa Chong, ACS(I)…) coded MIXED LEVEL.
            level_schools = schools_geo[
                schools_geo["mainlevel_code"].str.startswith("SECONDARY")
                | (schools_geo["mainlevel_code"] == "MIXED LEVEL (S1-JC2)")
            ]
        else:
            level_schools = schools_geo[schools_geo["mainlevel_code"] == level]
        if level_schools.empty:
            logger.warning("No schools found for level %r — quality score contributes 0", level)
            continue

        resolved = _resolve_tier(level_schools["_key"], tiers, scores)
        level_schools = level_schools.assign(
            _quality=resolved["quality"].to_numpy(), _is_tier1=resolved["is_tier1"].to_numpy()
        )

        nearest = _nearest_with_metadata(unique_coords, level_schools, ["_quality"])
        quality = pd.Series(nearest["_quality"], index=unique_coords.index).fillna(0.0)
        decay = (1.0 - nearest["__dist_m"] / _ACCESSIBILITY_DECAY_RANGE_M).clip(lower=0.0)
        level_scores[level] = decay * (1.0 + quality / 10.0) * quality / 10.0

        top_schools = level_schools[level_schools["_is_tier1"]]
        if top_schools.empty:
            logger.warning("No tier-1 %s schools with coordinates — %s stays NA", level, top_col)
        else:
            top_nearest = _nearest_with_metadata(unique_coords, top_schools, ["_key"])
            _map_back(properties_df, unique_coords, top_col, top_nearest["__dist_m"])

    overall = pd.Series(0.0, index=unique_coords.index)
    for level, weight in (
        ("PRIMARY", _PRIMARY_BLEND_WEIGHT),
        ("SECONDARY (S1-S5)", _SECONDARY_BLEND_WEIGHT),
    ):
        if level in level_scores:
            overall = overall + weight * level_scores[level]
    _map_back(properties_df, unique_coords, "school_accessibility_score", overall)

    return properties_df


def _geocode_schools(schools_df: pd.DataFrame, geocoder: Geocoder) -> pd.DataFrame:
    """Geocode schools by postal code, adding ``latitude``/``longitude`` columns.

    Delegates the actual geocoding (cache, API, rate limiting) to the injected
    ``geocoder`` — tests pass an ``InMemoryGeocoder``.
    """
    if "postal_code" not in schools_df.columns:
        df = schools_df.copy()
        df["latitude"] = pd.NA
        df["longitude"] = pd.NA
        return df

    df = geocoder.geocode_dataframe(schools_df, "postal_code")
    df = df.rename(columns={"lat": "latitude", "lon": "longitude"})
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")

    logger.info("Geocoded %s/%s schools", df["latitude"].notna().sum(), len(df))
    return df


_EARTH_RADIUS_M = 6_371_000


def _haversine_metres(
    lat1: np.ndarray, lon1: np.ndarray, lat2: np.ndarray, lon2: np.ndarray
) -> np.ndarray:
    """Vectorized haversine distance in metres (same formula as utils.geo)."""
    lat1, lon1, lat2, lon2 = (
        np.radians(np.asarray(a, dtype=float)) for a in (lat1, lon1, lat2, lon2)
    )
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return 2 * np.arcsin(np.sqrt(a)) * _EARTH_RADIUS_M


def _level_dist_column(level: str) -> str:
    """Distance column name for a school level (first word is the level code)."""
    return f"nearest_school{level.split()[0]}_dist"


def calculate_school_features(
    properties_df: pd.DataFrame,
    schools_df: pd.DataFrame,
    levels: list[str] = SCHOOL_LEVELS,
) -> pd.DataFrame:
    """Add the nearest-school distance per level to a property DataFrame.

    Computes only what downstream consumers read: the
    ``nearest_school<LEVEL>_dist`` columns (PRIMARY, SECONDARY, JUNIOR) that
    ``components.features`` reduces to ``dist_to_nearest_school``. Distance
    quality/count/score columns were pruned — nothing consumed them.

    Distances are haversine metres to the nearest school of each level,
    found via a per-level KD-tree queried in one batch over unique property
    locations, then mapped back onto every row with a vectorized lookup.

    Args:
        properties_df: DataFrame with 'lat', 'lon' columns.
        schools_df: DataFrame with 'latitude', 'longitude', 'mainlevel_code'.
        levels: List of school levels to process.

    Returns:
        DataFrame with school distance features added.
    """
    properties_df = properties_df.copy().reset_index(drop=True)
    dist_columns = [_level_dist_column(level) for level in levels]

    schools_geo = schools_df.dropna(subset=["latitude", "longitude"])
    if schools_geo.empty:
        logger.warning("No geocoded schools available")
        return properties_df

    for col in dist_columns:
        properties_df[col] = np.nan

    props_with_coords = properties_df[properties_df["lat"].notna() & properties_df["lon"].notna()]
    if props_with_coords.empty:
        logger.warning("No property coordinates available — school distances stay NA")
        return properties_df

    unique_coords = props_with_coords[["lat", "lon"]].drop_duplicates().reset_index(drop=True)
    logger.info(
        "Computing school distances for %s unique locations from %s total records",
        len(unique_coords),
        len(props_with_coords),
    )
    unique_rad = np.radians(unique_coords[["lat", "lon"]].to_numpy(dtype=float))

    level_summary: list[str] = []
    for level in levels:
        col = _level_dist_column(level)
        level_schools = schools_geo[schools_geo["mainlevel_code"] == level]
        if level_schools.empty:
            logger.warning("No schools found for level %r", level)
            continue

        schools_rad = np.radians(level_schools[["latitude", "longitude"]].to_numpy(dtype=float))
        tree = cKDTree(schools_rad)
        _chord, nearest_idx = tree.query(unique_rad, k=1)
        nearest = level_schools.iloc[nearest_idx]
        unique_coords[col] = _haversine_metres(
            unique_coords["lat"].to_numpy(dtype=float),
            unique_coords["lon"].to_numpy(dtype=float),
            nearest["latitude"].to_numpy(dtype=float),
            nearest["longitude"].to_numpy(dtype=float),
        )
        level_summary.append(f"{level[:3]}({len(level_schools)})")

    logger.info("Schools by level: %s", ", ".join(level_summary))

    # Map unique-location distances back onto every original row (1:many) with
    # a vectorized reindex — no per-row loops.
    lookup_index = pd.MultiIndex.from_frame(unique_coords[["lat", "lon"]])
    target_index = pd.MultiIndex.from_frame(properties_df[["lat", "lon"]])
    for col in dist_columns:
        if col not in unique_coords.columns:
            continue
        lookup = pd.Series(unique_coords[col].to_numpy(dtype=float), index=lookup_index)
        properties_df[col] = lookup.reindex(target_index).to_numpy()

    return properties_df
