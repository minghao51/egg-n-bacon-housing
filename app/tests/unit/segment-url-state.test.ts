/**
 * Unit tests for the segment workspace URL contract
 * (src/components/dashboard/segments/lib/segment-url-state.ts).
 *
 * The five pre-S7 IDs (`persona`, `tab`, `segment`, `segments`, `area`) must
 * survive both entry points; the visible constraints are versioned behind
 * `fv=1`, so an old link keeps persona-preset semantics.
 */

import { describe, expect, test } from "bun:test";

import {
  applySegmentQuery,
  defaultSegmentQueryState,
  parseSegmentQuery,
  serializeSegmentQuery,
  SEGMENT_COMPARISON_MAX,
  SEGMENT_QUERY_KEYS,
  type SegmentQueryState,
} from "../../src/components/dashboard/segments/lib/segment-url-state";
import {
  filtersDifferFromPreset,
  presetFilters,
} from "../../src/components/dashboard/segments/lib/segment-presets";

const SEGMENT_IDS = [
  "large_size_stable",
  "high_growth_recent",
  "speculator_hotspots",
  "declining_areas",
  "mid_tier_value",
  "premium_new_units",
];

function roundTrip(state: SegmentQueryState): SegmentQueryState {
  return parseSegmentQuery(serializeSegmentQuery(state), {
    knownSegmentIds: SEGMENT_IDS,
  });
}

describe("parseSegmentQuery", () => {
  test("an empty query string is the documented default", () => {
    expect(parseSegmentQuery("")).toEqual(defaultSegmentQueryState());
    expect(parseSegmentQuery("?")).toEqual(defaultSegmentQueryState());
  });

  test("keeps the five legacy IDs", () => {
    const state = parseSegmentQuery(
      "?persona=investor&tab=investigate&segment=large_size_stable&segments=large_size_stable,high_growth_recent&area=bishan",
      { knownSegmentIds: SEGMENT_IDS },
    );

    expect(state.persona).toBe("investor");
    expect(state.tab).toBe("investigate");
    expect(state.segmentId).toBe("large_size_stable");
    expect(state.comparisonIds).toEqual([
      "large_size_stable",
      "high_growth_recent",
    ]);
    expect(state.area).toBe("BISHAN");
  });

  test("unknown or malformed values fall back without throwing", () => {
    const state = parseSegmentQuery(
      "?persona=landlord&tab=forecast&segment=ghost_segment&segments=&area=",
      { knownSegmentIds: SEGMENT_IDS },
    );

    expect(state.persona).toBe("all");
    expect(state.tab).toBe("discover");
    expect(state.segmentId).toBeNull();
    expect(state.comparisonIds).toEqual([]);
    expect(state.area).toBeNull();
  });

  test("drops unknown segment IDs only when the known list is supplied", () => {
    const withKnown = parseSegmentQuery(
      "?segment=ghost&segments=ghost,mid_tier_value",
      {
        knownSegmentIds: SEGMENT_IDS,
      },
    );
    expect(withKnown.segmentId).toBeNull();
    expect(withKnown.comparisonIds).toEqual(["mid_tier_value"]);

    const withoutKnown = parseSegmentQuery("?segment=ghost");
    expect(withoutKnown.segmentId).toBe("ghost");
  });

  test("de-duplicates and caps the shortlist at four, keeping order", () => {
    const state = parseSegmentQuery(
      `?segments=${SEGMENT_IDS.join(",")},${SEGMENT_IDS[0]}`,
      { knownSegmentIds: SEGMENT_IDS },
    );
    expect(state.comparisonIds).toEqual(
      SEGMENT_IDS.slice(0, SEGMENT_COMPARISON_MAX),
    );
  });

  test("ignores constraints without the version tag", () => {
    const state = parseSegmentQuery(
      "?persona=first-time-buyer&psf=300-400&types=EC&regions=CCR&hotspot=HH",
    );
    expect(state.filters).toEqual(presetFilters("first-time-buyer"));
  });

  test("applies versioned constraints over the persona preset", () => {
    const state = parseSegmentQuery(
      "?persona=upgrader&fv=1&psf=600-900&types=EC,HDB&regions=OCR&hotspot=LL",
    );
    expect(state.filters.budgetRange).toEqual([600, 900]);
    expect(state.filters.propertyTypes).toEqual(["EC", "HDB"]);
    expect(state.filters.locations).toEqual(["OCR"]);
    expect(state.filters.hotspotFilter).toBe("LL");
    // Fields the panel does not expose keep the persona preset.
    expect(state.filters.investmentGoal).toBe("balanced");
  });

  test("invalid constraint values fall back field by field", () => {
    const state = parseSegmentQuery(
      "?persona=all&fv=1&psf=1000-400&types=Nope&regions=CCR&hotspot=ZZ",
    );
    expect(state.filters.budgetRange).toEqual([400, 1000]);
    expect(state.filters.propertyTypes).toEqual(["HDB", "Condominium", "EC"]);
    expect(state.filters.locations).toEqual(["CCR"]);
    expect(state.filters.hotspotFilter).toBe("all");
  });

  test("out-of-range PSF bounds are rejected rather than clamped", () => {
    const state = parseSegmentQuery("?fv=1&psf=200-1000");
    expect(state.filters.budgetRange).toEqual([400, 1000]);
  });
});

