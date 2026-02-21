/**
 * Analytics Data Types
 *
 * TypeScript interfaces for analytics layers in the price map dashboard.
 */

export interface AnalyticsMetadata {
  generated_at: string;
  data_version: string;
  methodology?: string;
}

// ==================== Spatial Analytics ====================

export interface SpatialAnalyticsData {
  metadata: AnalyticsMetadata & {
    methodology: string;
  };
  planning_areas: Record<string, SpatialAreaData>;
}

export interface SpatialAreaData {
  hotspot: HotspotData;
  lisa_cluster: LISAClusterData;
  neighborhood_effect: NeighborhoodEffectData;
}

export interface HotspotData {
  z_score: number | null;
  p_value: number | null;
  confidence: string;
  classification: 'HOTSPOT' | 'COLDSPOT' | 'NOT_SIGNIFICANT';
}

export interface LISAClusterData {
  type: LISAClusterType;
  yoy_appreciation: number | null;
  persistence_rate: number | null;
  transition_probabilities: {
    to_hotspot: number | null;
    to_stable: number | null;
    to_coldspot: number | null;
  };
}

export const allLISAClusterTypes = [
  'MATURE_HOTSPOT',
  'EMERGING_HOTSPOT',
  'VALUE_OPPORTUNITY',
  'STABLE',
  'DECLINING',
  'TRANSITIONAL',
] as const;

export type LISAClusterType = typeof allLISAClusterTypes[number];

export interface NeighborhoodEffectData {
  moran_i_local: number | null;
  spatial_lag: number | null;
  neighborhood_multiplier: number | null;
}

// ==================== Feature Impact ====================

export interface FeatureImpactData {
  metadata: AnalyticsMetadata & {
    methodology: string;
  };
  planning_areas: Record<string, FeatureImpactAreaData>;
}

export interface FeatureImpactAreaData {
  mrt_impact: MRTImpactData;
  school_quality: SchoolQualityData;
  amenity_score: AmenityScoreData;
}

export interface MRTImpactData {
  hdb_sensitivity_psf_per_100m: number | null;
  condo_sensitivity_psf_per_100m: number | null;
  cbd_distance_km: number | null;
  cbd_explains_variance: number | null;
  mrt_vs_cbd_ratio: number | null;
}

export interface SchoolQualityData {
  primary_school_score: number | null;
  secondary_school_score: number | null;
  weighted_score: number | null;
  num_top_tier_schools: number | null;
  predictive_power: number | null;
}

export interface AmenityScoreData {
  hawker_center_accessibility: number | null;
  mall_accessibility: number | null;
  park_accessibility: number | null;
  optimal_combination_score: number | null;
  amenity_cluster_synergy: number | null;
}

// ==================== Predictive Analytics ====================

export interface PredictiveAnalyticsData {
  metadata: ForecastMetadata;
  planning_areas: Record<string, PredictiveAreaData>;
}

export interface ForecastMetadata extends AnalyticsMetadata {
  forecast_horizon: string;
  model_r2: number | null;
  last_training_date?: string;
}

export interface PredictiveAreaData {
  price_forecast: PriceForecastData;
  policy_risk: PolicyRiskData;
  lease_arbitrage: LeaseArbitrageData;
}

export interface PriceForecastData {
  projected_change_pct: number | null;
  confidence_interval_lower: number | null;
  confidence_interval_upper: number | null;
  model_r2: number | null;
  forecast_date: string;
  signal: TradingSignal;
}

export type TradingSignal = 'BUY' | 'HOLD' | 'SELL';

export interface PolicyRiskData {
  cooling_measure_sensitivity: number | null;
  market_segment: 'HDB' | 'PRIVATE' | 'ALL';
  elasticity: number | null;
  risk_level: 'LOW' | 'MODERATE' | 'HIGH';
}

export interface LeaseArbitrageData {
  theoretical_value_30yr: number | null;
  market_value_30yr: number | null;
  arbitrage_pct: number | null;
  recommendation: TradingSignal;
  theoretical_value_95yr: number | null;
  market_value_95yr: number | null;
  arbitrage_pct_95yr: number | null;
}

// ==================== Layer State ====================

// Define and export LayerId type directly (Vite/Astro compatible)
export type LayerId =
  // Spatial Analysis
  'spatial.hotspot' |
  'spatial.lisa' |
  'spatial.neighborhood' |
  // Feature Impact
  'feature.mrt' |
  'feature.school' |
  'feature.amenity' |
  // Predictive Analytics
  'predictive.policy' |
  'predictive.lease' |
  'predictive.forecast';

// Helper constant with all layer IDs
export const ALL_LAYER_IDS: LayerId[] = [
  'spatial.hotspot',
  'spatial.lisa',
  'spatial.neighborhood',
  'feature.mrt',
  'feature.school',
  'feature.amenity',
  'predictive.policy',
  'predictive.lease',
  'predictive.forecast',
];

export interface LayerState {
  [layerId: string]: boolean;
}

