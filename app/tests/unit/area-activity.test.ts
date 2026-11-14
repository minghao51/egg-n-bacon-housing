/**
 * Tests for area activity (RF10).
 *
 * The activity window is the published rolling quarter, so these tests pin the
 * things that make the surface honest: the prior-year denominator is shown
 * separately, a `no-sales` quarter is never rendered as 0, a missing comparator
 * is stated rather than silently dropped, the 150-sale floor is applied to both
 * windows, and nothing here produces a directional label or a derived statistic.
 */

import { describe, expect, it } from "bun:test";

import {
  ACTIVITY_PROPERTY_TYPES,
  ACTIVITY_SALE_FLOOR,
  activityForObservation,
  buildAreaActivity,
  rollingQuarterPeriod,
} from "@/utils/area-activity";
import {
  observationKey,
  parsePeriodPack,
  type Observation,
  type PeriodDescriptor,
  type PeriodPack,
  type PropertyTypeId,
} from "@/utils/observed-periods";
import periodsFixture from "../fixtures/v2-pack/periods.json";
import summaryFixture from "../fixtures/v2-pack/summary.json";

function realPack(): PeriodPack {
  const result = parsePeriodPack(periodsFixture, summaryFixture);
  if (!result.ok) {
    throw new Error(`fixture failed to parse: ${result.errors.join("; ")}`);
  }
  return result.pack;
}

const QUARTER: PeriodDescriptor = {
  id: "rolling3_2026_10",
  kind: "rolling3",
  startMonth: "2026-08",
  endMonth: "2026-10",
  months: ["2026-08", "2026-09", "2026-10"],
  label: "2026-08 → 2026-10",
  comparatorId: "rolling3_2025_10",
};

const PRIOR_QUARTER: PeriodDescriptor = {
  id: "rolling3_2025_10",
  kind: "rolling3",
  startMonth: "2025-08",
  endMonth: "2025-10",
  months: ["2025-08", "2025-09", "2025-10"],
  label: "2025-08 → 2025-10",
  comparatorId: null,
};

const TTM: PeriodDescriptor = {
  id: "ttm_2026_10",
  kind: "ttm",
  startMonth: "2025-11",
  endMonth: "2026-10",
  months: [],
  label: "12 months to 2026-10",
  comparatorId: null,
};

function observation(
  geographyId: string,
  propertyType: PropertyTypeId,
  periodId: string,
  value: number | null,
  status: "available" | "no-sales" = "available",
): Observation {
  return {
    geographyId,
    propertyType,
    periodId,
    status,
    disposition: propertyType === "hdb" ? "publish" : "limited-display",
    coverage: { months: [], requestedMonths: 3 },
    metrics: {
      transactionCount: {
        value,
        unit: "transactions",
        observations: value ?? 0,
      },
      medianPrice: { value: null, unit: "SGD", observations: 0 },
      medianPsf: { value: null, unit: "SGD_PSF", observations: 0 },
    },
  };
}

function syntheticPack(
  options: {
    current?: number;
    prior?: number | null;
    status?: "available" | "no-sales";
    comparatorId?: string | null;
    includeQuarter?: boolean;
  } = {},
): PeriodPack {
  const current = options.current ?? 200;
  const prior = options.prior === undefined ? 100 : options.prior;
  const status = options.status ?? "available";
  const comparatorId =
    options.comparatorId === undefined
      ? "rolling3_2025_10"
      : options.comparatorId;
  const quarter: PeriodDescriptor = { ...QUARTER, comparatorId };

  const periods: PeriodDescriptor[] = [];
  if (options.includeQuarter !== false) periods.push(quarter);
  periods.push(TTM);
  if (comparatorId !== null && options.includeQuarter !== false) {
    periods.push(PRIOR_QUARTER);
  }

  const observations: Observation[] = [
    observation("TEST", "hdb", QUARTER.id, current, status),
  ];
  if (comparatorId !== null && prior !== null) {
    observations.push(observation("TEST", "hdb", PRIOR_QUARTER.id, prior));
  }

  return {
    schemaVersion: "2.1.0",
    methodVersion: "observed-aggregates-2",
    cutoffMonth: "2026-10",
    cutoffSource: "test",
    periods,
    observations,
    periodsById: new Map(periods.map((period) => [period.id, period])),
    observationsByKey: new Map(
      observations.map((entry) => [
        observationKey(entry.geographyId, entry.propertyType, entry.periodId),
        entry,
      ]),
    ),
  };
}

