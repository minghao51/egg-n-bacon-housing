/**
 * Runtime shape checks for the three archived research-tool assets (slice S8).
 *
 * `interactive_tools/*.json.gz` are *archive* assets: they are not listed in
 * `dashboard-release.json`, their extraction period and sample are not
 * supplied, and several of their fields are model outputs whose definition,
 * units or distance cap is undocumented. The workspace therefore validates
 * each payload before rendering it and falls back to an explicit unavailable
 * state instead of casting `unknown` into a convenient type (S1's containment
 * boundary, reused here).
 *
 * Pure module: no React, DOM or fetch.
 */

import type { SpatialHotspotsData } from "@/types/spatial-hotspots";

export interface LeaseBand {
  lease_age_band: string;
  min_lease_years: number;
  max_lease_years: number;
  discount_percent: number;
  annual_decay_rate: number;
  volume_category: string;
  risk_zone: string;
  transaction_count: number | null;
}

export interface LeaseInsight {
  band: string;
  discount: number;
  annual_rate: number;
  description: string;
}

export interface LeaseAsset {
  bands: LeaseBand[];
  insights: {
    maturity_cliff: LeaseInsight | null;
    best_value: LeaseInsight | null;
    safe_zone: LeaseInsight | null;
  };
}

export interface MrtTypeCoefficient {
  premium_per_100m: number;
  cbd_per_km: number;
}

export interface MrtAsset {
  property_type_multipliers: Record<string, MrtTypeCoefficient>;
  town_multipliers: Record<string, number>;
  town_premiums: Array<{
    town: string;
    multiplier: number;
  }>;
  cbd_coefficients: Record<
    string,
    { discount_per_km: number; explanation: string }
  >;
}

export type AssetRead<T> =
  | { ok: true; asset: T }
  | { ok: false; reason: string };

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function isString(value: unknown): value is string {
  return typeof value === "string";
}

function readInsight(value: unknown): LeaseInsight | null {
  if (!isRecord(value)) return null;
  return {
    band: isString(value.band) ? value.band : "Not supplied",
    discount: isFiniteNumber(value.discount) ? value.discount : 0,
    annual_rate: isFiniteNumber(value.annual_rate) ? value.annual_rate : 0,
    description: isString(value.description) ? value.description : "",
  };
}

/**
 * `lease_decay_analysis.json.gz`.
 *
 * `transaction_count` is present in the published asset but is treated as
 * optional: a band without it reports an unavailable row count instead of 0.
 */
export function readLeaseAsset(raw: unknown): AssetRead<LeaseAsset> {
  if (!isRecord(raw)) {
    return { ok: false, reason: "The lease asset is not an object." };
  }
  const rawBands = raw.bands;
  if (!Array.isArray(rawBands) || rawBands.length === 0) {
    return {
      ok: false,
      reason: "The lease asset supplies no stored lease bands.",
    };
  }

  const bands: LeaseBand[] = [];
  for (const entry of rawBands) {
    if (!isRecord(entry)) {
      return {
        ok: false,
        reason: "A stored lease band is not an object.",
      };
    }
    const {
      lease_age_band,
      min_lease_years,
      max_lease_years,
      discount_percent,
      annual_decay_rate,
      volume_category,
      risk_zone,
      transaction_count,
    } = entry;
    if (
      !isString(lease_age_band) ||
      !isFiniteNumber(min_lease_years) ||
      !isFiniteNumber(max_lease_years) ||
      !isFiniteNumber(discount_percent) ||
      !isFiniteNumber(annual_decay_rate) ||
      !isString(volume_category) ||
      !isString(risk_zone)
    ) {
      return {
        ok: false,
        reason:
          "A stored lease band is missing a label, an interval endpoint or a stored statistic.",
      };
    }
    bands.push({
      lease_age_band,
      min_lease_years,
      max_lease_years,
      discount_percent,
      annual_decay_rate,
      volume_category,
      risk_zone,
      transaction_count: isFiniteNumber(transaction_count)
        ? transaction_count
        : null,
    });
  }

  const rawInsights = isRecord(raw.insights) ? raw.insights : {};
  return {
    ok: true,
    asset: {
      bands,
      insights: {
        maturity_cliff: readInsight(rawInsights.maturity_cliff),
        best_value: readInsight(rawInsights.best_value),
        safe_zone: readInsight(rawInsights.safe_zone),
      },
    },
  };
}

