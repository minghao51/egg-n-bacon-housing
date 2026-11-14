/**
 * Tests for the v2 observed-period client resolver.
 *
 * The golden fixture in `tests/fixtures/v2-pack/` is a trimmed copy of a real
 * pack produced by `scripts/v2_observed.py` (cutoff 2026-10, national + three
 * planning areas, RF09 history grid trimmed to 26 months). Synthetic packs
 * cover the failure paths.
 */

import { describe, expect, it } from "bun:test";
import {
  DEFAULT_ALIAS_BY_SURFACE,
  V2_SCHEMA_VERSION,
  compareWithComparator,
  coveredMonths,
  cutoffUnobserved,
  findObservation,
  isPublishable,
  monthsBetween,
  observationKey,
  parsePeriodPack,
  resolvePeriodAlias,
  scopeNote,
} from "@/utils/observed-periods";
import periodsFixture from "../fixtures/v2-pack/periods.json";
import summaryFixture from "../fixtures/v2-pack/summary.json";

function realPack() {
  const result = parsePeriodPack(periodsFixture, summaryFixture);
  if (!result.ok)
    throw new Error(`fixture failed to parse: ${result.errors.join("; ")}`);
  return result.pack;
}

const metric = (value: number | null, unit = "SGD", observations = 10) => ({
  value,
  unit,
  observations,
});

function syntheticPayloads(
  options: {
    status?: "available" | "no-sales";
    current?: number | null;
    comparator?: number | null;
    comparatorId?: string | null;
    extraPeriod?: boolean;
  } = {},
) {
  const status = options.status ?? "available";
  const current = options.current === undefined ? 100 : options.current;
  const comparator = options.comparator === undefined ? 80 : options.comparator;

  const periods = [
    {
      id: "month_2026_10",
      kind: "month" as const,
      startMonth: "2026-10",
      endMonth: "2026-10",
      months: ["2026-10"],
      label: "2026-10",
      comparatorId:
        options.comparatorId === undefined
          ? "month_2025_10"
          : options.comparatorId,
    },
    {
      id: "month_2025_10",
      kind: "month" as const,
      startMonth: "2025-10",
      endMonth: "2025-10",
      months: ["2025-10"],
      label: "2025-10",
      comparatorId: null,
    },
  ];

  const noSales = status === "no-sales";

  const observations = [
    {
      geographyId: "SG",
      propertyType: "all" as const,
      periodId: "month_2026_10",
      status,
      disposition: "publish" as const,
      coverage: { months: ["2026-10"], requestedMonths: 1 },
      metrics: {
        transactionCount: metric(noSales ? 0 : current, "transactions"),
        medianPrice: metric(noSales ? null : current),
        medianPsf: metric(noSales ? null : current, "SGD_per_sqft"),
      },
    },
    {
      geographyId: "SG",
      propertyType: "all" as const,
      periodId: "month_2025_10",
      status: "available" as const,
      disposition: "publish" as const,
      coverage: { months: ["2025-10"], requestedMonths: 1 },
      metrics: {
        transactionCount: metric(comparator, "transactions"),
        medianPrice: metric(comparator),
        medianPsf: metric(comparator, "SGD_per_sqft"),
      },
    },
  ];

  return {
    periods: {
      schemaVersion: V2_SCHEMA_VERSION,
      methodVersion: "test",
      cutoffMonth: "2026-10",
      periods,
      propertyTypes: ["all", "hdb", "ec", "condo"],
      metrics: ["transactionCount", "medianPrice", "medianPsf"],
    },
    summary: {
      schemaVersion: V2_SCHEMA_VERSION,
      methodVersion: "test",
      cutoffMonth: "2026-10",
      cutoffSource: "declared",
      monthsPresent: ["2025-10", "2026-10"],
      observations:
        options.status === "no-sales"
          ? [observations[0], observations[1]]
          : observations,
    },
  };
}

describe("monthsBetween", () => {
  it("builds inclusive month lists across year boundaries", () => {
    expect(monthsBetween("2025-11", "2026-01")).toEqual([
      "2025-11",
      "2025-12",
      "2026-01",
    ]);
  });

  it("handles a single month and a leap February", () => {
    expect(monthsBetween("2026-10", "2026-10")).toEqual(["2026-10"]);
    expect(monthsBetween("2028-02", "2028-03")).toEqual(["2028-02", "2028-03"]);
  });

  it("rejects reversed or malformed bounds", () => {
    expect(monthsBetween("2026-10", "2026-01")).toBeNull();
    expect(monthsBetween("2026-13", "2026-13")).toBeNull();
  });
});

