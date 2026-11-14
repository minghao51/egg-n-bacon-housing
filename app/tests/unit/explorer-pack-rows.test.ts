/**
 * Unit tests for the pack row builder (src/utils/explorer-pack-rows.ts).
 *
 * Hermetic: the payloads below are hand-written versions of the two v2 pack
 * payloads (same schema, same field names), parsed by the same contract
 * validator the browser uses. No payload file is read at test time, and the
 * numbers are deliberately not the published snapshot's.
 */

import { describe, expect, test } from "bun:test";

import { buildPackExplorerDataset } from "../../src/utils/explorer-pack-rows";
import {
  V2_SCHEMA_VERSION,
  packPeriodLabel,
  parsePeriodPack,
  publishedPeriodOptions,
  type PeriodPack,
  type PropertyTypeId,
} from "../../src/utils/observed-periods";
import type { ExplorerRow } from "../../src/utils/observed-rows";

const TTM_MONTHS = [
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

const PERIODS_PAYLOAD = {
  schemaVersion: V2_SCHEMA_VERSION,
  cutoffMonth: "2026-10",
  cutoffSource: "test",
  methodVersion: "test-1",
  periods: [
    {
      id: "month_2026_10",
      kind: "month",
      startMonth: "2026-10",
      endMonth: "2026-10",
      months: ["2026-10"],
      label: "2026-10 (one month)",
      comparatorId: null,
    },
    {
      id: "ttm_2026_10",
      kind: "ttm",
      startMonth: "2025-11",
      endMonth: "2026-10",
      months: TTM_MONTHS,
      label: "12 months to 2026-10",
      comparatorId: null,
    },
    {
      // Shadowed by the legacy era of the same id: never offered as a pack
      // option, because the legacy id must keep reading the legacy asset.
      id: "year_2025",
      kind: "year",
      startMonth: "2025-01",
      endMonth: "2025-12",
      months: [
        "2025-01",
        "2025-02",
        "2025-03",
        "2025-04",
        "2025-05",
        "2025-06",
        "2025-07",
        "2025-08",
        "2025-09",
        "2025-10",
        "2025-11",
        "2025-12",
      ],
      label: "calendar year 2025",
      comparatorId: null,
    },
  ],
};

function metric(value: number | null, unit: string, observations: number) {
  return { value, unit, observations };
}

interface FixtureObservation {
  geographyId: string;
  propertyType: PropertyTypeId;
  periodId: string;
  status: "available" | "no-sales";
  disposition: "publish" | "limited-display";
  coverage: { months: string[]; requestedMonths: number };
  metrics: Record<
    "transactionCount" | "medianPrice" | "medianPsf",
    { value: number | null; unit: string; observations: number }
  >;
}

function observation(input: {
  geographyId: string;
  propertyType: PropertyTypeId;
  periodId?: string;
  status?: "available" | "no-sales";
  disposition?: "publish" | "limited-display";
  count: number | null;
  price: number | null;
  psf: number | null;
}): FixtureObservation {
  const status = input.status ?? "available";
  return {
    geographyId: input.geographyId,
    propertyType: input.propertyType,
    periodId: input.periodId ?? "ttm_2026_10",
    status,
    disposition: input.disposition ?? "publish",
    coverage: { months: TTM_MONTHS, requestedMonths: 12 },
    metrics: {
      transactionCount: metric(input.count, "transactions", input.count ?? 0),
      medianPrice: metric(input.price, "SGD", input.count ?? 0),
      medianPsf: metric(input.psf, "SGD_per_sqft", input.count ?? 0),
    },
  };
}

/** ttm_2026_10 HDB (publish) plus EC (limited-display) for the same window. */
const SUMMARY_PAYLOAD = {
  schemaVersion: V2_SCHEMA_VERSION,
  cutoffMonth: "2026-10",
  cutoffSource: "test",
  methodVersion: "test-1",
  observations: [
    // National, HDB.
    observation({
      geographyId: "SG",
      propertyType: "hdb",
      count: 21801,
      price: 633999,
      psf: 601,
    }),
    // HDB areas: two above the threshold, one thin, one verified no-sales.
    observation({
      geographyId: "ANG MO KIO",
      propertyType: "hdb",
      count: 971,
      price: 499000,
      psf: 583,
    }),
    observation({
      geographyId: "BEDOK",
      propertyType: "hdb",
      count: 1208,
      price: 548000,
      psf: 591,
    }),
    observation({
      geographyId: "BUKIT TIMAH",
      propertyType: "hdb",
      count: 60,
      price: 945500,
      psf: 821,
    }),
    observation({
      geographyId: "DOWNTOWN CORE",
      propertyType: "hdb",
      count: 0,
      price: null,
      psf: null,
      status: "no-sales",
    }),
    // An area the pack carries no row for at all.
    // (PUNGGOL only has a month window, checked by the month test.)
    observation({
      geographyId: "PUNGGOL",
      propertyType: "hdb",
      periodId: "month_2026_10",
      count: 0,
      price: null,
      psf: null,
      status: "no-sales",
    }),
    // National, EC — limited display in this release.
    observation({
      geographyId: "SG",
      propertyType: "ec",
      disposition: "limited-display",
      count: 3002,
      price: 1450000,
      psf: 1250,
    }),
    // EC areas, deliberately out of alphabetical order and out of value order.
    observation({
      geographyId: "TAMPINES",
      propertyType: "ec",
      disposition: "limited-display",
      count: 410,
      price: 1510000,
      psf: 1300,
    }),
    observation({
      geographyId: "ANG MO KIO",
      propertyType: "ec",
      disposition: "limited-display",
      count: 120,
      price: 1390000,
      psf: 1200,
    }),
  ],
};

function loadPack(): PeriodPack {
  const parsed = parsePeriodPack(PERIODS_PAYLOAD, SUMMARY_PAYLOAD);
  if (!parsed.ok) {
    throw new Error(`fixture pack did not parse: ${parsed.errors.join("; ")}`);
  }
  return parsed.pack;
}

const PACK = loadPack();

function ids(rows: ExplorerRow[]): string[] {
  return rows.map((row) => row.areaId);
}

function build(
  overrides: Partial<Parameters<typeof buildPackExplorerDataset>[0]> = {},
) {
  const result = buildPackExplorerDataset({
    pack: PACK,
    generation: "test-generation",
    periodId: "ttm_2026_10",
    property: "hdb",
    minSales: 150,
    search: "",
    sort: "median_price",
    direction: "asc",
    ...overrides,
  });
  if (!result.ok) throw new Error(`expected a dataset: ${result.reason}`);
  return result.dataset;
}

describe("buildPackExplorerDataset — published window", () => {
  test("builds rows from the pack, never from the national scope", () => {
    const dataset = build();

    expect(dataset.kind).toBe("pack");
    expect(dataset.periodId).toBe("ttm_2026_10");
    expect(dataset.period).toBe("ttm_2026_10");
    expect(dataset.label).toBe("12 months to 2026-10");
    expect(dataset.generation).toBe("test-generation");
    expect(dataset.totalAreas).toBe(4);
    expect(ids(dataset.rows)).not.toContain("SG");
    expect(dataset.rows[0]?.sectionLabel).toBe("12 months to 2026-10");
    expect(dataset.rows[0]?.observation).toBeUndefined();
    expect(dataset.rows[0]?.packObservation?.geographyId).toBeDefined();
  });

  test("carries the pack's own national baseline, with its disposition note", () => {
    const hdb = build();
    const national = hdb.national;
    if (national === null) throw new Error("expected a national baseline");

    expect(
      national.find((entry) => entry.metric === "median_price")?.value,
    ).toBe(633999);
    expect(national.find((entry) => entry.metric === "volume")?.value).toBe(
      21801,
    );
    expect(national[0]?.source).toBe(
      "observed pack · SG · 12 months to 2026-10",
    );
    expect(national[0]?.note).toBeNull();

    const ec = build({ property: "ec" });
    expect(ec.national?.[0]?.note).toContain("Coverage is limited");
  });

  test("the thin-sample rule reads the joint volume", () => {
    const dataset = build();

    expect(dataset.thinCount).toBe(2);
    expect(ids(dataset.filtered)).toEqual(["ANG MO KIO", "BEDOK"]);
    expect(ids(dataset.rows)).toContain("BUKIT TIMAH");
    expect(ids(dataset.rows)).toContain("DOWNTOWN CORE");
  });

  test("a verified no-sales window is a real zero, not a missing row", () => {
    const dataset = build({ minSales: null });
    const downtown = dataset.rows.find((row) => row.areaId === "DOWNTOWN CORE");
    if (downtown === undefined) throw new Error("expected the no-sales row");

    expect(downtown.volume).toBe(0);
    expect(downtown.medianPrice).toBeNull();
    expect(downtown.medianPsf).toBeNull();
    expect(downtown.packObservation?.status).toBe("no-sales");
  });

  test("nulls sort last in both directions", () => {
    const asc = build({
      minSales: null,
      sort: "median_price",
      direction: "asc",
    });
    const desc = build({
      minSales: null,
      sort: "median_price",
      direction: "desc",
    });

    expect(ids(asc.rows)).toEqual([
      "ANG MO KIO",
      "BEDOK",
      "BUKIT TIMAH",
      "DOWNTOWN CORE",
    ]);
    expect(ids(desc.rows)).toEqual([
      "BUKIT TIMAH",
      "BEDOK",
      "ANG MO KIO",
      "DOWNTOWN CORE",
    ]);
  });

  test("search still narrows the rows", () => {
    const dataset = build({ minSales: null, search: "bed" });
    expect(ids(dataset.filtered)).toEqual(["BEDOK"]);
    expect(dataset.totalAreas).toBe(4);
  });

  test("a window with no area rows is empty, not a fallback to another window", () => {
    const dataset = build({
      periodId: "month_2026_10",
      property: "hdb",
      minSales: null,
    });

    expect(dataset.totalAreas).toBe(1);
    expect(ids(dataset.rows)).toEqual(["PUNGGOL"]);
    expect(dataset.rows[0]?.volume).toBe(0);
    expect(dataset.national).toBeNull();
  });
});

describe("buildPackExplorerDataset — ranking gate", () => {
  test("a publish scope is rankable and orders by value", () => {
    const dataset = build({ sort: "volume", direction: "desc" });
    expect(dataset.rankable).toBe(true);
    expect(ids(dataset.rows)).toEqual([
      "BEDOK",
      "ANG MO KIO",
      "BUKIT TIMAH",
      "DOWNTOWN CORE",
    ]);
  });

  test("a limited-display scope keeps its values but is never ranked", () => {
    const dataset = build({
      property: "ec",
      minSales: null,
      sort: "median_price",
      direction: "desc",
    });

    expect(dataset.rankable).toBe(false);
    // Name order, not price order: Tampines is dearer but comes second.
    expect(ids(dataset.rows)).toEqual(["ANG MO KIO", "TAMPINES"]);
    expect(dataset.rows[1]?.medianPrice).toBe(1510000);
    // The threshold and the search still apply, they just do not rank.
    expect(build({ property: "ec" }).thinCount).toBe(1);
  });
});

describe("buildPackExplorerDataset — unpublished and malformed ids", () => {
  test("an unpublished but well-formed id is reported, not substituted", () => {
    const result = buildPackExplorerDataset({
      pack: PACK,
      generation: "test-generation",
      periodId: "ttm_2026_07",
      property: "hdb",
      minSales: null,
      search: "",
      sort: "median_price",
      direction: "asc",
    });

    if (result.ok) throw new Error("expected the id to be unavailable");
    expect(result.period).toBe("ttm_2026_07");
    expect(result.reason).toContain("ttm_2026_07");
    expect(result.reason).toContain("month_2026_10");
    expect(result.reason).toContain("ttm_2026_10");
  });

  test("a malformed id is rejected before the pack is consulted", () => {
    const result = buildPackExplorerDataset({
      pack: PACK,
      generation: "test-generation",
      periodId: "latest",
      property: "hdb",
      minSales: null,
      search: "",
      sort: "median_price",
      direction: "asc",
    });

    if (result.ok) throw new Error("expected the alias to be rejected");
    expect(result.reason).toContain("latest");
  });
});

describe("publishedPeriodOptions", () => {
  test("offers every published concrete id, legacy-shadowed ids excluded", () => {
    expect(publishedPeriodOptions(PACK)).toEqual([
      { value: "month_2026_10", label: "2026-10 (one month)" },
      { value: "ttm_2026_10", label: "12 months to 2026-10" },
    ]);
  });

  test("period labels resolve through the pack, or not at all", () => {
    expect(packPeriodLabel(PACK, "ttm_2026_10")).toBe("12 months to 2026-10");
    expect(packPeriodLabel(PACK, "ttm_2026_07")).toBeNull();
  });
});

/**
 * RF10: a rolling-quarter row carries its prior-year comparison and the D05
 * verdict. The pack here is a literal, so the test states the arithmetic it
 * expects instead of leaning on a published snapshot that a republish changes.
 */
describe("buildPackExplorerDataset — activity column", () => {
  const QUARTER = "rolling3_2026_10";
  const PRIOR = "rolling3_2025_10";

  function observation(
    geographyId: string,
    propertyType: PropertyTypeId,
    periodId: string,
    count: number | null,
    disposition: "publish" | "limited-display" = "publish",
  ) {
    return {
      geographyId,
      propertyType,
      periodId,
      status: count === null ? ("no-sales" as const) : ("available" as const),
      disposition,
      coverage: { months: [], requestedMonths: 3 },
      metrics: {
        transactionCount: {
          value: count,
          unit: "transactions",
          observations: count ?? 0,
        },
        medianPrice: {
          value: count === null ? null : 500000,
          unit: "SGD",
          observations: 0,
        },
        medianPsf: {
          value: count === null ? null : 600,
          unit: "SGD_PSF",
          observations: 0,
        },
      },
    };
  }

  function period(id: string, comparatorId: string | null) {
    return {
      id,
      kind: "rolling3" as const,
      startMonth: id === QUARTER ? "2026-08" : "2025-08",
      endMonth: id === QUARTER ? "2026-10" : "2025-10",
      months:
        id === QUARTER
          ? ["2026-08", "2026-09", "2026-10"]
          : ["2025-08", "2025-09", "2025-10"],
      label: id === QUARTER ? "2026-08 → 2026-10" : "2025-08 → 2025-10",
      comparatorId,
    };
  }

  function packWith(
    comparatorId: string | null,
    includePrior = true,
  ): PeriodPack {
    const periods = [period(QUARTER, comparatorId)];
    if (includePrior) periods.push(period(PRIOR, null));
    const observations = [
      observation("SG", "hdb", QUARTER, 500),
      observation("ELIGIBLE", "hdb", QUARTER, 300),
      observation("THIN", "hdb", QUARTER, 20),
      observation("SG", "ec", QUARTER, 300, "limited-display"),
      observation("ELIGIBLE", "ec", QUARTER, 250, "limited-display"),
    ];
    if (includePrior) {
      observations.push(
        observation("SG", "hdb", PRIOR, 400),
        observation("ELIGIBLE", "hdb", PRIOR, 200),
        observation("THIN", "hdb", PRIOR, 10),
        observation("SG", "ec", PRIOR, 200, "limited-display"),
        observation("ELIGIBLE", "ec", PRIOR, 200, "limited-display"),
      );
    }
    return {
      schemaVersion: V2_SCHEMA_VERSION,
      methodVersion: "observed-aggregates-2",
      cutoffMonth: "2026-10",
      cutoffSource: "test",
      periods,
      observations,
      periodsById: new Map(periods.map((entry) => [entry.id, entry])),
      observationsByKey: new Map(
        observations.map((entry) => [
          `${entry.geographyId}|${entry.propertyType}|${entry.periodId}`,
          entry,
        ]),
      ),
    };
  }

  test("an eligible area carries both denominators and the signed change", () => {
    const result = buildPackExplorerDataset({
      pack: packWith(PRIOR),
      generation: "test-generation",
      periodId: QUARTER as never,
      property: "hdb",
      minSales: null,
      search: "",
      sort: "volume",
      direction: "desc",
    });
    if (!result.ok) throw new Error(result.reason);

    const eligible = result.dataset.rows.find(
      (row) => row.areaId === "ELIGIBLE",
    )!;
    expect(eligible.activity).toEqual({
      priorCount: 200,
      changePercent: 50,
      reason: null,
      eligible: true,
    });

    const thin = result.dataset.rows.find((row) => row.areaId === "THIN")!;
    expect(thin.activity?.priorCount).toBe(10);
    expect(thin.activity?.changePercent).toBe(100);
    expect(thin.activity?.eligible).toBe(false);
  });

  test("a limited-display scope shows activity but is still never ranked", () => {
    const result = buildPackExplorerDataset({
      pack: packWith(PRIOR),
      generation: "test-generation",
      periodId: QUARTER as never,
      property: "ec",
      minSales: null,
      search: "",
      sort: "median_price",
      direction: "desc",
    });
    if (!result.ok) throw new Error(result.reason);

    expect(result.dataset.rankable).toBe(false);
    expect(result.dataset.rows[0]?.activity?.changePercent).toBe(25);
    expect(result.dataset.rows[0]?.activity?.eligible).toBe(true);
  });

  test("a window with no comparator carries no activity, not a zero change", () => {
    const result = buildPackExplorerDataset({
      pack: packWith(null, false),
      generation: "test-generation",
      periodId: QUARTER as never,
      property: "hdb",
      minSales: null,
      search: "",
      sort: "volume",
      direction: "desc",
    });
    if (!result.ok) throw new Error(result.reason);

    for (const row of result.dataset.rows) {
      expect(row.activity).toBeNull();
    }
  });

  test("a missing prior-year observation states the reason", () => {
    const pack = packWith(PRIOR, true);
    // Drop the prior-year row for THIN, leaving the comparator period present.
    const observations = pack.observations.filter(
      (entry) => !(entry.geographyId === "THIN" && entry.periodId === PRIOR),
    );
    const trimmed: PeriodPack = {
      ...pack,
      observations,
      observationsByKey: new Map(
        observations.map((entry) => [
          `${entry.geographyId}|${entry.propertyType}|${entry.periodId}`,
          entry,
        ]),
      ),
    };

    const result = buildPackExplorerDataset({
      pack: trimmed,
      generation: "test-generation",
      periodId: QUARTER as never,
      property: "hdb",
      minSales: null,
      search: "",
      sort: "volume",
      direction: "desc",
    });
    if (!result.ok) throw new Error(result.reason);

    const thin = result.dataset.rows.find((row) => row.areaId === "THIN")!;
    expect(thin.activity?.changePercent).toBeNull();
    expect(thin.activity?.priorCount).toBeNull();
    expect(thin.activity?.reason).toContain(
      "no prior-year-quarter observation",
    );
  });
});
