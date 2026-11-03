/**
 * Published shape of `public/data/interactive_tools/spatial_hotspots.json.gz`.
 *
 * Verified against the served asset (S0 baseline §4.2). Top-level keys are
 * `towns`, `town_clusters`, `cluster_descriptions` and `portfolio_allocation`.
 * There is no `clusters` array, no `analysis_date`, no `methodology` field and
 * no cluster-level aggregate block (average appreciation, average price PSF,
 * cluster persistence or cluster risk), so consumers must render an explicit
 * unavailable state for those readouts instead of inventing them.
 */

export type HotspotClusterType = "HH" | "LH" | "HL" | "LL";

export type HotspotRiskLevel = "low" | "medium" | "high";

/** Personas that carry a published allocation in this snapshot. */
export type HotspotPortfolioPersona =
  | "investor"
  | "first-time-buyer"
  | "upgrader";

/** One record of the published `towns` array (40 records at S0). */
export interface SpatialHotspotTown {
  town: string;
  median_price: number;
  appreciation_rate: number;
  cluster: HotspotClusterType;
  cluster_description: string;
  persistence_probability: number;
  risk_level: HotspotRiskLevel;
}

/** `town_clusters` — uppercase planning area name to LISA cluster type. */
export type TownClusterMap = Record<string, HotspotClusterType>;

export interface SpatialHotspotsData {
  towns: SpatialHotspotTown[];
  town_clusters: TownClusterMap;
  cluster_descriptions: Partial<Record<HotspotClusterType, string>>;
  portfolio_allocation: Partial<
    Record<HotspotPortfolioPersona, Partial<Record<HotspotClusterType, number>>>
  >;
}
