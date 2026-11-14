/**
 * Observed-comparison list for `/explore`.
 *
 * Consumes one already-derived `ExplorerDataset` (rows, filtered rows, thin
 * count, national baseline) and owns only presentation: the sort/search
 * controls, page slicing, number formatting and the unavailable-value states.
 * The dataset is never re-filtered or re-sorted here, so the list and any
 * sibling view of the same dataset cannot disagree.
 */

import type { ReactNode } from "react";
import {
  THIN_SAMPLE_THRESHOLD,
  type ExplorerMetric,
  type ExplorerSelection,
  type ExplorerSort,
} from "@/utils/explorer-selection";
import type { ExplorerDataset, ExplorerRow } from "@/utils/observed-rows";
import { ACTIVITY_SALE_FLOOR } from "@/utils/area-activity";
import type { ReleaseStatus } from "@/utils/release-manifest";
import { areaHref } from "@/utils/area-links";
import {
  METRIC_OPTIONS,
  propertyNoun,
  metricNoun,
} from "./ExplorerSettings";

/** Desktop page size; the mobile layout shows four rows of the same page. */
const PAGE_SIZE = 12;

const COMPANION_METRICS: Record<ExplorerMetric, readonly ExplorerMetric[]> = {
  median_price: ["volume", "median_psf"],
  median_psf: ["volume", "median_price"],
  volume: ["median_price", "median_psf"],
};

/**
 * One row's prior-year activity, as a sentence (RF10).
 *
 * Neutral by construction: a signed percentage or the reason it cannot be
 * computed. No "up/down", "hot/cold" or score wording, and a missing
 * comparison is stated rather than shown as 0%.
 */
function activitySentence(row: ExplorerRow): string | null {
  const activity = row.activity;
  if (activity === undefined || activity === null) return null;
  const belowFloor = activity.eligible
    ? ""
    : ` · below the ${ACTIVITY_SALE_FLOOR}-sale floor`;
  if (activity.changePercent === null || activity.priorCount === null) {
    return `Prior-year comparison: ${activity.reason ?? "not published"}${belowFloor}`;
  }
  const sign = activity.changePercent >= 0 ? "+" : "−";
  const prior = activity.priorCount.toLocaleString("en-US");
  return `Prior-year same window: ${prior} sales (${sign}${Math.abs(
    activity.changePercent,
  ).toFixed(1)}%)${belowFloor}`;
}

function formatMetricValue(metric: ExplorerMetric, value: number): string {
  const digits = Math.round(value).toLocaleString("en-US");
  if (metric === "volume") return `${digits} sales`;
  if (metric === "median_psf") return `S$${digits} psf`;
  return `S$${digits}`;
}

/**
 * The fieldnote link for one row, with the current property/period carried in
 * the query.
 *
 * The link shape is owned by `areaHref()` in `src/utils/area-links.ts`, which
 * is deliberately free of Node imports so the island can use it directly.
 */
function rowHref(row: ExplorerRow, selection: ExplorerSelection): string {
  const base = import.meta.env.BASE_URL.replace(/\/$/, "");
  return `${base}${areaHref(row.slug, selection)}`;
}

function rowValue(row: ExplorerRow, metric: ExplorerMetric): number | null {
  if (metric === "median_price") return row.medianPrice;
  if (metric === "median_psf") return row.medianPsf;
  return row.volume;
}

/**
 * Why a cell shows "N/A" instead of a number. Distinguishes a metric the window
 * does not publish from a subset the exporter wrote as empty or a verified
 * no-sales window, so a reader never sees `0` standing in for missing data.
 */
function unavailableReason(row: ExplorerRow, metric: ExplorerMetric): string {
  const noun = metricNoun(metric);
  const legacy = row.observation;

  if (legacy !== undefined) {
    const entry = legacy.metrics.find((item) => item.metric === metric);
    if (entry === undefined) {
      return `${noun} is not published for ${row.areaName} in this selection.`;
    }
    if (entry.status === "empty") {
      return `${row.areaName} has no transactions in this section, so no ${noun} is published.`;
    }
    return `${noun} is not published for ${row.areaName} in ${row.sectionLabel}.`;
  }

  if (row.packObservation?.status === "no-sales") {
    return `No sales were recorded for ${row.areaName} in ${row.sectionLabel}, so no ${noun} is published.`;
  }
  return `${noun} is not published for ${row.areaName} in ${row.sectionLabel}.`;
}

