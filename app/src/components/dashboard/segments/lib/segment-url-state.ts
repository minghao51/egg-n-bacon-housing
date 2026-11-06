/**
 * URL state for the segment workspace (both `/research/segments` and the
 * legacy `/dashboard/segments` wrapper).
 *
 * Pure — no React, no DOM access at module scope — so the parse/serialize
 * contract is testable and the workspace can read the address bar *before* its
 * first commit instead of serialising defaults over an incoming deep link.
 *
 * Owned query keys:
 * - `persona`, `tab`, `segment`, `segments`, `area` — the pre-S7 IDs, unchanged.
 * - `fv`, `psf`, `types`, `regions`, `hotspot` — the visible constraints, added
 *   deliberately and versioned: they are only read when `fv=1`, so an old link
 *   keeps its persona preset semantics.
 */

import type {
  FilterState,
  Persona,
  PropertyType,
  Region,
  SpatialCluster,
} from "@/types/segments";
import { filtersDifferFromPreset, presetFilters } from "./segment-presets";

export type SegmentTab = "discover" | "investigate" | "compare";

export const SEGMENT_TABS: readonly SegmentTab[] = [
  "discover",
  "investigate",
  "compare",
];

/** Version tag for the constraint parameters. */
export const SEGMENT_CONSTRAINTS_VERSION = "1";

export type PersonaLike = Persona;

export const SEGMENT_PERSONAS: readonly Persona[] = [
  "all",
  "investor",
  "first-time-buyer",
  "upgrader",
];

const PROPERTY_TYPES: readonly PropertyType[] = ["HDB", "Condominium", "EC"];
const REGIONS: readonly Region[] = ["CCR", "RCR", "OCR"];
const SPATIAL_CLUSTERS: readonly SpatialCluster[] = ["HH", "HL", "LH", "LL"];
const PSF_BOUNDS = { min: 300, max: 1500 } as const;
/** Two-to-four segments may be shortlisted; more is truncated, never merged. */
export const SEGMENT_COMPARISON_MIN = 2;
export const SEGMENT_COMPARISON_MAX = 4;

/** Every query key this workspace owns (and may therefore delete). */
export const SEGMENT_QUERY_KEYS = [
  "persona",
  "tab",
  "segment",
  "segments",
  "area",
  "fv",
  "psf",
  "types",
  "regions",
  "hotspot",
] as const;

export interface SegmentQueryState {
  persona: Persona;
  tab: SegmentTab;
  segmentId: string | null;
  comparisonIds: string[];
  area: string | null;
  filters: FilterState;
}

export interface ParseSegmentQueryOptions {
  /** When supplied, unknown segment IDs are dropped instead of kept. */
  knownSegmentIds?: readonly string[];
}

function isPersona(value: string | null): value is Persona {
  return value !== null && SEGMENT_PERSONAS.includes(value as Persona);
}

function isTab(value: string | null): value is SegmentTab {
  return value !== null && SEGMENT_TABS.includes(value as SegmentTab);
}

function parsePsfRange(value: string | null): [number, number] | null {
  if (!value) return null;
  const match = /^(\d{3,4})-(\d{3,4})$/.exec(value.trim());
  if (!match) return null;
  const min = Number(match[1]);
  const max = Number(match[2]);
  if (
    !Number.isFinite(min) ||
    !Number.isFinite(max) ||
    min < PSF_BOUNDS.min ||
    max > PSF_BOUNDS.max ||
    min >= max
  ) {
    return null;
  }
  return [min, max];
}

function parseList<T extends string>(
  value: string | null,
  allowed: readonly T[],
): T[] | null {
  if (!value) return null;
  const parsed = value
    .split(",")
    .map((entry) => entry.trim())
    .filter((entry): entry is T => allowed.includes(entry as T));
  return parsed.length > 0 ? Array.from(new Set(parsed)) : null;
}

function parseHotspot(value: string | null): SpatialCluster | "all" | null {
  if (value === "all") return "all";
  return value !== null && SPATIAL_CLUSTERS.includes(value as SpatialCluster)
    ? (value as SpatialCluster)
    : null;
}

