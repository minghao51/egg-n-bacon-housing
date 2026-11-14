/**
 * RF01 unit tests: scoped area rankings for Compare Areas.
 *
 * The published facts come from `app/tests/fixtures/rf00-observed-contract.json`,
 * which pins the released `map_metrics` / `dashboard_leaderboard` values at
 * generation 0e1013ee485f (through 2026-10). Synthetic cases in that fixture are
 * hand-authored and flagged as such.
 */

import { describe, expect, it } from "bun:test";
import { PLANNING_REGIONS, type LeaderboardEntry } from "@/types/leaderboard";
import {
  SAMPLE_CAUTION_THRESHOLD,
  buildPackScopedRows,
  buildScopedRows,
  isScopedRankMetric,
  isThinSample,
  readScopedAreaMetrics,
  resolvePlanningRegion,
  unsupportedMetricReason,
} from "@/utils/leaderboard-observed";
import { V2_SCHEMA_VERSION, parsePeriodPack } from "@/utils/observed-periods";
import fixture from "../fixtures/rf00-observed-contract.json";

const publishedMetrics = fixture.published.jointSections;

function makeEntry(area: string, region: string): LeaderboardEntry {
  return {
    planning_area: area,
    region,
    coordinates: null,
    spatial_hotspot: "Unknown",
    rank_overall: 99,
    median_price: 1,
    median_psf: 1,
    rental_yield_mean: 1,
    rental_yield_median: 1,
    yoy_growth_pct: 999,
    mom_change_pct: 999,
    momentum: 999,
    volume: 999999,
    affordability_ratio: 1,
    by_property_type: {
      hdb: { median_price: 500000, volume: 24854 },
      ec: { median_price: 1, volume: 1 },
      condo: { median_price: 1, volume: 1 },
    },
    by_time_period: {
      whole: { median_price: 1, yoy_growth: 1 },
      pre_covid: { median_price: 1, yoy_growth: 1 },
      recent: { median_price: 1, yoy_growth: 1 },
      year_2025: { median_price: 742444, yoy_growth: null },
    },
  };
}

function baseInput(overrides: Record<string, unknown> = {}) {
  return {
    entries: [
      makeEntry("PUNGGOL", "NORTH-EAST REGION"),
      makeEntry("TAMPINES", "EAST REGION"),
      makeEntry("ANG MO KIO", "CENTRAL REGION"),
    ],
    mapMetrics: publishedMetrics,
    era: "year_2025" as const,
    propertyType: "hdb" as const,
    metric: "median_price" as const,
    region: [...PLANNING_REGIONS],
    priceRange: [0, 5_000_000] as const,
    search: "",
    ...overrides,
  };
}

describe("scoped metric reads", () => {
  it("reads Punggol HDB 2025 from the joint section", () => {
    const metrics = readScopedAreaMetrics(
      publishedMetrics,
      "PUNGGOL",
      "year_2025",
      "hdb",
    );

    expect(metrics).not.toBeNull();
    expect(metrics?.medianPrice).toBe(672000);
    expect(metrics?.medianPsf).toBe(686);
    expect(metrics?.volume).toBe(1538);
    expect(metrics?.status).toBe("available");
    expect(metrics?.isThinSample).toBe(false);
  });

  it("never falls back to the property-only or period-only margins", () => {
    const metrics = readScopedAreaMetrics(
      publishedMetrics,
      "PUNGGOL",
      "year_2025",
      "hdb",
    );

    // The leaderboard margin says S$500,000 over 24,854 sales; the period-only
    // 2025 median is S$742,444. Neither may appear here.
    expect(metrics?.medianPrice).not.toBe(500000);
    expect(metrics?.volume).not.toBe(24854);
    expect(metrics?.medianPrice).not.toBe(742444);
  });

  it("returns null when the joint section is absent", () => {
    expect(
      readScopedAreaMetrics(
        { year_2025_hdb: publishedMetrics.year_2025_hdb },
        "TAMPINES",
        "year_2025",
        "ec",
      ),
    ).toBeNull();
  });

  it("treats an exporter zero block as empty, not S$0", () => {
    const metrics = readScopedAreaMetrics(
      {
        year_2025_hdb: {
          PUNGGOL: { median_price: 0, median_psf: 0, volume: 0 },
        },
      },
      "PUNGGOL",
      "year_2025",
      "hdb",
    );

    expect(metrics?.medianPrice).toBeNull();
    expect(metrics?.volume).toBeNull();
    expect(metrics?.status).toBe("empty");
  });
});

describe("sample caution rule", () => {
  it("flags 12 sales as thin and 1,538 as sufficient", () => {
    expect(isThinSample(12)).toBe(true);
    expect(isThinSample(SAMPLE_CAUTION_THRESHOLD - 1)).toBe(true);
    expect(isThinSample(SAMPLE_CAUTION_THRESHOLD)).toBe(false);
    expect(isThinSample(1538)).toBe(false);
  });

  it("treats an unknown count as thin", () => {
    expect(isThinSample(null)).toBe(true);
  });
});

