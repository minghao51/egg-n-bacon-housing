/**
 * Legacy research-map URL state (`/dashboard/map`).
 *
 * Pure helpers for the five query groups the map has always accepted:
 * `metric`, `timeBasis`, `propertyType`, `area` and `layers`.
 *
 * No React and no DOM access at module scope, so this module is safe to import
 * during SSR. Accepted values are derived from the real components/types rather
 * than duplicated by hand: metrics/time bases/property types come from
 * `types/analytics.ts`, layer ids come from the keys of `LAYER_METADATA`.
 */

import { LAYER_METADATA } from "../types/analytics";
import type {
  LayerId,
  MetricType,
  PropertyTypeFilter,
  TemporalFilter,
} from "../types/analytics";

export type MapMetric = MetricType;
export type MapTimeBasis = TemporalFilter;
export type MapPropertyType = PropertyTypeFilter;
export type MapLayerId = LayerId;

/** Metrics offered by the map metric selector (`PriceMap.tsx`). */
export const MAP_METRICS = [
  "median_price",
  "median_psf",
  "volume",
  "rental_yield_median",
  "yoy_change_pct",
  "affordability_ratio",
] as const satisfies readonly MapMetric[];

/** Period buttons offered by the map temporal filter (`PriceMap.tsx`). */
export const MAP_TIME_BASES = [
  "whole",
  "pre_covid",
  "recent",
  "year_2025",
] as const satisfies readonly MapTimeBasis[];

/** Property type buttons offered by the map property filter (`PriceMap.tsx`). */
export const MAP_PROPERTY_TYPES = [
  "all",
  "hdb",
  "ec",
  "condo",
] as const satisfies readonly MapPropertyType[];

/** Layer ids accepted in `?layers=` — exactly the `LAYER_METADATA` keys. */
export const MAP_LAYER_IDS: readonly MapLayerId[] = Object.keys(
  LAYER_METADATA,
) as MapLayerId[];

/** Query keys owned by the legacy map selection. */
export const MAP_SELECTION_KEYS = [
  "metric",
  "timeBasis",
  "propertyType",
  "area",
  "layers",
] as const;

export interface MapSelection {
  metric: MapMetric | null;
  timeBasis: MapTimeBasis | null;
  propertyType: MapPropertyType | null;
  area: string | null;
  layers: MapLayerId[];
}

/** Selection produced by a query string that carries no usable map state. */
export const EMPTY_MAP_SELECTION: MapSelection = {
  metric: null,
  timeBasis: null,
  propertyType: null,
  area: null,
  layers: [],
};

function buildLookup<T extends string>(values: readonly T[]): Map<string, T> {
  return new Map(values.map((value) => [value, value] as const));
}

const METRIC_LOOKUP: ReadonlyMap<string, MapMetric> = buildLookup(MAP_METRICS);
const TIME_BASIS_LOOKUP: ReadonlyMap<string, MapTimeBasis> =
  buildLookup(MAP_TIME_BASES);
const PROPERTY_TYPE_LOOKUP: ReadonlyMap<string, MapPropertyType> =
  buildLookup(MAP_PROPERTY_TYPES);
const LAYER_LOOKUP: ReadonlyMap<string, MapLayerId> = buildLookup(MAP_LAYER_IDS);

function toSearchParams(search: string): URLSearchParams {
  // `URLSearchParams` never throws on malformed percent-encoding (it leaves the
  // raw sequence in place), but the guard keeps a broken query from ever
  // bubbling out of render/effect code.
  try {
    const query = search.startsWith("?") ? search.slice(1) : search;
    return new URLSearchParams(query);
  } catch {
    return new URLSearchParams();
  }
}

function readAccepted<T extends string>(
  lookup: ReadonlyMap<string, T>,
  value: string | null,
): T | null {
  if (value === null) return null;
  return lookup.get(value.trim()) ?? null;
}

function readArea(value: string | null): string | null {
  if (value === null) return null;
  const area = value.trim().toUpperCase();
  return area.length > 0 ? area : null;
}

function readLayers(value: string | null): MapLayerId[] {
  if (value === null) return [];
  const layers: MapLayerId[] = [];
  const seen = new Set<MapLayerId>();

  for (const rawLayerId of value.split(",")) {
    const layerId = LAYER_LOOKUP.get(rawLayerId.trim());
    if (layerId === undefined || seen.has(layerId)) continue;
    seen.add(layerId);
    layers.push(layerId);
  }

  return layers;
}

/**
 * Parse a query string (with or without a leading `?`) into a map selection.
 * Unknown keys and unaccepted values are dropped; a group whose value is
 * missing or not accepted becomes `null` rather than being replaced by another
 * value.
 */
export function parseMapSelection(search: string): MapSelection {
  const params = toSearchParams(search);

  return {
    metric: readAccepted(METRIC_LOOKUP, params.get("metric")),
    timeBasis: readAccepted(TIME_BASIS_LOOKUP, params.get("timeBasis")),
    propertyType: readAccepted(PROPERTY_TYPE_LOOKUP, params.get("propertyType")),
    area: readArea(params.get("area")),
    layers: readLayers(params.get("layers")),
  };
}

/**
 * Serialize a selection to query parameters. Empty groups are omitted, so a
 * cleared area or layer set never produces `area=null` or `layers=`.
 */
export function serializeMapSelection(
  selection: Partial<MapSelection>,
): URLSearchParams {
  const params = new URLSearchParams();

  if (selection.metric) {
    params.set("metric", selection.metric);
  }
  if (selection.timeBasis) {
    params.set("timeBasis", selection.timeBasis);
  }
  if (selection.propertyType) {
    params.set("propertyType", selection.propertyType);
  }

  const area = selection.area ? selection.area.trim().toUpperCase() : "";
  if (area.length > 0) {
    params.set("area", area);
  }

  const layers = selection.layers ?? [];
  if (layers.length > 0) {
    params.set("layers", layers.join(","));
  }

  return params;
}

/**
 * Overlay an incoming (partial) selection on a base selection. Absent or `null`
 * groups keep the base value; an explicit empty `layers` array clears layers.
 */
export function mergeMapSelection(
  base: MapSelection,
  incoming: Partial<MapSelection>,
): MapSelection {
  return {
    metric: incoming.metric ?? base.metric,
    timeBasis: incoming.timeBasis ?? base.timeBasis,
    propertyType: incoming.propertyType ?? base.propertyType,
    area: incoming.area ?? base.area,
    layers: incoming.layers ? [...incoming.layers] : [...base.layers],
  };
}

/** Value equality, ignoring layer order (a layer set has no meaningful order). */
export function isSameMapSelection(a: MapSelection, b: MapSelection): boolean {
  if (
    a.metric !== b.metric ||
    a.timeBasis !== b.timeBasis ||
    a.propertyType !== b.propertyType ||
    a.area !== b.area
  ) {
    return false;
  }

  if (a.layers.length !== b.layers.length) {
    return false;
  }

  const layers = new Set(a.layers);
  return b.layers.every((layerId) => layers.has(layerId));
}
