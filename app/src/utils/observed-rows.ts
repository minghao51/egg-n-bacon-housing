/**
 * Explorer row builders — the one place published assets become explorer rows.
 *
 * Two sources, one row shape:
 *
 * - {@link buildExplorerDataset} reads the legacy `map_metrics.json.gz` joint
 *   `map_metrics[period_property]` section through the observed adapter (never
 *   a property-only or period-only fallback) for a historical era.
 * - `buildExplorerPackDataset` (in `explorer-pack-rows.ts`) reads the verified
 *   v2 observed pack for a concrete published window. It imports the row type
 *   and the shared ordering/sample rules from here, so a list, a map and a
 *   table built from either source cannot disagree about ordering, the
 *   thin-sample rule or the search filter.
 *
 * Constraints:
 * - No React, no DOM, no fetch — pure transformation of already-loaded assets.
 * - Numbers stay unrounded and unformatted; display is a UI concern.
 * - A missing metric stays `null`. It is never zero-filled, and a missing
 *   volume never hides a row: the reader sees an unavailable count instead.
 */

import {
  ERA_DEFINITIONS,
  canonicalAreaId,
  getSection,
  readAreaObservation,
  readNationalBaseline,
  sectionKey,
  type ObservedAreaRecord,
  type ObservedMetric,
} from "@/utils/observed-data";
import type { Observation as PackObservation } from "@/utils/observed-periods";
import type {
  ExplorerLegacyPeriod,
  ExplorerMetric,
  ExplorerPeriod,
  ExplorerProperty,
  ExplorerSelection,
  ExplorerSort,
} from "@/utils/explorer-selection";

export interface ExplorerRow {
  areaId: string;
  areaName: string;
  slug: string;
  /**
   * Label for the window the row's numbers belong to — the legacy era label or
   * the published period label. Prose uses this instead of assuming a section
   * key, so a row never claims to come from an asset it did not come from.
   */
  sectionLabel: string;
  /** Legacy `map_metrics` record; absent for rows built from the v2 pack. */
  observation?: ObservedAreaRecord;
  /** v2 pack observation; absent for rows built from `map_metrics`. */
  packObservation?: PackObservation;
  volume: number | null;
  medianPrice: number | null;
  medianPsf: number | null;
  /**
   * Year-on-year activity for the row's window (RF10), present only when the
   * window publishes a comparator. `null` means "this window has no
   * prior-year comparison", which is different from "no change".
   */
  activity?: ExplorerActivity | null;
}

/** The prior-year comparison a row carries, mirroring `area-activity.ts`. */
export interface ExplorerActivity {
  priorCount: number | null;
  changePercent: number | null;
  reason: string | null;
  eligible: boolean;
}

/**
 * One national baseline value, with the asset or scope it came from. `value` is
 * `null` when the scope publishes nothing for the metric; `note` says why.
 */
export interface ExplorerNationalMetric {
  metric: ExplorerMetric;
  value: number | null;
  /** e.g. `dashboard_overview.stats.year_2025_hdb` or `observed pack (SG)`. */
  source: string;
  note: string | null;
}

interface ExplorerDatasetBase {
  property: ExplorerProperty;
  period: ExplorerPeriod;
  /** Human label for the active window, e.g. "12 months to 2026-10". */
  label: string;
  rows: ExplorerRow[];
  filtered: ExplorerRow[];
  totalAreas: number;
  thinCount: number;
  /**
   * Whether the rows may be ordered by value. A scope cleared to publish may be
   * ranked; a `limited-display` scope is shown with its dates but ordered by
   * name only.
   */
  rankable: boolean;
  national: ExplorerNationalMetric[] | null;
}

export interface LegacyExplorerDataset extends ExplorerDatasetBase {
  kind: "legacy";
  /** Legacy joint section key, e.g. `year_2025_hdb`. */
  section: string;
  /** True only when the loaded legacy assets share one verified generation. */
  baselineCompatible: boolean;
}

export interface PackExplorerDataset extends ExplorerDatasetBase {
  kind: "pack";
  /** Concrete published period id, e.g. `ttm_2026_10`. */
  periodId: string;
  /** Generation the pack was verified as, in the same request. */
  generation: string;
}

export type ExplorerDataset = LegacyExplorerDataset | PackExplorerDataset;

/** Filters and ordering every row source shares. */
export interface ExplorerRowRules {
  minSales: number | null;
  search: string;
  /** `null` means "order by area name" — the unranked, limited-display state. */
  order: { sort: ExplorerSort; direction: "asc" | "desc" } | null;
}

/** The observation value for one legacy metric, or `null` when unavailable. */
function metricValue(
  observation: ObservedAreaRecord,
  metric: ObservedMetric,
): number | null {
  const found = observation.metrics.find((entry) => entry.metric === metric);
  return found === undefined ? null : found.value;
}

/** The pack value for one explorer metric, or `null` when unavailable. */
export function packMetricValue(
  observation: PackObservation,
  metric: ExplorerMetric,
): number | null {
  if (metric === "volume") return observation.metrics.transactionCount.value;
  if (metric === "median_price") return observation.metrics.medianPrice.value;
  return observation.metrics.medianPsf.value;
}

/** The row field a sort reads, kept in step with {@link ExplorerSort}. */
function sortValue(row: ExplorerRow, sort: ExplorerSort): number | null {
  if (sort === "median_price") return row.medianPrice;
  if (sort === "median_psf") return row.medianPsf;
  return row.volume;
}

function compareText(a: string, b: string): number {
  if (a < b) return -1;
  if (a > b) return 1;
  return 0;
}

