/**
 * Research-map archive contract (slice S9, SVG 17).
 *
 * The three `analytics/*` extracts are archived model outputs, not current
 * evidence: the spatial extract stores the same z-score/p-value/LISA class for
 * every area, feature scores repeat a mid-point value, and the forecast target
 * is a past date. This module is the single place that:
 *
 * - names each of the nine retained layer IDs, its source asset and its units;
 * - reports per-layer load/error/unavailable status (one failure never erases
 *   the observed map or another layer group);
 * - inspects the stored fields for one selected area, with uniform-value and
 *   historical-forecast warnings;
 *
 * It never produces a recommendation, a current fill value or a cross-layer
 * quantity. Pure: no React, DOM, fetch or Leaflet.
 */

import type { LayerId } from "@/types/analytics";

export interface ArchiveLayerSource {
  layerId: LayerId;
  label: string;
  group: "spatial" | "feature" | "predictive";
  asset: string;
  /** Quantity and unit, as disclosed in the legend. */
  unit: string;
  /** Why the layer cannot be used as a current analytical fill. */
  gate: string;
}

export const ARCHIVE_LAYER_SOURCES: Readonly<
  Record<LayerId, ArchiveLayerSource>
> = {
  "spatial.hotspot": {
    layerId: "spatial.hotspot",
    label: "Hotspot z / p-value",
    group: "spatial",
    asset: "analytics/spatial_analysis.json.gz",
    unit: "z-score (dimensionless) · p-value (0–1)",
    gate: "Stored z and p are uniform across areas.",
  },
  "spatial.lisa": {
    layerId: "spatial.lisa",
    label: "LISA classification",
    group: "spatial",
    asset: "analytics/spatial_analysis.json.gz",
    unit: "Categorical class",
    gate: "Every stored area shares one class.",
  },
  "spatial.neighborhood": {
    layerId: "spatial.neighborhood",
    label: "Neighborhood multiplier",
    group: "spatial",
    asset: "analytics/spatial_analysis.json.gz",
    unit: "Local Moran's I (dimensionless) · lag (SGD) · multiplier (×)",
    gate: "Local Moran's I is a stored placeholder value.",
  },
  "feature.mrt": {
    layerId: "feature.mrt",
    label: "MRT / CBD coefficients",
    group: "feature",
    asset: "analytics/feature_impact.json.gz",
    unit: "S$ per square foot per 100 m · CBD distance (km)",
    gate: "Coefficient sign and distance direction are unreconciled.",
  },
  "feature.school": {
    layerId: "feature.school",
    label: "School quality scores",
    group: "feature",
    asset: "analytics/feature_impact.json.gz",
    unit: "Index 0–10",
    gate: "Every area stores the same mid-point index.",
  },
  "feature.amenity": {
    layerId: "feature.amenity",
    label: "Amenity accessibility",
    group: "feature",
    asset: "analytics/feature_impact.json.gz",
    unit: "Index 0–10",
    gate: "Every area stores the same mid-point index.",
  },
  "predictive.policy": {
    layerId: "predictive.policy",
    label: "Policy sensitivity",
    group: "predictive",
    asset: "analytics/predictive_analytics.json.gz",
    unit: "SGD sensitivity · elasticity (dimensionless)",
    gate: "Policy sensitivity is an archived model output.",
  },
  "predictive.lease": {
    layerId: "predictive.lease",
    label: "Lease model values",
    group: "predictive",
    asset: "analytics/predictive_analytics.json.gz",
    unit: "SGD theoretical vs market value · arbitrage (%)",
    gate: "Theoretical/market values are stored placeholders.",
  },
  "predictive.forecast": {
    layerId: "predictive.forecast",
    label: "Historical forecast",
    group: "predictive",
    asset: "analytics/predictive_analytics.json.gz",
    unit: "Projected change (%) · interval (%) · target date",
    gate: "The target date is in the past; this is not a forward forecast.",
  },
};

