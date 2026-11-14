import type { Region } from "@/types/segments";
import {
  isObservedPeriodId,
  type ObservedPeriodId,
} from "@/utils/observed-periods";

/**
 * Leaderboard type definitions for the enhanced leaderboard dashboard.
 *
 * RF01 scope: observed rankings read the joint `map_metrics[era_property]`
 * section only. Fields that the published release cannot scope jointly
 * (growth, momentum, yield, affordability) are gone from the display row so no
 * margin-derived number can reach a renderer.
 */

/**
 * Metrics breakdown by property type (HDB, EC, Condo)
 */
export interface PropertyTypeMetrics {
  median_price: number | null;
  volume: number;
}

/**
 * Metrics breakdown by time period (whole, pre_covid, recent, year_2025)
 */
export interface TimePeriodMetrics {
  median_price: number | null;
  yoy_growth: number | null;
}

/**
 * Full leaderboard entry for a planning area.
 *
 * `by_property_type` and `by_time_period` are property-only and period-only
 * margins. They are retained here only because the asset publishes them; no
 * observed surface may read a price, PSF or volume from them.
 */
export interface LeaderboardEntry {
  /** Planning area name (e.g., "PASIR RIS") */
  planning_area: string;

  /** Region name (e.g., "EAST REGION") */
  region: string;

  /** Coordinates for map marker [longitude, latitude] */
  coordinates: [number, number] | null;

  /** Hotspot classification (e.g., "High Growth", "Elite Hotspot") */
  spatial_hotspot: string;

  /** Overall ranking score */
  rank_overall: number;

  /** Median transaction price */
  median_price: number;

  /** Median price per square foot */
  median_psf: number;

  /** Mean rental yield percentage */
  rental_yield_mean: number | null;

  /** Median rental yield percentage */
  rental_yield_median: number | null;

  /** Year-over-year growth percentage */
  yoy_growth_pct: number;

  /** Month-over-month change percentage */
  mom_change_pct: number;

  /** Momentum indicator (3-month growth - 12-month growth) */
  momentum: number;

  /** Transaction volume */
  volume: number;

  /** Affordability ratio (median price / median income) */
  affordability_ratio: number;

  /** Metrics broken down by property type */
  by_property_type: {
    hdb: PropertyTypeMetrics;
    ec: PropertyTypeMetrics;
    condo: PropertyTypeMetrics;
  };

  /** Metrics broken down by time period */
  by_time_period: {
    whole: TimePeriodMetrics;
    pre_covid: TimePeriodMetrics;
    recent: TimePeriodMetrics;
    year_2025: TimePeriodMetrics;
  };
}

/**
 * Available metrics for sorting and display.
 *
 * Kept wide for URL compatibility: link IDs that the release cannot scope
 * jointly resolve to an explicit unavailable state, never to a substituted
 * value.
 */
export type LeaderboardMetric =
  | "median_price"
  | "median_psf"
  | "rental_yield_mean"
  | "rental_yield_median"
  | "yoy_growth_pct"
  | "mom_change_pct"
  | "momentum"
  | "volume"
  | "affordability_ratio";

/**
 * Metric metadata for display
 */
export interface MetricMeta {
  key: LeaderboardMetric;
  label: string;
  description: string;
  formula: string;
  unit: string;
  colorScale: "sequential" | "diverging";
}

export type LeaderboardPropertyType = "all" | "hdb" | "ec" | "condo";

/** The historical eras `map_metrics.json.gz` publishes and this page accepts. */
export type LeaderboardLegacyTimeBasis = "recent" | "whole" | "year_2025";

/**
 * A selected comparison window: one of the legacy eras above, or a concrete v2
 * observed-period id (`ttm_2026_10`). A legacy id always reads the legacy era,
 * even where the pack publishes the same id, so existing links keep meaning.
 */
export type LeaderboardTimeBasis =
  | LeaderboardLegacyTimeBasis
  | ObservedPeriodId;

export const LEADERBOARD_LEGACY_TIME_BASES: readonly LeaderboardLegacyTimeBasis[] =
  ["recent", "whole", "year_2025"];

/** The bare-URL default; moving it onto a pack window is the migration step. */
export const LEADERBOARD_DEFAULT_TIME_BASIS: LeaderboardLegacyTimeBasis =
  "recent";

export function isLeaderboardLegacyTimeBasis(
  value: string,
): value is LeaderboardLegacyTimeBasis {
  return (LEADERBOARD_LEGACY_TIME_BASES as readonly string[]).includes(value);
}

/**
 * Read one `?timeBasis=` value.
 *
 * Legacy eras and well-formed concrete ids are kept verbatim; anything else
 * falls back to the documented default, like every other enumerated parameter.
 */
export function parseLeaderboardTimeBasis(
  value: string | null,
): LeaderboardTimeBasis {
  if (value === null) return LEADERBOARD_DEFAULT_TIME_BASIS;
  if (isLeaderboardLegacyTimeBasis(value)) return value;
  if (isObservedPeriodId(value)) return value;
  return LEADERBOARD_DEFAULT_TIME_BASIS;
}

/** The five planning regions published in the observed release. */
export const PLANNING_REGIONS = [
  "CENTRAL REGION",
  "EAST REGION",
  "NORTH REGION",
  "NORTH-EAST REGION",
  "WEST REGION",
] as const;

export type PlanningRegion = (typeof PLANNING_REGIONS)[number];

/** Short labels for chips and filters. */
export const PLANNING_REGION_LABELS: Record<PlanningRegion, string> = {
  "CENTRAL REGION": "Central",
  "EAST REGION": "East",
  "NORTH REGION": "North",
  "NORTH-EAST REGION": "North-East",
  "WEST REGION": "West",
};

export interface LeaderboardControlsState {
  region: PlanningRegion[];
  propertyType: LeaderboardPropertyType;
  timeBasis: LeaderboardTimeBasis;
  priceRange: [number, number];
  search: string;
  rankMetric: LeaderboardMetric;
}

export interface LeaderboardDisplayRow {
  sourceEntry: LeaderboardEntry;
  planningArea: string;
  areaKey: string;
  /** Explicit null when the published region label is not a planning region. */
  region: PlanningRegion | null;
  /** `null` means the row is visible but not ranked (sample too thin). */
  rank: number | null;
  rankMetric: LeaderboardMetric;
  rankMetricValue: number | null;
  medianPrice: number | null;
  medianPsf: number | null;
  volume: number | null;
  /** True when the selected window has fewer than the caution threshold. */
  isThinSample: boolean;
  /** Era-scoped volumes per property type; `null` when nothing is published. */
  propertyMix: {
    hdb: number | null;
    ec: number | null;
    condo: number | null;
    total: number;
  } | null;
}

/** Retained for compatibility with segment geography; not used by observed rankings. */
export type SegmentRegion = Region;
