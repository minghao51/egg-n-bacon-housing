/**
 * Client-safe builders for `/areas/<slug>` links and for the return path.
 *
 * Lives outside `area-page.ts` because that module reads the published assets
 * with Node built-ins at build time; importing it from a React island would
 * pull `node:fs` into the browser bundle. This file may import pure,
 * browser-safe modules only — never `area-page.ts`, `node:*` or a component.
 */

import { isObservedPeriodId } from "@/utils/observed-periods";

/**
 * Explorer query keys a fieldnote hands back. `[slug].astro` passes its search
 * string to {@link explorerReturnHref}, so this list is the only allow-list.
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
const EXPLORER_LEGACY_PERIODS = [
  "whole",
  "pre_covid",
  "recent",
  "year_2025",
] as const;
const EXPLORER_METRICS = ["median_price", "median_psf", "volume"] as const;

/** Legacy era id or a well-formed concrete observed-period id. */
export function isExplorerPeriodValue(value: string): boolean {
  return (
    (EXPLORER_LEGACY_PERIODS as readonly string[]).includes(value) ||
    isObservedPeriodId(value)
  );
}

export interface AreaHrefSelection {
  property?: string;
  period?: string;
}

/**
 * Build an area-page path, optionally carrying the explorer selection so the
 * page can offer a return link. Unknown filter values are dropped rather than
 * echoed into the URL.
 */
export function areaHref(slug: string, selection?: AreaHrefSelection): string {
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
  if (period !== undefined && isExplorerPeriodValue(period)) {
    params.set("period", period);
  }

  return `/areas/${encodeURIComponent(slug)}?${params.toString()}`;
}

/**
 * One allow-listed explorer query value, or `null` when it must be dropped.
 *
 * Every vocabulary is checked against what `/explore` actually accepts, so a
 * hand-edited fieldnote URL cannot smuggle an arbitrary value back into the
 * explorer's address bar.
 */
function acceptedValue(key: string, value: string): string | null {
  if (value.length > 80) return null;
  // Free-text keys are the only ones where whitespace is meaningless; the
  // explorer trims them itself, so a blank value is dropped rather than echoed.
  const isTextKey = key === "search" || key === "area" || key === "from";
  if (isTextKey && value.trim() === "") return null;
  if (!isTextKey && value === "") return null;

  if (key === "property") {
    return (EXPLORER_PROPERTIES as readonly string[]).includes(value)
      ? value
      : null;
  }
  if (key === "period") return isExplorerPeriodValue(value) ? value : null;
  if (key === "metric" || key === "sort") {
    return (EXPLORER_METRICS as readonly string[]).includes(value)
      ? value
      : null;
  }
  if (key === "direction") {
    return value === "asc" || value === "desc" ? value : null;
  }
  if (key === "minSales") {
    return value === "all" || /^\d{1,6}$/.test(value) ? value : null;
  }
  if (key === "page") return /^\d{1,4}$/.test(value) ? value : null;
  return value;
}

/**
 * The explorer URL a fieldnote's return link should point at.
 *
 * `search` is the fieldnote's own query string. Only keys in
 * {@link AREA_RETURN_PARAMETERS} survive, each in its published vocabulary, and
 * only when the reader actually arrived from `/explore` — otherwise the link is
 * the plain explorer route.
 */
export function explorerReturnHref(
  exploreHref: string,
  search: string,
): string {
  let params: URLSearchParams;
  try {
    params = new URLSearchParams(search);
  } catch {
    return exploreHref;
  }
  if (params.get("from") !== "explore") return exploreHref;

  const query = new URLSearchParams();
  for (const key of AREA_RETURN_PARAMETERS) {
    const raw = params.get(key);
    if (raw === null) continue;
    const value = acceptedValue(key, raw);
    if (value !== null) query.set(key, value);
  }

  const qs = query.toString();
  return qs === "" ? exploreHref : `${exploreHref}?${qs}`;
}
