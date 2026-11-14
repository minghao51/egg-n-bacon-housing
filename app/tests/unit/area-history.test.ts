/**
 * Tests for the fieldnote monthly-history view model (RF10 slice 2b).
 *
 * The rules under test are the ones that keep a monthly table honest: the grid
 * decides which months exist (never a bounds inference), a verified zero is a
 * `no-sales` reading labelled in words, an absent area is an empty view rather
 * than a column of zeros, and the payload size is bounded by the month limit.
 */

import { describe, expect, it } from "bun:test";

import {
  HISTORY_MONTH_LIMIT,
  buildAreaHistoryView,
  monthStatusLabel,
} from "@/utils/area-history";
import {
  parseMonthlyHistory,
  type MonthlyHistory,
} from "@/utils/observed-monthly";
import monthlyFixture from "../fixtures/v2-pack/area-monthly-hdb.json";

function fixtureHistory(): MonthlyHistory {
  const parsed = parseMonthlyHistory(monthlyFixture, { propertyType: "hdb" });
  if (!parsed.ok) {
    throw new Error(`fixture failed to parse: ${parsed.errors.join("; ")}`);
  }
  return parsed.history;
}

/** A hand-built history: one area, one grid month with a verified zero. */
function syntheticHistory(): MonthlyHistory {
  const months = ["2026-08", "2026-09", "2026-10"];
  return {
    schemaVersion: "2.1.0",
    methodVersion: "observed-aggregates-2",
    cutoffMonth: "2026-10",
    propertyType: "hdb",
    disposition: "publish",
    nationalId: "SG",
    unassignedIds: [],
    months,
    coverage: {
      firstMonth: "2026-08",
      lastMonth: "2026-10",
      monthCount: months.length,
      rule: "Covered months only.",
    },
    series: [],
    seriesById: new Map([
      [
        "SG",
        {
          geographyId: "SG",
          noSalesMonths: 1,
          cells: [
            [10, 500000, 10, 600, 10],
            [0, null, 0, null, 0],
            [4, 510000, 4, 610, 4],
          ],
        },
      ],
      [
        "EMPTY",
        {
          geographyId: "EMPTY",
          noSalesMonths: 3,
          cells: [
            [0, null, 0, null, 0],
            [0, null, 0, null, 0],
            [0, null, 0, null, 0],
          ],
        },
      ],
    ]),
  };
}

describe("monthly history view", () => {
  it("renders the newest grid months in ascending order", () => {
    const history = fixtureHistory();
    const view = buildAreaHistoryView(history, "PUNGGOL");

    expect(view.rows.length).toBe(
      Math.min(HISTORY_MONTH_LIMIT, history.months.length),
    );
    expect(view.months).toEqual(history.months.slice(-view.rows.length));
    // Ascending, oldest first: no reversed table by accident.
    expect(view.months).toEqual([...view.months].sort());
    expect(view.rows[0]?.month).toBe(view.months[0] as string);
    expect(view.rows.at(-1)?.month).toBe(history.months.at(-1) as string);
  });

  it("honours a smaller month limit", () => {
    const view = buildAreaHistoryView(fixtureHistory(), "PUNGGOL", 3);
    expect(view.rows).toHaveLength(3);
    expect(view.rows.at(-1)?.month).toBe("2026-10");
  });

  it("carries the payload's own coverage statement and cutoff", () => {
    const history = fixtureHistory();
    const view = buildAreaHistoryView(history, "PUNGGOL");
    expect(view.coverageRule).toBe(history.coverage.rule);
    expect(view.cutoffMonth).toBe(history.cutoffMonth);
  });

  it("returns an empty view for an area the release does not carry", () => {
    const view = buildAreaHistoryView(fixtureHistory(), "NOT AN AREA");
    expect(view.rows).toEqual([]);
    expect(view.months).toEqual([]);
    expect(view.hasObservations).toBe(false);
  });

  it("counts verified zero months without turning them into a value", () => {
    const view = buildAreaHistoryView(syntheticHistory(), "SG");
    const zeroMonth = view.rows.find((row) => row.month === "2026-09")!;

    expect(zeroMonth.status).toBe("no-sales");
    expect(zeroMonth.transactionCount).toBe(0);
    // The reader-facing label is a sentence, never "0".
    expect(monthStatusLabel(zeroMonth)).toBe("No observed sales");
    expect(view.noSalesMonths).toBe(1);
    expect(view.hasObservations).toBe(true);
  });

  it("distinguishes an all-zero area from a missing one", () => {
    const view = buildAreaHistoryView(syntheticHistory(), "EMPTY");
    expect(view.rows).toHaveLength(3);
    expect(view.hasObservations).toBe(false);
    expect(view.noSalesMonths).toBe(3);
    // Every row is a verified zero, not a missing-source placeholder.
    for (const row of view.rows) {
      expect(row.status).toBe("no-sales");
    }
  });

  it("labels missing source differently from a zero", () => {
    expect(
      monthStatusLabel({
        month: "2020-01",
        status: "missing-source",
        transactionCount: null,
        medianPrice: null,
        priceObservations: 0,
        medianPsf: null,
        psfObservations: 0,
      }),
    ).toBe("Not covered by this release");
    expect(
      monthStatusLabel({
        month: "2026-10",
        status: "available",
        transactionCount: 12,
        medianPrice: 500000,
        priceObservations: 12,
        medianPsf: 600,
        psfObservations: 12,
      }),
    ).toBe("");
  });
});
