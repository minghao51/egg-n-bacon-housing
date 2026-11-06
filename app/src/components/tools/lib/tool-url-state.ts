/**
 * URL state for the decision-tools workspace (slice S8).
 *
 * Shared by `/research/tools` and the legacy `/dashboard/trends` wrapper. Pure
 * — no React, no DOM at module scope — so the workspace can read the address
 * bar *before* its first commit instead of serialising defaults over an
 * incoming deep link (the S1 lifecycle fix, reused from S7).
 *
 * Owned query keys:
 * - `tool` — which of the four tools is open (`financing` by default).
 * - `ref`, `rt`, `rv` — the **named observed reference** a financing scenario
 *   was imported from: canonical planning-area id, property type, and a version
 *   tag so a future change cannot misread an old link.
 *
 * Loan inputs are deliberately absent: price after a manual edit, income,
 * down payment, term and rate are local component state only, and no input is
 * written to the URL, analytics or telemetry.
 */

export type ToolId = "financing" | "lease" | "mrt" | "spatial";

export const TOOL_IDS: readonly ToolId[] = [
  "financing",
  "lease",
  "mrt",
  "spatial",
];

export const TOOL_LABELS: Readonly<Record<ToolId, string>> = {
  financing: "Financing scenario",
  lease: "Lease bands",
  mrt: "MRT / CBD",
  spatial: "Spatial patterns",
};

/** Version tag for the reference-import parameters. */
export const TOOL_REFERENCE_VERSION = "1";

export type ToolProperty = "hdb" | "ec" | "condo";

export const TOOL_PROPERTIES: readonly ToolProperty[] = ["hdb", "ec", "condo"];

export const TOOL_PROPERTY_LABELS: Readonly<Record<ToolProperty, string>> = {
  hdb: "HDB",
  ec: "EC",
  condo: "Condominium",
};

export interface ToolReferenceSelection {
  /** Canonical uppercase planning-area id, e.g. `TAMPINES`. */
  area: string;
  property: ToolProperty;
}

export interface ToolQueryState {
  tool: ToolId;
  /** `null` means the documented default scenario (Tampines HDB, 2025). */
  reference: ToolReferenceSelection | null;
}

/** Every query key this workspace owns (and may therefore delete). */
export const TOOL_QUERY_KEYS = ["tool", "ref", "rt", "rv"] as const;

export const DEFAULT_TOOL_STATE: ToolQueryState = {
  tool: "financing",
  reference: null,
};

function isToolId(value: string | null): value is ToolId {
  return value !== null && TOOL_IDS.includes(value as ToolId);
}

function isToolProperty(value: string | null): value is ToolProperty {
  return value !== null && TOOL_PROPERTIES.includes(value as ToolProperty);
}

/**
 * Read the tool and the named reference out of a query string.
 *
 * Unknown values never throw and never invent state: an unknown `tool` falls
 * back to `financing`, and a reference is only accepted when all three of
 * `rv`/`ref`/`rt` are present and valid. A partial reference is ignored
 * entirely, because importing the wrong area's price would be worse than
 * showing the documented default.
 */
export function parseToolQuery(search: string): ToolQueryState {
  const params = new URLSearchParams(
    search.startsWith("?") ? search.slice(1) : search,
  );

  const tool = isToolId(params.get("tool"))
    ? (params.get("tool") as ToolId)
    : DEFAULT_TOOL_STATE.tool;

  const area = (params.get("ref") ?? "").trim();
  const property = params.get("rt");
  const reference =
    params.get("rv") === TOOL_REFERENCE_VERSION &&
    area !== "" &&
    isToolProperty(property)
      ? { area: area.toUpperCase(), property }
      : null;

  return { tool, reference };
}

/** Serialise the state, omitting defaults. */
export function serializeToolQuery(state: ToolQueryState): string {
  const params = new URLSearchParams();
  if (state.tool !== DEFAULT_TOOL_STATE.tool) params.set("tool", state.tool);
  if (state.reference !== null) {
    params.set("ref", state.reference.area);
    params.set("rt", state.reference.property);
    params.set("rv", TOOL_REFERENCE_VERSION);
  }
  return params.toString();
}

/**
 * Apply the state to a live URL: drop only the keys this workspace owns, then
 * write the ones it emits. Parameters owned by other surfaces survive.
 */
export function applyToolQuery(href: string, state: ToolQueryState): string {
  let url: URL;
  try {
    url = new URL(href);
  } catch {
    // An unparseable href is not ours to repair; leave the address alone.
    return href;
  }
  TOOL_QUERY_KEYS.forEach((key) => url.searchParams.delete(key));
  const next = new URLSearchParams(serializeToolQuery(state));
  next.forEach((value, key) => url.searchParams.set(key, value));
  return url.toString();
}
