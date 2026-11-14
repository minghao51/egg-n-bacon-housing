/**
 * Area activity from the verified v2 pack (RF10).
 *
 * The activity window is the published **rolling quarter** (three months ending
 * at the observation cutoff) with its own prior-year quarter as comparator. The
 * trailing-twelve-month count is carried separately and is context only — it is
 * never folded into the quarter, and no number here is annualised.
 *
 * What this module refuses to do, by design (D09, RF09 §3.4):
 * - No directional label, score, colour key or "hot/cold" wording. It returns
 *   counts, one year-on-year percentage and the two denominators.
 * - No derived statistic. Every number is a `transactionCount` the exporter
 *   published; nothing is divided, weighted or normalised (no turnover, no
 *   stock ratio, no per-capita figure).
 * - No zero for a missing month or an unpublished window. A verified
 *   `no-sales` window yields `transactionCount: null` plus a stated reason, and
 *   a missing comparator yields `changePercent: null`.
 *
 * Pure and client-safe: pack in, rows out. `area-page.ts` calls it at build time
 * (where the pack is already verified) and the fieldnote renders the result as
 * static HTML, so no monthly payload is fetched for a number this small.
 */

import {
  findObservation,
  type Observation,
  type PeriodDescriptor,
  type PeriodPack,
  type PropertyTypeId,
} from "./observed-periods";

/**
 * D05's 150-sale caution threshold, applied at quarter scale.
 *
 * RF09 §3 calibrated this rather than inventing a new one: a quarter holds
 * roughly a quarter of a year's sales, so the same floor is stricter here, which
 * the map permits (`calibration can tighten it`). The looser 38-sale
 * quarter-scaled alternative is evidence in that report, **not** an adopted
 * rule, so it is not implemented.
 */
export const ACTIVITY_SALE_FLOOR = 150;

/** Property types in display order: the specific ones first, then the pooled. */
export const ACTIVITY_PROPERTY_TYPES: readonly PropertyTypeId[] = [
  "hdb",
  "ec",
  "condo",
  "all",
];

export const ACTIVITY_PROPERTY_LABELS: Readonly<Record<PropertyTypeId, string>> =
  {
    hdb: "HDB resale",
    ec: "Executive condominium",
    condo: "Private residential",
    all: "All residential",
  };

export interface ActivityWindow {
  periodId: string;
  /** Month range as published, e.g. `2026-08 → 2026-10`. */
  range: string;
  months: string[];
  /** Observed sales, or `null` for a verified `no-sales` window. */
  transactionCount: number | null;
  status: Observation["status"];
  disposition: Observation["disposition"];
}

export interface AreaActivityRow {
  propertyType: PropertyTypeId;
  propertyLabel: string;
  current: ActivityWindow;
  priorYear: ActivityWindow | null;
  /** Year-on-year change in observed sales, or `null` when not computable. */
  changePercent: number | null;
  /** Why `changePercent` is `null`; never silently omitted. */
  changeUnavailableReason: string | null;
  /** D05: both windows observed with at least {@link ACTIVITY_SALE_FLOOR} sales. */
  eligible: boolean;
  /** Neutral reason the row is not eligible, or `null` when it is. */
  ineligibleReason: string | null;
  /** Trailing twelve months to the cutoff — context, not the activity window. */
  ttmCount: number | null;
}

export interface AreaActivity {
  /** `null` when the pack publishes no rolling-quarter period at all. */
  periodId: string | null;
  range: string | null;
  months: string[];
  comparatorId: string | null;
  comparatorRange: string | null;
  cutoffMonth: string;
  rows: AreaActivityRow[];
  /** Neutral, non-directional statements that qualify the numbers above. */
  notes: string[];
}

function rangeLabel(period: PeriodDescriptor): string {
  const first = period.months[0] ?? period.startMonth;
  const last = period.months.at(-1) ?? period.endMonth;
  return first === last ? first : `${first} → ${last}`;
}

/**
 * Observed sales for one window, or `null` for a verified `no-sales` window.
 *
 * `no-sales` is a verified zero-transaction window; it is reported as an absence
 * of observed sales, never as the number 0, so this helper is the only place
 * that decides which of the two a caller is looking at.
 */
function countOf(observation: Observation): number | null {
  return observation.status === "available"
    ? observation.metrics.transactionCount.value
    : null;
}

function windowOf(
  observation: Observation,
  period: PeriodDescriptor,
): ActivityWindow {
  return {
    periodId: observation.periodId,
    range: rangeLabel(period),
    months: period.months,
    transactionCount: countOf(observation),
    status: observation.status,
    disposition: observation.disposition,
  };
}

/** The newest published rolling-quarter period, or `null`. */
export function rollingQuarterPeriod(pack: PeriodPack): PeriodDescriptor | null {
  const quarters = pack.periods.filter((period) => period.kind === "rolling3");
  if (quarters.length === 0) return null;
  return quarters.reduce((newest, period) =>
    period.endMonth > newest.endMonth ? period : newest,
  );
}

function ttmCountFor(
  pack: PeriodPack,
  areaId: string,
  propertyType: PropertyTypeId,
): number | null {
  const observations = pack.observations.filter(
    (observation) =>
      observation.geographyId === areaId &&
      observation.propertyType === propertyType,
  );
  if (observations.length === 0) return null;
  const cutoff = pack.cutoffMonth;
  const ttm = pack.periods.find(
    (period) => period.kind === "ttm" && period.endMonth === cutoff,
  );
  if (ttm === undefined) return null;
  const observation = findObservation(pack, areaId, propertyType, ttm.id);
  if (observation === null) return null;
  return countOf(observation);
}

