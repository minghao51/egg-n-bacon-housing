/**
 * Pure observed-data adapter.
 *
 * Resolves observed area and national observations from the published
 * `map_metrics.json.gz` and `dashboard_overview.json.gz` shapes with explicit
 * availability states and per-observation source identity.
 *
 * Constraints (see docs/implementation/s0-baseline.md and
 * assets/svg/implementation-plan.md §3.1):
 * - No React, DOM, fetch or file access — this module is safe to import from an
 *   island, a build-time loader or a unit test.
 * - Section keys are the joint `map_metrics[era_property]` keys. The
 *   property-only (`hdb`) and period-only (`pre_covid`) sections that also
 *   exist in the asset are never used as a fallback.
 * - Missing section, missing area or non-object section value resolve to
 *   `null`; there is no zero-filled or partial record.
 * - A `null`/`undefined`/non-finite field is `"missing"`. An exact `0` is
 *   `"empty"` with a `null` value: the exporter writes an all-zero block when a
 *   subset has no rows (`get_stats`, scripts/export_app_data.py), and `0` must
 *   never render as a real S$0 median.
 * - Numbers are returned unrounded and unformatted; display is a UI concern.
 */

export type EraId = "whole" | "pre_covid" | "recent" | "year_2025";

export type PropertyTypeId = "all" | "hdb" | "ec" | "condo";

export type ObservedMetric = "median_price" | "median_psf" | "volume";

/** `volume` is the count field in the map_metrics / overview stats blocks. */
export const OBSERVED_METRICS = [
  "median_price",
  "median_psf",
  "volume",
] as const satisfies readonly ObservedMetric[];

export type ObservationStatus = "available" | "missing" | "empty";

export type ObservedAsset = "map_metrics" | "dashboard_overview";

export interface EraDefinition {
  id: EraId;
  label: string;
  coverageNote: string;
}

/**
 * Literal era labels and boundaries. These mirror the exporter's
 * `ERA_FILTERS` (scripts/export_app_data.py): whole = all rows,
 * pre_covid = `year <= 2021`, recent = `year >= 2022`,
 * year_2025 = `year == 2025`. Nothing here is computed from the current date.
 */
export const ERA_DEFINITIONS: readonly EraDefinition[] = [
  {
    id: "whole",
    label: "All history",
    coverageNote:
      "Every transaction in the published dataset, from the earliest recorded sale to the latest.",
  },
  {
    id: "pre_covid",
    label: "Through 2021",
    coverageNote: "Transactions dated on or before 2021-12-31.",
  },
  {
    id: "recent",
    label: "2022 onward",
    coverageNote:
      "Transactions dated 2022-01-01 or later, ending at the actual coverage of the published data — not at today.",
  },
  {
    id: "year_2025",
    label: "2025 complete year",
    coverageNote: "Transactions dated 2025-01-01 through 2025-12-31.",
  },
];

export interface ObservationSource {
  asset: ObservedAsset;
  section: string;
  propertyType: PropertyTypeId;
  era: EraId;
}

export interface ObservedObservation {
  metric: ObservedMetric;
  value: number | null;
  status: ObservationStatus;
  source: ObservationSource;
}

export interface ObservedAreaRecord {
  areaId: string;
  areaName: string;
  slug: string;
  era: EraId;
  propertyType: PropertyTypeId;
  section: string;
  metrics: ObservedObservation[];
}

/** Narrow an `unknown` payload to a plain object (not an array, not null). */
function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/**
 * Joint section key: `${era}` for the all-property view, else
 * `${era}_${propertyType}`. Never returns the property-only (`hdb`) or
 * period-only (`pre_covid`) keys that also exist in the asset.
 */
export function sectionKey(era: EraId, propertyType: PropertyTypeId): string {
  return propertyType === "all" ? era : `${era}_${propertyType}`;
}

/**
 * Canonical planning-area id: trimmed, internal whitespace collapsed,
 * uppercased. The asset's keys are already uppercase with single spaces, so an
 * already-canonical id is returned unchanged.
 */
export function canonicalAreaId(name: string): string {
  return name.trim().replace(/\s+/g, " ").toUpperCase();
}

/** URL slug for a planning area, e.g. "ang-mo-kio". */
export function areaSlug(name: string): string {
  return canonicalAreaId(name).toLowerCase().replace(/\s+/g, "-");
}

/**
 * Display name for a canonical id, e.g. "ANG MO KIO" -> "Ang Mo Kio" and
 * "NORTH-EASTERN ISLANDS" -> "North-Eastern Islands".
 */
export function formatAreaName(areaId: string): string {
  return canonicalAreaId(areaId)
    .split(" ")
    .map((word) =>
      word
        .split("-")
        .map((part) =>
          part === ""
            ? part
            : part.charAt(0).toUpperCase() + part.slice(1).toLowerCase(),
        )
        .join("-"),
    )
    .join(" ");
}

