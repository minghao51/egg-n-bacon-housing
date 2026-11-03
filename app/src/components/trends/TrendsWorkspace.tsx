/**
 * `/research/trends` workspace.
 *
 * One published asset (`dashboard_trends`), one selection, three readings of it:
 * a latest-value summary, a price chart and a volume chart, and the monthly
 * table that lists every month behind them.
 *
 * The selection is `?series=&window=` only. It is parsed once from the address
 * bar before the first commit (so a deep link is never overwritten by defaults)
 * and written back with `replaceState` only when the serialized selection
 * differs from the URL. Because the serializer omits default values, a link such
 * as `?series=hdb&window=year_2025` is canonicalised to `/research/trends`
 * instead of being treated as new state. Parameters this island does not own are
 * left untouched.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

import { useGzipJson } from "@/hooks/useGzipJson";
import {
  buildTrendSeries,
  filterWindow,
  formatTrendNumber,
  summarize,
  yearSum,
  TREND_QUERY_DEFAULTS,
  TREND_SERIES_IDS,
  TREND_SERIES_LABELS,
  TREND_WINDOWS,
  TREND_WINDOW_LABELS,
  type TrendSeries,
  type TrendSeriesId,
  type TrendWindow,
} from "@/utils/trend-series";
import TrendsChart from "./TrendsChart";
import TrendsTable from "./TrendsTable";

export interface TrendSelection {
  series: TrendSeriesId;
  window: TrendWindow;
}

/** The two query keys this workspace owns. */
export type TrendQueryKey = "series" | "window";

export const TREND_QUERY_KEYS: readonly TrendQueryKey[] = ["series", "window"];

/** Id of the monthly table, used as the charts' long description. */
const TABLE_ID = "trends-monthly-table";

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

/**
 * Read `?series=&window=` with validated fallbacks, mirroring the explorer's
 * parser: an unknown or malformed value lands on the documented default, never
 * on a different valid value. Accepts a leading `?`, a bare query string or a
 * full URL.
 */
export function parseTrendSelection(search: string): TrendSelection {
  let query = search.trim();
  if (query.startsWith("?")) {
    query = query.slice(1);
  } else if (/^[a-z][a-z0-9+.-]*:\/\//i.test(query)) {
    const questionMark = query.indexOf("?");
    query = questionMark >= 0 ? query.slice(questionMark + 1) : "";
  }

  let params: URLSearchParams;
  try {
    params = new URLSearchParams(query);
  } catch {
    return {
      series: TREND_QUERY_DEFAULTS.series,
      window: TREND_QUERY_DEFAULTS.window,
    };
  }

  return {
    series: pickEnum(
      params.get("series"),
      TREND_SERIES_IDS,
      TREND_QUERY_DEFAULTS.series,
    ),
    window: pickEnum(
      params.get("window"),
      TREND_WINDOWS,
      TREND_QUERY_DEFAULTS.window,
    ),
  };
}

/** Serialize a selection, omitting every default so the URL stays short. */
export function serializeTrendSelection(
  selection: TrendSelection,
): URLSearchParams {
  const params = new URLSearchParams();
  if (selection.series !== TREND_QUERY_DEFAULTS.series) {
    params.set("series", selection.series);
  }
  if (selection.window !== TREND_QUERY_DEFAULTS.window) {
    params.set("window", selection.window);
  }
  return params;
}

/** Read the incoming selection once, before the first render commit. */
function readSelectionFromUrl(): TrendSelection {
  if (typeof window === "undefined") {
    return {
      series: TREND_QUERY_DEFAULTS.series,
      window: TREND_QUERY_DEFAULTS.window,
    };
  }
  return parseTrendSelection(window.location.search);
}

interface Coverage {
  start: string | null;
  end: string | null;
  publishedMonths: number;
}

