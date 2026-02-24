/**
 * Data URL Constants
 *
 * Centralized list of all data endpoints used by the dashboard.
 */

const BASE_URL = import.meta.env.BASE_URL || '/';

export const DATA_URLS = {
  segments: `${BASE_URL}data/segments_enhanced.json.gz`,
  leaderboard: `${BASE_URL}data/dashboard_leaderboard.json.gz`,
  overview: `${BASE_URL}data/dashboard_overview.json.gz`,
  trends: `${BASE_URL}data/dashboard_trends.json.gz`,
  segmentsList: `${BASE_URL}data/dashboard_segments.json.gz`,
  leaderboardList: `${BASE_URL}data/dashboard_leaderboard.json.gz`,
  mapMetrics: `${BASE_URL}data/map_metrics.json.gz`,
  hotspots: `${BASE_URL}data/hotspots.json.gz`,
  amenitySummary: `${BASE_URL}data/amenity_summary.json.gz`,
  planningAreas: `${BASE_URL}data/planning_areas.geojson`,
  analytics: {
    spatial: `${BASE_URL}data/analytics/spatial_analysis.json.gz`,
    feature: `${BASE_URL}data/analytics/feature_impact.json.gz`,
    predictive: `${BASE_URL}data/analytics/predictive_analytics.json.gz`,
  },
  interactive: {
    mrtCbd: `${BASE_URL}data/interactive_tools/mrt_cbd_impact.json.gz`,
    spatialHotspots: `${BASE_URL}data/interactive_tools/spatial_hotspots.json.gz`,
    leaseDecay: `${BASE_URL}data/interactive_tools/lease_decay_analysis.json.gz`,
    affordability: `${BASE_URL}data/interactive_tools/affordability_metrics.json.gz`,
  },
} as const;

export type AnalyticsType = 'spatial' | 'feature' | 'predictive';

export function getAnalyticsUrl(type: AnalyticsType): string {
  return DATA_URLS.analytics[type];
}

export type DataEndpoint = keyof typeof DATA_URLS;
