/**
 * View switcher and accessible table for `/explore`.
 *
 * One derived `ExplorerDataset` is the single source of truth for every
 * representation: the list, the map and this table all read the same rows, so
 * they cannot disagree about the selected property, period, sample threshold or
 * search text. This module owns the tablist, the table markup and nothing else —
 * the view value itself lives in the workspace, which owns the address bar.
 *
 * The table is not a duplicate rendering for convenience: it is the
 * always-available reading surface. It works with the map geometry missing, and
 * it is what a reader is pointed at when the map cannot be drawn.
 */

import { useRef, type KeyboardEvent } from "react";
import type {
  ExplorerMetric,
  ExplorerSelection,
} from "@/utils/explorer-selection";
import type { ExplorerDataset, ExplorerRow } from "@/utils/observed-rows";
import { areaHref } from "@/utils/area-links";
import ExplorerList, { type ExplorerListProps } from "./ExplorerList";
import ExplorerMap from "./ExplorerMap";
import { METRIC_OPTIONS, periodLabel, propertyNoun } from "./ExplorerSettings";

/** The three representations of the same dataset. */
export type ExplorerViewKind = "list" | "map" | "table";

/** Query parameter that carries the view. Not part of `ExplorerSelection`. */
export const EXPLORER_VIEW_QUERY_KEY = "view";

/** The documented default, and the value the URL omits. */
export const EXPLORER_VIEW_DEFAULT: ExplorerViewKind = "list";

/**
 * Tab labels. The design sheet's first tab is "Chart + list"; this slice has no
 * chart, so the label says what the tab actually shows.
 */
export const EXPLORER_VIEW_TABS: readonly {
  value: ExplorerViewKind;
  label: string;
}[] = [
  { value: "list", label: "List" },
  { value: "map", label: "Map" },
  { value: "table", label: "Table" },
];

/** Shared id so every tab controls the single, swapped panel. */
const PANEL_ID = "explorer-view-panel";

function tabId(view: ExplorerViewKind): string {
  return `explorer-tab-${view}`;
}

/**
 * Parse a `?view=` value with the same fallback rule as the rest of the
 * explorer state: an unknown or malformed value lands on the documented
 * default, never on a different valid view.
 */
export function parseExplorerView(value: string | null): ExplorerViewKind {
  if (value === null) return EXPLORER_VIEW_DEFAULT;
  // Exact matching, like every other enumerated query parameter: a misspelt or
  // differently-cased value falls back to the documented default instead of
  // being silently coerced.
  for (const tab of EXPLORER_VIEW_TABS) {
    if (tab.value === value) return tab.value;
  }
  return EXPLORER_VIEW_DEFAULT;
}

/** The value to write into the address bar, or `null` for the default. */
export function serializeExplorerView(view: ExplorerViewKind): string | null {
  return view === EXPLORER_VIEW_DEFAULT ? null : view;
}

/**
 * Display value for one metric. `null` is never rendered as a number: the
 * caller decides how to say "not published".
 */
function formatTableValue(metric: ExplorerMetric, value: number): string {
  const digits = Math.round(value).toLocaleString("en-US");
  if (metric === "median_psf") return `S$${digits} psf`;
  if (metric === "volume") return digits;
  return `S$${digits}`;
}

/** Fieldnote link for one row, carrying the current property and period. */
function rowHref(row: ExplorerRow, selection: ExplorerSelection): string {
  const base = import.meta.env.BASE_URL.replace(/\/$/, "");
  return `${base}${areaHref(row.slug, selection)}`;
}

function TableCell({
  row,
  metric,
}: {
  row: ExplorerRow;
  metric: ExplorerMetric;
}) {
  const value =
    metric === "median_price"
      ? row.medianPrice
      : metric === "median_psf"
        ? row.medianPsf
        : row.volume;

  if (value === null) {
    return (
      <td className="px-3 py-2 text-right text-muted-foreground">
        <span title="Not published for this area in the selected section">
          N/A
        </span>
      </td>
    );
  }

  return (
    <td className="px-3 py-2 text-right text-foreground" data-numeric>
      {formatTableValue(metric, value)}
    </td>
  );
}

/**
 * The table view: every area the current filters keep, with the three observed
 * metrics side by side. No paging, so the whole selection is readable (and
 * printable) in one pass.
 */
