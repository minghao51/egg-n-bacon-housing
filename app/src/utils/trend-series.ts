/**
 * Monthly price and volume series for `/research/trends`.
 *
 * Source contract: `public/data/dashboard_trends.json.gz` is an **array** of
 * monthly rows keyed `date` (`YYYY-MM`), `Overall Price`, `HDB Price`,
 * `HDB Volume`, `EC Price`, `EC Volume`, `Condominium Price`,
 * `Condominium Volume`. The published payload has 441 rows, 1990-01 through
 * 2026-09; HDB is published for every row, EC and condominium from 2021-01, and
 * the combined `Overall Price` has no matching combined transaction count.
 *
 * Rules this module exists to enforce:
 * - never interpolate and never shift the calendar: every published month keeps
 *   its own point, and a missing value stays `null` (rendered `N/A`, never `0`);
 * - a combined count is never invented — the `all` series publishes a price but
 *   no volume, so its `volume` is `null` rather than the sum of three counts
 *   with different coverage;
 * - prices and counts are never negative: anything unusable becomes `null`
 *   instead of being clamped into a plausible number;
 * - windows are calendar-bounded (`year_2025` is exactly 2025-01..2025-12), so a
 *   type/range choice never implies coverage before a series starts;
 * - no rounding, and no arithmetic across months except an explicitly named
 *   `yearSum`, which returns `null` unless the whole calendar year is published.
 *
 * Pure: no React, no DOM, no fetch, no `window` at module scope.
 */

export type TrendSeriesId = "hdb" | "ec" | "condo" | "all";

export type TrendWindow = "all" | "recent" | "year_2025";

export interface TrendPoint {
  /** Calendar month, `YYYY-MM`. */
  month: string;
  /** Median transaction price in nominal SGD, or `null` when not published. */
  price: number | null;
  /** Count of included transactions, or `null` when not published. */
  volume: number | null;
}

export interface TrendSeries {
  id: TrendSeriesId;
  label: string;
  points: TrendPoint[];
  /** First month with a published price or volume, or null when empty. */
  coverageStart: string | null;
  /** Last month with a published price or volume, or null when empty. */
  coverageEnd: string | null;
}

export interface TrendSummary {
  months: number;
  startMonth: string | null;
  endMonth: string | null;
  latestPrice: number | null;
  latestVolume: number | null;
  nullPriceMonths: number;
  isPartialWindow: boolean;
}

export const TREND_SERIES_LABELS: Record<TrendSeriesId, string> = {
  hdb: "HDB",
  ec: "EC",
  condo: "Condo",
  all: "All property types",
};

export const TREND_WINDOW_LABELS: Record<TrendWindow, string> = {
  all: "All history",
  recent: "2022 onward",
  year_2025: "2025 complete year",
};

/** Selector order. HDB first, matching the published and designed default. */
export const TREND_SERIES_IDS: readonly TrendSeriesId[] = [
  "hdb",
  "ec",
  "condo",
  "all",
];

/** Selector order, from the widest window to the fixed complete year. */
export const TREND_WINDOWS: readonly TrendWindow[] = [
  "all",
  "recent",
  "year_2025",
];

/**
 * Default selection for `/research/trends`: the 2025 HDB series, which is the
 * fixed complete year the design and the published asset both verify.
 */
export const TREND_QUERY_DEFAULTS = {
  series: "hdb",
  window: "year_2025",
} as const satisfies { series: TrendSeriesId; window: TrendWindow };

/** First month of the "2022 onward" window (fixed calendar bound). */
const RECENT_START_MONTH = "2022-01";

/** Calendar bounds of the fixed complete year. */
const YEAR_2025_START_MONTH = "2025-01";
const YEAR_2025_END_MONTH = "2025-12";

/** A calendar month as the exporter writes it. */
const MONTH_PATTERN = /^\d{4}-(?:0[1-9]|1[0-2])$/;

/** A calendar year as accepted by `yearSum`. */
const YEAR_PATTERN = /^\d{4}$/;

interface TrendFieldMap {
  price: string;
  /** `null` when the asset publishes no count for this series. */
  volume: string | null;
}

const TREND_FIELDS: Record<TrendSeriesId, TrendFieldMap> = {
  hdb: { price: "HDB Price", volume: "HDB Volume" },
  ec: { price: "EC Price", volume: "EC Volume" },
  condo: { price: "Condominium Price", volume: "Condominium Volume" },
  all: { price: "Overall Price", volume: null },
};

