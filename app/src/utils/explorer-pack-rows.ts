/**
 * Explorer rows from the verified v2 observed pack.
 *
 * The pack is the published current-period contract (`periods` + `summary`
 * payloads behind `dashboard-release-v2.json`), so an area's numbers here are
 * the bytes both the browser and `validate-data` verified — not a recomputation
 * from `map_metrics`.
 *
 * Constraints:
 * - No React, no DOM, no fetch — the caller passes an already-verified pack.
 * - A row is only kept when the pack publishes at least one of the three
 *   metrics for it; a verified zero-sales window is a real `0` count with null
 *   prices, and an unobserved metric stays `null`.
 * - Ordering by value is a ranking, so it is only offered for a scope whose
 *   ratified disposition is `publish`. A `limited-display` scope (EC, condo and
 *   therefore All) is returned in name order with the reason attached; the
 *   values themselves stay visible with their window label.
 * - The national baseline is the pack's own `SG` observation, never the mean of
 *   the area rows.
 */

import { areaSlug, canonicalAreaId, formatAreaName } from "@/utils/observed-data";
import { activityForObservation } from "@/utils/area-activity";
import {
  findObservation,
  scopeNote,
  type Observation,
  type PeriodPack,
  type PropertyTypeId,
} from "@/utils/observed-periods";
import {
  isConcretePeriod,
  type ExplorerProperty,
  type ExplorerSort,
} from "@/utils/explorer-selection";
import {
  finaliseExplorerRows,
  packMetricValue,
  type ExplorerNationalMetric,
  type ExplorerRow,
  type PackExplorerDataset,
} from "@/utils/observed-rows";

/** National geography id inside the pack. */
const NATIONAL_GEOGRAPHY = "SG";

/** Project the shared comparison onto the row shape the explorer renders. */
function toRowActivity(
  comparison: ReturnType<typeof activityForObservation>,
): ExplorerRow["activity"] {
  return {
    priorCount: comparison.priorYear?.transactionCount ?? null,
    changePercent: comparison.changePercent,
    reason: comparison.changeUnavailableReason,
    eligible: comparison.eligible,
  };
}

const EXPLORER_METRICS = ["median_price", "median_psf", "volume"] as const;

export interface PackRowInput {
  pack: PeriodPack;
  /** Generation the pack was verified as, in this request. */
  generation: string;
  /** Concrete period id, e.g. `ttm_2026_10`. */
  periodId: string;
  property: ExplorerProperty;
  minSales: number | null;
  search: string;
  sort: ExplorerSort;
  direction: "asc" | "desc";
}

export type PackRowResult =
  | { ok: true; dataset: PackExplorerDataset }
  | { ok: false; period: string; reason: string };

/** Published period ids, for a message that says what *is* available. */
function publishedIds(pack: PeriodPack): string {
  return pack.periods.map((period) => period.id).join(", ");
}

/**
 * Build the explorer dataset for one property x published-period selection.
 *
 * Returns `ok: false` (never an empty dataset that looks like "no areas match")
 * when the requested period is not published by this pack, so an unknown id is
 * reported as unknown instead of silently rendering another window.
 */
export function buildPackExplorerDataset(input: PackRowInput): PackRowResult {
  const { pack, generation, periodId, property, minSales, search, sort, direction } =
    input;

  if (!isConcretePeriod(periodId)) {
    return {
      ok: false,
      period: periodId,
      reason: `${periodId} is not a concrete observed-period id (for example ttm_2026_10).`,
    };
  }

  const period = pack.periodsById.get(periodId);
  if (period === undefined) {
    return {
      ok: false,
      period: periodId,
      reason: `This build does not publish a period with the id ${periodId}. Published periods: ${publishedIds(pack)}.`,
    };
  }

  const propertyType: PropertyTypeId = property;
  const nationalObservation = findObservation(
    pack,
    NATIONAL_GEOGRAPHY,
    propertyType,
    periodId,
  );

  // Disposition is ratified per scope (source set x property type x window), so
  // one observation settles it for the section; the national one is used when
  // it exists so the gate and the baseline cannot come from different scopes.
  const scopeObservation =
    nationalObservation ??
    pack.observations.find(
      (observation) =>
        observation.periodId === periodId &&
        observation.propertyType === propertyType,
    ) ??
    null;
  const rankable = scopeObservation?.disposition === "publish";

  const rows: ExplorerRow[] = [];
  for (const observation of pack.observations) {
    if (observation.periodId !== periodId) continue;
    if (observation.propertyType !== propertyType) continue;
    if (observation.geographyId === NATIONAL_GEOGRAPHY) continue;

    const areaId = canonicalAreaId(observation.geographyId);
    if (areaId === "") continue;

    const volume = packMetricValue(observation, "volume");
    const medianPrice = packMetricValue(observation, "median_price");
    const medianPsf = packMetricValue(observation, "median_psf");
    if (volume === null && medianPrice === null && medianPsf === null) {
      continue;
    }

    rows.push({
      areaId,
      areaName: formatAreaName(areaId),
      slug: areaSlug(areaId),
      sectionLabel: period.label,
      packObservation: observation,
      volume,
      medianPrice,
      medianPsf,
      // RF10: the same quarter-to-quarter arithmetic and D05 verdict the
      // fieldnote uses. Absent (not `null`) for a window with no comparator, so
      // a caller can tell "no comparison published" from "no change".
      activity:
        period.comparatorId === null
          ? null
          : toRowActivity(activityForObservation(pack, observation)),
    });
  }

  const { ordered, filtered, totalAreas, thinCount } = finaliseExplorerRows(
    rows,
    {
      minSales,
      search,
      order: rankable ? { sort, direction } : null,
    },
  );

  return {
    ok: true,
    dataset: {
      kind: "pack",
      property,
      period: periodId,
      periodId,
      generation,
      label: period.label,
      rows: ordered,
      filtered,
      totalAreas,
      thinCount,
      rankable,
      national: nationalMetrics(nationalObservation, period.label),
    },
  };
}

/** The pack's national values for one window, with the reason a value is null. */
function nationalMetrics(
  observation: Observation | null,
  periodLabel: string,
): ExplorerNationalMetric[] | null {
  if (observation === null) return null;
  const note = scopeNote(observation);
  const source = `observed pack · SG · ${periodLabel}`;
  return EXPLORER_METRICS.map((metric) => ({
    metric,
    value: packMetricValue(observation, metric),
    source,
    note,
  }));
}
