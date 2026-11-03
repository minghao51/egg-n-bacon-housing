/**
 * Explorer row builder — the one place published assets become explorer rows.
 *
 * Reads the joint `map_metrics[period_property]` section through the observed
 * adapter (never a property-only or period-only fallback) and returns the rows,
 * the filtered rows, the pre-filter area count, the thin-sample count and the
 * national baseline that the explorer table, map and plot all consume.
 *
 * Constraints:
 * - No React, no DOM, no fetch — pure transformation of already-loaded assets.
 * - Numbers stay unrounded and unformatted; display is a UI concern.
 * - A missing metric stays `null`. It is never zero-filled, and a missing
 *   volume never hides a row: the reader sees an unavailable count instead.
 */

import {
  canonicalAreaId,
  getSection,
  readAreaObservation,
  readNationalBaseline,
  sectionKey,
  type ObservedAreaRecord,
  type ObservedMetric,
} from "@/utils/observed-data";
import type {
  ExplorerPeriod,
  ExplorerProperty,
  ExplorerSelection,
  ExplorerSort,
} from "@/utils/explorer-selection";

export interface ExplorerRow {
  areaId: string;
  areaName: string;
  slug: string;
  observation: import("@/utils/observed-data").ObservedAreaRecord;
  volume: number | null;
  medianPrice: number | null;
  medianPsf: number | null;
}

export interface ExplorerDataset {
  property: ExplorerProperty;
  period: ExplorerPeriod;
  section: string;
  rows: ExplorerRow[];
  filtered: ExplorerRow[];
  totalAreas: number;
  thinCount: number;
  national: import("@/utils/observed-data").ObservedObservation[] | null;
  baselineCompatible: boolean;
}

/** The observation value for one metric, or `null` when it is not available. */
function metricValue(
  observation: ObservedAreaRecord,
  metric: ObservedMetric,
): number | null {
  const found = observation.metrics.find((entry) => entry.metric === metric);
  return found === undefined ? null : found.value;
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

  const byName = compareText(a.areaName, b.areaName);
  return byName !== 0 ? byName : compareText(a.areaId, b.areaId);
}

/**
 * Build the explorer dataset for one property x period selection.
 *
 * - `rows` holds every area of the joint section that has at least one
 *   available metric, ordered by the current sort.
 * - `totalAreas` is the row count before the sample and search filters.
 * - `thinCount` is how many rows the sample threshold removes (`0` when
 *   `minSales` is `null`). It is counted before the search filter so the number
 *   stays stable while the reader types; rows with an unavailable volume are
 *   never removed and never counted.
 * - `national` is present only when the caller established that the loaded
 *   assets come from one verified generation.
 */
export function buildExplorerDataset(input: {
  mapMetrics: unknown;
  overviewStats: unknown;
  selection: Pick<
    ExplorerSelection,
    "property" | "period" | "minSales" | "search" | "sort" | "direction"
  >;
  baselineCompatible: boolean;
}): ExplorerDataset {
  const { mapMetrics, overviewStats, selection, baselineCompatible } = input;
  const { property, period, minSales, search, sort, direction } = selection;

  const section = sectionKey(period, property);
  const rawSection = getSection(mapMetrics, period, property);

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
        observation,
        volume,
        medianPrice,
        medianPsf,
      });
    }
  }

  const ordered = [...rows].sort((a, b) => compareRows(a, b, sort, direction));

  const threshold = minSales;
  const thinCount =
    threshold === null
      ? 0
      : ordered.filter((row) => row.volume !== null && row.volume < threshold)
          .length;
  const afterSample =
    threshold === null
      ? ordered
      : ordered.filter((row) => row.volume === null || row.volume >= threshold);

  const query = search.trim().toLowerCase();
  const filtered =
    query === ""
      ? afterSample
      : afterSample.filter((row) => row.areaName.toLowerCase().includes(query));

  const national = baselineCompatible
    ? readNationalBaseline(overviewStats, period, property)
    : null;

  return {
    property,
    period,
    section,
    rows: ordered,
    filtered,
    totalAreas: ordered.length,
    thinCount,
    national,
    baselineCompatible,
  };
}