describe("parsing the real pack", () => {
  it("accepts the published fixture", () => {
    const pack = realPack();

    expect(pack.schemaVersion).toBe(V2_SCHEMA_VERSION);
    expect(pack.cutoffMonth).toBe("2026-10");
    expect(pack.periods.length).toBe(10);
    expect(pack.observations.length).toBeGreaterThan(0);
  });

  it("publishes the rolling quarter with its prior-year comparator", () => {
    const pack = realPack();
    const rolling = pack.periodsById.get("rolling3_2026_10");

    expect(rolling?.kind).toBe("rolling3");
    expect(rolling?.startMonth).toBe("2026-08");
    expect(rolling?.months).toEqual(["2026-08", "2026-09", "2026-10"]);
    expect(rolling?.comparatorId).toBe("rolling3_2025_10");
    expect(pack.periodsById.get("rolling3_2025_10")?.months).toEqual([
      "2025-08",
      "2025-09",
      "2025-10",
    ]);
  });

  it("keeps concrete period windows and comparator links", () => {
    const pack = realPack();
    const ytd = pack.periodsById.get("ytd_2026_10");

    expect(ytd?.startMonth).toBe("2026-01");
    expect(ytd?.months.length).toBe(10);
    expect(ytd?.comparatorId).toBe("ytd_2025_10");
    expect(pack.periodsById.get("ttm_2026_10")?.months.length).toBe(12);
  });
});

describe("parse rejection", () => {
  it("rejects an unsupported schema version", () => {
    const { periods, summary } = syntheticPayloads();
    const result = parsePeriodPack(
      { ...periods, schemaVersion: "1.0.0" },
      summary,
    );

    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.errors.join(" ")).toContain("schemaVersion");
  });

  it("rejects a duplicate period id", () => {
    const { periods, summary } = syntheticPayloads();
    const duplicated = {
      ...periods,
      periods: [periods.periods[0], periods.periods[0]],
    };
    const result = parsePeriodPack(duplicated, summary);

    expect(result.ok).toBe(false);
    if (!result.ok)
      expect(result.errors.join(" ")).toContain("duplicate period id");
  });

  it("rejects an observation that references an unpublished period", () => {
    const { periods, summary } = syntheticPayloads();
    const orphaned = {
      ...summary,
      observations: [{ ...summary.observations[0], periodId: "month_2030_01" }],
    };
    const result = parsePeriodPack(periods, orphaned);

    expect(result.ok).toBe(false);
    if (!result.ok)
      expect(result.errors.join(" ")).toContain("unpublished period");
  });

  it("rejects months that disagree with the bounds", () => {
    const { periods, summary } = syntheticPayloads();
    const broken = {
      ...periods,
      periods: [
        { ...periods.periods[0], months: ["2026-09"] },
        periods.periods[1],
      ],
    };
    const result = parsePeriodPack(broken, summary);

    expect(result.ok).toBe(false);
    if (!result.ok)
      expect(result.errors.join(" ")).toContain("months do not match");
  });

  it("rejects a no-sales observation that carries a price", () => {
    const { periods, summary } = syntheticPayloads({ status: "no-sales" });
    const contradictory = {
      ...summary,
      observations: [
        {
          ...summary.observations[0],
          metrics: {
            ...summary.observations[0].metrics,
            medianPrice: metric(500000),
          },
        },
      ],
    };
    const result = parsePeriodPack(periods, contradictory);

    expect(result.ok).toBe(false);
    if (!result.ok)
      expect(result.errors.join(" ")).toContain("no-sales with a price");
  });

  it("rejects periods and summary that disagree about the cutoff", () => {
    const { periods, summary } = syntheticPayloads();
    const result = parsePeriodPack(periods, {
      ...summary,
      cutoffMonth: "2026-09",
    });

    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.errors.join(" ")).toContain("cutoff month");
  });
});

describe("alias resolution", () => {
  it("resolves latest, ytd and ttm to concrete period ids", () => {
    const pack = realPack();

    expect(resolvePeriodAlias(pack, "latest")?.id).toBe("month_2026_10");
    expect(resolvePeriodAlias(pack, "ytd")?.id).toBe("ytd_2026_10");
    expect(resolvePeriodAlias(pack, "ttm")?.id).toBe("ttm_2026_10");
  });

  it("never resolves to a comparator window with an older end month", () => {
    const pack = realPack();

    // month_2025_10 ends earlier, so `latest` must not pick it.
    expect(resolvePeriodAlias(pack, "latest")?.endMonth).toBe("2026-10");
  });

  it("uses the ratified default window per surface", () => {
    expect(DEFAULT_ALIAS_BY_SURFACE.dashboard).toBe("ytd");
    expect(DEFAULT_ALIAS_BY_SURFACE.trends).toBe("ttm");
    expect(DEFAULT_ALIAS_BY_SURFACE.explorer).toBe("ttm");
    expect(DEFAULT_ALIAS_BY_SURFACE.rankings).toBe("ttm");
  });
});

