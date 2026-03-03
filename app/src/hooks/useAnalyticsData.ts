/**
 * Analytics Data Loading Hook
 *
 * Custom React hook for lazy-loading analytics data with caching.
 */

import type {
  SpatialAnalyticsData,
  FeatureImpactData,
  PredictiveAnalyticsData,
} from '../types/analytics';
import { useGzipJson } from './useGzipJson';
import { getAnalyticsUrl } from '@/constants/data-urls';
import type { AnalyticsType } from '@/constants/data-urls';

type UseAnalyticsDataResult<T> = ReturnType<typeof useGzipJson<T>>;

export function useAnalyticsData<T>(type: AnalyticsType): UseAnalyticsDataResult<T> {
  return useGzipJson<T>(getAnalyticsUrl(type), `analytics-${type}`, true);
}

export function useSpatialAnalytics(): UseAnalyticsDataResult<SpatialAnalyticsData> {
  return useAnalyticsData<SpatialAnalyticsData>('spatial');
}

export function useFeatureImpact(): UseAnalyticsDataResult<FeatureImpactData> {
  return useAnalyticsData<FeatureImpactData>('feature');
}

export function usePredictiveAnalytics(): UseAnalyticsDataResult<PredictiveAnalyticsData> {
  return useAnalyticsData<PredictiveAnalyticsData>('predictive');
}
