/**
 * Planning-area geometry projection and value binning for the observed map.
 *
 * Two pure concerns that the `/explore` map shares with its legend and its
 * accessible table:
 *
 * 1. {@link projectPlanningAreas} turns the published
 *    `public/data/planning_areas.geojson` into one SVG path string per planning
 *    area, projected with an equirectangular transform corrected by
 *    `cos(mean latitude)` so Singapore is not stretched east-west, then fitted
 *    into the requested canvas while preserving aspect. The tile-free map is
 *    the only representation the app can always draw, so this is deliberately
 *    free of DOM, React, fetch and Leaflet.
 * 2. {@link quantileBins} cuts the plotted metric into at most `binCount`
 *    quantile bins, with `binForValue`/`binIndex` resolving a value back to its
 *    bin. Bins are lower-inclusive (`[min, max)`, last bin inclusive of `max`),
 *    which is what the design's legend note states.
 *
 * Constraints:
 * - No throwing on malformed geometry. A feature with no usable ring is
 *   skipped, exactly like a feature with no planning-area name.
 * - Coordinates are rounded to 2 decimals, so path strings stay small and
 *   stable between renders.
 * - Labels stay numeric-neutral (`"499000–550000"`): currency and unit text is
 *   the caller's job, because the same bins serve price and sales counts.
 */

import { planningAreaName } from "@/utils/geometry";
import {
  areaSlug,
  canonicalAreaId,
  formatAreaName,
} from "@/utils/observed-data";

/** One planning area, ready to render as a single `<path d={path}>`. */
export interface ProjectedArea {
  /** Canonical id, e.g. `"ANG MO KIO"` (matches `map_metrics` section keys). */
  areaId: string;
  /** Display name, e.g. `"Ang Mo Kio"`. */
  areaName: string;
  /** URL slug, e.g. `"ang-mo-kio"` (matches `/areas/[slug]`). */
  slug: string;
  /**
   * One subpath per ring (`M … Z`), outer ring first, then holes. Join them
   * with `fill-rule="evenodd"` so holes punch through the outer ring whatever
   * the ring winding order in the source file is.
   */
  path: string;
  /** `[x, y]` in canvas coordinates, rounded to 2 decimals. */
  centroid: [number, number];
}

export interface ProjectedMap {
  /** Canvas width in user units; equals the requested `width`. */
  width: number;
  /** Canvas height in user units; equals the requested `height`. */
  height: number;
  /** Areas in source feature order, one per planning area. */
  areas: ProjectedArea[];
}

/** Five sequential steps, low to high, last step darkest (design 09 legend). */
export const MAP_PALETTE: readonly string[] = [
  "#D2E4DB",
  "#9BC7BA",
  "#5DA392",
  "#277D72",
  "#005E58",
];

/** Fill for an area with no value: unavailable or below the sample threshold. */
export const MAP_NO_DATA_FILL = "#E3E4DF";

const DEFAULT_WIDTH = 960;
const DEFAULT_HEIGHT = 640;
const DEFAULT_PADDING = 8;
const DEFAULT_BIN_COUNT = 5;

/** A projected or geographic `[x, y]` / `[lon, lat]` pair. */
type Position = readonly [number, number];

/** A polygon is its outer ring followed by zero or more holes. */
type Ring = Position[];
type Polygon = Ring[];

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function dimension(value: number | undefined, fallback: number): number {
  return typeof value === "number" && Number.isFinite(value) && value > 0
    ? value
    : fallback;
}

function paddingOption(value: number | undefined): number {
  return typeof value === "number" && Number.isFinite(value) && value >= 0
    ? value
    : DEFAULT_PADDING;
}

/** A `[lon, lat]` pair with both members finite, or `null`. */
function readPosition(value: unknown): Position | null {
  if (!Array.isArray(value) || value.length < 2) {
    return null;
  }
  const lon: unknown = value[0];
  const lat: unknown = value[1];
  if (typeof lon !== "number" || typeof lat !== "number") {
    return null;
  }
  if (!Number.isFinite(lon) || !Number.isFinite(lat)) {
    return null;
  }
  return [lon, lat];
}

/**
 * Read one ring. Consecutive duplicate points and the closing duplicate are
 * dropped (the emitted subpath closes with `Z`), and a ring with fewer than
 * three distinct points cannot enclose anything, so it is unusable.
 */