describe("serializeSegmentQuery", () => {
  test("omits defaults", () => {
    expect(serializeSegmentQuery(defaultSegmentQueryState())).toBe("");
  });

  test("writes only non-default IDs", () => {
    const query = serializeSegmentQuery({
      persona: "investor",
      tab: "compare",
      segmentId: "mid_tier_value",
      comparisonIds: ["large_size_stable", "mid_tier_value"],
      area: "BISHAN",
      filters: presetFilters("investor"),
    });
    const params = new URLSearchParams(query);
    expect(params.get("persona")).toBe("investor");
    expect(params.get("tab")).toBe("compare");
    expect(params.get("segment")).toBe("mid_tier_value");
    expect(params.get("segments")).toBe("large_size_stable,mid_tier_value");
    expect(params.get("area")).toBe("BISHAN");
    // A persona link stays short: the preset is not re-encoded as constraints.
    expect(params.get("fv")).toBeNull();
  });

  test("round-trips a selection with constraints", () => {
    const start: SegmentQueryState = {
      persona: "first-time-buyer",
      tab: "investigate",
      segmentId: "mid_tier_value",
      comparisonIds: ["declining_areas", "mid_tier_value"],
      area: "LIM CHU KANG",
      filters: {
        ...presetFilters("first-time-buyer"),
        budgetRange: [450, 550],
        propertyTypes: ["HDB", "EC"],
        locations: ["OCR"],
        hotspotFilter: "LL",
      },
    };

    const parsed = roundTrip(start);
    expect(parsed.persona).toBe(start.persona);
    expect(parsed.tab).toBe(start.tab);
    expect(parsed.segmentId).toBe(start.segmentId);
    expect(parsed.comparisonIds).toEqual(start.comparisonIds);
    expect(parsed.area).toBe(start.area);
    expect(parsed.filters.budgetRange).toEqual([450, 550]);
    expect(parsed.filters.propertyTypes).toEqual(["HDB", "EC"]);
    expect(parsed.filters.locations).toEqual(["OCR"]);
    expect(parsed.filters.hotspotFilter).toBe("LL");
  });

  test("reset to persona settings stops emitting constraints", () => {
    const withConstraints: SegmentQueryState = {
      ...defaultSegmentQueryState(),
      filters: { ...presetFilters("all"), budgetRange: [500, 700] },
    };
    expect(filtersDifferFromPreset(withConstraints.filters, "all")).toBe(true);
    expect(
      new URLSearchParams(serializeSegmentQuery(withConstraints)).get("fv"),
    ).toBe("1");

    const reset: SegmentQueryState = {
      ...withConstraints,
      filters: presetFilters("all"),
    };
    expect(serializeSegmentQuery(reset)).toBe("");
  });
});

describe("applySegmentQuery", () => {
  test("replaces its own keys and keeps parameters owned by others", () => {
    const href =
      "https://example.test/egg-n-bacon-housing/research/segments?persona=investor&tab=compare&utm_source=notes&segments=ghost";

    const next = new URL(
      applySegmentQuery(href, {
        ...defaultSegmentQueryState(),
        persona: "upgrader",
      }),
    );

    expect(next.searchParams.get("persona")).toBe("upgrader");
    expect(next.searchParams.get("utm_source")).toBe("notes");
    // Stale keys of ours are removed, not left behind.
    expect(next.searchParams.get("tab")).toBeNull();
    expect(next.searchParams.get("segments")).toBeNull();
    expect(next.pathname).toBe("/egg-n-bacon-housing/research/segments");
  });

  test("every owned key is removable", () => {
    const populated = SEGMENT_QUERY_KEYS.map((key) => `${key}=x`).join("&");
    const next = new URL(
      applySegmentQuery(
        `https://example.test/research/segments?${populated}`,
        defaultSegmentQueryState(),
      ),
    );
    SEGMENT_QUERY_KEYS.forEach((key) =>
      expect(next.searchParams.get(key)).toBeNull(),
    );
  });

  test("an unparseable href is returned untouched", () => {
    expect(applySegmentQuery("not a url", defaultSegmentQueryState())).toBe(
      "not a url",
    );
  });
});
