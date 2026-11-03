/**
 * Unit tests for the legacy research-map URL state helpers.
 *
 * Covers the reproduced first-load defect: a request for
 * `/dashboard/map?metric=median_psf&timeBasis=year_2025&propertyType=hdb&area=TAMPINES&layers=spatial.lisa`
 * must survive parsing and re-serialization intact.
 */

import { describe, expect, test } from "bun:test";

import {
  EMPTY_MAP_SELECTION,
  MAP_LAYER_IDS,
  isSameMapSelection,
  mergeMapSelection,
  parseMapSelection,
  serializeMapSelection,
} from "../../src/utils/map-url-state";
import type { MapSelection } from "../../src/utils/map-url-state";

const LEGACY_SEARCH =
  "?metric=median_psf&timeBasis=year_2025&propertyType=hdb&area=TAMPINES&layers=spatial.lisa";

const FULL_SELECTION: MapSelection = {
  metric: "median_psf",
  timeBasis: "year_2025",
  propertyType: "hdb",
  area: "TAMPINES",
  layers: ["spatial.lisa"],
};

describe("parseMapSelection", () => {
  test("round-trips all five groups from the reported URL", () => {
    const selection = parseMapSelection(LEGACY_SEARCH);

    expect(selection.metric).toBe("median_psf");
    expect(selection.timeBasis).toBe("year_2025");
    expect(selection.propertyType).toBe("hdb");
    expect(selection.area).toBe("TAMPINES");
    expect(selection.layers).toEqual(["spatial.lisa"]);
    expect(selection).toEqual(FULL_SELECTION);

    expect(parseMapSelection(serializeMapSelection(selection).toString())).toEqual(
      FULL_SELECTION,
    );
  });

  test("drops values that are not accepted instead of substituting another value", () => {
    const selection = parseMapSelection(
      "?metric=median_rent&timeBasis=year_2030&propertyType=landed",
    );

    expect(selection).toEqual({
      metric: null,
      timeBasis: null,
      propertyType: null,
      area: null,
      layers: [],
    });
    expect(selection.metric).not.toBe("median_price");
  });

  test("keeps known layer ids, drops unknown ids and duplicates, preserves order", () => {
    expect(
      parseMapSelection(
        "?layers=feature.mrt,spatial.lisa,unknown.layer,feature.mrt,spatial.lisa",
      ).layers,
    ).toEqual(["feature.mrt", "spatial.lisa"]);

    expect(
      parseMapSelection("?layers=predictive.lease,spatial.hotspot").layers,
    ).toEqual(["predictive.lease", "spatial.hotspot"]);

    expect(parseMapSelection("?layers=").layers).toEqual([]);
    expect(parseMapSelection("?layers=,,,").layers).toEqual([]);
  });

  test("accepts every layer id declared by the map layer metadata", () => {
    const selection = parseMapSelection(`?layers=${MAP_LAYER_IDS.join(",")}`);

    expect(selection.layers).toEqual([...MAP_LAYER_IDS]);
  });

  test("uppercases and trims the area, and treats a missing area as null", () => {
    expect(parseMapSelection("?area=%20tampines%20").area).toBe("TAMPINES");
    expect(parseMapSelection("?area=Tampines").area).toBe("TAMPINES");
    expect(parseMapSelection("?area=").area).toBeNull();
    expect(parseMapSelection("?metric=volume").area).toBeNull();
  });

  test("tolerates a leading '?', a bare query string, an empty string and broken encoding", () => {
    expect(parseMapSelection("?metric=volume").metric).toBe("volume");
    expect(parseMapSelection("metric=volume").metric).toBe("volume");
    expect(parseMapSelection("")).toEqual(EMPTY_MAP_SELECTION);
    expect(parseMapSelection("?")).toEqual(EMPTY_MAP_SELECTION);

    expect(() => parseMapSelection("%")).not.toThrow();
    expect(() =>
      parseMapSelection("?metric=%zz&area=%E0%A4%A&layers=%%"),
    ).not.toThrow();
    expect(parseMapSelection("?metric=%zz").metric).toBeNull();
    expect(parseMapSelection("?area=%E0%A4%A&metric=volume").metric).toBe(
      "volume",
    );
  });

  test("ignores unknown query keys", () => {
    const selection = parseMapSelection(
      "?metric=volume&persona=investor&tab=map",
    );

    expect(selection.metric).toBe("volume");
    expect(selection.timeBasis).toBeNull();
    expect(selection.propertyType).toBeNull();
    expect(selection.area).toBeNull();
    expect(selection.layers).toEqual([]);
  });
});