function readRing(value: unknown): Ring | null {
  if (!Array.isArray(value)) {
    return null;
  }

  const points: Position[] = [];
  for (const raw of value) {
    const position = readPosition(raw);
    if (position === null) {
      // A ring with an unreadable vertex is not repaired: dropping the vertex
      // would draw a different polygon under the published area's name.
      return null;
    }
    const previous = points[points.length - 1];
    if (
      previous !== undefined &&
      previous[0] === position[0] &&
      previous[1] === position[1]
    ) {
      continue;
    }
    points.push(position);
  }

  const first = points[0];
  const last = points[points.length - 1];
  if (
    points.length > 1 &&
    first !== undefined &&
    last !== undefined &&
    first[0] === last[0] &&
    first[1] === last[1]
  ) {
    points.pop();
  }

  return points.length >= 3 ? points : null;
}

/** Read one polygon's rings, dropping unusable rings. `null` when none survive. */
function readPolygon(value: unknown): Polygon | null {
  if (!Array.isArray(value)) {
    return null;
  }

  const rings: Ring[] = [];
  for (const raw of value) {
    const ring = readRing(raw);
    if (ring !== null) {
      rings.push(ring);
    }
  }
  return rings.length > 0 ? rings : null;
}

/**
 * Read `Polygon` / `MultiPolygon` coordinates. Any other geometry type, and a
 * geometry with no usable ring, yields `null`.
 */
function readGeometry(geometry: unknown): Polygon[] | null {
  if (!isRecord(geometry)) {
    return null;
  }

  const { type, coordinates } = geometry;
  const rawPolygons: unknown =
    type === "Polygon"
      ? [coordinates]
      : type === "MultiPolygon"
        ? coordinates
        : null;
  if (!Array.isArray(rawPolygons)) {
    return null;
  }

  const polygons: Polygon[] = [];
  for (const raw of rawPolygons) {
    const polygon = readPolygon(raw);
    if (polygon !== null) {
      polygons.push(polygon);
    }
  }
  return polygons.length > 0 ? polygons : null;
}

/** The feature list of a `FeatureCollection` (or of a bare feature array). */
function readFeatures(geojson: unknown): unknown[] {
  if (Array.isArray(geojson)) {
    return geojson;
  }
  if (isRecord(geojson) && Array.isArray(geojson.features)) {
    return geojson.features;
  }
  return [];
}

/** Twice-signed area is summed into `polygonArea`; kept here for one pass. */
function polygonArea(points: readonly Position[]): number {
  let twice = 0;
  for (let index = 0; index < points.length; index += 1) {
    const current = points[index];
    const next = points[(index + 1) % points.length];
    if (current === undefined || next === undefined) {
      continue;
    }
    twice += current[0] * next[1] - next[0] * current[1];
  }
  return twice / 2;
}

function boundsCentre(points: readonly Position[]): [number, number] {
  let minX = Number.POSITIVE_INFINITY;
  let minY = Number.POSITIVE_INFINITY;
  let maxX = Number.NEGATIVE_INFINITY;
  let maxY = Number.NEGATIVE_INFINITY;
  for (const [x, y] of points) {
    minX = Math.min(minX, x);
    minY = Math.min(minY, y);
    maxX = Math.max(maxX, x);
    maxY = Math.max(maxY, y);
  }
  return [(minX + maxX) / 2, (minY + maxY) / 2];
}

/**
 * Area-weighted centroid of a ring, falling back to the ring's bounding-box
 * centre when the ring encloses no measurable area.
 */
function ringCentroid(points: readonly Position[]): [number, number] {
  const area = polygonArea(points);
  if (!Number.isFinite(area) || Math.abs(area) < 1e-6) {
    return boundsCentre(points);
  }

  let weightedX = 0;
  let weightedY = 0;
  for (let index = 0; index < points.length; index += 1) {
    const current = points[index];
    const next = points[(index + 1) % points.length];
    if (current === undefined || next === undefined) {
      continue;
    }
    const cross = current[0] * next[1] - next[0] * current[1];
    weightedX += (current[0] + next[0]) * cross;
    weightedY += (current[1] + next[1]) * cross;
  }

  const factor = 1 / (6 * area);
  const x = weightedX * factor;
  const y = weightedY * factor;
  if (!Number.isFinite(x) || !Number.isFinite(y)) {
    return boundsCentre(points);
  }
  return [x, y];
}

/** Round to 2 decimals, normalising `-0` to `0`. */
function round2(value: number): number {
  const rounded = Math.round(value * 100) / 100;
  return rounded === 0 ? 0 : rounded;
}