/** Narrow an untrusted series id without casting. */
function fieldMapFor(id: string): TrendFieldMap | null {
  for (const candidate of TREND_SERIES_IDS) {
    if (candidate === id) return TREND_FIELDS[candidate];
  }
  return null;
}

/** `YYYY-MM` to a month ordinal, so comparisons never use string quirks. */
function monthIndex(month: string): number {
  const year = Number(month.slice(0, 4));
  const monthOfYear = Number(month.slice(5, 7));
  return year * 12 + (monthOfYear - 1);
}

/** Inverse of {@link monthIndex}: ordinal back to `YYYY-MM`. */
function monthLabel(index: number): string {
  const year = Math.floor(index / 12);
  const monthOfYear = index % 12;
  return `${String(year).padStart(4, "0")}-${String(monthOfYear + 1).padStart(2, "0")}`;
}

/**
 * Read one published value.
 *
 * `null`/`undefined` mean "not published". A finite non-negative number is a
 * measurement. Everything else (a string, a boolean, `NaN`, an infinity, a
 * negative count) is unusable and becomes `null`, never `0` and never an
 * absolute value.
 */
function readValue(value: unknown): number | null {
  if (typeof value !== "number" || !Number.isFinite(value)) return null;
  return value < 0 ? null : value;
}

/**
 * Build one monthly series from the raw payload.
 *
 * Returns `null` when the payload is unusable: not an array, empty, a row that
 * is not an object, a `date` that is not `YYYY-MM`, or two rows for the same
 * month. A single bad row is not silently skipped — a series with fewer months
 * than the asset claims would misrepresent coverage.
 */
export function buildTrendSeries(
  rows: unknown,
  id: TrendSeriesId,
): TrendSeries | null {
  const fields = fieldMapFor(id);
  if (fields === null) return null;
  if (!Array.isArray(rows) || rows.length === 0) return null;

  const points: TrendPoint[] = [];

  for (const row of rows) {
    if (row === null || typeof row !== "object" || Array.isArray(row)) {
      return null;
    }
    const record = row as Record<string, unknown>;
    const month = record["date"];
    if (typeof month !== "string" || !MONTH_PATTERN.test(month)) return null;

    points.push({
      month,
      price: readValue(record[fields.price]),
      volume: fields.volume === null ? null : readValue(record[fields.volume]),
    });
  }

  points.sort((a, b) => monthIndex(a.month) - monthIndex(b.month));

  for (let index = 1; index < points.length; index += 1) {
    if (points[index - 1].month === points[index].month) return null;
  }

  // A month the asset omits inside its own range is an explicit gap, not a
  // shorter series: insert a null point so tables and charts cannot compress it.
  const withGaps: TrendPoint[] = [];
  for (const point of points) {
    const previous = withGaps[withGaps.length - 1];
    if (previous !== undefined) {
      let next = monthIndex(previous.month) + 1;
      const target = monthIndex(point.month);
      while (next < target) {
        withGaps.push({
          month: monthLabel(next),
          price: null,
          volume: null,
        });
        next += 1;
      }
    }
    withGaps.push(point);
  }
  points.length = 0;
  points.push(...withGaps);

  const coverage = points.filter(
    (point) => point.price !== null || point.volume !== null,
  );

  return {
    id,
    label: TREND_SERIES_LABELS[id],
    points,
    coverageStart: coverage[0]?.month ?? null,
    coverageEnd: coverage[coverage.length - 1]?.month ?? null,
  };
}

/** Inclusive month ordinals of a window, before any point is filtered. */
function windowBounds(
  series: TrendSeries,
  window: TrendWindow,
): { start: number | null; end: number | null } {
  if (window === "all") return { start: null, end: null };
  if (window === "year_2025") {
    return {
      start: monthIndex(YEAR_2025_START_MONTH),
      end: monthIndex(YEAR_2025_END_MONTH),
    };
  }
  // "2022 onward" ends at the series' own coverage, not at today.
  const start = monthIndex(RECENT_START_MONTH);
  const last = series.points[series.points.length - 1];
  return { start, end: last === undefined ? start - 1 : monthIndex(last.month) };
}

/**
 * Keep exactly the months inside the window's calendar range.
 *
 * Months absent from the series stay absent (they are not invented as null
 * points), but the range itself never moves: `year_2025` returns the 2025 months
 * only, even when the series ends earlier or starts later.
 */
