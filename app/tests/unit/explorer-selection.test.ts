/**
 * Unit tests for the validated explorer query state
 * (src/utils/explorer-selection.ts).
 *
 * Hermetic: no fixtures, no DOM, no `window`. Every case is a query string in
 * and a selection out, so a hand-edited deep link cannot silently change scope.
 */

import { describe, expect, test } from "bun:test";

import {
  EXPLORER_DEFAULTS,
  THIN_SAMPLE_THRESHOLD,
  parseExplorerSelection,
  serializeExplorerSelection,
  withSelection,
  type ExplorerSelection,
} from "../../src/utils/explorer-selection";

const FULL: ExplorerSelection = {
  property: "condo",
  period: "pre_covid",
  metric: "median_psf",
  sort: "volume",
  direction: "desc",
  minSales: 250,
  search: "marine parade",
  area: "MARINE PARADE",
  page: 3,
};

describe("EXPLORER_DEFAULTS", () => {
  test("is 2025 HDB at the thin-sample threshold, cheapest first", () => {
    expect(EXPLORER_DEFAULTS).toEqual({
      property: "hdb",
      period: "year_2025",
      metric: "median_price",
      sort: "median_price",
      direction: "asc",
      minSales: 150,
      search: "",
      area: null,
      page: 1,
    });
    expect(THIN_SAMPLE_THRESHOLD).toBe(150);
    expect(EXPLORER_DEFAULTS.minSales).toBe(THIN_SAMPLE_THRESHOLD);
  });
});

describe("parseExplorerSelection", () => {
  test("an empty query is the defaults", () => {
    expect(parseExplorerSelection("")).toEqual(EXPLORER_DEFAULTS);
    expect(parseExplorerSelection("?")).toEqual(EXPLORER_DEFAULTS);
    expect(parseExplorerSelection("   ")).toEqual(EXPLORER_DEFAULTS);
  });

  test("round-trips the defaults through an empty query string", () => {
    const params = serializeExplorerSelection(EXPLORER_DEFAULTS);
    expect(params.toString()).toBe("");
    expect(parseExplorerSelection(params.toString())).toEqual(
      EXPLORER_DEFAULTS,
    );
    expect(parseExplorerSelection(`?${params.toString()}`)).toEqual(
      EXPLORER_DEFAULTS,
    );
  });

  test("round-trips a non-default selection", () => {
    const params = serializeExplorerSelection(FULL);
    expect(parseExplorerSelection(params.toString())).toEqual(FULL);
    expect(parseExplorerSelection(`?${params.toString()}`)).toEqual(FULL);
  });

  test("accepts a full URL and a bare query string", () => {
    expect(
      parseExplorerSelection(
        "https://example.test/explore?property=ec&period=recent&page=2",
      ),
    ).toEqual({
      ...EXPLORER_DEFAULTS,
      property: "ec",
      period: "recent",
      page: 2,
    });
    expect(parseExplorerSelection("property=ec&period=recent&page=2")).toEqual({
      ...EXPLORER_DEFAULTS,
      property: "ec",
      period: "recent",
      page: 2,
    });
  });

  test("a bare query string is never split on a question mark inside a value", () => {
    expect(parseExplorerSelection("search=what?now").search).toBe("what?now");
    expect(parseExplorerSelection("?search=what?now").search).toBe("what?now");
  });

  test("unknown values fall back to the default, never to another valid value", () => {
    const selection = parseExplorerSelection(
      "?property=landed&period=2024&metric=yield&sort=yield&direction=sideways",
    );

    expect(selection).toEqual(EXPLORER_DEFAULTS);
    expect(selection.property).toBe("hdb");
    expect(selection.period).toBe("year_2025");
    expect(selection.metric).toBe("median_price");
    expect(selection.sort).toBe("median_price");
    expect(selection.direction).toBe("asc");
  });

  test("a partially valid query keeps only the valid parts", () => {
    expect(
      parseExplorerSelection("?property=condo&metric=yield&direction=desc"),
    ).toEqual({
      ...EXPLORER_DEFAULTS,
      property: "condo",
      direction: "desc",
    });
  });

  test("minSales=all means no threshold", () => {
    expect(parseExplorerSelection("?minSales=all").minSales).toBeNull();
    expect(
      serializeExplorerSelection({ ...EXPLORER_DEFAULTS, minSales: null }).get(
        "minSales",
      ),
    ).toBe("all");
    expect(
      parseExplorerSelection(
        serializeExplorerSelection({
          ...EXPLORER_DEFAULTS,
          minSales: null,
        }).toString(),
      ).minSales,
    ).toBeNull();
  });

  test("minSales accepts only a non-negative integer and clamps at 100000", () => {
    expect(parseExplorerSelection("?minSales=0").minSales).toBe(0);
    expect(parseExplorerSelection("?minSales=75").minSales).toBe(75);
    expect(parseExplorerSelection("?minSales=100000").minSales).toBe(100000);
    expect(parseExplorerSelection("?minSales=100001").minSales).toBe(100000);
    expect(parseExplorerSelection("?minSales=999999999").minSales).toBe(100000);
    expect(parseExplorerSelection("?minSales=-5").minSales).toBe(150);
    expect(parseExplorerSelection("?minSales=1.5").minSales).toBe(150);
    expect(parseExplorerSelection("?minSales=").minSales).toBe(150);
    expect(parseExplorerSelection("?minSales=lots").minSales).toBe(150);
  });

  test("page is an integer of at least 1", () => {
    expect(parseExplorerSelection("?page=2").page).toBe(2);
    expect(parseExplorerSelection("?page=0").page).toBe(1);
    expect(parseExplorerSelection("?page=-3").page).toBe(1);
    expect(parseExplorerSelection("?page=1.5").page).toBe(1);
    expect(parseExplorerSelection("?page=two").page).toBe(1);
  });

  test("search is trimmed and capped at 80 characters", () => {
    expect(parseExplorerSelection("?search=%20%20tampines%20").search).toBe(
      "tampines",
    );
    expect(parseExplorerSelection("?search=").search).toBe("");

    const long = "a".repeat(120);
    expect(parseExplorerSelection(`?search=${long}`).search).toHaveLength(80);
    expect(parseExplorerSelection(`?search=${long}`).search).toBe(
      "a".repeat(80),
    );
  });

  test("area is trimmed and uppercased, or null", () => {
    expect(parseExplorerSelection("?area=%20tampines%20").area).toBe(
      "TAMPINES",
    );
    expect(parseExplorerSelection("?area=").area).toBeNull();
    expect(parseExplorerSelection("?area=%20%20").area).toBeNull();
    expect(EXPLORER_DEFAULTS.area).toBeNull();
  });

  test("tolerates malformed percent-encoding without throwing", () => {
    expect(() => parseExplorerSelection("?search=%zz")).not.toThrow();
    expect(parseExplorerSelection("?search=%zz").search).toBe("%zz");
    expect(() => parseExplorerSelection("?area=%")).not.toThrow();
    expect(parseExplorerSelection("?area=%").area).toBe("%");

    const broken = parseExplorerSelection("?search=%E0%A4%A&property=hdb");
    expect(typeof broken.search).toBe("string");
    expect(broken.property).toBe("hdb");
  });
});