function coordinate(value: number): string {
  return round2(value).toFixed(2);
}

function ringPath(points: readonly Position[]): string {
  const commands: string[] = [];
  for (let index = 0; index < points.length; index += 1) {
    const point = points[index];
    if (point === undefined) {
      continue;
    }
    commands.push(
      `${index === 0 ? "M" : "L"} ${coordinate(point[0])},${coordinate(point[1])}`,
    );
  }
  return `${commands.join(" ")} Z`;
}

/**
 * Project `planning_areas.geojson` into SVG path strings.
 *
 * - Equirectangular transform corrected by `cos(mean latitude)`, so a degree
 *   of longitude is shortened by the same factor a degree of latitude is
 *   already shortened by at Singapore's latitude (~1.32°N, factor 0.99974).
 * - Fitted into `width` x `height` minus `padding` on every side, preserving
 *   aspect and centring the leftover space; latitude increases upwards.
 * - `Polygon` and `MultiPolygon` are both accepted. Features without a usable
 *   ring, and features without a `PLN_AREA_N`/`pln_area_n` name, are skipped
 *   rather than thrown on.
 * - Returns the requested canvas size unchanged (default 960 x 640), so the
 *   caller can use it directly as the `viewBox`.
 */
export function projectPlanningAreas(
  geojson: unknown,
  options: { width?: number; height?: number; padding?: number } = {},
): ProjectedMap {
  const width = dimension(options.width, DEFAULT_WIDTH);
  const height = dimension(options.height, DEFAULT_HEIGHT);
  const padding = paddingOption(options.padding);

  const parsed: { areaId: string; polygons: Polygon[] }[] = [];
  const seen = new Set<string>();
  let minLon = Number.POSITIVE_INFINITY;
  let minLat = Number.POSITIVE_INFINITY;
  let maxLon = Number.NEGATIVE_INFINITY;
  let maxLat = Number.NEGATIVE_INFINITY;

  for (const raw of readFeatures(geojson)) {
    if (!isRecord(raw)) {
      continue;
    }

    const name = planningAreaName(raw.properties);
    if (name === null) {
      continue;
    }
    const areaId = canonicalAreaId(name);
    if (seen.has(areaId)) {
      continue;
    }

    const polygons = readGeometry(raw.geometry);
    if (polygons === null) {
      continue;
    }

    for (const polygon of polygons) {
      for (const ring of polygon) {
        for (const [lon, lat] of ring) {
          minLon = Math.min(minLon, lon);
          maxLon = Math.max(maxLon, lon);
          minLat = Math.min(minLat, lat);
          maxLat = Math.max(maxLat, lat);
        }
      }
    }

    seen.add(areaId);
    parsed.push({ areaId, polygons });
  }

  if (
    parsed.length === 0 ||
    !Number.isFinite(minLon) ||
    !Number.isFinite(minLat)
  ) {
    return { width, height, areas: [] };
  }

  const availableWidth = Math.max(width - 2 * padding, 0);
  const availableHeight = Math.max(height - 2 * padding, 0);
  const meanLatRad = (((minLat + maxLat) / 2) * Math.PI) / 180;
  const lonScale = Math.cos(meanLatRad);
  const contentWidth = (maxLon - minLon) * lonScale;
  const contentHeight = maxLat - minLat;
  const scale =
    contentWidth > 0 && contentHeight > 0
      ? Math.min(availableWidth / contentWidth, availableHeight / contentHeight)
      : 0;
  const offsetX = padding + (availableWidth - contentWidth * scale) / 2;
  const offsetY = padding + (availableHeight - contentHeight * scale) / 2;

  const projectX = (lon: number): number =>
    offsetX + (lon - minLon) * lonScale * scale;
  const projectY = (lat: number): number => offsetY + (maxLat - lat) * scale;

  const areas: ProjectedArea[] = [];
  for (const { areaId, polygons } of parsed) {
    const subpaths: string[] = [];
    let centroid: [number, number] | null = null;
    let largestArea = -1;

    for (const polygon of polygons) {
      for (let ringIndex = 0; ringIndex < polygon.length; ringIndex += 1) {
        const ring = polygon[ringIndex];
        if (ring === undefined) {
          continue;
        }

        const projected: Position[] = ring.map(
          ([lon, lat]) => [projectX(lon), projectY(lat)] as const,
        );
        subpaths.push(ringPath(projected));

        // The label point comes from the largest outer ring: the biggest land
        // piece of a multi-part area, never a hole or a sliver.
        if (ringIndex === 0) {
          const area = Math.abs(polygonArea(projected));
          if (area > largestArea) {
            largestArea = area;
            centroid = ringCentroid(projected);
          }
        }
      }
    }

    const centre = round2Point(centroid ?? [width / 2, height / 2]);
    areas.push({
      areaId,
      areaName: formatAreaName(areaId),
      slug: areaSlug(areaId),
      path: subpaths.join(" "),
      centroid: centre,
    });
  }

  return { width, height, areas };
}

