/**
 * Monthly history view model for an area fieldnote (RF10 slice 2b).
 *
 * The monthly payload is the one asset big enough to matter (up to ~233 KB), so
 * the fieldnote fetches it **only when the reader asks** and this module keeps
 * the derivation pure and testable.
 *
 * Two rules from RF09 that this module exists to keep:
 * - Months are enumerated from `history.months` (the published grid), never from
 *   `coverage.firstMonth`/`lastMonth` — the grid may contain an interior gap.
 * - A month inside the grid with zero sales is a verified `no-sales` reading; a
 *   month outside the grid, or an area the release does not carry, is
 *   `missing-source`. Neither is ever rendered as 0.
 */

import {
  readMonth,
  type MonthlyHistory,
  type MonthlyReading,
} from "./observed-monthly";

/** How many of the newest covered months the fieldnote renders. */
export const HISTORY_MONTH_LIMIT = 24;

export interface AreaHistoryView {
  /** Grid months rendered, oldest → newest. */
  months: string[];
  rows: MonthlyReading[];
  /** True when at least one rendered month has observed sales. */
  hasObservations: boolean;
  /** Rendered months that are verified zeros (inside the grid, no sales). */
  noSalesMonths: number;
  /** The payload's own coverage statement. */
  coverageRule: string;
  cutoffMonth: string;
}

/**
 * Rows for one area, newest `limit` grid months.
 *
 * An area the release does not carry returns an empty view rather than a grid
 * of "missing" rows: absence of the area and absence of a month are different
 * facts, and the fieldnote states the first one itself.
 */
export function buildAreaHistoryView(
  history: MonthlyHistory,
  areaId: string,
  limit: number = HISTORY_MONTH_LIMIT,
): AreaHistoryView {
  if (!history.seriesById.has(areaId)) {
    return {
      months: [],
      rows: [],
      hasObservations: false,
      noSalesMonths: 0,
      coverageRule: history.coverage.rule,
      cutoffMonth: history.cutoffMonth,
    };
  }

  const grid = history.months;
  const start = Math.max(0, grid.length - Math.max(1, limit));
  const months = grid.slice(start);
  const rows = months.map((month) => readMonth(history, areaId, month));

  return {
    months,
    rows,
    hasObservations: rows.some((row) => row.status === "available"),
    noSalesMonths: rows.filter((row) => row.status === "no-sales").length,
    coverageRule: history.coverage.rule,
    cutoffMonth: history.cutoffMonth,
  };
}

/** Reader-facing sentence for one month's status. */
export function monthStatusLabel(row: MonthlyReading): string {
  if (row.status === "no-sales") return "No observed sales";
  if (row.status === "missing-source") return "Not covered by this release";
  return "";
}
