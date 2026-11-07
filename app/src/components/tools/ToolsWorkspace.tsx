/**
 * Decision-tools workspace island (slice S8).
 *
 * Shared by `/research/tools` and the legacy `/dashboard/trends` wrapper, which
 * both render `components/tools/ToolsSurface.astro`.
 *
 * Four tools, four output contracts:
 * - financing — illustrative amortization over user inputs, with a named
 *   observed reference price (build-time `map_metrics.year_2025_*` table);
 * - lease — stored archive band lookup, signed statistics, endpoint policy
 *   surfaced, no forecast or safe/cliff recommendation;
 * - MRT/CBD — controls retained, total-dollar estimate withheld;
 * - spatial — validated label inspection only, no allocation or BUY/SELL.
 *
 * State: the address bar is read once, before the first commit (the island is
 * client-only) and written back with `replaceState`. Only `tool` and the named
 * reference (`ref`/`rt`/`rv`) are serialised; loan inputs never leave the tab.
 *
 * S8-F1: the financing draft lives here too, not in `FinancingScenario`, so
 * selecting another tool no longer resets it. The observed reference price is
 * imported only when the resolved reference key changes, so a manual price
 * survives a tool switch and a reload still starts from the defaults.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import FinancingScenario, { type ToolsReleaseInfo } from "./FinancingScenario";
import LeaseBands from "./LeaseBands";
import MrtCbdInspection from "./MrtCbdInspection";
import SpatialInspection from "./SpatialInspection";
import ToolErrorBoundary from "./ToolErrorBoundary";
import {
  applyReferenceToDraft,
  createFinancingDraftState,
  mergeDraft,
  type FinancingDraft,
  type FinancingDraftState,
} from "./lib/financing-draft";
import {
  defaultReferenceEntry,
  resolveReference,
  type ReferencePriceTable,
  type ReferenceSourceStatus,
} from "./lib/tool-reference";
import {
  applyToolQuery,
  parseToolQuery,
  TOOL_LABELS,
  type ToolId,
  type ToolQueryState,
  type ToolReferenceSelection,
} from "./lib/tool-url-state";

export interface ToolsWorkspaceProps {
  /** Deployment base path, resolved once by the Astro shell. */
  baseUrl: string;
  referenceTable: ReferencePriceTable;
  /** Whether the reference asset could be read at build time. */
  referenceSource: ReferenceSourceStatus;
  release: ToolsReleaseInfo;
  /** Raw `interactive_tools/*` payloads; validated per tool before rendering. */
  lease: unknown;
  mrt: unknown;
  spatial: unknown;
}

const TOOL_SUMMARIES: Readonly<Record<ToolId, string>> = {
  financing: "Illustrative monthly payment from editable assumptions.",
  lease: "Stored remaining-lease bands with signed statistics.",
  mrt: "Stored coefficients and formula, total withheld.",
  spatial: "Stored cluster labels for inspection only.",
};

const TOOL_ORDER: readonly ToolId[] = ["financing", "lease", "mrt", "spatial"];

/** Read the state once, before the first commit. */
function readInitialState(): ToolQueryState {
  if (typeof window === "undefined") {
    // The island is client-only; this only guards a stray server render.
    return parseToolQuery("");
  }
  return parseToolQuery(window.location.search);
}