export const ARCHIVE_LAYER_IDS: readonly LayerId[] = Object.keys(
  ARCHIVE_LAYER_SOURCES,
) as LayerId[];

export type ArchiveLoadState = "loading" | "available" | "error";

export interface AnalyticsGroupState {
  data: unknown | null;
  loading: boolean;
  error: string | null;
}

export interface ArchiveLayerStatus {
  layerId: LayerId;
  state: ArchiveLoadState;
  /** Human-readable detail for the layer list. */
  detail: string;
  asset: string;
}

function groupState(
  group: ArchiveLayerSource["group"],
  states: {
    spatial: AnalyticsGroupState;
    feature: AnalyticsGroupState;
    predictive: AnalyticsGroupState;
  },
): ArchiveLoadState {
  const state = states[group];
  if (state.error !== null) return "error";
  if (state.loading && state.data === null) return "loading";
  return "available";
}

/**
 * Per-layer status. Each group can fail on its own: a spatial fetch error marks
 * the three spatial layers only, while the feature and predictive layers and
 * the observed map keep working.
 */
export function archiveLayerStatuses(states: {
  spatial: AnalyticsGroupState;
  feature: AnalyticsGroupState;
  predictive: AnalyticsGroupState;
}): Record<LayerId, ArchiveLayerStatus> {
  const statuses = {} as Record<LayerId, ArchiveLayerStatus>;
  for (const layerId of ARCHIVE_LAYER_IDS) {
    const source = ARCHIVE_LAYER_SOURCES[layerId];
    const state = groupState(source.group, states);
    const groupError =
      states[source.group].error === null
        ? null
        : String(states[source.group].error);
    statuses[layerId] = {
      layerId,
      state,
      detail:
        state === "error"
          ? `Source unavailable. ${groupError ?? "The published asset could not be read."}`
          : state === "loading"
            ? "Loading the archived asset…"
            : "Archived fields available for inspection.",
      asset: source.asset,
    };
  }
  return statuses;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function canonicalAreaId(value: string): string {
  return value.trim().replace(/\s+/g, " ").toUpperCase();
}

/** Find an area entry regardless of key case; never a fallback to another area. */
function findArea(
  areas: unknown,
  areaId: string,
): Record<string, unknown> | null {
  if (!isRecord(areas)) return null;
  const canonical = canonicalAreaId(areaId);
  for (const [key, value] of Object.entries(areas)) {
    if (canonicalAreaId(key) === canonical && isRecord(value)) {
      return value;
    }
  }
  return null;
}

function numberField(
  record: Record<string, unknown> | null,
  key: string,
): number | null {
  if (record === null) return null;
  const value = record[key];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function stringField(
  record: Record<string, unknown> | null,
  key: string,
): string | null {
  if (record === null) return null;
  const value = record[key];
  return typeof value === "string" ? value : null;
}

function nested(
  record: Record<string, unknown> | null,
  key: string,
): Record<string, unknown> | null {
  if (record === null) return null;
  const value = record[key];
  return isRecord(value) ? value : null;
}

function formatNumber(value: number | null, digits = 1): string {
  return value === null ? "N/A" : value.toFixed(digits);
}

export interface ArchiveFieldRow {
  layerId: LayerId;
  label: string;
  values: Array<{ label: string; value: string }>;
}

export interface ArchiveGroupMeta {
  group: ArchiveLayerSource["group"];
  asset: string;
  generatedAt: string | null;
  dataVersion: string | null;
  extra: string | null;
}

export interface ArchiveInspection {
  areaId: string | null;
  rows: ArchiveFieldRow[];
  warnings: string[];
  metadata: ArchiveGroupMeta[];
  coverage: { archivedAreas: number; mapFeatures: number } | null;
}

function areaCount(data: unknown): number {
  if (!isRecord(data)) return 0;
  const areas = data.planning_areas;
  return isRecord(areas) ? Object.keys(areas).length : 0;
}

function distinctCount(data: unknown, keys: readonly string[]): number | null {
  if (!isRecord(data) || !isRecord(data.planning_areas)) return null;
  const seen = new Set<string>();
  for (const value of Object.values(data.planning_areas)) {
    if (!isRecord(value)) continue;
    let current: unknown = value;
    for (const key of keys) {
      current = isRecord(current) ? current[key] : null;
    }
    seen.add(JSON.stringify(current ?? null));
  }
  return seen.size;
}

function metadataFor(
  group: ArchiveLayerSource["group"],
  data: unknown,
): ArchiveGroupMeta {
  const source =
    ARCHIVE_LAYER_SOURCES[
      group === "spatial"
        ? "spatial.hotspot"
        : group === "feature"
          ? "feature.mrt"
          : "predictive.forecast"
    ];
  const meta = isRecord(data) && isRecord(data.metadata) ? data.metadata : null;
  return {
    group,
    asset: source.asset,
    generatedAt: stringField(meta, "generated_at"),
    dataVersion: stringField(meta, "data_version"),
    extra:
      group === "predictive"
        ? [
            stringField(meta, "forecast_horizon")
              ? `horizon ${stringField(meta, "forecast_horizon")}`
              : null,
            stringField(meta, "last_training_date")
              ? `trained ${stringField(meta, "last_training_date")}`
              : null,
          ]
            .filter(Boolean)
            .join(" · ") || null
        : null,
  };
}

function spatialRows(
  area: Record<string, unknown> | null,
  layerId: LayerId,
): ArchiveFieldRow | null {
  const source = ARCHIVE_LAYER_SOURCES[layerId];
  if (layerId === "spatial.hotspot") {
    const hotspot = nested(area, "hotspot");
    return {
      layerId,
      label: source.label,
      values: [
        {
          label: "Stored z-score",
          value: formatNumber(numberField(hotspot, "z_score"), 2),
        },
        {
          label: "Stored p-value",
          value: formatNumber(numberField(hotspot, "p_value"), 2),
        },
        {
          label: "Stored classification",
          value: stringField(hotspot, "classification") ?? "N/A",
        },
      ],
    };
  }
  if (layerId === "spatial.lisa") {
    const lisa = nested(area, "lisa_cluster");
    return {
      layerId,
      label: source.label,
      values: [
        {
          label: "Stored LISA class",
          value: stringField(lisa, "type") ?? "N/A",
        },
        {
          label: "Stored YoY field",
          value:
            numberField(lisa, "yoy_appreciation") === null
              ? "N/A"
              : `${formatNumber(numberField(lisa, "yoy_appreciation"))}%`,
        },
        {
          label: "Stored persistence field",
          value:
            numberField(lisa, "persistence_rate") === null
              ? "N/A"
              : `${(numberField(lisa, "persistence_rate")! * 100).toFixed(0)}%`,
        },
      ],
    };
  }
  const neighborhood = nested(area, "neighborhood_effect");
  return {
    layerId,
    label: source.label,
    values: [
      {
        label: "Local Moran's I",
        value: formatNumber(numberField(neighborhood, "moran_i_local"), 2),
      },
      {
        label: "Spatial lag",
        value:
          numberField(neighborhood, "spatial_lag") === null
            ? "N/A"
            : `S$${numberField(neighborhood, "spatial_lag")!.toLocaleString("en-SG")}`,
      },
      {
        label: "Neighborhood multiplier",
        value:
          numberField(neighborhood, "neighborhood_multiplier") === null
            ? "N/A"
            : `${formatNumber(numberField(neighborhood, "neighborhood_multiplier"), 2)}×`,
      },
    ],
  };
}

function featureRows(
  area: Record<string, unknown> | null,
  layerId: LayerId,
  propertyType: "hdb" | "condo",
): ArchiveFieldRow | null {
  const source = ARCHIVE_LAYER_SOURCES[layerId];
  if (layerId === "feature.mrt") {
    const mrt = nested(area, "mrt_impact");
    return {
      layerId,
      label: source.label,
      values: [
        {
          label: `HDB sensitivity (S$/sqft/100m)`,
          value: formatNumber(
            numberField(mrt, "hdb_sensitivity_psf_per_100m"),
            1,
          ),
        },
        {
          label: "Condo sensitivity (S$/sqft/100m)",
          value: formatNumber(
            numberField(mrt, "condo_sensitivity_psf_per_100m"),
            1,
          ),
        },
        {
          label: "CBD distance (km)",
          value: formatNumber(numberField(mrt, "cbd_distance_km"), 1),
        },
        {
          label: `Stored direction (${propertyType})`,
          value:
            propertyType === "hdb"
              ? formatNumber(
                  numberField(mrt, "hdb_sensitivity_psf_per_100m"),
                  1,
                )
              : formatNumber(
                  numberField(mrt, "condo_sensitivity_psf_per_100m"),
                  1,
                ),
        },
      ],
    };
  }
  if (layerId === "feature.school") {
    const school = nested(area, "school_quality");
    return {
      layerId,
      label: source.label,
      values: [
        {
          label: "Weighted score (0–10)",
          value: formatNumber(numberField(school, "weighted_score"), 1),
        },
        {
          label: "Top-tier schools",
          value: formatNumber(numberField(school, "num_top_tier_schools"), 0),
        },
        {
          label: "Stored predictive power",
          value: formatNumber(numberField(school, "predictive_power"), 2),
        },
      ],
    };
  }
  const amenity = nested(area, "amenity_score");
  return {
    layerId,
    label: source.label,
    values: [
      {
        label: "Hawker accessibility (0–10)",
        value: formatNumber(
          numberField(amenity, "hawker_center_accessibility"),
          1,
        ),
      },
      {
        label: "Mall accessibility (0–10)",
        value: formatNumber(numberField(amenity, "mall_accessibility"), 1),
      },
      {
        label: "Park accessibility (0–10)",
        value: formatNumber(numberField(amenity, "park_accessibility"), 1),
      },
    ],
  };
}

function predictiveRows(
  area: Record<string, unknown> | null,
  layerId: LayerId,
): ArchiveFieldRow | null {
  const source = ARCHIVE_LAYER_SOURCES[layerId];
  if (layerId === "predictive.policy") {
    const policy = nested(area, "policy_risk");
    return {
      layerId,
      label: source.label,
      values: [
        {
          label: "Stored cooling sensitivity (SGD)",
          value:
            numberField(policy, "cooling_measure_sensitivity") === null
              ? "N/A"
              : `S$${numberField(policy, "cooling_measure_sensitivity")!.toLocaleString("en-SG")}`,
        },
        {
          label: "Stored segment",
          value: stringField(policy, "market_segment") ?? "N/A",
        },
        {
          label: "Stored risk label",
          value: stringField(policy, "risk_level") ?? "N/A",
        },
      ],
    };
  }
  if (layerId === "predictive.lease") {
    const lease = nested(area, "lease_arbitrage");
    return {
      layerId,
      label: source.label,
      values: [
        {
          label: "Theoretical value, 30yr",
          value:
            numberField(lease, "theoretical_value_30yr") === null
              ? "N/A"
              : `S$${numberField(lease, "theoretical_value_30yr")!.toLocaleString("en-SG")}`,
        },
        {
          label: "Market value, 30yr",
          value:
            numberField(lease, "market_value_30yr") === null
              ? "N/A"
              : `S$${numberField(lease, "market_value_30yr")!.toLocaleString("en-SG")}`,
        },
        {
          label: "Stored arbitrage (%)",
          value:
            numberField(lease, "arbitrage_pct") === null
              ? "N/A"
              : `${formatNumber(numberField(lease, "arbitrage_pct"))}%`,
        },
      ],
    };
  }
  const forecast = nested(area, "price_forecast");
  return {
    layerId,
    label: source.label,
    values: [
      {
        label: "Stored projected change (%)",
        value:
          numberField(forecast, "projected_change_pct") === null
            ? "N/A"
            : `${formatNumber(numberField(forecast, "projected_change_pct"))}%`,
      },
      {
        label: "Stored interval (%)",
        value:
          numberField(forecast, "confidence_interval_lower") === null ||
          numberField(forecast, "confidence_interval_upper") === null
            ? "N/A"
            : `${formatNumber(numberField(forecast, "confidence_interval_lower"))} to ${formatNumber(numberField(forecast, "confidence_interval_upper"))}%`,
      },
      {
        label: "Stored forecast target",
        value: stringField(forecast, "forecast_date") ?? "N/A",
      },
      {
        label: "Stored signal (archive, not advice)",
        value: stringField(forecast, "signal") ?? "N/A",
      },
    ],
  };
}

export interface InspectArchiveArgs {
  spatial: unknown;
  feature: unknown;
  predictive: unknown;
  selectedArea: string | null;
  activeLayers: readonly LayerId[];
  propertyType?: "hdb" | "condo";
  mapFeatureCount?: number;
}

/**
 * Inspect the stored archive fields for one area. Warnings are computed from
 * the published values (not hardcoded) so a repaired asset stops warning.
 */
export function inspectArchiveArea({
  spatial,
  feature,
  predictive,
  selectedArea,
  activeLayers,
  propertyType = "hdb",
  mapFeatureCount = 0,
}: InspectArchiveArgs): ArchiveInspection {
  const warnings: string[] = [];
  const rows: ArchiveFieldRow[] = [];
  const activeGroups = new Set(
    activeLayers.map((layerId) => ARCHIVE_LAYER_SOURCES[layerId].group),
  );

  const spatialAreas = isRecord(spatial) ? spatial.planning_areas : null;
  const featureAreas = isRecord(feature) ? feature.planning_areas : null;
  const predictiveAreas = isRecord(predictive)
    ? predictive.planning_areas
    : null;

  const areaId = selectedArea === null ? null : canonicalAreaId(selectedArea);
  const spatialArea = areaId === null ? null : findArea(spatialAreas, areaId);
  const featureArea = areaId === null ? null : findArea(featureAreas, areaId);
  const predictiveArea =
    areaId === null ? null : findArea(predictiveAreas, areaId);

  for (const layerId of activeLayers) {
    const source = ARCHIVE_LAYER_SOURCES[layerId];
    const areaRecord =
      source.group === "spatial"
        ? spatialArea
        : source.group === "feature"
          ? featureArea
          : predictiveArea;
    // An absent area is unavailable: no row of N/A placeholders is invented.
    if (areaId === null || areaRecord === null) continue;
    const row =
      source.group === "spatial"
        ? spatialRows(areaRecord, layerId)
        : source.group === "feature"
          ? featureRows(areaRecord, layerId, propertyType)
          : predictiveRows(areaRecord, layerId);
    if (row !== null) rows.push(row);
  }

  if (areaId !== null) {
    const missingGroups: string[] = [];
    if (activeGroups.has("spatial") && spatialArea === null) {
      missingGroups.push("spatial");
    }
    if (activeGroups.has("feature") && featureArea === null) {
      missingGroups.push("feature");
    }
    if (activeGroups.has("predictive") && predictiveArea === null) {
      missingGroups.push("predictive");
    }
    if (missingGroups.length > 0) {
      warnings.push(
        `No archived ${missingGroups.join(" / ")} record exists for ${areaId}. An absent record is unavailable, not a zero.`,
      );
    }
  }

  // Uniform-value checks are data-driven: they disappear when an asset carries
  // real variation.
  // Every field the warning text claims is shared must actually be uniform;
  // a repaired p-value or LISA label alone must stop the warning.
  const spatialVariations = [
    distinctCount(spatial, ["hotspot", "z_score"]),
    distinctCount(spatial, ["hotspot", "p_value"]),
    distinctCount(spatial, ["lisa_cluster", "type"]),
  ];
  const spatialUniform = spatialVariations.every(
    (variation) => variation === 1,
  );
  const spatialAreaCount = areaCount(spatial);
  if (
    areaId !== null &&
    activeGroups.has("spatial") &&
    spatialUniform &&
    spatialAreaCount > 0
  ) {
    const hotspot = nested(spatialArea, "hotspot");
    const lisa = nested(spatialArea, "lisa_cluster");
    warnings.push(
      `All ${spatialAreaCount} archived areas share the same stored spatial pattern (z ${formatNumber(numberField(hotspot, "z_score"), 2)}, p ${formatNumber(numberField(hotspot, "p_value"), 2)}, LISA ${stringField(lisa, "type") ?? "N/A"}). Uniform values are not evidence of current spatial stability.`,
    );
  }

  const schoolVariation = distinctCount(feature, [
    "school_quality",
    "weighted_score",
  ]);
  const featureAreaCount = areaCount(feature);
  if (
    areaId !== null &&
    activeGroups.has("feature") &&
    schoolVariation === 1 &&
    featureAreaCount > 0
  ) {
    warnings.push(
      `All ${featureAreaCount} archived areas store the same school score. A uniform index is a placeholder, not a measured school effect.`,
    );
  }

  const forecastVariation = distinctCount(predictive, [
    "price_forecast",
    "projected_change_pct",
  ]);
  const predictiveAreaCount = areaCount(predictive);
  if (
    areaId !== null &&
    activeGroups.has("predictive") &&
    forecastVariation === 1 &&
    predictiveAreaCount > 0
  ) {
    const forecast = nested(predictiveArea, "price_forecast");
    warnings.push(
      `All ${predictiveAreaCount} archived areas store the same projected change (${formatNumber(numberField(forecast, "projected_change_pct"))}%). A uniform projection is a placeholder, not a market forecast.`,
    );
  }

  const forecastTarget = stringField(
    nested(predictiveArea, "price_forecast"),
    "forecast_date",
  );
  const predictiveGeneratedAt = metadataFor(
    "predictive",
    predictive,
  ).generatedAt;
  if (
    activeGroups.has("predictive") &&
    areaId !== null &&
    forecastTarget !== null &&
    predictiveGeneratedAt !== null &&
    forecastTarget < predictiveGeneratedAt.slice(0, 10)
  ) {
    warnings.push(
      `The stored forecast target ${forecastTarget} predates this extract's generation (${predictiveGeneratedAt.slice(0, 10)}). It is an archived forecast, never a current or forward-looking one.`,
    );
  }

  const metadata = [
    metadataFor("spatial", spatial),
    metadataFor("feature", feature),
    metadataFor("predictive", predictive),
  ];

  return {
    areaId,
    rows,
    warnings,
    metadata,
    coverage:
      mapFeatureCount > 0
        ? {
            archivedAreas: Math.max(
              spatialAreaCount,
              featureAreaCount,
              predictiveAreaCount,
            ),
            mapFeatures: mapFeatureCount,
          }
        : null,
  };
}

/** Observed-map legend text: quantity, unit, period, evidence status. */
export function observedLegend(
  metric: string,
  periodLabel: string,
  propertyLabel: string,
): { quantity: string; unit: string; period: string; status: string } {
  const quantity: Record<string, { label: string; unit: string }> = {
    median_price: { label: "Median price", unit: "SGD" },
    median_psf: { label: "Median PSF", unit: "SGD per square foot" },
    volume: { label: "Transactions", unit: "count" },
    rental_yield_median: { label: "Rental yield", unit: "%" },
    yoy_change_pct: { label: "Year-on-year change", unit: "%" },
    affordability_ratio: {
      label: "Affordability ratio",
      unit: "× annual income",
    },
  };
  const entry = quantity[metric] ?? { label: metric, unit: "not declared" };
  return {
    quantity: entry.label,
    unit: entry.unit,
    period: `${periodLabel} · ${propertyLabel}`,
    status: "Observed transactions",
  };
}