function round2Point(point: readonly [number, number]): [number, number] {
  return [round2(point[0]), round2(point[1])];
}

/** One closed value range. `label` is numeric-neutral, e.g. `"499000–550000"`. */
export interface Bin {
  min: number;
  max: number;
  label: string;
  /** True only for the last bin, which contains its maximum value. */
  upperInclusive?: boolean;
}

function binCountOption(value: number | undefined): number {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return DEFAULT_BIN_COUNT;
  }
  return Math.floor(value);
}

function binLabel(min: number, max: number): string {
  return min === max ? `${min}` : `${min}–${max}`;
}

/**
 * Cut `values` into at most `binCount` ascending, non-overlapping quantile
 * bins.
 *
 * - Non-finite and negative values are ignored (a negative price is not a
 *   low price, it is a missing value).
 * - Bins are lower-inclusive: `[min, max)`, with the last bin also containing
 *   its `max`, so every plotted value resolves to exactly one bin.
 * - Edges are taken from the sorted distinct values, so a repeated value never
 *   straddles two bins.
 * - Empty (or entirely unusable) input yields `[]`; a single distinct value
 *   yields one bin whose `min` and `max` are that value.
 */
export function quantileBins(
  values: number[],
  binCount = DEFAULT_BIN_COUNT,
): Bin[] {
  const usable = values.filter((value) => Number.isFinite(value) && value >= 0);
  if (usable.length === 0) {
    return [];
  }

  // Rank-based cuts over the observations themselves. Using distinct values
  // would weight an unusually common price as heavily as a cluster of different
  // prices, so the legend's "quantiles of the areas shown" claim would be false.
  const requested = binCountOption(binCount);
  if (requested < 1) return [];

  const sorted = [...usable].sort((a, b) => a - b);
  const only = sorted[0];
  const largest = sorted[sorted.length - 1];
  if (only !== undefined && largest !== undefined && only === largest) {
    // Every observation is the same value: one bin, inclusive at both ends.
    return [
      {
        min: only,
        max: largest,
        label: binLabel(only, largest),
        upperInclusive: true,
      },
    ];
  }
  const edges: number[] = [sorted[0]];
  for (let index = 1; index < requested; index += 1) {
    const edge = sorted[Math.floor((index * sorted.length) / requested)];
    if (edge !== undefined && edge !== edges[edges.length - 1]) {
      edges.push(edge);
    }
  }
  const lastValue = sorted[sorted.length - 1];
  if (edges[edges.length - 1] !== lastValue) {
    edges.push(lastValue);
  }

  // Bins are half-open [min, max); the final bin also contains its maximum.
  const bins: Bin[] = [];
  for (let index = 0; index < edges.length - 1; index += 1) {
    const min = edges[index];
    const max = edges[index + 1];
    if (min === undefined || max === undefined || min === max) continue;
    bins.push({
      min,
      max,
      label: binLabel(min, max),
      upperInclusive: index === edges.length - 2,
    });
  }
  return bins;
}

/**
 * Index of the bin containing `value`, or `null` when the value is not a
 * finite number or lies outside every bin.
 */
export function binIndex(value: number, bins: Bin[]): number | null {
  if (!Number.isFinite(value)) {
    return null;
  }

  for (let index = 0; index < bins.length; index += 1) {
    const bin = bins[index];
    if (bin === undefined || value < bin.min) {
      continue;
    }
    if (value < bin.max) {
      return index;
    }
    if (index === bins.length - 1 && value === bin.max) {
      return index;
    }
  }
  return null;
}

/** The bin containing `value`, or `null` when {@link binIndex} finds none. */
export function binForValue(value: number, bins: Bin[]): Bin | null {
  const index = binIndex(value, bins);
  return index === null ? null : (bins[index] ?? null);
}