describe("observation lookup", () => {
  it("finds a published observation and reports absence otherwise", () => {
    const pack = realPack();

    const punggol = findObservation(pack, "PUNGGOL", "hdb", "year_2025");
    expect(punggol?.metrics.transactionCount.value).toBe(1538);
    expect(punggol?.metrics.medianPrice.value).toBe(672000);

    expect(
      findObservation(pack, "PUNGGOL", "hdb", "month_2026_10"),
    ).not.toBeNull();
    expect(findObservation(pack, "NOWHERE", "hdb", "year_2025")).toBeNull();
    expect(findObservation(pack, "PUNGGOL", "hdb", "ytd_1999_01")).toBeNull();
  });

  it("builds the same key the index uses", () => {
    expect(observationKey("SG", "all", "year_2025")).toBe("SG|all|year_2025");
  });
});

describe("comparisons", () => {
  it("compares a published window with its comparator", () => {
    const pack = realPack();
    const current = findObservation(pack, "SG", "hdb", "month_2026_10");
    expect(current).not.toBeNull();

    const comparison = compareWithComparator(pack, current!);
    expect(comparison).not.toBeNull();
    expect(comparison?.comparatorPeriod.id).toBe("month_2025_10");

    const count = comparison?.changes.find(
      (change) => change.metric === "transactionCount",
    );
    expect(count).toBeDefined();
    expect(count!.absolute).toBe(
      (current!.metrics.transactionCount.value ?? 0) -
        (comparison!.comparator.metrics.transactionCount.value ?? 0),
    );
  });

  it("returns null when the period has no comparator", () => {
    const pack = realPack();
    const terminal = findObservation(pack, "SG", "hdb", "month_2025_10");

    expect(compareWithComparator(pack, terminal!)).toBeNull();
  });

  it("returns null when the comparator observation is absent", () => {
    const { periods, summary } = syntheticPayloads();
    const withoutComparatorObservation = {
      ...summary,
      observations: [summary.observations[0]],
    };
    const result = parsePeriodPack(periods, withoutComparatorObservation);
    expect(result.ok).toBe(true);
    if (!result.ok) return;

    expect(
      compareWithComparator(result.pack, result.pack.observations[0]),
    ).toBeNull();
  });

  it("skips metrics that cannot be compared instead of inventing them", () => {
    const { periods, summary } = syntheticPayloads({ status: "no-sales" });
    const result = parsePeriodPack(periods, summary);
    expect(result.ok).toBe(true);
    if (!result.ok) return;

    const comparison = compareWithComparator(
      result.pack,
      result.pack.observations[0],
    );
    expect(comparison?.changes).toEqual([]);
    expect(comparison?.skipped.map((entry) => entry.metric).sort()).toEqual([
      "medianPrice",
      "medianPsf",
      "transactionCount",
    ]);
    expect(comparison?.skipped[0].reason).toContain(
      "not observed in both windows",
    );
  });

  it("refuses a zero comparator denominator", () => {
    const { periods, summary } = syntheticPayloads({
      current: 5,
      comparator: 0,
    });
    const result = parsePeriodPack(periods, summary);
    expect(result.ok).toBe(true);
    if (!result.ok) return;

    const comparison = compareWithComparator(
      result.pack,
      result.pack.observations[0],
    );
    const reasons = comparison?.skipped.map((entry) => entry.reason) ?? [];
    expect(reasons).toContain("zero comparator denominator");
    expect(comparison?.changes).toEqual([]);
  });

  it("computes a percentage change for an available scope", () => {
    const { periods, summary } = syntheticPayloads({
      current: 120,
      comparator: 100,
    });
    const result = parsePeriodPack(periods, summary);
    expect(result.ok).toBe(true);
    if (!result.ok) return;

    const comparison = compareWithComparator(
      result.pack,
      result.pack.observations[0],
    );
    const count = comparison?.changes.find(
      (change) => change.metric === "transactionCount",
    );

    expect(count?.absolute).toBe(20);
    expect(count?.percent).toBeCloseTo(20, 10);
  });
});

describe("dispositions", () => {
  it("treats only cleared, observed scopes as publishable", () => {
    const pack = realPack();

    expect(
      isPublishable(findObservation(pack, "SG", "hdb", "month_2026_10")!),
    ).toBe(true);
    expect(
      isPublishable(findObservation(pack, "SG", "condo", "month_2026_10")!),
    ).toBe(false);
  });

  it("explains why a scope is limited", () => {
    const pack = realPack();

    expect(
      scopeNote(findObservation(pack, "SG", "condo", "month_2026_10")!),
    ).toContain("Coverage is limited");
    expect(
      scopeNote(findObservation(pack, "SG", "hdb", "month_2026_10")!),
    ).toBeNull();
  });
});

describe("coverage", () => {
  it("reports covered months from observations", () => {
    const pack = realPack();

    expect(coveredMonths(pack)).toContain("2026-10");
    expect(coveredMonths(pack)).toContain("2024-11");
    expect(coveredMonths(pack)).not.toContain("1990-01");
  });

  it("detects a pack whose cutoff month has no observation", () => {
    const pack = realPack();

    expect(cutoffUnobserved(pack)).toBe(false);
  });
});