/** Name, then canonical id, so equal values never reorder between renders. */
function compareByName(a: ExplorerRow, b: ExplorerRow): number {
  const byName = compareText(a.areaName, b.areaName);
  return byName !== 0 ? byName : compareText(a.areaId, b.areaId);
}

/**
 * Order rows by the chosen metric. Nulls sort last in both directions, and the
 * name (then the canonical id) is the tiebreaker so equal values never reorder
 * between renders.
 */
function compareRows(
  a: ExplorerRow,
  b: ExplorerRow,
  sort: ExplorerSort,
  direction: "asc" | "desc",
): number {
  const left = sortValue(a, sort);
  const right = sortValue(b, sort);

  if (left === null && right !== null) return 1;
  if (left !== null && right === null) return -1;
  if (left !== null && right !== null && left !== right) {
    return direction === "asc" ? left - right : right - left;
  }

  return compareByName(a, b);
}

/**
 * Apply the ordering, the sample threshold and the search filter.
 *
 * - `thinCount` is how many rows the sample threshold removes (`0` when
 *   `minSales` is `null`). It is counted before the search filter so the number
 *   stays stable while the reader types; rows with an unavailable volume are
 *   never removed and never counted.
 * - `order: null` means the rows are not rankable: they are returned in name
 *   order, and the threshold and search still apply.
 */
export function finaliseExplorerRows(
  rows: readonly ExplorerRow[],
  rules: ExplorerRowRules,
): {
  ordered: ExplorerRow[];
  filtered: ExplorerRow[];
  totalAreas: number;
  thinCount: number;
} {
  const order = rules.order;
  const comparator =
    order === null
      ? compareByName
      : (a: ExplorerRow, b: ExplorerRow): number =>
          compareRows(a, b, order.sort, order.direction);
  const ordered = [...rows].sort(comparator);

  const threshold = rules.minSales;
  const thinCount =
    threshold === null
      ? 0
      : ordered.filter((row) => row.volume !== null && row.volume < threshold)
          .length;
  const afterSample =
    threshold === null
      ? ordered
      : ordered.filter((row) => row.volume === null || row.volume >= threshold);

  const query = rules.search.trim().toLowerCase();
  const filtered =
    query === ""
      ? afterSample
      : afterSample.filter((row) => row.areaName.toLowerCase().includes(query));

  return {
    ordered,
    filtered,
    totalAreas: ordered.length,
    thinCount,
  };
}

/** Display label for one legacy era. */
export function legacyPeriodLabel(period: ExplorerLegacyPeriod): string {
  const definition = ERA_DEFINITIONS.find((entry) => entry.id === period);
  return definition === undefined ? period : definition.label;
}

/**
 * Build the explorer dataset for one legacy property x era selection.
 *
 * - `rows` holds every area of the joint section that has at least one
 *   available metric, ordered by the current sort.
 * - `national` is present only when the caller established that the loaded
 *   assets come from one verified generation.
 * - Legacy eras are the labelled historical/diagnostic view, so they keep their
 *   existing ordering behaviour; the publish/limited-display gate belongs to
 *   the ratified v2 dispositions, which this source does not carry.
 */
export function buildExplorerDataset(input: {
  mapMetrics: unknown;
  overviewStats: unknown;
  selection: Pick<
    ExplorerSelection,
    "property" | "period" | "minSales" | "search" | "sort" | "direction"
  > & { period: ExplorerLegacyPeriod };
  baselineCompatible: boolean;
}): LegacyExplorerDataset {
  const { mapMetrics, overviewStats, selection, baselineCompatible } = input;
  const { property, period, minSales, search, sort, direction } = selection;

  const section = sectionKey(period, property);
  const rawSection = getSection(mapMetrics, period, property);
  const sectionLabel = legacyPeriodLabel(period);

  const rows: ExplorerRow[] = [];
  if (rawSection !== null) {
    // A non-canonical key that resolves to an id already seen is the same area,
    // not a second row.
    const seen = new Set<string>();
    for (const key of Object.keys(rawSection)) {
      const areaId = canonicalAreaId(key);
      if (areaId === "" || seen.has(areaId)) continue;
      seen.add(areaId);

      const observation = readAreaObservation(
        mapMetrics,
        period,
        property,
        key,
      );
      if (observation === null) continue;

      const volume = metricValue(observation, "volume");
      const medianPrice = metricValue(observation, "median_price");
      const medianPsf = metricValue(observation, "median_psf");
      // No available metric means the exporter has no data for this area in
      // this section; a blank row would claim coverage it does not have.
      if (volume === null && medianPrice === null && medianPsf === null) {
        continue;
      }

      rows.push({
        areaId: observation.areaId,
        areaName: observation.areaName,
        slug: observation.slug,
        sectionLabel,
        observation,
        volume,
        medianPrice,
        medianPsf,
      });
    }
  }

  const { ordered, filtered, totalAreas, thinCount } = finaliseExplorerRows(
    rows,
    { minSales, search, order: { sort, direction } },
  );

  const nationalValues = baselineCompatible
    ? readNationalBaseline(overviewStats, period, property)
    : null;
  const nationalSource = `dashboard_overview.stats.${section}`;
  const national: ExplorerNationalMetric[] | null =
    nationalValues === null
      ? null
      : nationalValues.map((entry) => ({
          metric: entry.metric,
          value: entry.value,
          source: nationalSource,
          note: null,
        }));

  return {
    kind: "legacy",
    property,
    period,
    label: sectionLabel,
    section,
    rows: ordered,
    filtered,
    totalAreas,
    thinCount,
    rankable: true,
    national,
    baselineCompatible,
  };
}