export function filterWindow(
  series: TrendSeries,
  window: TrendWindow,
): TrendSeries {
  const { start, end } = windowBounds(series, window);
  const points = series.points.filter((point) => {
    const index = monthIndex(point.month);
    if (start !== null && index < start) return false;
    if (end !== null && index > end) return false;
    return true;
  });

  // "All history" means all *published* history: a series that starts in 2021
  // must not present 1990–2020 as blank rows. Internal gaps are preserved.
  const trimmed =
    window === "all" ? trimToCoverage(points) : points;

  return {
    id: series.id,
    label: series.label,
    points: trimmed,
    coverageStart: series.coverageStart,
    coverageEnd: series.coverageEnd,
  };
}

function trimToCoverage(points: TrendPoint[]): TrendPoint[] {
  const hasValue = (point: TrendPoint) =>
    point.price !== null || point.volume !== null;
  let first = 0;
  let last = points.length - 1;
  while (first <= last && !hasValue(points[first])) first += 1;
  while (last >= first && !hasValue(points[last])) last -= 1;
  return points.slice(first, last + 1);
}

/**
 * True when the window's calendar boundaries are not both present in the
 * filtered points — the selection is wider than the published coverage (for
 * example an EC window that starts before 2021-01) or nothing is published in
 * it at all.
 *
 * `all` has no calendar bound of its own, so it is never partial. An empty
 * filtered range is always partial: there is no coverage to show.
 */
function isWindowPartial(points: TrendPoint[], window: TrendWindow): boolean {
  if (window === "all") return false;
  if (points.length === 0) return true;
  if (window === "year_2025") {
    return (
      points[0].month !== YEAR_2025_START_MONTH ||
      points[points.length - 1].month !== YEAR_2025_END_MONTH
    );
  }
  return points[0].month !== RECENT_START_MONTH;
}

/**
 * Summarize the points it is given.
 *
 * `latest*` describe the last month in the range, not the last non-null value:
 * a month whose price is not published reports `N/A` rather than reaching back
 * to an older month. Pass the same window used for `filterWindow` so
 * `isPartialWindow` can compare the range with its calendar bounds; with no
 * window the summary treats the points as unbounded (`all`).
 */
export function summarize(
  series: TrendSeries,
  window: TrendWindow = "all",
): TrendSummary {
  const points = series.points;
  const first = points[0];
  const last = points[points.length - 1];

  return {
    months: points.length,
    startMonth: first === undefined ? null : first.month,
    endMonth: last === undefined ? null : last.month,
    latestPrice: last === undefined ? null : last.price,
    latestVolume: last === undefined ? null : last.volume,
    nullPriceMonths: points.filter((point) => point.price === null).length,
    isPartialWindow: isWindowPartial(points, window),
  };
}

/**
 * Sum one field over a whole calendar year.
 *
 * Returns `null` unless all twelve months of `year` are present exactly once and
 * every one of them publishes the field: a partial year has no honest total.
 * The result is a plain sum — for prices it is **not** an annual median, and
 * the annual median is not the average of the twelve monthly medians.
 */
export function yearSum(
  points: TrendPoint[],
  year: string,
  field: "price" | "volume",
): number | null {
  if (!YEAR_PATTERN.test(year)) return null;

  const expected = new Set(
    Array.from({ length: 12 }, (_, index) => `${year}-${String(index + 1).padStart(2, "0")}`),
  );
  const values = new Map<string, number | null>();

  for (const point of points) {
    if (!expected.has(point.month)) continue;
    if (values.has(point.month)) return null;
    values.set(point.month, field === "price" ? point.price : point.volume);
  }

  if (values.size !== 12) return null;

  let total = 0;
  for (const value of values.values()) {
    if (value === null || !Number.isFinite(value)) return null;
    total += value;
  }
  return total;
}

/**
 * Group a value with thousands separators for display, or `N/A` when absent.
 *
 * Presentation only: the digits are never rounded, and no unit is added (the
 * caller owns `S$` and the column headers).
 */
export function formatTrendNumber(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "N/A";

  const text = String(value);
  // Exponential notation for exotic magnitudes is returned untouched rather
  // than reformatted into a different value.
  if (text.includes("e") || text.includes("E")) return text;

  const negative = text.startsWith("-");
  const unsigned = negative ? text.slice(1) : text;
  const [whole, fraction] = unsigned.split(".");
  const grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  const body = fraction === undefined ? grouped : `${grouped}.${fraction}`;
  return negative ? `-${body}` : body;
}