describe("geography", () => {
  it("resolves the five published planning regions", () => {
    for (const region of PLANNING_REGIONS) {
      expect(resolvePlanningRegion(region)).toBe(region);
    }
    expect(resolvePlanningRegion("east region")).toBe("EAST REGION");
  });

  it("does not invent a region for CCR/RCR/OCR or unknown labels", () => {
    expect(resolvePlanningRegion("CCR")).toBeNull();
    expect(resolvePlanningRegion("RCR")).toBeNull();
    expect(resolvePlanningRegion("OCR")).toBeNull();
    expect(resolvePlanningRegion("")).toBeNull();
    expect(resolvePlanningRegion(null)).toBeNull();
  });
});

describe("metric availability", () => {
  it("supports only the jointly published metrics", () => {
    expect(isScopedRankMetric("median_price")).toBe(true);
    expect(isScopedRankMetric("median_psf")).toBe(true);
    expect(isScopedRankMetric("volume")).toBe(true);
    expect(isScopedRankMetric("yoy_growth_pct")).toBe(false);
    expect(isScopedRankMetric("momentum")).toBe(false);
  });

  it("explains why an unsupported metric cannot be ranked", () => {
    expect(unsupportedMetricReason("yoy_growth_pct")).toContain("margin");
    expect(unsupportedMetricReason("rental_yield_median")).toContain("review");
    expect(unsupportedMetricReason("median_price")).toBeNull();
  });
});

describe("ranking rows", () => {
  it("ranks published areas by the scoped metric", () => {
    const result = buildScopedRows(baseInput());

    expect(result.rows.map((row) => row.planningArea)).toEqual([
      "TAMPINES",
      "PUNGGOL",
      "ANG MO KIO",
    ]);
    expect(result.rows.map((row) => row.rank)).toEqual([1, 2, 3]);
    expect(result.rows[0].medianPrice).toBe(710000);
    expect(result.unpublishedAreas).toEqual([]);
    expect(result.rankedCount).toBe(3);
  });

  it("reports an area the release does not publish for the scope", () => {
    const entries = [
      makeEntry("PUNGGOL", "NORTH-EAST REGION"),
      makeEntry("TAMPINES", "EAST REGION"),
    ];
    const mapMetrics = {
      year_2025_ec: publishedMetrics.year_2025_ec,
    };
    const result = buildScopedRows(
      baseInput({ entries, mapMetrics, propertyType: "hdb" as const }),
    );

    expect(result.rows).toHaveLength(0);
    expect(result.unpublishedAreas).toEqual(["PUNGGOL", "TAMPINES"]);
  });

  it("keeps a thin row visible but unranked, after the ranked rows", () => {
    const mapMetrics = {
      year_2025_hdb: {
        ...publishedMetrics.year_2025_hdb,
        TAMPINES: { median_price: 812000, median_psf: 640, volume: 12 },
      },
    };
    const result = buildScopedRows(baseInput({ mapMetrics }));

    const tampines = result.rows.find((row) => row.planningArea === "TAMPINES");
    expect(tampines?.rank).toBeNull();
    expect(tampines?.isThinSample).toBe(true);
    expect(result.rows.at(-1)?.planningArea).toBe("TAMPINES");
    expect(result.unrankedCount).toBe(1);
  });

  it("drops rows whose region label cannot be resolved when filtering", () => {
    const entries = [
      makeEntry("PUNGGOL", "NORTH-EAST REGION"),
      makeEntry("TAMPINES", "CCR"),
    ];
    const result = buildScopedRows(
      baseInput({ entries, region: ["NORTH-EAST REGION"] }),
    );

    expect(result.rows.map((row) => row.planningArea)).toEqual(["PUNGGOL"]);
  });

  it("uses the scoped median price for the price filter", () => {
    const result = buildScopedRows(
      baseInput({ priceRange: [0, 500000] as const }),
    );

    // Punggol S$672,000 and Ang Mo Kio S$499,000; only the latter fits.
    expect(result.rows.map((row) => row.planningArea)).toEqual(["ANG MO KIO"]);
  });

  it("builds property mix from the same period, not all-time volumes", () => {
    const result = buildScopedRows(baseInput());
    const punggol = result.rows.find((row) => row.planningArea === "PUNGGOL");

    // 1,538 HDB + 433 EC + 303 condo, all 2025. The all-time entry says 99,999.
    expect(punggol?.propertyMix?.hdb).toBe(1538);
    expect(punggol?.propertyMix?.ec).toBe(433);
    expect(punggol?.propertyMix?.condo).toBe(303);
    expect(punggol?.propertyMix?.total).toBe(2274);
    expect(punggol?.volume).toBe(1538);
  });

  it("marks unranked rows without a numeric ranking value", () => {
    const mapMetrics = {
      year_2025_hdb: {
        PUNGGOL: { median_price: null, median_psf: null, volume: 412 },
      },
    };
    const entries = [makeEntry("PUNGGOL", "NORTH-EAST REGION")];
    const result = buildScopedRows(baseInput({ entries, mapMetrics }));

    expect(result.rows[0].rank).toBeNull();
    expect(result.rows[0].rankMetricValue).toBeNull();
  });
});

