import type { Region } from '@/types/segments';

/**
 * Leaderboard type definitions for the enhanced leaderboard dashboard.
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
 * Full leaderboard entry for a planning area
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
 * Available metrics for sorting and display
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

export type LeaderboardPropertyType = 'all' | 'hdb' | 'ec' | 'condo';
export type LeaderboardTimeBasis = 'recent' | 'whole' | 'year_2025';

export interface LeaderboardControlsState {
  region: Region[];
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
  region: string;
  rank: number;
  rankMetric: LeaderboardMetric;
  rankMetricValue: number;
  medianPrice: number | null;
  medianPsf: number | null;
  rentalYieldMean: number | null;
  rentalYieldMedian: number | null;
  yoyGrowthPct: number | null;
  momChangePct: number | null;
  momentum: number | null;
  volume: number;
  affordabilityRatio: number | null;
  propertyMix: {
    hdb: number;
    ec: number;
    condo: number;
    total: number;
  };
}
