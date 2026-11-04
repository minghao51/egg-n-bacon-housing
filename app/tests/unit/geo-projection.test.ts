/**
 * Unit tests for the map geometry projection and value binning
 * (src/utils/geo-projection.ts).
 *
 * Hermetic: the projection rules, the tolerance for malformed features and the
 * bin arithmetic are exercised on small hand-built fixtures. One block reads
 * the published `public/data/planning_areas.geojson` because "55 planning areas
 * become 55 paths" is a property of that asset, not of a fixture.
 */

import { describe, expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import { join } from "node:path";

import {
  MAP_NO_DATA_FILL,
  MAP_PALETTE,
  binForValue,
  binIndex,
  projectPlanningAreas,
  quantileBins,
} from "../../src/utils/geo-projection";

/** Ring helper: closes a ring the way GeoJSON does. */
function ring(points: [number, number][]): [number, number][] {
  const [first] = points;
  if (first === undefined) return [];
  return [...points, first];
}

/** Two areas: a plain polygon, and a multi-part area whose first part has a hole. */
const twoAreaFixture = {
  type: "FeatureCollection",
  features: [
    {
      type: "Feature",
      properties: { PLN_AREA_N: "TAMPINES" },
      geometry: {
        type: "Polygon",
        coordinates: [
          ring([
            [103.94, 1.35],
            [103.96, 1.35],
            [103.96, 1.37],
            [103.94, 1.37],
          ]),
        ],
      },
    },
    {
      type: "Feature",
      properties: { pln_area_n: "bedok" },
      geometry: {
        type: "MultiPolygon",
        coordinates: [
          [
            ring([
              [103.9, 1.32],
              [103.93, 1.32],
              [103.93, 1.34],
              [103.9, 1.34],
            ]),
            ring([
              [103.91, 1.325],
              [103.92, 1.325],
              [103.92, 1.335],
              [103.91, 1.335],
            ]),
          ],
          [
            ring([
              [103.99, 1.29],
              [104.0, 1.29],
              [103.995, 1.3],
            ]),
          ],
        ],
      },
    },
  ],
};

/** One area spanning 40°N–60°N, where the cos(mean latitude) term is large. */
const highLatitudeFixture = {
  type: "FeatureCollection",
  features: [
    {
      type: "Feature",
      properties: { PLN_AREA_N: "TEST" },
      geometry: {
        type: "Polygon",
        coordinates: [
          ring([
            [0, 40],
            [1, 40],
            [1, 60],
            [0, 60],
          ]),
        ],
      },
    },
  ],
};

/** Every `[x, y]` pair in a projected path string. */
function pathCoordinates(path: string): [number, number][] {
  const numbers = path.match(/-?\d+\.\d+/g) ?? [];
  const pairs: [number, number][] = [];
  for (let index = 0; index + 1 < numbers.length; index += 2) {
    const x = numbers[index];
    const y = numbers[index + 1];
    if (x === undefined || y === undefined) continue;
    pairs.push([Number(x), Number(y)]);
  }
  return pairs;
}

function boundsOf(paths: string[]): {
  minX: number;
  maxX: number;
  minY: number;
  maxY: number;
} {
  let minX = Number.POSITIVE_INFINITY;
  let minY = Number.POSITIVE_INFINITY;
  let maxX = Number.NEGATIVE_INFINITY;
  let maxY = Number.NEGATIVE_INFINITY;
  for (const path of paths) {
    for (const [x, y] of pathCoordinates(path)) {
      minX = Math.min(minX, x);
      maxX = Math.max(maxX, x);
      minY = Math.min(minY, y);
      maxY = Math.max(maxY, y);
    }
  }
  return { minX, maxX, minY, maxY };
}

/**
 * `expect(value).toMatch(...)` is not part of the shared `bun:test` ambient
 * declarations in `tests/unit/bun-test.d.ts`, so assert the pattern directly.
 */
function expectMatches(value: string, pattern: RegExp): void {
  expect(pattern.test(value)).toBe(true);
}

/** Relative luminance of a `#RRGGBB` colour, enough to order a palette. */
function luminance(hex: string): number {
  const value = hex.replace("#", "");
  const channels = [0, 2, 4].map((offset) => {
    const channel = Number.parseInt(value.slice(offset, offset + 2), 16) / 255;
    return channel <= 0.03928
      ? channel / 12.92
      : ((channel + 0.055) / 1.055) ** 2.4;
  });
  const [r = 0, g = 0, b = 0] = channels;
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

describe("projectPlanningAreas — published asset", () => {
  const geojson: unknown = JSON.parse(
    readFileSync(
      join(process.cwd(), "public", "data", "planning_areas.geojson"),
      "utf8",
    ),
  );
  const map = projectPlanningAreas(geojson);

  test("projects all 55 published features to 55 areas", () => {
    expect(map.areas).toHaveLength(55);
    expect(new Set(map.areas.map((area) => area.areaId)).size).toBe(55);
  });

  test("uses canonical ids, display names and slugs", () => {
    const angMoKio = map.areas.find((area) => area.areaId === "ANG MO KIO");
    expect(angMoKio).toBeDefined();
    expect(angMoKio?.areaName).toBe("Ang Mo Kio");
    expect(angMoKio?.slug).toBe("ang-mo-kio");
    expect(
      map.areas.find((area) => area.areaId === "NORTH-EASTERN ISLANDS")?.slug,
    ).toBe("north-eastern-islands");
  });

  test("every path is a well-formed, two-decimal SVG path that starts with M", () => {
    for (const area of map.areas) {
      expect(area.path.startsWith("M ")).toBe(true);
      expect(area.path.endsWith(" Z")).toBe(true);
      expect(area.path).not.toContain("NaN");
      expect(area.path).not.toContain("undefined");
      for (const number of area.path.match(/-?\d+\.?\d*/g) ?? []) {
        expectMatches(number, /^\d+\.\d{2}$/);
      }
    }
  });

  test("every coordinate and centroid stays inside the canvas", () => {
    const bounds = boundsOf(map.areas.map((area) => area.path));
    expect(bounds.minX).toBeGreaterThanOrEqual(0);
    expect(bounds.minY).toBeGreaterThanOrEqual(0);
    expect(bounds.maxX).toBeLessThanOrEqual(map.width);
    expect(bounds.maxY).toBeLessThanOrEqual(map.height);

    for (const area of map.areas) {
      const [x, y] = area.centroid;
      expect(x).toBeGreaterThanOrEqual(0);
      expect(x).toBeLessThanOrEqual(map.width);
      expect(y).toBeGreaterThanOrEqual(0);
      expect(y).toBeLessThanOrEqual(map.height);
    }
  });

  test("preserves the projected aspect ratio of the island", () => {
    const bounds = boundsOf(map.areas.map((area) => area.path));
    const projected = (bounds.maxX - bounds.minX) / (bounds.maxY - bounds.minY);

    // Singapore's bbox: lon 103.6057–104.0885, lat 1.1587–1.4708.
    const expected =
      ((104.08848306516335 - 103.60570070513404) *
        Math.cos(
          (((1.1586987006322145 + 1.4707748320860872) / 2) * Math.PI) / 180,
        )) /
      (1.4707748320860872 - 1.1586987006322145);
    expect(projected).toBeCloseTo(expected, 2);
  });

  test("keeps the published holes as separate subpaths", () => {
    const jurongEast = map.areas.find((area) => area.areaId === "JURONG EAST");
    // Two polygons: a 5-point sliver and an 885-point body with a 39-point hole.
    expect((jurongEast?.path.match(/M /g) ?? []).length).toBe(3);
    expect((jurongEast?.path.match(/ Z/g) ?? []).length).toBe(3);
  });
});

describe("projectPlanningAreas — fixtures", () => {
  test("accepts Polygon and MultiPolygon and keeps source order", () => {
    const map = projectPlanningAreas(twoAreaFixture);
    expect(map.areas.map((area) => area.areaId)).toEqual(["TAMPINES", "BEDOK"]);
    expect(map.areas.map((area) => area.slug)).toEqual(["tampines", "bedok"]);
  });

  test("emits one subpath per ring, so holes can be filled with evenodd", () => {
    const map = projectPlanningAreas(twoAreaFixture);
    const bedok = map.areas.find((area) => area.areaId === "BEDOK");
    expect(bedok).toBeDefined();
    // Outer ring + hole + second polygon's outer ring.
    expect((bedok?.path.match(/M /g) ?? []).length).toBe(3);
    expect((bedok?.path.match(/ Z/g) ?? []).length).toBe(3);
    expect((map.areas[0]?.path.match(/M /g) ?? []).length).toBe(1);
  });

  test("respects the requested canvas and padding", () => {
    const map = projectPlanningAreas(twoAreaFixture, {
      width: 400,
      height: 300,
      padding: 0,
    });
    expect(map.width).toBe(400);
    expect(map.height).toBe(300);

    const bounds = boundsOf(map.areas.map((area) => area.path));
    expect(bounds.minX).toBeGreaterThanOrEqual(0);
    expect(bounds.minY).toBeGreaterThanOrEqual(0);
    expect(bounds.maxX).toBeLessThanOrEqual(400);
    expect(bounds.maxY).toBeLessThanOrEqual(300);
    // Aspect is preserved, so the fit touches the box on one axis only.
    const fillsWidth = bounds.minX < 0.5 && bounds.maxX > 399.5;
    const fillsHeight = bounds.minY < 0.5 && bounds.maxY > 299.5;
    expect(fillsWidth !== fillsHeight).toBe(true);
  });

  test("leaves the default padding free of geometry", () => {
    const map = projectPlanningAreas(twoAreaFixture);
    const bounds = boundsOf(map.areas.map((area) => area.path));
    expect(bounds.minX).toBeGreaterThanOrEqual(7.99);
    expect(bounds.minY).toBeGreaterThanOrEqual(7.99);
    expect(bounds.maxX).toBeLessThanOrEqual(map.width - 7.99);
    expect(bounds.maxY).toBeLessThanOrEqual(map.height - 7.99);
  });

  test("shrinks longitude by cos(mean latitude) so the map is not stretched", () => {
    const map = projectPlanningAreas(highLatitudeFixture);
    const bounds = boundsOf(map.areas.map((area) => area.path));
    const projected = (bounds.maxX - bounds.minX) / (bounds.maxY - bounds.minY);

    const corrected = Math.cos((50 * Math.PI) / 180) / 20;
    const uncorrected = 1 / 20;
    expect(projected).toBeCloseTo(corrected, 4);
    expect(Math.abs(projected - uncorrected)).toBeGreaterThan(0.01);
  });

  test("puts north at the top", () => {
    const map = projectPlanningAreas(twoAreaFixture);
    const tampines = map.areas.find((area) => area.areaId === "TAMPINES");
    const bedok = map.areas.find((area) => area.areaId === "BEDOK");
    // Tampines sits at lat 1.35–1.37, Bedok reaches down to 1.29.
    expect(tampines?.centroid[1]).toBeLessThan(bedok?.centroid[1] ?? 0);
  });

  test("skips features without a usable planning-area name", () => {
    const map = projectPlanningAreas({
      type: "FeatureCollection",
      features: [
        {
          type: "Feature",
          properties: { REGION_N: "EAST REGION" },
          geometry: {
            type: "Polygon",
            coordinates: [
              ring([
                [103.7, 1.2],
                [103.8, 1.2],
                [103.8, 1.3],
              ]),
            ],
          },
        },
        {
          type: "Feature",
          properties: { PLN_AREA_N: "  ang   mo kio " },
          geometry: {
            type: "Polygon",
            coordinates: [
              ring([
                [103.83, 1.36],
                [103.85, 1.36],
                [103.85, 1.38],
              ]),
            ],
          },
        },
      ],
    });

    expect(map.areas).toHaveLength(1);
    expect(map.areas[0]?.areaId).toBe("ANG MO KIO");
    expect(map.areas[0]?.areaName).toBe("Ang Mo Kio");
    expect(map.areas[0]?.slug).toBe("ang-mo-kio");
  });

  test("sanitises lowercase ids from exporters that write pln_area_n", () => {
    const map = projectPlanningAreas({
      type: "FeatureCollection",
      features: [
        {
          type: "Feature",
          properties: { pln_area_n: "  tampines  " },
          geometry: {
            type: "Polygon",
            coordinates: [
              ring([
                [103.94, 1.35],
                [103.96, 1.35],
                [103.96, 1.37],
              ]),
            ],
          },
        },
      ],
    });
    expect(map.areas[0]?.areaId).toBe("TAMPINES");
    expect(map.areas[0]?.slug).toBe("tampines");
  });

  test("skips features with no usable ring instead of throwing", () => {
    const map = projectPlanningAreas({
      type: "FeatureCollection",
      features: [
        { type: "Feature", properties: { PLN_AREA_N: "NO GEOMETRY" } },
        {
          type: "Feature",
          properties: { PLN_AREA_N: "POINT AREA" },
          geometry: { type: "Point", coordinates: [103.8, 1.3] },
        },
        {
          type: "Feature",
          properties: { PLN_AREA_N: "DEGENERATE" },
          geometry: {
            type: "Polygon",
            // Two distinct points: enclosed area is zero, so it cannot be drawn.
            coordinates: [
              [
                [103.8, 1.3],
                [103.9, 1.31],
                [103.8, 1.3],
              ],
            ],
          },
        },
        {
          type: "Feature",
          properties: { PLN_AREA_N: "CLEMENTI" },
          geometry: {
            type: "Polygon",
            coordinates: [
              ring([
                [103.76, 1.31],
                [103.78, 1.31],
                [103.78, 1.33],
              ]),
            ],
          },
        },
      ],
    });

    expect(map.areas).toHaveLength(1);
    expect(map.areas[0]?.areaId).toBe("CLEMENTI");
  });

  test("collapses a duplicated area to its first feature", () => {
    const polygon = {
      type: "Polygon" as const,
      coordinates: [
        ring([
          [103.94, 1.35],
          [103.96, 1.35],
          [103.96, 1.37],
        ]),
      ],
    };
    const map = projectPlanningAreas({
      type: "FeatureCollection",
      features: [
        {
          type: "Feature",
          properties: { PLN_AREA_N: "TAMPINES" },
          geometry: polygon,
        },
        {
          type: "Feature",
          properties: { pln_area_n: "tampines" },
          geometry: polygon,
        },
      ],
    });
    expect(map.areas).toHaveLength(1);
  });

  test("returns an empty map for payloads it cannot read", () => {
    for (const payload of [
      null,
      undefined,
      {},
      { type: "FeatureCollection" },
      { type: "FeatureCollection", features: "nope" },
      "planning_areas.geojson",
      42,
    ]) {
      const map = projectPlanningAreas(payload);
      expect(map.areas).toEqual([]);
      expect(map.width).toBeGreaterThan(0);
      expect(map.height).toBeGreaterThan(0);
    }
  });

  test("ignores features that are not objects", () => {
    const map = projectPlanningAreas({
      type: "FeatureCollection",
      features: [null, 7, { type: "Feature", properties: {} }],
    });
    expect(map.areas).toEqual([]);
  });
});

describe("quantileBins", () => {
  test("returns no bins for empty or entirely unusable input", () => {
    expect(quantileBins([])).toEqual([]);
    expect(
      quantileBins([Number.NaN, Number.POSITIVE_INFINITY, -1, -500]),
    ).toEqual([]);
  });

  test("yields a single bin for one value", () => {
    const bins = quantileBins([499000]);
    expect(bins).toHaveLength(1);
    expect(bins[0]).toMatchObject({
      min: 499000,
      max: 499000,
      label: "499000",
    });
  });

  test("yields a single bin when every value is identical", () => {
    const bins = quantileBins([710000, 710000, 710000]);
    expect(bins).toHaveLength(1);
    expect(bins[0]?.min).toBe(710000);
    expect(bins[0]?.max).toBe(710000);
  });

  test("cuts five values into ascending, non-overlapping bins covering all of them", () => {
    const bins = quantileBins([500, 600, 700, 800, 900]);
    // Half-open bins need one more edge than bins, so five observations give at
    // most four bins; every observation must still land in exactly one.
    expect(bins.length).toBeGreaterThan(1);
    expect(bins.length).toBeLessThanOrEqual(5);
    for (const value of [500, 600, 700, 800, 900]) {
      expect(binIndex(value, bins)).not.toBeNull();
    }
    expect(bins[0]?.min).toBe(500);
    expect(bins[bins.length - 1]?.max).toBe(900);
    for (let index = 0; index < bins.length; index += 1) {
      const bin = bins[index];
      const next = bins[index + 1];
      expect(bin).toBeDefined();
      expect(bin?.min).toBeLessThanOrEqual(bin?.max ?? 0);
      if (bin !== undefined && next !== undefined) {
        expect(bin.max).toBeLessThanOrEqual(next.min);
      }
    }
  });

  test("cuts thirty values into the default five bins", () => {
    const values = Array.from({ length: 30 }, (_, index) => (index + 1) * 1000);
    const bins = quantileBins(values);
    expect(bins).toHaveLength(5);
    expect(bins[0]?.min).toBe(1000);
    expect(bins[4]?.max).toBe(30000);
    expect(bins.map((bin) => bin.min)).toEqual([
      1000, 7000, 13000, 19000, 25000,
    ]);
    for (let index = 0; index + 1 < bins.length; index += 1) {
      const bin = bins[index];
      const next = bins[index + 1];
      if (bin === undefined || next === undefined) continue;
      expect(bin.max).toBeLessThanOrEqual(next.min);
      expect(bin.label).toBe(`${bin.min}–${bin.max}`);
    }
  });

  test("assigns every value to exactly one bin, lower boundary inclusive", () => {
    const values = Array.from({ length: 30 }, (_, index) => (index + 1) * 1000);
    const bins = quantileBins(values);
    for (const value of values) {
      const index = binIndex(value, bins);
      expect(index).not.toBeNull();
      const bin = index === null ? undefined : bins[index];
      if (bin === undefined) throw new Error(`no bin for ${value}`);
      const isLast = index === bins.length - 1;
      expect(value).toBeGreaterThanOrEqual(bin.min);
      expect(value < bin.max || (isLast && value === bin.max)).toBe(true);
    }
    // A boundary value belongs to the bin that starts at it.
    const boundary = bins[1]?.min ?? 0;
    expect(binIndex(boundary, bins)).toBe(1);
    expect(binForValue(boundary, bins)).toEqual(bins[1]);
  });

  test("honours a smaller bin count", () => {
    const values = Array.from({ length: 30 }, (_, index) => index + 1);
    expect(quantileBins(values, 3)).toHaveLength(3);
    expect(quantileBins(values, 1)).toHaveLength(1);
    expect(quantileBins(values, 0)).toEqual([]);
  });

  test("keeps labels numeric-neutral and free of separators", () => {
    const bins = quantileBins([499000, 550000, 628000, 710000, 820000]);
    for (const bin of bins) {
      expectMatches(bin.label, /^\d+(\.\d+)?(–\d+(\.\d+)?)?$/);
    }
  });

  test("ignores negative and non-finite values before binning", () => {
    const bins = quantileBins([
      Number.NaN,
      -5,
      10,
      20,
      30,
      Number.POSITIVE_INFINITY,
    ]);
    expect(bins[0]?.min).toBe(10);
    expect(bins[bins.length - 1]?.max).toBe(30);
  });

  test("returns null for values outside the bins", () => {
    const bins = quantileBins([100, 200, 300]);
    expect(binForValue(99, bins)).toBeNull();
    expect(binIndex(99, bins)).toBeNull();
    expect(binForValue(301, bins)).toBeNull();
    expect(binIndex(301, bins)).toBeNull();
    expect(binIndex(Number.NaN, bins)).toBeNull();
    expect(binForValue(Number.NaN, bins)).toBeNull();
    expect(binIndex(200, [])).toBeNull();
    expect(binIndex(200, bins)).not.toBeNull();
  });

  test("places the maximum in the last bin", () => {
    const bins = quantileBins([100, 200, 300, 400, 500, 600]);
    expect(binIndex(600, bins)).toBe(bins.length - 1);
    expect(binIndex(100, bins)).toBe(0);
  });
});

describe("palette", () => {
  test("has one step per default bin", () => {
    const values = Array.from({ length: 30 }, (_, index) => (index + 1) * 1000);
    expect(MAP_PALETTE).toHaveLength(5);
    expect(MAP_PALETTE).toHaveLength(quantileBins(values).length);
  });

  test("runs low to high, last step darkest", () => {
    expect(MAP_PALETTE).toHaveLength(5);
    for (const step of MAP_PALETTE) {
      expectMatches(step, /^#[0-9A-F]{6}$/);
    }
    const luminances = MAP_PALETTE.map(luminance);
    for (let index = 0; index + 1 < luminances.length; index += 1) {
      const current = luminances[index] ?? 0;
      const next = luminances[index + 1] ?? 0;
      expect(current).toBeGreaterThan(next);
    }
  });

  test("no-data fill differs from every palette step", () => {
    expectMatches(MAP_NO_DATA_FILL, /^#[0-9A-F]{6}$/);
    expect(MAP_PALETTE).not.toContain(MAP_NO_DATA_FILL);
  });
});