function MetricCell({
  row,
  metric,
  className,
}: {
  row: ExplorerRow;
  metric: ExplorerMetric;
  className: string;
}) {
  const value = rowValue(row, metric);
  if (value === null) {
    const reason = unavailableReason(row, metric);
    return (
      <span className={className} title={reason}>
        <span aria-hidden="true">N/A</span>
        <span className="sr-only">{reason}</span>
      </span>
    );
  }
  return (
    <span className={className} data-numeric>
      {formatMetricValue(metric, value)}
    </span>
  );
}

export interface ExplorerListProps {
  dataset: ExplorerDataset;
  selection: ExplorerSelection;
  releaseStatus: ReleaseStatus;
  nationalLoading: boolean;
  nationalError: string | null;
  onRetryNational: () => void;
  onChange: (patch: Partial<ExplorerSelection>) => void;
  onReset: () => void;
}

export default function ExplorerList({
  dataset,
  selection,
  releaseStatus,
  nationalLoading,
  nationalError,
  onRetryNational,
  onChange,
  onReset,
}: ExplorerListProps) {
  const rows = dataset.filtered;
  const pageCount = Math.max(1, Math.ceil(rows.length / PAGE_SIZE));
  const page = Math.min(Math.max(selection.page, 1), pageCount);
  const start = (page - 1) * PAGE_SIZE;
  const pageRows = rows.slice(start, start + PAGE_SIZE);

  const metricOption =
    METRIC_OPTIONS.find((option) => option.value === selection.metric) ??
    METRIC_OPTIONS[0];
  const sortOption =
    METRIC_OPTIONS.find((option) => option.value === selection.sort) ??
    METRIC_OPTIONS[0];

  const national =
    dataset.national?.find((entry) => entry.metric === selection.metric) ?? null;

  /** The national line: the value is the same kind of number, the source differs. */
  const nationalValue = (sourceLabel: string, source: string) => (
    <p className="mt-3 rounded border border-border bg-accent px-3 py-2 text-sm text-foreground">
      <span className="font-bold">
        National {propertyNoun(dataset.property)} {metricNoun(selection.metric)}:{" "}
        {formatMetricValue(selection.metric, national!.value!)}
      </span>
      <span className="text-muted-foreground">
        {" "}
        &middot; {sourceLabel}{" "}
        <code className="font-mono">{source}</code>
      </span>
    </p>
  );

  const nationalNotPublished = (source: string) => (
    <p className="mt-3 rounded border border-border bg-muted px-3 py-2 text-sm text-muted-foreground">
      The national value for <code className="font-mono">{source}</code> is not
      published for this selection, so no baseline is shown.
    </p>
  );

  let baselineBlock: ReactNode;
  if (dataset.kind === "pack") {
    // The pack carries its own national scope and its own disposition, so the
    // legacy asset-identity checks below do not apply to this window.
    const coverageNote = dataset.national?.[0]?.note ?? null;
    baselineBlock = (
      <>
        {national !== null && national.value !== null
          ? nationalValue("from the same verified payload,", national.source)
          : nationalNotPublished(
              dataset.national?.[0]?.source ??
                `observed pack · SG · ${dataset.label}`,
            )}
        {coverageNote !== null ? (
          <p className="mt-2 rounded border border-border bg-muted px-3 py-2 text-sm text-muted-foreground">
            {coverageNote}
          </p>
        ) : null}
        {!dataset.rankable ? (
          <p className="mt-2 text-sm text-muted-foreground">
            Areas are listed by name, not ranked, for this scope.
          </p>
        ) : null}
      </>
    );
  } else if (releaseStatus === "mismatch") {
    // Only a hash/generation disagreement proves the pair is mixed. A missing
    // or unreadable manifest proves nothing about compatibility, so it must not
    // be described as one.
    baselineBlock = (
      <div className="mt-3 rounded border border-border bg-muted px-3 py-2 text-sm">
        <p className="font-bold text-foreground">
          Assets do not share one publication generation; national comparison
          withheld
        </p>
        <p className="mt-1 text-muted-foreground">
          The area values below are published for{" "}
          <code className="font-mono">{dataset.section}</code> and are shown as
          they are. No national figure is shown, and none is computed from these
          area rows.
        </p>
      </div>
    );
  } else if (!dataset.baselineCompatible) {
    baselineBlock = (
      <div className="mt-3 rounded border border-border bg-muted px-3 py-2 text-sm">
        <p className="font-bold text-foreground">
          National comparison could not be verified; withheld
        </p>
        <p className="mt-1 text-muted-foreground">
          This snapshot has no verified publication manifest for{" "}
          <code className="font-mono">{dataset.section}</code> (status:{" "}
          {releaseStatus}). The area values below are shown as published; no
          national figure is drawn from them.
        </p>
      </div>
    );
  } else if (nationalLoading) {
    baselineBlock = (
      <p
        role="status"
        className="mt-3 rounded border border-border bg-muted px-3 py-2 text-sm text-muted-foreground"
      >
        Loading the national baseline for{" "}
        <code className="font-mono">
          dashboard_overview.stats.{dataset.section}
        </code>
        &hellip;
      </p>
    );
  } else if (nationalError !== null) {
    baselineBlock = (
      <div className="mt-3 rounded border border-border bg-muted px-3 py-2 text-sm">
        <p className="font-bold text-foreground">
          National baseline unavailable
        </p>
        <p className="mt-1 text-muted-foreground">{nationalError}</p>
        <button
          type="button"
          onClick={onRetryNational}
          className="mt-2 rounded border border-input px-3 py-1 text-sm font-bold text-foreground"
        >
          Retry baseline
        </button>
      </div>
    );
  } else if (national !== null && national.value !== null) {
    baselineBlock = nationalValue("same joint section, from", national.source);
  } else {
    baselineBlock = nationalNotPublished(
      `dashboard_overview.stats.${dataset.section}`,
    );
  }

  return (
    <div className="min-w-0">
      <h2 className="text-2xl font-bold text-foreground">
        {dataset.label} {propertyNoun(dataset.property)} {metricOption.noun}
      </h2>
      <p className="mt-1 text-sm text-muted-foreground">
        Showing {pageRows.length} of {rows.length} areas &middot;{" "}
        {dataset.rankable
          ? `${selection.direction === "asc" ? "ascending" : "descending"} ${sortOption.noun}`
          : "listed by name"}{" "}
        &middot; page {page} of {pageCount}
      </p>

      {baselineBlock}

      <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-end">
        {dataset.rankable ? (
          <>
            <div className="sm:w-60">
              <label
                htmlFor="explorer-sort"
                className="block text-sm font-bold text-foreground"
              >
                Sort by
              </label>
              <select
                id="explorer-sort"
                value={selection.sort}
                onChange={(event) => {
                  // The visible metric and the ordering stay in step: the list
                  // always shows the quantity it is sorted by.
                  const next = event.target.value as ExplorerSort;
                  onChange({ sort: next, metric: next });
                }}
                className="mt-1 w-full rounded border border-input bg-card px-3 py-2 text-sm text-foreground"
              >
                {METRIC_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>

            <button
              type="button"
              onClick={() =>
                onChange({
                  direction: selection.direction === "asc" ? "desc" : "asc",
                })
              }
              className="rounded border border-input bg-card px-3 py-2 text-sm font-bold text-foreground"
            >
              <span className="sr-only">Sort direction: </span>
              {selection.direction === "asc" ? "Ascending ↑" : "Descending ↓"}
            </button>
          </>
        ) : (
          <div className="sm:w-60">
            {/* No ordering control: this scope may not be ranked, so the
                reader can still choose which value is shown in the main
                column without the list implying a league table. */}
            <label
              htmlFor="explorer-metric"
              className="block text-sm font-bold text-foreground"
            >
              Show metric
            </label>
            <select
              id="explorer-metric"
              value={selection.metric}
              onChange={(event) =>
                onChange({ metric: event.target.value as ExplorerMetric })
              }
              className="mt-1 w-full rounded border border-input bg-card px-3 py-2 text-sm text-foreground"
            >
              {METRIC_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
        )}

        <div className="flex-1">
          <label
            htmlFor="explorer-search"
            className="block text-sm font-bold text-foreground"
          >
            Search planning areas
          </label>
          <input
            id="explorer-search"
            type="search"
            maxLength={80}
            value={selection.search}
            onChange={(event) => onChange({ search: event.target.value })}
            placeholder="e.g. Tampines"
            className="mt-1 w-full rounded border border-input bg-card px-3 py-2 text-sm text-foreground"
          />
        </div>
      </div>

      {dataset.thinCount > 0 ? (
        <p className="mt-4 rounded border border-border bg-[hsl(var(--note))] px-3 py-2 text-sm text-foreground">
          {dataset.thinCount} thin-sample{" "}
          {dataset.thinCount === 1 ? "area" : "areas"} hidden (fewer than{" "}
          {selection.minSales ?? THIN_SAMPLE_THRESHOLD} sales in this period and
          property type).{" "}
          <button
            type="button"
            onClick={() => onChange({ minSales: null })}
            className="font-bold text-[hsl(var(--teal))] underline underline-offset-4 hover:no-underline"
          >
            Show thin samples
          </button>
        </p>
      ) : null}

      {pageRows.length > 0 ? (
        <p className="mt-4 text-xs text-muted-foreground md:hidden">
          Four areas are visible at a time on this screen. Scroll the list for
          the rest of page {page}.
        </p>
      ) : null}

      <div
        role="group"
        aria-label="Area results"
        tabIndex={0}
        className="mt-2 max-h-[17rem] overflow-y-auto rounded-lg border border-border bg-card focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[hsl(var(--ring))] md:mt-4 md:max-h-none md:overflow-y-visible"
      >
        {pageRows.length === 0 ? (
          <div className="px-4 py-10 text-center">
            <p className="font-bold text-foreground">
              No planning areas match these settings
            </p>
            <p className="mt-1 text-sm text-muted-foreground">
              {selection.search.trim().length > 0
                ? `Nothing matches “${selection.search.trim()}” in this section. Try another area name, a wider period, or a lower sales threshold.`
                : "No area in this section meets the current sample-size threshold. Try a wider period or a lower threshold."}
            </p>
            <button
              type="button"
              onClick={onReset}
              className="mt-3 rounded border border-input px-3 py-2 text-sm font-bold text-foreground"
            >
              Reset filters
            </button>
          </div>
        ) : (
          <>
            <ul aria-label="Planning areas" className="divide-y divide-border">
              {pageRows.map((row) => (
                <li
                  key={row.areaId}
                  className="flex items-baseline justify-between gap-4 px-4 py-3"
                >
                  <div className="min-w-0">
                    <p className="truncate text-base font-bold text-foreground">
                      <a
                        href={rowHref(row, selection)}
                        className="text-foreground underline-offset-4 hover:underline"
                      >
                        {row.areaName}
                      </a>
                    </p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {COMPANION_METRICS[selection.metric].map(
                        (companion, index) => (
                          <span key={companion}>
                            {index > 0 ? " · " : null}
                            <MetricCell
                              row={row}
                              metric={companion}
                              className=""
                            />
                          </span>
                        ),
                      )}
                    </p>
                    {(() => {
                      const sentence = activitySentence(row);
                      if (sentence === null) return null;
                      return (
                        <p
                          className="mt-1 text-xs text-muted-foreground"
                          data-explorer-activity={
                            row.activity?.eligible === true
                              ? "eligible"
                              : "ineligible"
                          }
                        >
                          {sentence}
                        </p>
                      );
                    })()}
                  </div>
                  <MetricCell
                    row={row}
                    metric={selection.metric}
                    className="shrink-0 text-right text-base font-bold text-foreground"
                  />
                </li>
              ))}
            </ul>
          </>
        )}
      </div>

      <div className="mt-4 flex items-center justify-between gap-3">
        <button
          type="button"
          onClick={() => onChange({ page: page - 1 })}
          disabled={page <= 1}
          className="rounded border border-input bg-card px-3 py-2 text-sm text-foreground disabled:cursor-not-allowed disabled:opacity-50"
        >
          Previous page
        </button>
        <p className="text-sm text-muted-foreground">
          Page {page} of {pageCount}
        </p>
        <button
          type="button"
          onClick={() => onChange({ page: page + 1 })}
          disabled={page >= pageCount}
          className="rounded border border-input bg-card px-3 py-2 text-sm text-foreground disabled:cursor-not-allowed disabled:opacity-50"
        >
          Next page
        </button>
      </div>
    </div>
  );
}