/** First and last month of the series that actually carries a price. */
function publishedCoverage(series: TrendSeries): Coverage {
  const published = series.points.filter((point) => point.price !== null);
  if (published.length === 0) {
    return { start: null, end: null, publishedMonths: 0 };
  }
  return {
    start: published[0].month,
    end: published[published.length - 1].month,
    publishedMonths: published.length,
  };
}

interface ChoiceProps {
  name: string;
  value: string;
  checked: boolean;
  onSelect: () => void;
  children: ReactNode;
}

/**
 * One radio rendered as a selectable chip. The input itself is stretched over
 * the chip so the page-wide focus ring has a real boundary and the whole chip is
 * the click target.
 */
function Choice({ name, value, checked, onSelect, children }: ChoiceProps) {
  return (
    <label className="relative flex cursor-pointer items-stretch">
      <input
        type="radio"
        name={name}
        value={value}
        checked={checked}
        onChange={onSelect}
        className="peer absolute inset-0 m-0 h-full w-full cursor-pointer appearance-none rounded border border-input bg-card checked:border-[hsl(var(--teal))] checked:bg-accent"
      />
      <span className="pointer-events-none relative flex w-full items-center justify-center px-3 py-2 text-sm font-medium text-foreground peer-checked:font-bold peer-checked:text-[hsl(var(--teal))]">
        {children}
      </span>
    </label>
  );
}

export interface TrendsWorkspaceProps {
  trendsUrl: string;
}