/** The prior-year comparison and D05 verdict for one observation. */
export interface ActivityComparison {
  priorYear: ActivityWindow | null;
  changePercent: number | null;
  changeUnavailableReason: string | null;
  eligible: boolean;
  ineligibleReason: string | null;
}

/**
 * Compare one observation with its period's published comparator.
 *
 * This is the single implementation of the quarter-to-quarter arithmetic and of
 * the D05 floor rule; the fieldnote table and the explorer row both call it, so
 * the two surfaces cannot drift into different definitions of "eligible".
 */
export function activityForObservation(
  pack: PeriodPack,
  observation: Observation,
): ActivityComparison {
  const period = pack.periodsById.get(observation.periodId) ?? null;
  const comparator =
    period === null || period.comparatorId === null
      ? null
      : (pack.periodsById.get(period.comparatorId) ?? null);

  const currentCount = countOf(observation);

  const priorObservation =
    comparator === null
      ? null
      : findObservation(
          pack,
          observation.geographyId,
          observation.propertyType,
          comparator.id,
        );
  const priorYear =
    priorObservation === null || comparator === null
      ? null
      : windowOf(priorObservation, comparator);
  const priorCount = priorYear?.transactionCount ?? null;

  let changePercent: number | null = null;
  let changeUnavailableReason: string | null = null;
  if (comparator === null) {
    changeUnavailableReason =
      "this quarter publishes no comparator window (its prior-year quarter is not covered)";
  } else if (priorYear === null) {
    changeUnavailableReason =
      "no prior-year-quarter observation is published for this area";
  } else if (currentCount === null) {
    changeUnavailableReason =
      "no observed sales in the current quarter, so a percentage would be undefined";
  } else if (priorCount === null) {
    changeUnavailableReason =
      "no observed sales in the prior-year quarter, so a percentage would be undefined";
  } else if (priorCount === 0) {
    changeUnavailableReason =
      "the prior-year quarter reports zero observed sales";
  } else {
    changePercent = ((currentCount - priorCount) / priorCount) * 100;
  }

  const eligible =
    currentCount !== null &&
    priorCount !== null &&
    currentCount >= ACTIVITY_SALE_FLOOR &&
    priorCount >= ACTIVITY_SALE_FLOOR;

  let ineligibleReason: string | null = null;
  if (!eligible) {
    if (currentCount === null) {
      ineligibleReason = "no observed sales in the current quarter";
    } else if (priorCount === null) {
      ineligibleReason = "no prior-year-quarter denominator is published";
    } else {
      const shortWindows: string[] = [];
      if (currentCount < ACTIVITY_SALE_FLOOR) shortWindows.push("the current quarter");
      if (priorCount < ACTIVITY_SALE_FLOOR) shortWindows.push("the prior-year quarter");
      ineligibleReason = `fewer than ${ACTIVITY_SALE_FLOOR} observed sales in ${shortWindows.join(" and ")}`;
    }
  }

  return { priorYear, changePercent, changeUnavailableReason, eligible, ineligibleReason };
}

/**
 * Activity rows for one planning area.
 *
 * Returns `null` when the pack publishes no rolling-quarter period. A row is
 * emitted only for property types the quarter actually reports for this area,
 * so an unpublished type is absent rather than a fabricated zero row.
 */
export function buildAreaActivity(
  pack: PeriodPack,
  areaId: string,
): AreaActivity | null {
  const period = rollingQuarterPeriod(pack);
  if (period === null) return null;

  const comparator =
    period.comparatorId === null
      ? null
      : (pack.periodsById.get(period.comparatorId) ?? null);

  const rows: AreaActivityRow[] = [];
  for (const propertyType of ACTIVITY_PROPERTY_TYPES) {
    const observation = findObservation(pack, areaId, propertyType, period.id);
    if (observation === null) continue;

    const current = windowOf(observation, period);
    const { priorYear, changePercent, changeUnavailableReason, eligible, ineligibleReason } =
      activityForObservation(pack, observation);

    rows.push({
      propertyType,
      propertyLabel: ACTIVITY_PROPERTY_LABELS[propertyType],
      current,
      priorYear,
      changePercent,
      changeUnavailableReason,
      eligible,
      ineligibleReason,
      ttmCount: ttmCountFor(pack, areaId, propertyType),
    });
  }

  const notes = [
    `Counts are observed resale transactions in ${rangeLabel(period)}, not demand, liquidity, listing supply or an expected return.`,
    `A row is eligible for ranking only with at least ${ACTIVITY_SALE_FLOOR} observed sales in both quarters (D05). No directional label, score or colour-by-change is published.`,
  ];
  if (rows.some((row) => row.current.status === "no-sales")) {
    notes.push(
      "A quarter with no observed sales is a verified zero for this population — usually an area with little or no stock of that property type — not missing data and not a cold market.",
    );
  }
  if (rows.length === 0) {
    notes.push(
      "No rolling-quarter observation is published for this area. Nothing is shown rather than a zero.",
    );
  }

  return {
    periodId: period.id,
    range: rangeLabel(period),
    months: period.months,
    comparatorId: comparator?.id ?? null,
    comparatorRange: comparator === null ? null : rangeLabel(comparator),
    cutoffMonth: pack.cutoffMonth,
    rows,
    notes,
  };
}
