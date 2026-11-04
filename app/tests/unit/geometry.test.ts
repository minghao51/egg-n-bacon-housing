import { describe, expect, test } from "bun:test";
import { planningAreaName, samePlanningArea } from "../../src/utils/geometry";

describe("planningAreaName", () => {
  test("reads the uppercase PLN_AREA_N key served by planning_areas.geojson", () => {
    expect(planningAreaName({ PLN_AREA_N: "BISHAN" })).toBe("BISHAN");
  });

  test("reads the lowercase pln_area_n key written by some exporters", () => {
    expect(planningAreaName({ pln_area_n: "bishan" })).toBe("BISHAN");
  });

  test("prefers PLN_AREA_N when both casings are present", () => {
    expect(
      planningAreaName({ PLN_AREA_N: "TAMPINES", pln_area_n: "bedok" }),
    ).toBe("TAMPINES");
  });

  test("returns null when no name key is present", () => {
    expect(planningAreaName({ REGION_N: "EAST REGION" })).toBeNull();
  });

  test("returns null for an empty string value", () => {
    expect(planningAreaName({ PLN_AREA_N: "" })).toBeNull();
  });

  test("returns null for a whitespace-only value", () => {
    expect(planningAreaName({ pln_area_n: "   " })).toBeNull();
  });

  test("returns null for non-string values", () => {
    expect(planningAreaName({ PLN_AREA_N: 42 })).toBeNull();
    expect(planningAreaName({ PLN_AREA_N: null })).toBeNull();
    expect(planningAreaName({ PLN_AREA_N: { name: "BISHAN" } })).toBeNull();
  });

  test("returns null when properties are absent or not an object", () => {
    expect(planningAreaName(undefined)).toBeNull();
    expect(planningAreaName(null)).toBeNull();
    expect(planningAreaName("BISHAN")).toBeNull();
  });

  test("trims and uppercases the published name", () => {
    expect(planningAreaName({ PLN_AREA_N: "  ang mo kio  " })).toBe(
      "ANG MO KIO",
    );
  });

  test("tolerates prefixed keys", () => {
    expect(planningAreaName({ source_pln_area_n: "queenstown" })).toBe(
      "QUEENSTOWN",
    );
    expect(planningAreaName({ "properties.PLN_AREA_N": "woodlands" })).toBe(
      "WOODLANDS",
    );
  });

  test("falls through an empty preferred key to a populated variant", () => {
    expect(planningAreaName({ PLN_AREA_N: "", pln_area_n: "serangoon" })).toBe(
      "SERANGOON",
    );
  });
});

describe("samePlanningArea", () => {
  test("matches names that differ only by case", () => {
    expect(samePlanningArea("Bishan", "BISHAN")).toBe(true);
  });

  test("matches names that differ only by surrounding whitespace", () => {
    expect(samePlanningArea("  bishan ", "BISHAN")).toBe(true);
  });

  test("rejects different areas", () => {
    expect(samePlanningArea("BISHAN", "BEDOK")).toBe(false);
  });

  test("never matches when either side is null", () => {
    expect(samePlanningArea(null, "BISHAN")).toBe(false);
    expect(samePlanningArea("BISHAN", null)).toBe(false);
    expect(samePlanningArea(null, null)).toBe(false);
  });

  test("never matches when either side is empty", () => {
    expect(samePlanningArea("", "BISHAN")).toBe(false);
    expect(samePlanningArea("   ", "   ")).toBe(false);
  });
});