describe("serializeMapSelection", () => {
  test("omits null and empty groups", () => {
    const params = serializeMapSelection({
      metric: "volume",
      timeBasis: null,
      propertyType: null,
      area: null,
      layers: [],
    });

    expect(params.toString()).toBe("metric=volume");
    expect(params.has("timeBasis")).toBe(false);
    expect(params.has("propertyType")).toBe(false);
    expect(params.has("area")).toBe(false);
    expect(params.has("layers")).toBe(false);
  });

  test("never emits area=null or layers=", () => {
    const params = serializeMapSelection({
      metric: null,
      timeBasis: null,
      propertyType: null,
      area: null,
      layers: [],
    });

    expect(params.toString()).toBe("");
    expect(params.toString()).not.toContain("null");
    expect(params.has("layers")).toBe(false);

    expect(serializeMapSelection({}).toString()).toBe("");
  });

  test("writes the full selection in a stable key order", () => {
    expect(serializeMapSelection(FULL_SELECTION).toString()).toBe(
      "metric=median_psf&timeBasis=year_2025&propertyType=hdb&area=TAMPINES&layers=spatial.lisa",
    );
  });

  test("uppercases and trims the area", () => {
    expect(serializeMapSelection({ area: "  tampines " }).get("area")).toBe(
      "TAMPINES",
    );
  });

  test("joins multiple layers with a comma", () => {
    expect(
      serializeMapSelection({ layers: ["spatial.lisa", "feature.mrt"] }).get(
        "layers",
      ),
    ).toBe("spatial.lisa,feature.mrt");
  });
});

describe("mergeMapSelection", () => {
  test("keeps base values when the incoming groups are absent or null", () => {
    expect(mergeMapSelection(FULL_SELECTION, {})).toEqual(FULL_SELECTION);
    expect(
      mergeMapSelection(FULL_SELECTION, {
        metric: null,
        timeBasis: null,
        propertyType: null,
        area: null,
        layers: undefined,
      }),
    ).toEqual(FULL_SELECTION);
  });

  test("applies incoming values and clears layers only for an explicit empty array", () => {
    expect(mergeMapSelection(FULL_SELECTION, { metric: "volume" }).metric).toBe(
      "volume",
    );
    expect(
      mergeMapSelection(FULL_SELECTION, { layers: [] }).layers,
    ).toEqual([]);
    expect(
      mergeMapSelection(FULL_SELECTION, { layers: ["feature.mrt"] }).layers,
    ).toEqual(["feature.mrt"]);
  });

  test("does not alias the base layer array", () => {
    const merged = mergeMapSelection(FULL_SELECTION, {});

    expect(merged.layers).toEqual(FULL_SELECTION.layers);
    expect(merged.layers).not.toBe(FULL_SELECTION.layers);
  });
});

describe("isSameMapSelection", () => {
  test("compares layer lists order-insensitively", () => {
    const a: MapSelection = {
      ...FULL_SELECTION,
      layers: ["spatial.lisa", "feature.mrt"],
    };
    const b: MapSelection = {
      ...FULL_SELECTION,
      layers: ["feature.mrt", "spatial.lisa"],
    };

    expect(isSameMapSelection(a, b)).toBe(true);
    expect(isSameMapSelection(FULL_SELECTION, FULL_SELECTION)).toBe(true);
  });

  test("detects differences in any group", () => {
    expect(
      isSameMapSelection(FULL_SELECTION, {
        ...FULL_SELECTION,
        metric: "volume",
      }),
    ).toBe(false);
    expect(
      isSameMapSelection(FULL_SELECTION, {
        ...FULL_SELECTION,
        timeBasis: "whole",
      }),
    ).toBe(false);
    expect(
      isSameMapSelection(FULL_SELECTION, {
        ...FULL_SELECTION,
        propertyType: "all",
      }),
    ).toBe(false);
    expect(
      isSameMapSelection(FULL_SELECTION, { ...FULL_SELECTION, area: null }),
    ).toBe(false);
    expect(
      isSameMapSelection(FULL_SELECTION, { ...FULL_SELECTION, layers: [] }),
    ).toBe(false);
    expect(
      isSameMapSelection(FULL_SELECTION, {
        ...FULL_SELECTION,
        layers: ["spatial.lisa", "feature.mrt"],
      }),
    ).toBe(false);
  });

  test("treats a parsed URL and the re-serialized selection as equal", () => {
    const parsed = parseMapSelection(LEGACY_SEARCH);

    expect(
      isSameMapSelection(
        parsed,
        parseMapSelection(serializeMapSelection(parsed).toString()),
      ),
    ).toBe(true);
  });
});