/*
 * Pack-backed rankings (RF05 T2).
 *
 * The payloads below are a hand-authored miniature of the two v2 payloads,
 * parsed by the same contract validator the browser uses. Numbers are chosen to
 * exercise the publish/limited-display gate, the 150-sale rule and the
 * no-sales state; they are not the published snapshot's values.
 */

const PACK_MONTHS = [
  "2025-11",
  "2025-12",
  "2026-01",
  "2026-02",
  "2026-03",
  "2026-04",
  "2026-05",
  "2026-06",
  "2026-07",
  "2026-08",
  "2026-09",
  "2026-10",
];

const PACK_PERIODS = {
  schemaVersion: V2_SCHEMA_VERSION,
  cutoffMonth: "2026-10",
  cutoffSource: "test",
  methodVersion: "test-1",
  periods: [
    {
      id: "ttm_2026_10",
      kind: "ttm",
      startMonth: "2025-11",
      endMonth: "2026-10",
      months: PACK_MONTHS,
      label: "12 months to 2026-10",
      comparatorId: null,
    },
  ],
};

function packObservation(input: {
  area: string;
  propertyType: "all" | "hdb" | "ec" | "condo";
  count: number | null;
  price: number | null;
  psf: number | null;
  disposition?: "publish" | "limited-display";
  noSales?: boolean;
}) {
  const status = input.noSales === true ? "no-sales" : "available";
  return {
    geographyId: input.area,
    propertyType: input.propertyType,
    periodId: "ttm_2026_10",
    status,
    disposition: input.disposition ?? "publish",
    coverage: { months: PACK_MONTHS, requestedMonths: 12 },
    metrics: {
      transactionCount: {
        value: input.count,
        unit: "transactions",
        observations: input.count ?? 0,
      },
      medianPrice: {
        value: input.price,
        unit: "SGD",
        observations: input.count ?? 0,
      },
      medianPsf: {
        value: input.psf,
        unit: "SGD_per_sqft",
        observations: input.count ?? 0,
      },
    },
  };
}

const PACK_SUMMARY = {
  schemaVersion: V2_SCHEMA_VERSION,
  cutoffMonth: "2026-10",
  cutoffSource: "test",
  methodVersion: "test-1",
  observations: [
    packObservation({
      area: "SG",
      propertyType: "hdb",
      count: 21801,
      price: 631000,
      psf: 601,
    }),
    packObservation({
      area: "PUNGGOL",
      propertyType: "hdb",
      count: 1702,
      price: 672888,
      psf: 640,
    }),
    packObservation({
      area: "TAMPINES",
      propertyType: "hdb",
      count: 2103,
      price: 720000,
      psf: 655,
    }),
    packObservation({
      area: "ANG MO KIO",
      propertyType: "hdb",
      count: 60,
      price: 499000,
      psf: 583,
    }),
    packObservation({
      area: "BUKIT TIMAH",
      propertyType: "hdb",
      count: 0,
      price: null,
      psf: null,
      noSales: true,
    }),
    // Same-window mix (counts with dates are allowed for a limited-display scope).
    packObservation({
      area: "PUNGGOL",
      propertyType: "ec",
      count: 266,
      price: 1697500,
      psf: 1250,
      disposition: "limited-display",
    }),
    packObservation({
      area: "PUNGGOL",
      propertyType: "condo",
      count: 188,
      price: 1644444,
      psf: 1300,
      disposition: "limited-display",
    }),
    packObservation({
      area: "SG",
      propertyType: "ec",
      count: 3002,
      price: 1450000,
      psf: 1200,
      disposition: "limited-display",
    }),
  ],
};

function loadPack() {
  const parsed = parsePeriodPack(PACK_PERIODS, PACK_SUMMARY);
  if (!parsed.ok) throw new Error(parsed.errors.join("; "));
  return parsed.pack;
}

const PACK = loadPack();