describe("rolling-quarter selection", () => {
  it("picks the newest published rolling quarter", () => {
    expect(rollingQuarterPeriod(realPack())?.id).toBe("rolling3_2026_10");
    expect(
      rollingQuarterPeriod(syntheticPack({ includeQuarter: false })),
    ).toBeNull();
  });

  it("returns null when the pack publishes no rolling quarter", () => {
    expect(
      buildAreaActivity(syntheticPack({ includeQuarter: false }), "TEST"),
    ).toBeNull();
  });
});

describe("area activity rows (published pack)", () => {
  const pack = realPack();

  it("uses the quarter and its prior-year comparator with explicit ranges", () => {
    const activity = buildAreaActivity(pack, "PUNGGOL");
    expect(activity).not.toBeNull();
    expect(activity!.periodId).toBe("rolling3_2026_10");
    expect(activity!.range).toBe("2026-08 → 2026-10");
    expect(activity!.comparatorId).toBe("rolling3_2025_10");
    expect(activity!.comparatorRange).toBe("2025-08 → 2025-10");
    expect(activity!.months).toEqual(["2026-08", "2026-09", "2026-10"]);
  });

  it("reports both denominators and the year-on-year change", () => {
    const hdb = buildAreaActivity(pack, "PUNGGOL")!.rows.find(
      (row) => row.propertyType === "hdb",
    )!;

    expect(hdb.current.transactionCount).toBe(488);
    expect(hdb.priorYear?.transactionCount).toBe(370);
    expect(hdb.changePercent).toBeCloseTo(((488 - 370) / 370) * 100, 6);
    expect(hdb.eligible).toBe(true);
    expect(hdb.ineligibleReason).toBeNull();
    // TTM context is carried separately, never folded into the quarter.
    expect(hdb.ttmCount).toBe(1702);
  });

  it("marks a thin property type ineligible without hiding its numbers", () => {
    const ec = buildAreaActivity(pack, "ANG MO KIO")!.rows.find(
      (row) => row.propertyType === "ec",
    )!;

    expect(ec.current.transactionCount).toBe(2);
    expect(ec.priorYear?.transactionCount).toBe(2);
    expect(ec.changePercent).toBe(0);
    expect(ec.eligible).toBe(false);
    expect(ec.ineligibleReason).toContain(
      `fewer than ${ACTIVITY_SALE_FLOOR} observed sales`,
    );
  });

  it("lists one row per published property type, specific types first", () => {
    const types = buildAreaActivity(pack, "TAMPINES")!.rows.map(
      (row) => row.propertyType,
    );
    expect(types).toEqual(["hdb", "ec", "condo", "all"]);
  });

  it("says counts are observed transactions and publishes no directional label", () => {
    const activity = buildAreaActivity(pack, "TAMPINES")!;
    const notes = activity.notes.join(" ");
    expect(notes).toContain("observed resale transactions");
    expect(notes).toContain(
      `${ACTIVITY_SALE_FLOOR} observed sales in both quarters`,
    );
    for (const row of activity.rows) {
      expect(Object.keys(row).sort()).toEqual(
        [
          "changePercent",
          "changeUnavailableReason",
          "current",
          "eligible",
          "ineligibleReason",
          "priorYear",
          "propertyLabel",
          "propertyType",
          "ttmCount",
        ].sort(),
      );
    }
    // No score, label or normalized statistic may ride along as a *field*: the
    // notes are allowed to name the things the module refuses to compute.
    const forbidden = /score|hotness|turnover|demand|liquidity|ranking/i;
    const keys = new Set<string>();
    const collect = (value: unknown): void => {
      if (value === null || typeof value !== "object") return;
      for (const [key, entry] of Object.entries(value)) {
        keys.add(key);
        collect(entry);
      }
    };
    collect(activity);
    for (const key of keys) {
      expect(forbidden.test(key)).toBe(false);
    }
  });
});

