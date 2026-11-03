/**
 * Geometry / GeoJSON property helpers
 *
 * `public/data/planning_areas.geojson` carries the planning-area name as
 * uppercase `PLN_AREA_N` (verified against the published asset: all 55 features
 * expose `PLN_AREA_N`, none expose lowercase `pln_area_n`). Some exporters also
 * write lowercase `pln_area_n` into feature properties. Reading only one casing
 * silently yields `undefined` lookups, so every overlay funnels property access
 * through the helpers below.
 */

const NAME_KEY_PREFERENCE = ["PLN_AREA_N", "pln_area_n"] as const;
const NAME_KEY_SUFFIX = "pln_area_n";

function isPropertyBag(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isPreferredNameKey(key: string): boolean {
  return NAME_KEY_PREFERENCE.some((preferred) => preferred === key);
}

/**
 * Trim and uppercase a raw planning-area name. Returns `null` for absent,
 * empty, whitespace-only or non-string values.
 */
function normalizeName(value: unknown): string | null {
  if (typeof value !== "string") {
    return null;
  }
  const trimmed = value.trim();
  if (trimmed.length === 0) {
    return null;
  }
  return trimmed.toUpperCase();
}

/**
 * Read the planning-area name from a GeoJSON feature's `properties` bag.
 *
 * Accepts `PLN_AREA_N` / `pln_area_n` in any casing (uppercase wins when both
 * are present) and tolerates prefixed variants such as `source_pln_area_n` or
 * `properties.PLN_AREA_N`. Always returns a trimmed, uppercase name, or `null`
 * when no usable name is published.
 */
export function planningAreaName(properties: unknown): string | null {
  if (!isPropertyBag(properties)) {
    return null;
  }

  for (const key of NAME_KEY_PREFERENCE) {
    if (!(key in properties)) {
      continue;
    }
    const name = normalizeName(properties[key]);
    if (name !== null) {
      return name;
    }
  }

  // Tolerate prefixed keys (e.g. `source_pln_area_n`, `properties.PLN_AREA_N`).
  for (const key of Object.keys(properties)) {
    if (isPreferredNameKey(key)) {
      continue;
    }
    if (!key.toLowerCase().endsWith(NAME_KEY_SUFFIX)) {
      continue;
    }
    const name = normalizeName(properties[key]);
    if (name !== null) {
      return name;
    }
  }

  return null;
}

/**
 * Compare two planning-area names using the same normalisation as
 * {@link planningAreaName}. Unknown (`null`) areas never match anything,
 * including each other.
 */
export function samePlanningArea(a: string | null, b: string | null): boolean {
  const left = normalizeName(a);
  const right = normalizeName(b);
  return left !== null && right !== null && left === right;
}