function packInput(overrides: Record<string, unknown> = {}) {
  return {
    entries: [
      makeEntry("PUNGGOL", "NORTH-EAST REGION"),
      makeEntry("TAMPINES", "EAST REGION"),
      makeEntry("ANG MO KIO", "CENTRAL REGION"),
      makeEntry("BUKIT TIMAH", "CENTRAL REGION"),
      makeEntry("BEDOK", "EAST REGION"),
    ],
    pack: PACK,
    periodId: "ttm_2026_10",
    propertyType: "hdb" as const,
    metric: "median_price" as const,
    region: [...PLANNING_REGIONS],
    priceRange: [0, 5_000_000] as const,
    search: "",
    ...overrides,
  };
}

describe("pack-backed rankings", () => {
  it("ranks a publish scope from the pack and keeps thin rows unranked", () => {
    const outcome = buildPackScopedRows(packInput());
    if (!outcome.ok) throw new Error(outcome.reason);

    expect(outcome.periodLabel).toBe("12 months to 2026-10");
    expect(outcome.scope.rankable).toBe(true);
    expect(outcome.scope.rankedCount).toBe(2);
    expect(outcome.scope.rows.map((row) => row.planningArea)).toEqual([
      "TAMPINES",
      "PUNGGOL",
      "ANG MO KIO",
      "BUKIT TIMAH",
    ]);
    expect(outcome.scope.rows.map((row) => row.rank)).toEqual([
      1,
      2,
      null,
      null,
    ]);
    expect(outcome.scope.rows[1]?.medianPrice).toBe(672888);
    expect(outcome.scope.rows[1]?.volume).toBe(1702);
    // BEDOK is not published for this window; it is reported, not zeroed.
    expect(outcome.scope.unpublishedAreas).toEqual(["BEDOK"]);
  });

  it("keeps a verified no-sales window as zero sales with null prices", () => {
    const outcome = buildPackScopedRows(packInput());
    if (!outcome.ok) throw new Error(outcome.reason);

    const row = outcome.scope.rows.find(
      (entry) => entry.planningArea === "BUKIT TIMAH",
    );
    if (row === undefined) throw new Error("expected the no-sales row");
    expect(row.volume).toBe(0);
    expect(row.medianPrice).toBeNull();
    expect(row.rank).toBeNull();
    expect(row.isThinSample).toBe(true);
  });

  it("reads the same-window property mix from the pack", () => {
    const outcome = buildPackScopedRows(packInput({ search: "PUNGGOL" }));
    if (!outcome.ok) throw new Error(outcome.reason);

    // Search matches the area name, so the mix shown is Punggol's.
    const row = outcome.scope.rows[0];
    expect(row?.propertyMix).toEqual({
      hdb: 1702,
      ec: 266,
      condo: 188,
      total: 2156,
    });
  });

  it("never ranks a limited-display scope and lists rows by name", () => {
    const outcome = buildPackScopedRows(
      packInput({ propertyType: "ec", metric: "median_price" }),
    );
    if (!outcome.ok) throw new Error(outcome.reason);

    expect(outcome.disposition).toBe("limited-display");
    expect(outcome.scope.rankable).toBe(false);
    expect(outcome.scope.rankedCount).toBe(0);
    expect(outcome.scope.rows.map((row) => row.planningArea)).toEqual([
      "PUNGGOL",
    ]);
    expect(outcome.scope.rows[0]?.rank).toBeNull();
    expect(outcome.scope.rows[0]?.medianPrice).toBe(1697500);
    expect(outcome.note).toContain("Coverage is limited");
  });

  it("reports an unpublished or malformed period instead of another window", () => {
    const unknown = buildPackScopedRows(packInput({ periodId: "ttm_2026_07" }));
    expect(unknown.ok).toBe(false);
    if (!unknown.ok) {
      expect(unknown.period).toBe("ttm_2026_07");
      expect(unknown.reason).toContain("ttm_2026_10");
    }

    const malformed = buildPackScopedRows(packInput({ periodId: "latest" }));
    expect(malformed.ok).toBe(false);
    if (!malformed.ok) expect(malformed.reason).toContain("latest");
  });

  it("legacy eras stay rankable, so the old view is unchanged", () => {
    const result = buildScopedRows(baseInput());
    expect(result.rankable).toBe(true);
  });

  it("applies the region and price filters to pack rows too", () => {
    const east = buildPackScopedRows(
      packInput({ region: ["EAST REGION"], search: "" }),
    );
    if (!east.ok) throw new Error(east.reason);
    expect(east.scope.rows.map((row) => row.planningArea)).toEqual([
      "TAMPINES",
    ]);

    const cheap = buildPackScopedRows(
      packInput({ priceRange: [0, 700000] as const }),
    );
    if (!cheap.ok) throw new Error(cheap.reason);
    // A row with no published price is never dropped by the price range: there
    // is nothing to compare, and hiding it would claim it does not exist.
    expect(cheap.scope.rows.map((row) => row.planningArea)).toEqual([
      "PUNGGOL",
      "ANG MO KIO",
      "BUKIT TIMAH",
    ]);
  });
});
