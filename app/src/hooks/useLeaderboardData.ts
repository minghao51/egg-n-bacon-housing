// app/src/hooks/useLeaderboardData.ts
import { useState, useEffect, useMemo } from 'react';
import { LeaderboardEntry, LeaderboardMetric } from '@/types/leaderboard';
import { fetchGzipJson } from '@/utils/gzip';

// Define types locally to avoid circular dependencies
type PropertyType = 'HDB' | 'Condominium' | 'EC';
type TimeHorizon = 'short' | 'medium' | 'long';
type Region = 'CCR' | 'RCR' | 'OCR';

interface FilterState {
  investmentGoal: string | null;
  budgetRange: [number, number];
  propertyTypes: PropertyType[];
  locations: Region[];
  timeHorizon: TimeHorizon | null;
  hotspotFilter: string;
}

interface UseLeaderboardDataResult {
  data: LeaderboardEntry[];
  loading: boolean;
  error: string | null;
  reload: () => void;
}

/**
 * Map FilterState property types to data property types
 */
function mapPropertyType(propType: PropertyType): string {
  switch (propType) {
    case 'HDB':
      return 'hdb';
    case 'EC':
      return 'ec';
    case 'Condominium':
      return 'condo';
    default:
      return 'condo';
  }
}

/**
 * Map FilterState time horizon to data time period
 */
function mapTimeHorizon(timeHorizon: TimeHorizon | null): string {
  switch (timeHorizon) {
    case 'short':
      return 'year_2025';
    case 'medium':
      return 'recent';
    case 'long':
      return 'whole';
    default:
      return 'recent';
  }
}

/**
 * Map FilterState region codes to full region names
 */
function mapRegion(region: string): string {
  switch (region) {
    case 'CCR':
      return 'CENTRAL REGION';
    case 'RCR':
      return 'REST OF CENTRAL REGION';
    case 'OCR':
      return 'OUTSIDE CENTRAL REGION';
    default:
      return region;
  }
}

/**
 * Get the current metric value for a planning area based on applied filters
 */
function getCurrentMetricValue(
  entry: LeaderboardEntry,
  metricName: LeaderboardMetric,
  filters: FilterState
): number {
  // Determine if we should use property-type-specific metrics
  const usePropertyType = filters.propertyTypes.length === 1
    ? mapPropertyType(filters.propertyTypes[0])
    : null;

  // Determine time period
  const timePeriod = mapTimeHorizon(filters.timeHorizon);

  // Navigate to correct nested object
  let source: any = entry;

  // If single property type selected, use that type's metrics
  if (usePropertyType) {
    const propMetrics = entry.by_property_type[usePropertyType as keyof typeof entry.by_property_type];
    if (propMetrics && propMetrics.median_price !== null) {
      source = propMetrics;
    }
  }

  // If time period is specified and not 'recent' (default), use period-specific metrics
  if (timePeriod !== 'recent') {
    const periodMetrics = entry.by_time_period[timePeriod as keyof typeof entry.by_time_period];
    if (periodMetrics) {
      source = periodMetrics;
    }
  }

  // Get metric value
  const value = (source as any)[metricName];

  // Handle null/undefined
  if (value === null || value === undefined) {
    // Fall back to overall metric
    const fallbackValue = (entry as any)[metricName];
    return fallbackValue ?? 0;
  }

  return value as number;
}

/**
 * Apply filters to leaderboard data
 */
function applyFilters(
  data: LeaderboardEntry[],
  filters: FilterState
): LeaderboardEntry[] {
  let filtered = [...data];

  // 1. Property type filter
  if (filters.propertyTypes.length === 1) {
    const propType = mapPropertyType(filters.propertyTypes[0]);
    filtered = filtered.filter(entry => {
      const metrics = entry.by_property_type[propType as keyof typeof entry.by_property_type];
      return metrics && metrics.volume > 0;
    });
  }

  // 2. Location filter
  if (filters.locations.length > 0 && filters.locations.length < 3) {
    const regions = filters.locations.map(mapRegion);
    filtered = filtered.filter(entry =>
      regions.includes(entry.region)
    );
  }

  // 3. Budget filter (convert PSF to price range)
  const [minBudget, maxBudget] = filters.budgetRange;
  filtered = filtered.filter(entry => {
    const price = getCurrentMetricValue(entry, 'median_price', filters);
    return price >= minBudget * 1000 && price <= maxBudget * 1000;
  });

  // Note: Hotspot filtering is not directly applicable to leaderboard
  // as it uses different classification (SpatialCluster vs hotspot category)

  return filtered;
}

/**
 * Sort and rank data by specified metric
 */
function sortAndRank(
  data: LeaderboardEntry[],
  sortBy: LeaderboardMetric,
  filters: FilterState
): LeaderboardEntry[] {
  const sorted = [...data].sort((a, b) => {
    const valueA = getCurrentMetricValue(a, sortBy, filters);
    const valueB = getCurrentMetricValue(b, sortBy, filters);
    return valueB - valueA; // Descending order
  });

  // Assign new ranks
  return sorted.map((entry, index) => ({
    ...entry,
    rank_overall: index + 1,
  }));
}

export function useLeaderboardData(
  filters: FilterState,
  sortBy: LeaderboardMetric = 'yoy_growth_pct'
): UseLeaderboardDataResult {
  const [rawData, setRawData] = useState<LeaderboardEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);

    try {
      const dataUrl = `${import.meta.env.BASE_URL}data/dashboard_leaderboard.json.gz`;
      const parsed = await fetchGzipJson<LeaderboardEntry[]>(dataUrl);
      setRawData(parsed);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      setError(message);
      console.error('Failed to load leaderboard data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Apply filters and sorting
  const data = useMemo(() => {
    let result = applyFilters(rawData, filters);
    result = sortAndRank(result, sortBy, filters);
    return result;
  }, [rawData, filters, sortBy]);

  return {
    data,
    loading,
    error,
    reload: loadData,
  };
}

/**
 * Get the current metric value for a specific entry (exported for use in components)
 */
export { getCurrentMetricValue };