/**
 * Read one era x property-type section object from a map_metrics payload.
 * Returns `null` when the section is absent or is not a plain object.
 */
export function getSection(
  mapMetrics: unknown,
  era: EraId,
  propertyType: PropertyTypeId,
): Record<string, unknown> | null {
  if (!isRecord(mapMetrics)) return null;
  const section = mapMetrics[sectionKey(era, propertyType)];
  return isRecord(section) ? section : null;
}

/**
 * Look up an area entry by canonical id. The asset's keys are already
 * canonical, but a non-canonical key with the same identity is accepted.
 */
function findAreaEntry(
  section: Record<string, unknown>,
  areaId: string,
): unknown {
  const direct = section[areaId];
  if (direct !== undefined) return direct;
  const matchedKey = Object.keys(section).find(
    (key) => canonicalAreaId(key) === areaId,
  );
  return matchedKey === undefined ? undefined : section[matchedKey];
}

/** Classify one metric field: available / missing / exporter-empty. */
function toObservation(
  rawSection: Record<string, unknown>,
  metric: ObservedMetric,
  source: ObservationSource,
): ObservedObservation {
  const raw = rawSection[metric];
  if (typeof raw !== "number" || !Number.isFinite(raw)) {
    return { metric, value: null, status: "missing", source };
  }
  if (raw === 0) {
    // Exporter empty block (no rows in the subset) — never a real S$0 median.
    return { metric, value: null, status: "empty", source };
  }
  if (raw > 0) {
    return { metric, value: raw, status: "available", source };
  }
  // Negative finite values are not a valid median/PSF/count.
  return { metric, value: null, status: "missing", source };
}

/**
 * Read one planning area's observed metrics for a joint era x property section.
 * Returns `null` when the section is missing, the area is absent, or the area
 * entry is not a plain object. Area matching is on {@link canonicalAreaId}.
 */
export function readAreaObservation(
  mapMetrics: unknown,
  era: EraId,
  propertyType: PropertyTypeId,
  area: string,
): ObservedAreaRecord | null {
  const section = getSection(mapMetrics, era, propertyType);
  if (section === null) return null;

  const areaId = canonicalAreaId(area);
  if (areaId === "") return null;

  const rawArea = findAreaEntry(section, areaId);
  if (!isRecord(rawArea)) return null;

  const sectionName = sectionKey(era, propertyType);
  const source: ObservationSource = {
    asset: "map_metrics",
    section: sectionName,
    propertyType,
    era,
  };

  return {
    areaId,
    areaName: formatAreaName(areaId),
    slug: areaSlug(areaId),
    era,
    propertyType,
    section: sectionName,
    metrics: OBSERVED_METRICS.map((metric) =>
      toObservation(rawArea, metric, source),
    ),
  };
}

/**
 * Resolve the stats block from a dashboard_overview payload. Accepts either the
 * full payload (`{ metadata, stats, distributions }`) or the `stats` block
 * itself; returns `null` for anything else.
 */
function resolveOverviewStats(
  overview: unknown,
): Record<string, unknown> | null {
  if (!isRecord(overview)) return null;
  const stats = overview["stats"];
  if (isRecord(stats)) return stats;
  return overview;
}

/**
 * Read the national baseline for a joint era x property section from
 * `dashboard_overview.stats`. These are national aggregates, not the mean of
 * the area medians in `map_metrics`. Returns `null` when the section is absent
 * or not a plain object — there is no all-history fallback.
 */
export function readNationalBaseline(
  overviewStats: unknown,
  era: EraId,
  propertyType: PropertyTypeId,
): ObservedObservation[] | null {
  const stats = resolveOverviewStats(overviewStats);
  if (stats === null) return null;

  const sectionName = sectionKey(era, propertyType);
  const rawSection = stats[sectionName];
  if (!isRecord(rawSection)) return null;

  const source: ObservationSource = {
    asset: "dashboard_overview",
    section: sectionName,
    propertyType,
    era,
  };

  return OBSERVED_METRICS.map((metric) =>
    toObservation(rawSection, metric, source),
  );
}

/**
 * Area minus baseline difference and percent-of-baseline, unrounded.
 * Returns `null` when either value is missing/empty or the baseline is `0`.
 */
export function compareWithBaseline(
  area: ObservedObservation,
  baseline: ObservedObservation,
): { difference: number; percentOfBaseline: number } | null {
  if (area.value === null || baseline.value === null) return null;
  if (baseline.value === 0) return null;
  const difference = area.value - baseline.value;
  return {
    difference,
    percentOfBaseline: (difference / baseline.value) * 100,
  };
}
