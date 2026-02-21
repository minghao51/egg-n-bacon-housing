/**
 * Analytics Data Loading Hook
 *
 * Custom React hook for lazy-loading analytics data with caching.
 */

import { useState, useEffect, useRef } from 'react';
import zlib from 'zlib';
import {
  SpatialAnalyticsData,
  FeatureImpactData,
  PredictiveAnalyticsData,
} from '../types/analytics';

interface UseAnalyticsDataResult<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

// Cache for loaded analytics data
const analyticsCache = new Map<string, unknown>();

/**
 * Load analytics data with caching
 *
 * @param type - Type of analytics to load ('spatial', 'feature', 'predictive')
 * @returns Object with data, loading state, and error
 */
export function useAnalyticsData<T>(
  type: 'spatial' | 'feature' | 'predictive'
): UseAnalyticsDataResult<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    // Return cached data if available
    const cacheKey = type;
    const cached = analyticsCache.get(cacheKey);
    if (cached) {
      setData(cached as T);
      setLoading(false);
      setError(null);
      return;
    }

    // Cancel previous request if component unmounts
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    // Create new abort controller for this request
    abortControllerRef.current = new AbortController();
    const signal = abortControllerRef.current.signal;

    const loadData = async () => {
      setLoading(true);
      setError(null);

      try {
        // Map type to correct filename
        const filename = type === 'feature'
          ? 'feature_impact'
          : type === 'predictive'
            ? 'predictive_analytics'
            : `${type}_analysis`;

        const response = await fetch(`/data/analytics/${filename}.json.gz`, {
          signal,
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        // Handle gzipped response
        const buffer = await response.arrayBuffer();
        const decompressed = zlib.inflateSync(Buffer.from(buffer)).toString('utf-8');
        const json = JSON.parse(decompressed);

        // Cache the response
        analyticsCache.set(cacheKey, json);
        setData(json);
        setError(null);
      } catch (err) {
        if (err instanceof Error) {
          if (err.name === 'AbortError') {
            // Request was cancelled, don't update state
            return;
          }
          setError(err.message);
        } else {
          setError('Failed to load analytics data');
        }
        setData(null);
      } finally {
        setLoading(false);
      }
    };

    loadData();

    // Cleanup function
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [type]);

  return { data, loading, error };
}

/**
 * Hook specifically for spatial analytics
 */
export function useSpatialAnalytics(): UseAnalyticsDataResult<SpatialAnalyticsData> {
  return useAnalyticsData<SpatialAnalyticsData>('spatial');
}

/**
 * Hook specifically for feature impact data
 */
export function useFeatureImpact(): UseAnalyticsDataResult<FeatureImpactData> {
  return useAnalyticsData<FeatureImpactData>('feature');
}

/**
 * Hook specifically for predictive analytics
 */
export function usePredictiveAnalytics(): UseAnalyticsDataResult<PredictiveAnalyticsData> {
  return useAnalyticsData<PredictiveAnalyticsData>('predictive');
}

/**
 * Clear the analytics cache (useful for testing or refresh)
 */
export function clearAnalyticsCache(): void {
  analyticsCache.clear();
}
