/**
 * Validated query state for the `/explore` workspace.
 *
 * One selection object is the single source of truth for the URL, the controls,
 * the table and the map. Parsing is total: an unknown or malformed value falls
 * back to the documented default instead of throwing or silently landing on a
 * different valid value, so a hand-edited or truncated deep link never renders
 * a scope the reader did not ask for.
 *
 * No React, no DOM, no `window` at module scope — the caller owns the address
 * bar and history.
 */

export type ExplorerProperty = "all" | "hdb" | "ec" | "condo";

export type ExplorerPeriod = "whole" | "pre_covid" | "recent" | "year_2025";

export type ExplorerMetric = "median_price" | "median_psf" | "volume";

export type ExplorerSort = ExplorerMetric;

export interface ExplorerSelection {
  property: ExplorerProperty;
  period: ExplorerPeriod;
  metric: ExplorerMetric;
  sort: ExplorerSort;
  direction: "asc" | "desc";
  minSales: number | null;
  search: string;
  area: string | null;
  page: number;
}

export const EXPLORER_PROPERTIES: readonly ExplorerProperty[] = [
  "all",
  "hdb",
  "ec",
  "condo",
];

export const EXPLORER_PERIODS: readonly ExplorerPeriod[] = [
  "whole",
  "pre_covid",
  "recent",
  "year_2025",
];

export const EXPLORER_METRICS: readonly ExplorerMetric[] = [
  "median_price",
  "median_psf",
  "volume",
];

/** Below this many sales in the selected period an area is flagged thin. */
export const THIN_SAMPLE_THRESHOLD = 150;

/** Highest accepted `minSales` value; anything above it is clamped. */
const MAX_MIN_SALES = 100000;

/** Canonical empty state: 2025 HDB at the thin-sample threshold, cheapest first. */
export const EXPLORER_DEFAULTS: ExplorerSelection = {
  property: "hdb",
  period: "year_2025",
  metric: "median_price",
  sort: "median_price",
  direction: "asc",
  minSales: THIN_SAMPLE_THRESHOLD,
  search: "",
  area: null,
  page: 1,
};

/** Longest accepted free-text search (characters, after trimming). */
const MAX_SEARCH_LENGTH = 80;

/** Fields whose change invalidates the current page offset. */
const PAGE_RESET_KEYS: readonly (keyof ExplorerSelection)[] = [
  "property",
  "period",
  "metric",
  "sort",
  "direction",
  "minSales",
  "search",
  "area",
];

/** One of `allowed`, else `fallback` — never a different valid value. */
function pickEnum<T extends string>(
  value: string | null,
  allowed: readonly T[],
  fallback: T,
): T {
  if (value === null) return fallback;
  for (const candidate of allowed) {
    if (candidate === value) return candidate;
  }
  return fallback;
}

/** Non-negative integer text, or `null` when the text is anything else. */
function parseCount(value: string): number | null {
  const trimmed = value.trim();
  if (!/^\d+$/.test(trimmed)) return null;
  const parsed = Number(trimmed);
  return Number.isSafeInteger(parsed) ? parsed : null;
}

/** `scheme://` prefix, used only to recognise a full URL in the input. */
const SCHEME_URL = /^[a-z][a-z0-9+.-]*:\/\//i;

/**
 * Read one `?property=…&period=…` string.
 *
 * Accepts a leading `?`, a bare query string, a full URL (everything before the
 * first `?` is ignored) or an empty string. Malformed percent-encoding is
 * tolerated: `URLSearchParams` decodes leniently, and a decode failure falls
 * back to the defaults rather than throwing.
 */