export const LAYER_CATEGORIES: Record<string, LayerId[]> = {
  spatial: ['spatial.hotspot', 'spatial.lisa', 'spatial.neighborhood'],
  feature: ['feature.mrt', 'feature.school', 'feature.amenity'],
  predictive: ['predictive.policy', 'predictive.lease', 'predictive.forecast'],
};

export const LAYER_METADATA: Record<LayerId, LayerMetadata> = {
  'spatial.hotspot': {
    id: 'spatial.hotspot',
    name: 'Hotspots/Coldspots',
    category: 'spatial',
    description: 'Getis-Ord Gi* z-scores showing statistically significant price clusters',
    colorScale: 'diverging',
  },
  'spatial.lisa': {
    id: 'spatial.lisa',
    name: 'LISA Clusters',
    category: 'spatial',
    description: 'Local Indicators of Spatial Association cluster classification',
    colorScale: 'categorical',
  },
  'spatial.neighborhood': {
    id: 'spatial.neighborhood',
    name: 'Neighborhood Effects',
    category: 'spatial',
    description: 'Local Moran\'s I showing neighborhood multiplier effects',
    colorScale: 'sequential',
  },
  'feature.mrt': {
    id: 'feature.mrt',
    name: 'MRT Sensitivity',
    category: 'feature',
    description: 'Price impact per 100m distance from MRT stations',
    colorScale: 'sequential',
  },
  'feature.school': {
    id: 'feature.school',
    name: 'School Quality',
    category: 'feature',
    description: 'Quality-weighted primary and secondary school scores',
    colorScale: 'sequential',
  },
  'feature.amenity': {
    id: 'feature.amenity',
    name: 'Amenity Scores',
    category: 'feature',
    description: 'Hawker, mall, and park accessibility scores',
    colorScale: 'sequential',
  },
  'predictive.policy': {
    id: 'predictive.policy',
    name: 'Policy Risk',
    category: 'predictive',
    description: 'Cooling measure sensitivity by market segment',
    colorScale: 'sequential',
  },
  'predictive.lease': {
    id: 'predictive.lease',
    name: 'Lease Arbitrage',
    category: 'predictive',
    description: 'Theoretical vs market value for 30-year and 95-year leases',
    colorScale: 'diverging',
  },
  'predictive.forecast': {
    id: 'predictive.forecast',
    name: 'Price Forecasts',
    category: 'predictive',
    description: '6-month price projections with confidence intervals',
    colorScale: 'diverging',
  },
};

export interface LayerMetadata {
  id: LayerId;
  name: string;
  category: string;
  description: string;
  colorScale: 'diverging' | 'sequential' | 'categorical';
}

export type ColorScaleType = 'diverging' | 'sequential' | 'categorical';

// ==================== GeoJSON Types ====================

/**
 * GeoJSON types for map data
 */
export interface GeoJSONProperties {
  [key: string]: string | number | boolean | null | undefined;
}

export interface GeoJSONFeature {
  type: 'Feature';
  id?: string | number;
  geometry: GeoJSONGeometry;
  properties: GeoJSONProperties;
}

export interface GeoJSONFeatureCollection {
  type: 'FeatureCollection';
  features: GeoJSONFeature[];
}

export type GeoJSONGeometry =
  | { type: 'Point'; coordinates: [number, number] }
  | { type: 'MultiPoint'; coordinates: [number, number][] }
  | { type: 'LineString'; coordinates: [number, number][] }
  | { type: 'MultiLineString'; coordinates: [number, number][][] }
  | { type: 'Polygon'; coordinates: [number, number][][] }
  | { type: 'MultiPolygon'; coordinates: [number, number][][][] };

// ==================== Map Metrics Types ====================

export interface MapMetrics {
  [areaName: string]: MetricValues;
}

export interface MetricValues {
  median_price: number;
  median_psf: number;
  volume: number;
  mom_change_pct?: number;
  yoy_change_pct?: number;
  momentum?: number;
  momentum_signal?: string;
  rental_yield_mean?: number;
  rental_yield_median?: number;
  rental_yield_std?: number;
  affordability_ratio?: number;
  affordability_class?: string;
  mortgage_to_income_pct?: number;
}

export interface MapData {
  whole: MapMetrics;
  pre_covid: MapMetrics;
  recent: MapMetrics;
  year_2025: MapMetrics;
  hdb: MapMetrics;
  ec: MapMetrics;
  condo: MapMetrics;
  whole_hdb: MapMetrics;
  whole_ec: MapMetrics;
  whole_condo: MapMetrics;
  pre_covid_hdb: MapMetrics;
  pre_covid_ec: MapMetrics;
  pre_covid_condo: MapMetrics;
  recent_hdb: MapMetrics;
  recent_ec: MapMetrics;
  recent_condo: MapMetrics;
  year_2025_hdb: MapMetrics;
  year_2025_ec: MapMetrics;
  year_2025_condo: MapMetrics;
}

export type TemporalFilter = 'whole' | 'pre_covid' | 'recent' | 'year_2025';
export type PropertyTypeFilter = 'all' | 'hdb' | 'ec' | 'condo';
export type MetricType =
  | 'median_price'
  | 'median_psf'
  | 'volume'
  | 'rental_yield_median'
  | 'yoy_change_pct'
  | 'affordability_ratio';