/** The default workspace: persona `all`, discover tab, no selection. */
export function defaultSegmentQueryState(): SegmentQueryState {
  return {
    persona: "all",
    tab: "discover",
    segmentId: null,
    comparisonIds: [],
    area: null,
    filters: presetFilters("all"),
  };
}

/**
 * Read the segment selection out of a query string.
 *
 * Unknown or malformed values never throw and never invent state: each field
 * falls back to its own default, and constraints fall back field-by-field to
 * the persona preset.
 */
export function parseSegmentQuery(
  search: string,
  options: ParseSegmentQueryOptions = {},
): SegmentQueryState {
  const params = new URLSearchParams(
    search.startsWith("?") ? search.slice(1) : search,
  );
  const persona = isPersona(params.get("persona"))
    ? (params.get("persona") as Persona)
    : "all";
  const tab = isTab(params.get("tab"))
    ? (params.get("tab") as SegmentTab)
    : "discover";

  const known = options.knownSegmentIds;
  const isKnown = (id: string) => !known || known.includes(id);

  const rawSegment = params.get("segment")?.trim() ?? "";
  const segmentId =
    rawSegment !== "" && isKnown(rawSegment) ? rawSegment : null;

  const comparisonIds = Array.from(
    new Set(
      (params.get("segments") ?? "")
        .split(",")
        .map((entry) => entry.trim())
        .filter((entry) => entry !== "" && isKnown(entry)),
    ),
  ).slice(0, SEGMENT_COMPARISON_MAX);

  const rawArea = params.get("area")?.trim() ?? "";
  const area = rawArea === "" ? null : rawArea.toUpperCase();

  const filters = presetFilters(persona);
  if (params.get("fv") === SEGMENT_CONSTRAINTS_VERSION) {
    const psf = parsePsfRange(params.get("psf"));
    const types = parseList(params.get("types"), PROPERTY_TYPES);
    const regions = parseList(params.get("regions"), REGIONS);
    const hotspot = parseHotspot(params.get("hotspot"));
    if (psf) filters.budgetRange = psf;
    if (types) filters.propertyTypes = types;
    if (regions) filters.locations = regions;
    if (hotspot !== null) filters.hotspotFilter = hotspot;
  }

  return { persona, tab, segmentId, comparisonIds, area, filters };
}

/**
 * Serialise the selection, omitting defaults.
 *
 * Constraints are written only when they differ from the persona preset, so a
 * plain persona link stays short and a reset returns to preset semantics.
 */
export function serializeSegmentQuery(state: SegmentQueryState): string {
  const params = new URLSearchParams();

  if (state.persona !== "all") params.set("persona", state.persona);
  if (state.tab !== "discover") params.set("tab", state.tab);
  if (state.segmentId) params.set("segment", state.segmentId);
  if (state.comparisonIds.length > 0) {
    params.set("segments", state.comparisonIds.join(","));
  }
  if (state.area) params.set("area", state.area);

  if (filtersDifferFromPreset(state.filters, state.persona)) {
    params.set("fv", SEGMENT_CONSTRAINTS_VERSION);
    params.set("psf", state.filters.budgetRange.join("-"));
    params.set("types", state.filters.propertyTypes.join(","));
    params.set("regions", state.filters.locations.join(","));
    params.set("hotspot", state.filters.hotspotFilter);
  }

  return params.toString();
}

/**
 * Apply the selection to a live URL: drop only the keys this workspace owns,
 * then write the ones it emits. Parameters owned by other surfaces survive.
 */
export function applySegmentQuery(
  href: string,
  state: SegmentQueryState,
): string {
  let url: URL;
  try {
    url = new URL(href);
  } catch {
    // An unparseable href is not ours to repair; leave the address alone.
    return href;
  }
  SEGMENT_QUERY_KEYS.forEach((key) => url.searchParams.delete(key));
  const next = new URLSearchParams(serializeSegmentQuery(state));
  next.forEach((value, key) => url.searchParams.set(key, value));
  return url.toString();
}