export function parseExplorerSelection(search: string): ExplorerSelection {
  let query = search.trim();
  if (query.startsWith("?")) {
    query = query.slice(1);
  } else if (SCHEME_URL.test(query)) {
    // A full URL: keep only its query. A bare query string may legitimately
    // contain a "?" inside the search text, so it is never split.
    const questionMark = query.indexOf("?");
    query = questionMark >= 0 ? query.slice(questionMark + 1) : "";
  }

  let params: URLSearchParams;
  try {
    params = new URLSearchParams(query);
  } catch {
    return { ...EXPLORER_DEFAULTS };
  }

  const property = pickEnum(
    params.get("property"),
    EXPLORER_PROPERTIES,
    EXPLORER_DEFAULTS.property,
  );
  const period = pickEnum(
    params.get("period"),
    EXPLORER_PERIODS,
    EXPLORER_DEFAULTS.period,
  );
  const metric = pickEnum(
    params.get("metric"),
    EXPLORER_METRICS,
    EXPLORER_DEFAULTS.metric,
  );
  const sort = pickEnum(
    params.get("sort"),
    EXPLORER_METRICS,
    EXPLORER_DEFAULTS.sort,
  );
  const direction = pickEnum(
    params.get("direction"),
    ["asc", "desc"] as const,
    EXPLORER_DEFAULTS.direction,
  );

  const minSales = parseMinSales(params.get("minSales"));
  const page = parsePage(params.get("page"));

  return {
    property,
    period,
    metric,
    sort,
    direction,
    minSales,
    search: parseSearch(params.get("search")),
    area: parseArea(params.get("area")),
    page,
  };
}

function parseMinSales(value: string | null): number | null {
  if (value === null) return EXPLORER_DEFAULTS.minSales;
  const trimmed = value.trim();
  if (trimmed.toLowerCase() === "all") return null;
  const parsed = parseCount(trimmed);
  if (parsed === null) return EXPLORER_DEFAULTS.minSales;
  return Math.min(parsed, MAX_MIN_SALES);
}

function parsePage(value: string | null): number {
  if (value === null) return EXPLORER_DEFAULTS.page;
  const parsed = parseCount(value);
  return parsed === null || parsed < 1 ? EXPLORER_DEFAULTS.page : parsed;
}

function parseSearch(value: string | null): string {
  if (value === null) return EXPLORER_DEFAULTS.search;
  return value.trim().slice(0, MAX_SEARCH_LENGTH);
}

function parseArea(value: string | null): string | null {
  if (value === null) return EXPLORER_DEFAULTS.area;
  const trimmed = value.trim();
  return trimmed === "" ? null : trimmed.toUpperCase();
}

/**
 * Serialize a selection, omitting every default so the canonical URL stays
 * short. `minSales=all` is written only when it differs from the default.
 */
export function serializeExplorerSelection(
  selection: ExplorerSelection,
): URLSearchParams {
  const params = new URLSearchParams();

  if (selection.property !== EXPLORER_DEFAULTS.property) {
    params.set("property", selection.property);
  }
  if (selection.period !== EXPLORER_DEFAULTS.period) {
    params.set("period", selection.period);
  }
  if (selection.metric !== EXPLORER_DEFAULTS.metric) {
    params.set("metric", selection.metric);
  }
  if (selection.sort !== EXPLORER_DEFAULTS.sort) {
    params.set("sort", selection.sort);
  }
  if (selection.direction !== EXPLORER_DEFAULTS.direction) {
    params.set("direction", selection.direction);
  }
  if (selection.minSales !== EXPLORER_DEFAULTS.minSales) {
    params.set(
      "minSales",
      selection.minSales === null ? "all" : String(selection.minSales),
    );
  }
  if (selection.search !== EXPLORER_DEFAULTS.search) {
    params.set("search", selection.search);
  }
  if (selection.area !== EXPLORER_DEFAULTS.area && selection.area !== null) {
    params.set("area", selection.area);
  }
  if (selection.page !== EXPLORER_DEFAULTS.page) {
    params.set("page", String(selection.page));
  }

  return params;
}

/**
 * Apply a patch and keep the page offset honest: changing a filter, the search,
 * the sample threshold or the sort returns the reader to page 1, unless the
 * patch sets the page explicitly.
 */
export function withSelection(
  current: ExplorerSelection,
  patch: Partial<ExplorerSelection>,
): ExplorerSelection {
  const next: ExplorerSelection = {
    property: patch.property ?? current.property,
    period: patch.period ?? current.period,
    metric: patch.metric ?? current.metric,
    sort: patch.sort ?? current.sort,
    direction: patch.direction ?? current.direction,
    minSales: patch.minSales !== undefined ? patch.minSales : current.minSales,
    search: patch.search ?? current.search,
    area: patch.area !== undefined ? patch.area : current.area,
    page: patch.page ?? current.page,
  };

  if (patch.page === undefined) {
    const changed = PAGE_RESET_KEYS.some((key) => next[key] !== current[key]);
    if (changed) next.page = EXPLORER_DEFAULTS.page;
  }

  return next;
}