export default function ToolsWorkspace({
  baseUrl,
  referenceTable,
  referenceSource,
  release,
  lease,
  mrt,
  spatial,
}: ToolsWorkspaceProps) {
  const [state, setState] = useState<ToolQueryState>(readInitialState);
  const [financing, setFinancing] = useState<FinancingDraftState>(() =>
    createFinancingDraftState(
      resolveReference(referenceTable, state.reference).entry,
    ),
  );
  const tabRefs = useRef<Array<HTMLButtonElement | null>>([]);

  // One resolved reference for the workspace and the financing tool. The entry
  // object only changes when the table or the selection changes.
  const reference = useMemo(
    () => resolveReference(referenceTable, state.reference),
    [referenceTable, state.reference],
  );

  // A new named reference (select, deep link, back/forward) imports that
  // area's observed median exactly once. `applyReferenceToDraft` is a no-op
  // when the key is unchanged, which is what keeps a manual price manual across
  // tool switches — the draft survives, but nothing is re-imported over it.
  useEffect(() => {
    setFinancing((current) => applyReferenceToDraft(current, reference.entry));
  }, [reference.entry]);

  const selectTool = useCallback((tool: ToolId) => {
    setState((current) =>
      current.tool === tool ? current : { ...current, tool },
    );
  }, []);

  const selectReference = useCallback(
    (reference: ToolReferenceSelection | null) => {
      setState((current) => ({ ...current, reference }));
    },
    [],
  );

  const updateFinancingDraft = useCallback((patch: Partial<FinancingDraft>) => {
    setFinancing((current) => ({
      ...current,
      draft: mergeDraft(current.draft, patch),
    }));
  }, []);

  const resetFinancing = useCallback(() => {
    setState((current) => ({ ...current, reference: null }));
    setFinancing(() =>
      createFinancingDraftState(defaultReferenceEntry(referenceTable)),
    );
  }, [referenceTable]);

  // Keep the address bar in step with the state. The serializer omits defaults,
  // so a deep link is canonicalised rather than treated as new state, and
  // parameters other surfaces own are never touched.
  useEffect(() => {
    if (typeof window === "undefined") return;
    const next = applyToolQuery(window.location.href, state);
    if (next !== window.location.href) {
      window.history.replaceState({}, "", next);
    }
  }, [state]);

  // Back/forward: the URL is the source of truth.
  useEffect(() => {
    if (typeof window === "undefined") return;
    const handlePopState = () => {
      setState(parseToolQuery(window.location.search));
    };
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  const onTabKeyDown = (
    event: React.KeyboardEvent<HTMLButtonElement>,
    index: number,
  ) => {
    let nextIndex: number | null = null;
    if (event.key === "ArrowRight") {
      nextIndex = (index + 1) % TOOL_ORDER.length;
    } else if (event.key === "ArrowLeft") {
      nextIndex = (index - 1 + TOOL_ORDER.length) % TOOL_ORDER.length;
    } else if (event.key === "Home") {
      nextIndex = 0;
    } else if (event.key === "End") {
      nextIndex = TOOL_ORDER.length - 1;
    }
    if (nextIndex === null) return;
    event.preventDefault();
    selectTool(TOOL_ORDER[nextIndex]);
    tabRefs.current[nextIndex]?.focus();
  };

  return (
    <div className="mt-8">
      <div className="flex flex-col gap-4 border-b border-border pb-4 sm:flex-row sm:items-end sm:justify-between">
        <div className="w-full sm:hidden">
          <label
            htmlFor="tool-select"
            className="block text-sm font-bold text-foreground"
          >
            Tool
          </label>
          <select
            id="tool-select"
            value={state.tool}
            onChange={(event) => selectTool(event.target.value as ToolId)}
            className="mt-1 w-full rounded border border-input bg-background px-3 py-2 text-sm text-foreground"
          >
            {TOOL_ORDER.map((tool) => (
              <option key={tool} value={tool}>
                {TOOL_LABELS[tool]}
              </option>
            ))}
          </select>
        </div>

        <div
          role="tablist"
          aria-label="Decision tools"
          className="hidden flex-wrap gap-2 sm:flex"
        >
          {TOOL_ORDER.map((tool, index) => {
            const selected = state.tool === tool;
            return (
              <button
                key={tool}
                ref={(element) => {
                  tabRefs.current[index] = element;
                }}
                id={`tool-tab-${tool}`}
                type="button"
                role="tab"
                aria-selected={selected}
                aria-controls="tool-panel"
                tabIndex={selected ? 0 : -1}
                onClick={() => selectTool(tool)}
                onKeyDown={(event) => onTabKeyDown(event, index)}
                className={`rounded border px-3 py-2 text-left text-sm transition-colors ${
                  selected
                    ? "border-[hsl(var(--rust))] bg-[hsl(var(--secondary))] font-bold text-foreground"
                    : "border-border bg-card text-muted-foreground hover:bg-muted/40"
                }`}
              >
                <span className="block">{TOOL_LABELS[tool]}</span>
                <span className="mt-1 block text-xs font-normal text-muted-foreground">
                  {TOOL_SUMMARIES[tool]}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      <div
        id="tool-panel"
        role="tabpanel"
        aria-label={TOOL_LABELS[state.tool]}
        tabIndex={-1}
        className="mt-6"
      >
        <ToolErrorBoundary key={state.tool}>
          {state.tool === "financing" ? (
            <FinancingScenario
              baseUrl={baseUrl}
              referenceTable={referenceTable}
              referenceSource={referenceSource}
              release={release}
              referenceSelection={state.reference}
              onReferenceChange={selectReference}
              referenceEntry={reference.entry}
              referenceMissing={reference.missingRequested}
              draft={financing.draft}
              onDraftChange={updateFinancingDraft}
              onReset={resetFinancing}
            />
          ) : null}
          {state.tool === "lease" ? (
            <LeaseBands data={lease} baseUrl={baseUrl} />
          ) : null}
          {state.tool === "mrt" ? (
            <MrtCbdInspection data={mrt} baseUrl={baseUrl} />
          ) : null}
          {state.tool === "spatial" ? (
            <SpatialInspection data={spatial} />
          ) : null}
        </ToolErrorBoundary>
      </div>
    </div>
  );
}
