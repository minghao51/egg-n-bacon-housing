// Segment types for the enhanced dashboard

export type InvestmentType = 'yield' | 'growth' | 'value' | 'balanced' | 'luxury' | 'speculative';
export type SpatialCluster = 'HH' | 'HL' | 'LH' | 'LL';
export type PriceTier = 'affordable' | 'moderate' | 'premium' | 'luxury';
export type RiskLevel = 'low' | 'medium' | 'high' | 'very_high';
export type Volatility = 'low' | 'moderate' | 'high';
export type AppreciationPotential = 'low' | 'moderate' | 'high' | 'exceptional';
export type Region = 'CCR' | 'RCR' | 'OCR';
export type PropertyType = 'HDB' | 'Condominium' | 'EC';
export type SchoolTier = 'tier_1' | 'tier_2' | 'tier_3' | 'mixed';
export type MrtSensitivity = 'low' | 'moderate' | 'high';
export type Persona = 'all' | 'investor' | 'first-time-buyer' | 'upgrader';
export type InvestmentGoal = 'yield' | 'growth' | 'value' | 'balanced';
export type TimeHorizon = 'short' | 'medium' | 'long';

export interface SegmentMetrics {
  avgPricePsf: number;
  avgYield: number;
  yoyGrowth: number;
  transactionCount: number;
  marketShare: number;
}

export interface SegmentCharacteristics {
  priceTier: PriceTier;
  riskLevel: RiskLevel;
  volatility: Volatility;
  appreciationPotential: AppreciationPotential;
}

export interface SegmentImplications {
  investor: string;
  firstTimeBuyer: string;
  upgrader: string;
}

export interface Segment {
  id: string;
  name: string;
  description: string;
  investmentType: InvestmentType;
  clusterClassification: SpatialCluster;
  persistenceProbability: number;
  metrics: SegmentMetrics;
  characteristics: SegmentCharacteristics;
  implications: SegmentImplications;
  planningAreas: string[];
  regions: Region[];
  propertyTypes: PropertyType[];
  spatialClassification: SpatialCluster;
  mrtSensitivity: MrtSensitivity;
  schoolQuality: SchoolTier;
  riskFactors: string[];
  opportunities: string[];
}

export interface PlanningArea {
  name: string;
  region: Region;
  spatialCluster: SpatialCluster;
  hotspotConfidence: '99%' | '95%' | 'not_significant';
  persistenceProbability: number;
  mrtPremium: number;
  mrtSensitivity: MrtSensitivity;
  cbdDistance: number;
  schoolTier: SchoolTier;
  schoolPremium: number;
  forecast6m: number;
  avgPricePsf: number;
  avgYield: number;
  segments: string[];
}

export type PersonaApplicability = 'critical' | 'helpful' | 'optional';

export interface Insight {
  id: string;
  title: string;
  content: string;
  source: string;
  relevantFor: Persona[];
  propertyTypes?: PropertyType[];
  segments?: string[];
  personaApplicability: Record<Persona, PersonaApplicability>;
  learnMoreUrl?: string;
}

export interface SegmentsData {
  segments: Segment[];
  planningAreas: Record<string, PlanningArea>;
  insights: Insight[];
  lastUpdated: string;
  version: string;
}

export interface FilterState {
  investmentGoal: InvestmentGoal | null;
  budgetRange: [number, number];
  propertyTypes: PropertyType[];
  locations: Region[];
  timeHorizon: TimeHorizon | null;
  hotspotFilter: SpatialCluster | 'all';
}

export interface PersonaPreset {
  filters: Partial<FilterState>;
  priorityMetrics: string[];
  defaultInsights: string[];
}