describe("serializeExplorerSelection", () => {
  test("omits every default value", () => {
    expect(serializeExplorerSelection(EXPLORER_DEFAULTS).toString()).toBe("");
    expect(
      serializeExplorerSelection({ ...EXPLORER_DEFAULTS, page: 1 }).toString(),
    ).toBe("");
  });

  test("writes only the non-default fields, in a stable order", () => {
    expect(serializeExplorerSelection(FULL).toString()).toBe(
      "property=condo&period=pre_covid&metric=median_psf&sort=volume&direction=desc&minSales=250&search=marine+parade&area=MARINE+PARADE&page=3",
    );
  });
});

describe("withSelection", () => {
  test("keeps the page when nothing filtered changes", () => {
    const paged = { ...EXPLORER_DEFAULTS, page: 4 };
    expect(withSelection(paged, {})).toEqual(paged);
    expect(withSelection(paged, { page: 2 }).page).toBe(2);
  });

  test("resets the page when a filter, search, threshold or sort changes", () => {
    const paged = { ...EXPLORER_DEFAULTS, page: 4 };

    expect(withSelection(paged, { property: "condo" }).page).toBe(1);
    expect(withSelection(paged, { period: "whole" }).page).toBe(1);
    expect(withSelection(paged, { metric: "volume" }).page).toBe(1);
    expect(withSelection(paged, { sort: "median_psf" }).page).toBe(1);
    expect(withSelection(paged, { direction: "desc" }).page).toBe(1);
    expect(withSelection(paged, { minSales: 300 }).page).toBe(1);
    expect(withSelection(paged, { minSales: null }).page).toBe(1);
    expect(withSelection(paged, { search: "bedok" }).page).toBe(1);
    expect(withSelection(paged, { area: "BEDOK" }).page).toBe(1);
  });

  test("does not reset when a patched value equals the current one", () => {
    const paged = { ...EXPLORER_DEFAULTS, page: 4 };
    expect(withSelection(paged, { property: "hdb" }).page).toBe(4);
    expect(withSelection(paged, { search: "" }).page).toBe(4);
  });

  test("an explicit page in the same patch wins", () => {
    const paged = { ...EXPLORER_DEFAULTS, page: 4 };
    expect(withSelection(paged, { property: "condo", page: 7 })).toEqual({
      ...EXPLORER_DEFAULTS,
      property: "condo",
      page: 7,
    });
  });

  test("clearing the area works", () => {
    const withArea = { ...EXPLORER_DEFAULTS, area: "TAMPINES" };
    expect(withSelection(withArea, { area: null })).toEqual(EXPLORER_DEFAULTS);
  });
});