describe("area activity states", () => {
  it("keeps a verified no-sales quarter as an absence, not a zero", () => {
    const activity = buildAreaActivity(
      syntheticPack({ status: "no-sales", current: 0, prior: 0 }),
      "TEST",
    )!;
    const row = activity.rows[0]!;

    expect(row.current.transactionCount).toBeNull();
    expect(row.current.status).toBe("no-sales");
    expect(row.changePercent).toBeNull();
    expect(row.changeUnavailableReason).toContain("no observed sales");
    expect(row.eligible).toBe(false);
    expect(activity.notes.join(" ")).toContain(
      "verified zero for this population",
    );
  });

  it("states a missing comparator instead of dropping the change", () => {
    const activity = buildAreaActivity(
      syntheticPack({ comparatorId: null }),
      "TEST",
    )!;
    const row = activity.rows[0]!;

    expect(activity.comparatorId).toBeNull();
    expect(activity.comparatorRange).toBeNull();
    expect(row.priorYear).toBeNull();
    expect(row.changePercent).toBeNull();
    expect(row.changeUnavailableReason).toContain("no comparator");
    expect(row.ineligibleReason).toContain("prior-year-quarter denominator");
  });

  it("applies the floor to both windows", () => {
    const atFloor = buildAreaActivity(
      syntheticPack({
        current: ACTIVITY_SALE_FLOOR,
        prior: ACTIVITY_SALE_FLOOR,
      }),
      "TEST",
    )!.rows[0]!;
    const justUnder = buildAreaActivity(
      syntheticPack({
        current: ACTIVITY_SALE_FLOOR,
        prior: ACTIVITY_SALE_FLOOR - 1,
      }),
      "TEST",
    )!.rows[0]!;

    expect(atFloor.eligible).toBe(true);
    expect(justUnder.eligible).toBe(false);
    expect(justUnder.ineligibleReason).toContain("prior-year quarter");
  });

  it("reports a zero prior-year denominator rather than dividing by zero", () => {
    const row = buildAreaActivity(syntheticPack({ prior: 0 }), "TEST")!
      .rows[0]!;
    expect(row.changePercent).toBeNull();
    expect(row.changeUnavailableReason).toContain("zero observed sales");
  });

  it("emits no row for a property type the quarter does not report", () => {
    const activity = buildAreaActivity(syntheticPack(), "TEST")!;
    expect(activity.rows).toHaveLength(1);
    expect(activity.rows[0]!.propertyType).toBe("hdb");
  });

  it("returns notes but no rows for an area the quarter does not report", () => {
    const activity = buildAreaActivity(syntheticPack(), "NOWHERE")!;
    expect(activity.rows).toEqual([]);
    expect(activity.notes.join(" ")).toContain(
      "Nothing is shown rather than a zero",
    );
  });
});

/**
 * The fieldnote table and the explorer row share one implementation, so this
 * pins the shared function against the table it feeds. If they ever diverge, a
 * reader sees two different definitions of the same quarter on two pages.
 */
describe("activityForObservation parity", () => {
  it("matches the fieldnote row for the same observation", () => {
    const pack = realPack();
    const quarter = rollingQuarterPeriod(pack)!;
    for (const propertyType of ACTIVITY_PROPERTY_TYPES) {
      const row = buildAreaActivity(pack, "PUNGGOL")!.rows.find(
        (entry) => entry.propertyType === propertyType,
      );
      if (row === undefined) continue;
      const observation = pack.observationsByKey.get(
        observationKey("PUNGGOL", propertyType, quarter.id),
      )!;
      const comparison = activityForObservation(pack, observation);

      expect(comparison.priorYear?.transactionCount ?? null).toBe(
        row.priorYear?.transactionCount ?? null,
      );
      expect(comparison.changePercent).toBe(row.changePercent);
      expect(comparison.changeUnavailableReason).toBe(
        row.changeUnavailableReason,
      );
      expect(comparison.eligible).toBe(row.eligible);
      expect(comparison.ineligibleReason).toBe(row.ineligibleReason);
    }
  });

  it("reports the same absence for a no-sales window as the table", () => {
    const pack = syntheticPack({ status: "no-sales", current: 0, prior: 0 });
    const observation = pack.observationsByKey.get(
      observationKey("TEST", "hdb", "rolling3_2026_10"),
    )!;
    const comparison = activityForObservation(pack, observation);
    const row = buildAreaActivity(pack, "TEST")!.rows[0]!;

    expect(comparison.priorYear?.transactionCount ?? null).toBe(
      row.priorYear?.transactionCount ?? null,
    );
    expect(comparison.changePercent).toBeNull();
    expect(comparison.eligible).toBe(false);
  });
});
