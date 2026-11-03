/**
 * Client-safe builder for `/areas/<slug>` links.
 *
 * Lives outside `area-page.ts` because that module reads the published assets
 * with Node built-ins at build time; importing it from a React island would
 * pull `node:fs` into the browser bundle. Keep this file free of imports.
 */

/**
 * Explorer query keys the area page may hand back. Must stay identical to the
 * inline allow-list in `src/pages/areas/[slug].astro` (pinned by a unit test).
 */
export const AREA_RETURN_PARAMETERS = [
  "from",
  "property",
  "period",
  "metric",
  "sort",
  "direction",
  "minSales",
  "search",
  "area",
  "page",
] as const;

const EXPLORER_PROPERTIES = ["all", "hdb", "ec", "condo"] as const;
const EXPLORER_PERIODS = ["whole", "pre_covid", "recent", "year_2025"] as const;

export interface AreaHrefSelection {
  property?: string;
  period?: string;
}

/**
 * Build an area-page path, optionally carrying the explorer selection so the
 * page can offer a return link. Unknown filter values are dropped rather than
 * echoed into the URL.
 */
export function areaHref(
  slug: string,
  selection?: AreaHrefSelection,
): string {
  const params = new URLSearchParams();
  params.set("from", "explore");

  const property = selection?.property;
  if (
    property !== undefined &&
    EXPLORER_PROPERTIES.some((candidate) => candidate === property)
  ) {
    params.set("property", property);
  }

  const period = selection?.period;
  if (
    period !== undefined &&
    EXPLORER_PERIODS.some((candidate) => candidate === period)
  ) {
    params.set("period", period);
  }

  return `/areas/${encodeURIComponent(slug)}?${params.toString()}`;
}
