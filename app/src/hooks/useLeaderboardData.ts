import { useMemo } from 'react';
import type {
  LeaderboardControlsState,
  LeaderboardDisplayRow,
  LeaderboardEntry,
  LeaderboardMetric,
  LeaderboardPropertyType,
} from '@/types/leaderboard';
import { useGzipJson } from './useGzipJson';
import { DATA_URLS } from '@/constants/data-urls';

function mapEntryRegion(region: LeaderboardEntry['region']) {
  switch (region) {
    case 'CENTRAL REGION':
      return 'CCR';
    case 'REST OF CENTRAL REGION':
      return 'RCR';
    case 'OUTSIDE CENTRAL REGION':
      return 'OCR';
    default:
      return null;
  }
}

function getPropertyMetrics(entry: LeaderboardEntry, propertyType: LeaderboardPropertyType) {
  if (propertyType === 'all') {
    return null;
  }

  return entry.by_property_type[propertyType];
}

function getTimePeriodMetrics(entry: LeaderboardEntry, timeBasis: LeaderboardControlsState['timeBasis']) {
  if (timeBasis === 'recent') {
    return null;
  }

  return entry.by_time_period[timeBasis];
}

function resolveMetricValue(
  entry: LeaderboardEntry,
  metric: LeaderboardMetric,
  controls: LeaderboardControlsState
): number {
  const propertyMetrics = getPropertyMetrics(entry, controls.propertyType);
  const timeMetrics = getTimePeriodMetrics(entry, controls.timeBasis);

  if (metric === 'median_price') {
    if (propertyMetrics?.median_price !== null && propertyMetrics?.median_price !== undefined) {
      return propertyMetrics.median_price;
    }
    if (timeMetrics?.median_price !== null && timeMetrics?.median_price !== undefined) {
      return timeMetrics.median_price;
    }
    return entry.median_price;
  }

  if (metric === 'volume') {
    if (propertyMetrics) {
      return propertyMetrics.volume;
    }
    return entry.volume;
  }

  if (metric === 'yoy_growth_pct' && timeMetrics?.yoy_growth !== null && timeMetrics?.yoy_growth !== undefined) {
    return timeMetrics.yoy_growth;
  }

  const fallback = entry[metric];
  return typeof fallback === 'number' ? fallback : 0;
}

function toDisplayRow(
  entry: LeaderboardEntry,
  controls: LeaderboardControlsState,
  rank: number
): LeaderboardDisplayRow {
  const resolvedMedianPrice = resolveMetricValue(entry, 'median_price', controls);
  const resolvedVolume = resolveMetricValue(entry, 'volume', controls);
  const resolvedYoyGrowth = resolveMetricValue(entry, 'yoy_growth_pct', controls);

  return {
    sourceEntry: entry,
    planningArea: entry.planning_area,
    areaKey: entry.planning_area.toUpperCase(),
    region: entry.region,
    rank,
    rankMetric: controls.rankMetric,
    rankMetricValue: resolveMetricValue(entry, controls.rankMetric, controls),
    medianPrice: resolvedMedianPrice,
    medianPsf: entry.median_psf,
    rentalYieldMean: entry.rental_yield_mean,
    rentalYieldMedian: entry.rental_yield_median,
    yoyGrowthPct: resolvedYoyGrowth,
    momChangePct: entry.mom_change_pct,
    momentum: entry.momentum,
    volume: resolvedVolume,
    affordabilityRatio: entry.affordability_ratio,
    propertyMix: {
      hdb: entry.by_property_type.hdb.volume,
      ec: entry.by_property_type.ec.volume,
      condo: entry.by_property_type.condo.volume,
      total: entry.volume,
    },
  };
}

function applyFilters(data: LeaderboardEntry[], controls: LeaderboardControlsState): LeaderboardEntry[] {
  return data.filter((entry) => {
    const entryRegion = mapEntryRegion(entry.region);
    const regionMatch =
      controls.region.length === 3 ||
      (entryRegion !== null && controls.region.includes(entryRegion));

    if (!regionMatch) {
      return false;
    }

    const resolvedMedianPrice = resolveMetricValue(entry, 'median_price', controls);
    const [minPrice, maxPrice] = controls.priceRange;

    if (resolvedMedianPrice < minPrice || resolvedMedianPrice > maxPrice) {
      return false;
    }

    if (controls.search.trim()) {
      const query = controls.search.trim().toUpperCase();
      if (!entry.planning_area.toUpperCase().includes(query)) {
        return false;
      }
    }

    if (controls.propertyType !== 'all') {
      const propertyMetrics = getPropertyMetrics(entry, controls.propertyType);
      if (!propertyMetrics || propertyMetrics.volume <= 0) {
        return false;
      }
    }

    return true;
  });
}

function sortRows(data: LeaderboardEntry[], controls: LeaderboardControlsState): LeaderboardDisplayRow[] {
  const sorted = [...data].sort((a, b) => {
    return resolveMetricValue(b, controls.rankMetric, controls) - resolveMetricValue(a, controls.rankMetric, controls);
  });

  return sorted.map((entry, index) => toDisplayRow(entry, controls, index + 1));
}

export function getMetricValue(row: LeaderboardDisplayRow, metric: LeaderboardMetric): number | null {
  switch (metric) {
    case 'median_price':
      return row.medianPrice;
    case 'median_psf':
      return row.medianPsf;
    case 'rental_yield_mean':
      return row.rentalYieldMean;
    case 'rental_yield_median':
      return row.rentalYieldMedian;
    case 'yoy_growth_pct':
      return row.yoyGrowthPct;
    case 'mom_change_pct':
      return row.momChangePct;
    case 'momentum':
      return row.momentum;
    case 'volume':
      return row.volume;
    case 'affordability_ratio':
      return row.affordabilityRatio;
    default:
      return null;
  }
}

export function useLeaderboardData(
  controls: LeaderboardControlsState,
  initialData?: LeaderboardEntry[]
): { data: LeaderboardDisplayRow[]; loading: boolean; error: string | null; reload: () => void } {
  const { data: rawData, loading, error, reload } = useGzipJson<LeaderboardEntry[]>(
    DATA_URLS.leaderboard,
    'leaderboard',
    true,
    initialData ?? null
  );

  const data = useMemo(() => {
    if (!rawData) {
      return [];
    }

    const filtered = applyFilters(rawData, controls);
    return sortRows(filtered, controls);
  }, [rawData, controls]);

  return { data, loading, error, reload };
}