/** `mrt_cbd_impact.json.gz`. */
export function readMrtAsset(raw: unknown): AssetRead<MrtAsset> {
  if (!isRecord(raw)) {
    return { ok: false, reason: "The MRT/CBD asset is not an object." };
  }
  const rawTypes = raw.property_type_multipliers;
  const rawTowns = raw.town_multipliers;
  if (!isRecord(rawTypes) || !isRecord(rawTowns)) {
    return {
      ok: false,
      reason:
        "The MRT/CBD asset is missing its property-type or town coefficient block.",
    };
  }
  if (
    Object.keys(rawTypes).length === 0 ||
    Object.keys(rawTowns).length === 0
  ) {
    return {
      ok: false,
      reason: "The MRT/CBD asset supplies no coefficients.",
    };
  }

  const property_type_multipliers: Record<string, MrtTypeCoefficient> = {};
  for (const [key, value] of Object.entries(rawTypes)) {
    if (
      !isRecord(value) ||
      !isFiniteNumber(value.premium_per_100m) ||
      !isFiniteNumber(value.cbd_per_km)
    ) {
      return {
        ok: false,
        reason: `The stored coefficient for ${key} is incomplete.`,
      };
    }
    property_type_multipliers[key] = {
      premium_per_100m: value.premium_per_100m,
      cbd_per_km: value.cbd_per_km,
    };
  }

  const town_multipliers: Record<string, number> = {};
  for (const [key, value] of Object.entries(rawTowns)) {
    if (!isFiniteNumber(value)) {
      return {
        ok: false,
        reason: `The stored town multiplier for ${key} is not a number.`,
      };
    }
    town_multipliers[key] = value;
  }

  const town_premiums: MrtAsset["town_premiums"] = [];
  if (Array.isArray(raw.town_premiums)) {
    for (const entry of raw.town_premiums) {
      if (
        isRecord(entry) &&
        isString(entry.town) &&
        isFiniteNumber(entry.multiplier)
      ) {
        town_premiums.push({ town: entry.town, multiplier: entry.multiplier });
      }
    }
  }

  const cbd_coefficients: MrtAsset["cbd_coefficients"] = {};
  const rawCbd = raw.cbd_coefficients;
  if (isRecord(rawCbd)) {
    for (const [key, value] of Object.entries(rawCbd)) {
      if (isRecord(value) && isFiniteNumber(value.discount_per_km)) {
        cbd_coefficients[key] = {
          discount_per_km: value.discount_per_km,
          explanation: isString(value.explanation) ? value.explanation : "",
        };
      }
    }
  }

  return {
    ok: true,
    asset: {
      property_type_multipliers,
      town_multipliers,
      town_premiums,
      cbd_coefficients,
    },
  };
}

const CLUSTER_TYPES = ["HH", "HL", "LH", "LL"] as const;
const RISK_LEVELS = ["low", "medium", "high"] as const;

function isClusterType(value: unknown): boolean {
  return isString(value) && CLUSTER_TYPES.includes(value as never);
}

/**
 * `spatial_hotspots.json.gz`.
 *
 * The published snapshot supplies `towns[]`; it has no `clusters[]` aggregate
 * block, no analysis date and no methodology field. `portfolio_allocation` is
 * deliberately *not* read: it is a model recommendation whose basis is
 * unreviewed (decision register), so the workspace never surfaces it.
 */
export function readSpatialAsset(raw: unknown): AssetRead<SpatialHotspotsData> {
  if (!isRecord(raw)) {
    return { ok: false, reason: "The spatial asset is not an object." };
  }
  const rawTowns = raw.towns;
  if (!Array.isArray(rawTowns) || rawTowns.length === 0) {
    return {
      ok: false,
      reason:
        "The spatial asset supplies no town records (the published snapshot uses towns[], not an aggregate clusters[] block).",
    };
  }

  const towns: SpatialHotspotsData["towns"] = [];
  for (const entry of rawTowns) {
    if (!isRecord(entry)) {
      return { ok: false, reason: "A spatial town record is not an object." };
    }
    const {
      town,
      median_price,
      appreciation_rate,
      cluster,
      cluster_description,
      persistence_probability,
      risk_level,
    } = entry;
    if (
      !isString(town) ||
      !isFiniteNumber(median_price) ||
      !isFiniteNumber(appreciation_rate) ||
      !isClusterType(cluster) ||
      !isFiniteNumber(persistence_probability) ||
      !isString(risk_level) ||
      !RISK_LEVELS.includes(risk_level as never)
    ) {
      return {
        ok: false,
        reason: `The spatial record for ${isString(town) ? town : "an unnamed town"} is incomplete.`,
      };
    }
    towns.push({
      town,
      median_price,
      appreciation_rate,
      cluster: cluster as SpatialHotspotsData["towns"][number]["cluster"],
      cluster_description: isString(cluster_description)
        ? cluster_description
        : "",
      persistence_probability,
      risk_level:
        risk_level as SpatialHotspotsData["towns"][number]["risk_level"],
    });
  }

  const town_clusters: SpatialHotspotsData["town_clusters"] = {};
  if (isRecord(raw.town_clusters)) {
    for (const [key, value] of Object.entries(raw.town_clusters)) {
      if (isClusterType(value)) {
        town_clusters[key] =
          value as SpatialHotspotsData["town_clusters"][string];
      }
    }
  }

  const cluster_descriptions: SpatialHotspotsData["cluster_descriptions"] = {};
  if (isRecord(raw.cluster_descriptions)) {
    for (const [key, value] of Object.entries(raw.cluster_descriptions)) {
      if (isClusterType(key) && isString(value)) {
        cluster_descriptions[key as keyof typeof cluster_descriptions] = value;
      }
    }
  }

  return {
    ok: true,
    asset: {
      towns,
      town_clusters,
      cluster_descriptions,
      // Never surfaced: see the doc comment above.
      portfolio_allocation: {},
    },
  };
}
