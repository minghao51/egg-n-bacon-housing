/**
 * Observed reference prices for the financing scenario (slice S8).
 *
 * The financing tool needs one honest, named price: an observed 2025 median for
 * a chosen planning area and property type. It must not read the retired
 * `affordability_metrics` extract (a separate period-unknown asset) and it must
 * not average area medians into a national figure.
 *
 * This module is pure, so it can be called from the Astro shell's frontmatter
 * (build time) and from unit tests. It resolves values through the joint-section
 * adapter in `src/utils/observed-data.ts`: `map_metrics.year_2025_hdb` etc.,
 * never the property-only (`hdb`) or period-only (`year_2025`) blocks.
 */

import {
  getSection,
  readAreaObservation,
  type EraId,
  type PropertyTypeId,
} from "@/utils/observed-data";
import type { ToolProperty, ToolReferenceSelection } from "./tool-url-state";

/** The only era a financing reference may come from (fixed, verified 2025). */
export const REFERENCE_ERA: Extract<EraId, "year_2025"> = "year_2025";

export const REFERENCE_PROPERTIES: readonly ToolProperty[] = [
  "hdb",
  "ec",
  "condo",
];

/** Documented fallback scenario: Tampines HDB at the 2025 median. */
export const DEFAULT_REFERENCE: { area: string; property: ToolProperty } = {
  area: "TAMPINES",
  property: "hdb",
};

export interface ReferencePriceEntry {
  areaId: string;
  areaName: string;
  slug: string;
  property: ToolProperty;
  /** Available observed median only; absent observations are not listed. */
  medianPrice: number;
  volume: number | null;
  /** Joint section key the value came from, e.g. `year_2025_hdb`. */
  section: string;
}

export type ReferenceSourceStatus = "available" | "unavailable";

/**
 * Distinguish an unreadable reference asset from a readable asset that simply
 * has no 2025 joint section. Both produce an empty table, but only the former
 * means the reference price itself is unavailable; the UI must not present it
 * as an absent observation.
 */
export function referenceSourceStatus(
  mapMetrics: unknown,
): ReferenceSourceStatus {
  return mapMetrics !== null &&
    typeof mapMetrics === "object" &&
    !Array.isArray(mapMetrics)
    ? "available"
    : "unavailable";
}

export interface ReferencePriceTable {
  era: Extract<EraId, "year_2025">;
  entries: ReferencePriceEntry[];
  /** Every joint section this table read. */
  sections: string[];
}

/**
 * Build the reference table for the three property subsets from a
 * `map_metrics.json.gz` payload. A combination with no available median is
 * omitted rather than zero-filled; the UI reports the missing combination.
 */
export function buildReferencePriceTable(
  mapMetrics: unknown,
): ReferencePriceTable {
  const entries: ReferencePriceEntry[] = [];
  const sections: string[] = [];

  for (const property of REFERENCE_PROPERTIES) {
    const sectionKey = `${REFERENCE_ERA}_${property}`;
    sections.push(sectionKey);

    const section = getSection(
      mapMetrics,
      REFERENCE_ERA,
      property as PropertyTypeId,
    );
    if (section === null) continue;

    for (const areaKey of Object.keys(section)) {
      const observation = readAreaObservation(
        mapMetrics,
        REFERENCE_ERA,
        property as PropertyTypeId,
        areaKey,
      );
      if (observation === null) continue;

      const median = observation.metrics.find(
        (metric) => metric.metric === "median_price",
      );
      if (median === undefined || median.value === null) continue;

      const volume = observation.metrics.find(
        (metric) => metric.metric === "volume",
      );

      entries.push({
        areaId: observation.areaId,
        areaName: observation.areaName,
        slug: observation.slug,
        property,
        medianPrice: median.value,
        volume: volume === undefined ? null : volume.value,
        section: observation.section,
      });
    }
  }

  entries.sort((a, b) => a.areaName.localeCompare(b.areaName));
  return { era: REFERENCE_ERA, entries, sections };
}

/** Areas present in the table for one property type, sorted by display name. */
export function referenceAreasFor(
  table: ReferencePriceTable,
  property: ToolProperty,
): ReferencePriceEntry[] {
  return table.entries.filter((entry) => entry.property === property);
}

/** Exact (area, property) lookup; `null` when that combination is absent. */
export function findReferenceEntry(
  table: ReferencePriceTable,
  area: string,
  property: ToolProperty,
): ReferencePriceEntry | null {
  const canonical = area.trim().replace(/\s+/g, " ").toUpperCase();
  return (
    table.entries.find(
      (entry) => entry.areaId === canonical && entry.property === property,
    ) ?? null
  );
}

/** The documented default, or the first available HDB entry as a fallback. */
export function defaultReferenceEntry(
  table: ReferencePriceTable,
): ReferencePriceEntry | null {
  return (
    findReferenceEntry(
      table,
      DEFAULT_REFERENCE.area,
      DEFAULT_REFERENCE.property,
    ) ??
    referenceAreasFor(table, "hdb")[0] ??
    table.entries[0] ??
    null
  );
}

/**
 * The named reference the financing tool should display, plus whether an
 * explicit selection could not be honoured.
 *
 * A selection with no published observation falls back to the documented
 * default rather than substituting a value; `missingRequested` lets the UI say
 * so. Resolution is pure so the workspace and the tool can share one answer.
 */
export interface ReferenceResolution {
  entry: ReferencePriceEntry | null;
  missingRequested: boolean;
}

export function resolveReference(
  table: ReferencePriceTable,
  selection: ToolReferenceSelection | null,
): ReferenceResolution {
  if (selection === null) {
    return { entry: defaultReferenceEntry(table), missingRequested: false };
  }
  const requested = findReferenceEntry(
    table,
    selection.area,
    selection.property,
  );
  if (requested !== null) {
    return { entry: requested, missingRequested: false };
  }
  return { entry: defaultReferenceEntry(table), missingRequested: true };
}

/**
 * Stable identity for a resolved reference (`area:property`), or `none`.
 *
 * Used to decide whether a reference change is *new*: the workspace imports a
 * published median only when this key changes, so a manual price survives a
 * tool switch and a remount, while a deep link or back/forward that names a
 * different area still imports that area's median.
 */
export function referenceKey(entry: ReferencePriceEntry | null): string {
  return entry === null ? "none" : `${entry.areaId}:${entry.property}`;
}