function ExplorerTable({
  dataset,
  selection,
}: {
  dataset: ExplorerDataset;
  selection: ExplorerSelection;
}) {
  const rows = dataset.filtered;
  const metricOption =
    METRIC_OPTIONS.find((option) => option.value === selection.metric) ??
    METRIC_OPTIONS[0];

  return (
    <div className="min-w-0">
      <h2 className="text-2xl font-bold text-foreground">
        {periodLabel(dataset.period)} {propertyNoun(dataset.property)}{" "}
        {metricOption.noun}
      </h2>
      <p className="mt-1 text-sm text-muted-foreground">
        Every area the current settings keep, with all three observed metrics.
      </p>

      <div className="mt-4 overflow-x-auto">
        <table className="w-full min-w-[36rem] border-collapse text-sm">
          <caption className="pb-2 text-left text-xs text-muted-foreground">
            {`Observed values for ${rows.length} ${
              rows.length === 1 ? "planning area" : "planning areas"
            } · ${propertyNoun(dataset.property)} · ${periodLabel(
              dataset.period,
            )} · `}
            <code className="font-mono">map_metrics.{dataset.section}</code>
            {
              ". N/A means the section does not publish that value for the area."
            }
          </caption>
          <thead>
            <tr className="border-b border-border text-left">
              <th scope="col" className="px-3 py-2 font-bold text-foreground">
                Planning area
              </th>
              <th
                scope="col"
                className="px-3 py-2 text-right font-bold text-foreground"
              >
                Median price
              </th>
              <th
                scope="col"
                className="px-3 py-2 text-right font-bold text-foreground"
              >
                Median PSF
              </th>
              <th
                scope="col"
                className="px-3 py-2 text-right font-bold text-foreground"
              >
                Transactions
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {rows.map((row) => (
              <tr key={row.areaId}>
                <th
                  scope="row"
                  className="px-3 py-2 text-left font-bold text-foreground"
                >
                  <a
                    href={rowHref(row, selection)}
                    className="text-foreground underline-offset-4 hover:underline"
                  >
                    {row.areaName}
                  </a>
                </th>
                <TableCell row={row} metric="median_price" />
                <TableCell row={row} metric="median_psf" />
                <TableCell row={row} metric="volume" />
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {rows.length === 0 ? (
        <p className="mt-4 rounded border border-border bg-muted px-3 py-2 text-sm text-muted-foreground">
          No planning areas match these settings, so the table has no rows.
          Widen the period, clear the search or lower the sample threshold.
        </p>
      ) : null}
    </div>
  );
}

export interface ExplorerViewProps extends ExplorerListProps {
  view: ExplorerViewKind;
  onViewChange: (view: ExplorerViewKind) => void;
}

export default function ExplorerView({
  view,
  onViewChange,
  ...listProps
}: ExplorerViewProps) {
  const { dataset, selection } = listProps;
  const tabRefs = useRef<
    Partial<Record<ExplorerViewKind, HTMLButtonElement | null>>
  >({});

  /** Move selection to another tab and put focus on it, per the tab pattern. */
  const selectAndFocus = (next: ExplorerViewKind) => {
    onViewChange(next);
    tabRefs.current[next]?.focus();
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLButtonElement>) => {
    const current = EXPLORER_VIEW_TABS.findIndex((tab) => tab.value === view);
    if (current < 0) return;

    let nextIndex: number | null = null;
    if (event.key === "ArrowRight" || event.key === "ArrowDown") {
      nextIndex = (current + 1) % EXPLORER_VIEW_TABS.length;
    } else if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
      nextIndex =
        (current - 1 + EXPLORER_VIEW_TABS.length) % EXPLORER_VIEW_TABS.length;
    } else if (event.key === "Home") {
      nextIndex = 0;
    } else if (event.key === "End") {
      nextIndex = EXPLORER_VIEW_TABS.length - 1;
    }

    if (nextIndex === null) return;
    event.preventDefault();
    selectAndFocus(EXPLORER_VIEW_TABS[nextIndex].value);
  };

  return (
    <div className="min-w-0">
      <div
        role="tablist"
        aria-label="Explorer view"
        className="flex flex-wrap gap-2"
      >
        {EXPLORER_VIEW_TABS.map((tab) => {
          const selected = tab.value === view;
          return (
            <button
              key={tab.value}
              ref={(element) => {
                tabRefs.current[tab.value] = element;
              }}
              type="button"
              role="tab"
              id={tabId(tab.value)}
              aria-selected={selected}
              aria-controls={PANEL_ID}
              tabIndex={selected ? 0 : -1}
              onClick={() => onViewChange(tab.value)}
              onKeyDown={handleKeyDown}
              className={`rounded border px-3 py-2 text-sm ${
                selected
                  ? "border-[hsl(var(--teal))] bg-accent font-bold text-[hsl(var(--teal))]"
                  : "border-input bg-card font-medium text-foreground"
              }`}
            >
              {tab.label}
            </button>
          );
        })}
      </div>

      <div
        role="tabpanel"
        id={PANEL_ID}
        aria-labelledby={tabId(view)}
        className="mt-4"
      >
        {view === "list" ? <ExplorerList {...listProps} /> : null}
        {view === "map" ? (
          <ExplorerMap dataset={dataset} selection={selection} />
        ) : null}
        {view === "table" ? (
          <ExplorerTable dataset={dataset} selection={selection} />
        ) : null}
      </div>
    </div>
  );
}
