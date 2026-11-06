/**
 * Unit tests for the segment investigation row builder
 * (src/components/dashboard/segments/lib/buildSegmentAreaRows.ts).
 *
 * Hermetic: every fixture is written here. Values are the published archive's
 * stored numbers (Bishan 644 PSF, Serangoon 566, Bukit Timah 500, Marina South
 * 500, Newton 500) so the tests pin the real declared-area behaviour without
 * reading the payload at test time.
 */

import { describe, expect, test } from "bun:test";

import { buildSegmentAreaRows } from "../../src/components/dashboard/segments/lib/buildSegmentAreaRows";
import { presetFilters } from "../../src/components/dashboard/segments/lib/segment-presets";
import type {
  FilterState,
  PlanningArea,
  Segment,
} from "../../src/types/segments";

function makeArea(
  name: string,
  overrides: Partial<PlanningArea> = {},
): PlanningArea {
  return {
    name,
    region: "RCR",
    spatialCluster: "HH",
    hotspotConfidence: "99%",
    persistenceProbability: 0.6,
    mrtPremium: 5.88,
    mrtSensitivity: "moderate",
    cbdDistance: 4.2,
    schoolTier: "mixed",
    schoolPremium: -23.67,
    forecast6m: 4.94,
    avgPricePsf: 644,
    avgYield: 4.95,
    segments: ["large_size_stable"],
    ...overrides,
  };
}

const PLANNING_AREAS: Record<string, PlanningArea> = {
  Bishan: makeArea("Bishan", { avgPricePsf: 644, region: "RCR" }),
  Serangoon: makeArea("Serangoon", { avgPricePsf: 566, region: "RCR" }),
  "Bukit Timah": makeArea("Bukit Timah", {
    avgPricePsf: 500,
    region: "CCR",
    spatialCluster: "LH",
  }),
  "Marina South": makeArea("Marina South", {
    avgPricePsf: 500,
    region: "CCR",
    spatialCluster: "LL",
  }),
  Newton: makeArea("Newton", { avgPricePsf: 500, region: "RCR" }),
  // Published in the archive but **not** declared by the segment below.
  Orchard: makeArea("Orchard", { avgPricePsf: 1200, region: "CCR" }),
};

function makeSegment(overrides: Partial<Segment> = {}): Segment {
  return {
    id: "large_size_stable",
    name: "Large Size Stable",
    description: "fixture",
    investmentType: "yield",
    clusterClassification: "HH",
    persistenceProbability: 0.6,
    metrics: {
      avgPricePsf: 570,
      avgYield: 5.54,
      yoyGrowth: 12,
      transactionCount: 114700,
      marketShare: 0.126,
    },
    characteristics: {
      priceTier: "premium",
      riskLevel: "low",
      volatility: "low",
      appreciationPotential: "moderate",
    },
    implications: {
      investor: "fixture",
      firstTimeBuyer: "fixture",
      upgrader: "fixture",
    },
    planningAreas: [
      "Bishan",
      "Serangoon",
      "Bukit Timah",
      "Marina South",
      "Newton",
    ],
    regions: ["CCR", "RCR"],
    propertyTypes: ["HDB", "Condominium"],
    spatialClassification: "HH",
    mrtSensitivity: "high",
    schoolQuality: "tier_1",
    riskFactors: [],
    opportunities: [],
    ...overrides,
  };
}

function filters(overrides: Partial<FilterState> = {}): FilterState {
  return { ...presetFilters("all"), ...overrides };
}

describe("buildSegmentAreaRows", () => {
  test("returns only the areas the segment declares", () => {
    const rows = buildSegmentAreaRows(
      makeSegment(),
      PLANNING_AREAS,
      filters(),
      "avgPricePsf",
    );

    expect(rows).toHaveLength(5);
    expect(rows.map((row) => row.planningArea)).not.toContain("Orchard");
    expect(
      rows.every((row) => row.areaKey === row.planningArea.toUpperCase()),
    ).toBe(true);
  });

  test("a declared area missing from the archive is skipped, not invented", () => {
    const segment = makeSegment({
      planningAreas: ["Bishan", "Atlantis"],
    });
    const rows = buildSegmentAreaRows(
      segment,
      PLANNING_AREAS,
      filters(),
      "avgPricePsf",
    );

    expect(rows.map((row) => row.planningArea)).toEqual(["Bishan"]);
  });

  test("sorts by the selected stored field, descending", () => {
    const byPsf = buildSegmentAreaRows(
      makeSegment(),
      PLANNING_AREAS,
      filters(),
      "avgPricePsf",
    );
    expect(byPsf.map((row) => row.avgPricePsf)).toEqual([
      644, 566, 500, 500, 500,
    ]);
    expect(byPsf[0].planningArea).toBe("Bishan");

    const scaled = Object.fromEntries(
      Object.entries(PLANNING_AREAS).map(([name, area]) => [
        name,
        { ...area, forecast6m: area.avgPricePsf === 644 ? 1 : 9 },
      ]),
    );
    const byForecast = buildSegmentAreaRows(
      makeSegment(),
      scaled,
      filters(),
      "forecast6m",
    );
    expect(byForecast[byForecast.length - 1].planningArea).toBe("Bishan");
  });

  test("applies the hard filters: region, spatial class and PSF range", () => {
    const central = buildSegmentAreaRows(
      makeSegment(),
      PLANNING_AREAS,
      filters({ locations: ["CCR"] }),
      "avgPricePsf",
    );
    expect(central.map((row) => row.planningArea).sort()).toEqual([
      "Bukit Timah",
      "Marina South",
    ]);

    const hotspots = buildSegmentAreaRows(
      makeSegment(),
      PLANNING_AREAS,
      filters({ hotspotFilter: "HH" }),
      "avgPricePsf",
    );
    expect(hotspots.map((row) => row.planningArea).sort()).toEqual([
      "Bishan",
      "Newton",
      "Serangoon",
    ]);

    const narrow = buildSegmentAreaRows(
      makeSegment(),
      PLANNING_AREAS,
      filters({ budgetRange: [600, 700] }),
      "avgPricePsf",
    );
    expect(narrow.map((row) => row.planningArea)).toEqual(["Bishan"]);
  });

  test("a property-type mismatch yields no rows instead of a fallback", () => {
    const rows = buildSegmentAreaRows(
      makeSegment({ propertyTypes: ["EC"] }),
      PLANNING_AREAS,
      filters({ propertyTypes: ["HDB"] }),
      "avgPricePsf",
    );
    expect(rows).toEqual([]);
  });

  test("filters that exclude every declared area produce an empty list", () => {
    const rows = buildSegmentAreaRows(
      makeSegment(),
      PLANNING_AREAS,
      filters({ locations: ["OCR"] }),
      "avgPricePsf",
    );
    expect(rows).toEqual([]);
  });
});