export default function TrendsWorkspace({ trendsUrl }: TrendsWorkspaceProps) {
  const [selection, setSelection] =
    useState<TrendSelection>(readSelectionFromUrl);
  const trends = useGzipJson<unknown>(
    trendsUrl,
    "research-trends:dashboard_trends",
  );

  const update = useCallback((patch: Partial<TrendSelection>) => {
    setSelection((current) => ({
      series: patch.series ?? current.series,
      window: patch.window ?? current.window,
    }));
  }, []);

  // Keep the address bar in step with the selection, and only when it changed.
  useEffect(() => {
    if (typeof window === "undefined") return;

    const next = serializeTrendSelection(selection);
    const url = new URL(window.location.href);
    let changed = false;

    for (const key of TREND_QUERY_KEYS) {
      if (!next.has(key) && url.searchParams.has(key)) {
        url.searchParams.delete(key);
        changed = true;
      }
    }
    next.forEach((value, key) => {
      if (url.searchParams.get(key) !== value) {
        url.searchParams.set(key, value);
        changed = true;
      }
    });

    if (!changed) return;
    window.history.replaceState({}, "", url.toString());
  }, [selection]);

  // Back/forward: the URL is the source of truth, so re-apply it.
  useEffect(() => {
    if (typeof window === "undefined") return;

    const handlePopState = () => {
      setSelection(parseTrendSelection(window.location.search));
    };

    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  const full = useMemo(
    () => buildTrendSeries(trends.data, selection.series),
    [trends.data, selection.series],
  );
  const filtered = useMemo(
    () => (full === null ? null : filterWindow(full, selection.window)),
    [full, selection.window],
  );
  const summary = useMemo(
    () => (filtered === null ? null : summarize(filtered, selection.window)),
    [filtered, selection.window],
  );
  const coverage = useMemo(
    () => (full === null ? null : publishedCoverage(full)),
    [full],
  );
  const year2025Volume = useMemo(() => {
    if (filtered === null || selection.window !== "year_2025") return null;
    return yearSum(filtered.points, "2025", "volume");
  }, [filtered, selection.window]);

  const reload = trends.reload;
  const retry = useCallback(() => {
    void reload();
  }, [reload]);

  const label = TREND_SERIES_LABELS[selection.series];
  const windowLabel = TREND_WINDOW_LABELS[selection.window];
  const loading = trends.loading && trends.data === null;
  const failed = trends.error !== null && trends.data === null;
  const unusable = trends.data !== null && full === null;

  return (
    <div className="mt-8">
      <section
        aria-labelledby="trend-reading-heading"
        className="rounded-lg border border-border bg-card p-5"
      >
        <h2
          id="trend-reading-heading"
          className="text-xs font-bold uppercase tracking-[1.6px] text-muted-foreground"
        >
          Reading setup
        </h2>

        <fieldset className="mt-4">
          <legend className="text-sm font-bold text-foreground">
            Property type
          </legend>
          <div className="mt-2 grid grid-cols-2 gap-2 sm:flex sm:flex-wrap">
            {TREND_SERIES_IDS.map((id) => (
              <Choice
                key={id}
                name="trend-series"
                value={id}
                checked={selection.series === id}
                onSelect={() => update({ series: id })}
              >
                {TREND_SERIES_LABELS[id]}
              </Choice>
            ))}
          </div>
        </fieldset>

        <fieldset className="mt-5">
          <legend className="text-sm font-bold text-foreground">Window</legend>
          <div className="mt-2 grid grid-cols-2 gap-2 sm:flex sm:flex-wrap">
            {TREND_WINDOWS.map((id) => (
              <Choice
                key={id}
                name="trend-window"
                value={id}
                checked={selection.window === id}
                onSelect={() => update({ window: id })}
              >
                {TREND_WINDOW_LABELS[id]}
              </Choice>
            ))}
          </div>
        </fieldset>

        <p className="mt-4 text-sm text-muted-foreground">
          A type or window choice never implies coverage: each series starts the
          month the asset first publishes it, and months before that are shown
          as <span className="font-bold text-foreground">N/A</span>, not zero.
        </p>

        <a
          href={`#${TABLE_ID}`}
          className="mt-4 inline-block text-sm font-bold text-[hsl(var(--teal))] underline underline-offset-4 hover:no-underline"
        >
          Read all monthly prices &amp; counts &rarr;
        </a>
      </section>

      {loading ? (
        <p
          role="status"
          aria-live="polite"
          className="mt-6 rounded-lg border border-border bg-card p-6 text-sm text-muted-foreground"
        >
          Loading published monthly data&hellip;
        </p>
      ) : null}

      {failed ? (
        <div
          role="alert"
          className="mt-6 rounded-lg border border-border bg-card p-6 text-sm"
        >
          <p className="font-bold text-foreground">
            The monthly trends asset could not be loaded
          </p>
          <p className="mt-2 text-muted-foreground">{trends.error}</p>
          <button
            type="button"
            onClick={retry}
            className="mt-3 rounded border border-input px-3 py-2 font-bold text-foreground"
          >
            Try again
          </button>
        </div>
      ) : null}

      {unusable ? (
        <div
          role="alert"
          className="mt-6 rounded-lg border border-border bg-card p-6 text-sm"
        >
          <p className="font-bold text-foreground">
            The published trends asset has an unexpected shape
          </p>
          <p className="mt-2 text-muted-foreground">
            No monthly series is shown, because rendering a partial one would
            misstate coverage. The asset is expected to be a list of monthly
            rows keyed <code className="font-mono">date</code> (
            <code className="font-mono">YYYY-MM</code>) with one price and one
            count per property type.
          </p>
          <button
            type="button"
            onClick={retry}
            className="mt-3 rounded border border-input px-3 py-2 font-bold text-foreground"
          >
            Try again
          </button>
        </div>
      ) : null}

      {full !== null &&
      filtered !== null &&
      summary !== null &&
      coverage !== null ? (
        <>
          <section
            aria-labelledby="trend-latest-heading"
            className="mt-6 rounded-lg border border-border bg-[hsl(var(--accent))] p-5"
          >
            <h2
              id="trend-latest-heading"
              className="text-xs font-bold uppercase tracking-[1.6px] text-muted-foreground"
            >
              {label} &middot; {windowLabel}
            </h2>
            <dl className="mt-3 grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-4">
              <div>
                <dt className="text-xs uppercase tracking-[1.6px] text-muted-foreground">
                  Latest month in this window
                </dt>
                <dd className="mt-1 text-lg font-bold text-foreground">
                  {summary.endMonth ?? "N/A"}
                </dd>
              </div>
              <div>
                <dt className="text-xs uppercase tracking-[1.6px] text-muted-foreground">
                  Median price
                </dt>
                <dd className="mt-1 text-lg font-bold text-foreground">
                  {summary.latestPrice === null
                    ? "N/A"
                    : `S$${formatTrendNumber(summary.latestPrice)}`}
                </dd>
              </div>
              <div>
                <dt className="text-xs uppercase tracking-[1.6px] text-muted-foreground">
                  Transactions
                </dt>
                <dd className="mt-1 text-lg font-bold text-foreground">
                  {formatTrendNumber(summary.latestVolume)}
                </dd>
              </div>
              {selection.window === "year_2025" ? (
                <div>
                  <dt className="text-xs uppercase tracking-[1.6px] text-muted-foreground">
                    2025 transactions (12 months)
                  </dt>
                  <dd className="mt-1 text-lg font-bold text-foreground">
                    {formatTrendNumber(year2025Volume)}
                  </dd>
                </div>
              ) : null}
            </dl>

            {selection.window === "year_2025" ? (
              <p className="mt-3 text-sm text-foreground">
                {year2025Volume === null
                  ? "No published count completes the twelve months of 2025 for this series, so no 2025 transaction total is given: the monthly medians are published, the count is not invented."
                  : `${formatTrendNumber(year2025Volume)} ${label} transactions were published across the twelve months of 2025. A full-year count is the sum of the monthly counts; it is not an annual median price and not the average of the twelve monthly medians.`}
              </p>
            ) : (
              <p className="mt-3 text-sm text-foreground">
                {summary.months === 1
                  ? "One month is"
                  : `${summary.months} months are`}{" "}
                published in this window. Choose the 2025 complete year to see a
                twelve-month transaction total.
              </p>
            )}

            <p className="mt-2 text-sm text-muted-foreground">
              Published coverage for {label}:{" "}
              {coverage.start === null
                ? "no month carries a price"
                : `${coverage.start} to ${coverage.end} (${coverage.publishedMonths} of ${full.points.length} months)`}
              .
              {summary.nullPriceMonths > 0
                ? ` ${summary.nullPriceMonths} ${summary.nullPriceMonths === 1 ? "month" : "months"} in the selected window publish no median price.`
                : ""}
              {summary.isPartialWindow
                ? " The selected window is not fully covered by the published series, so it is only partly filled — the missing months are not zero."
                : ""}
            </p>
          </section>

          <div className="mt-6 grid gap-6">
            <TrendsChart
              metric="price"
              title={`${label} monthly median transaction price`}
              points={filtered.points}
              idPrefix="trend-price"
              detailId={TABLE_ID}
            />
            <TrendsChart
              metric="volume"
              title={`${label} monthly sales`}
              points={filtered.points}
              idPrefix="trend-volume"
              detailId={TABLE_ID}
            />
          </div>

          <TrendsTable series={filtered} id={TABLE_ID} />

          <footer className="mt-10 border-t border-border pt-4 text-xs text-muted-foreground">
            <p>
              Source: <code className="font-mono">dashboard_trends</code>{" "}
              &mdash; one row per month with a median transaction price and a
              count of included transactions per property type. Last month
              actually present in the asset:{" "}
              <span className="font-bold text-foreground">
                {full.points[full.points.length - 1].month}
              </span>
              . The selected window ends {summary.endMonth ?? "N/A"}.
            </p>
            <p className="mt-1">
              These are monthly medians of observed transactions in nominal SGD,
              not an adjusted price index, not asking prices and not a
              valuation. The price axis is zoomed to the window's own range and
              says so; the volume axis always starts at zero. The asset embeds
              no export timestamp, so this page does not claim one.
            </p>
          </footer>
        </>
      ) : null}
    </div>
  );
}
