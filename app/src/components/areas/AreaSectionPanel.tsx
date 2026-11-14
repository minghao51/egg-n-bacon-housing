/**
 * Selected-section panel for an area fieldnote (`/areas/<slug>`).
 *
 * The page is a static build, so the server renders the **fixed default
 * section** — the same numbers, labels and provenance a reader without
 * JavaScript sees. After hydration this component reads `?property=` and
 * `?period=` and, when they name a section this fieldnote publishes, swaps the
 * whole panel together: values, labels and provenance never disagree.
 *
 * Rules:
 * - A concrete v2 period id is recognised but **not carried** by a fieldnote;
 *   the reader gets an explicit message and the fixed default stays visible.
 *   Nothing is substituted silently (RF06 §2/§3, contract §5.3).
 * - A combination with nothing published shows its own note instead of a zero.
 * - The national comparison appears only when the build-time generation proved
 *   both assets agree; the verdict travels in props, never from the browser.
 */

import { useEffect, useMemo, useState } from "react";

import {
  resolveAreaPageSelection,
  type AreaPageOption,
  type AreaPageValues,
} from "@/utils/area-selection";
import { explorerReturnHref } from "@/utils/area-links";

export interface AreaSectionPanelProps {
  areaName: string;
  areaId: string;
  options: AreaPageOption[];
  defaultOptionId: string;
  baseline: { compatible: boolean; status: string };
  /** Deployment base without its trailing slash ("" at the root path). */
  base: string;
}

function formatCount(value: number | null): string {
  return value === null
    ? "Not published"
    : Math.round(value).toLocaleString("en-US");
}

function formatPrice(value: number | null): string {
  return value === null
    ? "Not published"
    : `S$${Math.round(value).toLocaleString("en-US")}`;
}

function formatPsf(value: number | null): string {
  return value === null
    ? "Not published"
    : `S$${Math.round(value).toLocaleString("en-US")} psf`;
}

function formatDifference(value: number): string {
  return `S$${Math.round(Math.abs(value)).toLocaleString("en-US")}`;
}

function differenceSentence(areaPrice: number, nationalPrice: number) {
  const difference = areaPrice - nationalPrice;
  const percent = nationalPrice === 0 ? 0 : (difference / nationalPrice) * 100;
  return { difference, percent };
}

/** Read the requested section once, before the first commit. */
function readRequestedSelection(input: {
  options: AreaPageOption[];
  defaultOption: AreaPageOption;
  search: string;
}) {
  if (typeof window === "undefined") {
    return { optionId: input.defaultOption.id, notice: null as string | null };
  }
  const params = new URLSearchParams(input.search);
  const resolved = resolveAreaPageSelection({
    options: input.options,
    defaultOption: input.defaultOption,
    requestedPeriod: params.get("period"),
    requestedProperty: params.get("property"),
  });
  return resolved.kind === "unavailable"
    ? { optionId: resolved.fallback.id, notice: resolved.message }
    : { optionId: resolved.option.id, notice: null as string | null };
}

/** Keep the explorer return link in step with the section on screen. */
function refreshReturnHref(base: string, search: string): void {
  const link = document.getElementById("area-return");
  if (!(link instanceof HTMLAnchorElement)) return;
  link.href = explorerReturnHref(`${base}/explore`, search);
}

export default function AreaSectionPanel({
  areaName,
  areaId,
  options,
  defaultOptionId,
  baseline,
  base,
}: AreaSectionPanelProps) {
  const defaultOption =
    options.find((option) => option.id === defaultOptionId) ?? options[0];

  const [state, setState] = useState(() =>
    readRequestedSelection({
      options,
      defaultOption,
      search: typeof window === "undefined" ? "" : window.location.search,
    }),
  );

  // The server rendered the fixed default; this is the first chance to read the
  // query, and it also points the return link at the resolved selection.
  useEffect(() => {
    if (typeof window === "undefined") return;
    refreshReturnHref(base, window.location.search);
  }, [base]);

  const option =
    options.find((candidate) => candidate.id === state.optionId) ??
    defaultOption;

  const selectable = useMemo(
    () =>
      options.map((candidate) => ({
        id: candidate.id,
        label: candidate.label,
      })),
    [options],
  );

  const select = (nextId: string) => {
    const next = options.find((candidate) => candidate.id === nextId);
    if (next === undefined) return;
    setState({ optionId: next.id, notice: null });

    if (typeof window !== "undefined") {
      try {
        const url = new URL(window.location.href);
        url.searchParams.set("property", next.property);
        url.searchParams.set("period", next.period);
        window.history.replaceState({}, "", url.toString());
        refreshReturnHref(base, url.search);
      } catch {
        // A malformed address bar is not worth failing the render over: the
        // panel still shows the section the reader picked.
      }
    }
  };

  const values: AreaPageValues = option.area;
  const national = option.national;
  const priceNote =
    values.medianPrice === null
      ? "No transaction-price median is published for this area in this section."
      : `The middle sale was ${formatPrice(values.medianPrice)}.`;

  const comparison =
    option.comparable && national !== null && national.medianPrice !== null
      ? differenceSentence(values.medianPrice as number, national.medianPrice)
      : null;

  return (
    <section aria-labelledby="area-comparison-heading" className="min-w-0">
      <h2
        id="area-comparison-heading"
        className="text-2xl font-bold text-foreground"
      >
        What this area sold for
      </h2>

      <div className="mt-3 rounded-lg border border-border bg-card p-4">
        <label
          htmlFor="area-section"
          className="block text-sm font-bold text-foreground"
        >
          Section
        </label>
        <select
          id="area-section"
          value={option.id}
          onChange={(event) => select(event.target.value)}
          className="mt-2 w-full rounded border border-input bg-card px-3 py-2 text-sm text-foreground sm:w-96"
        >
          {selectable.map((candidate) => (
            <option key={candidate.id} value={candidate.id}>
              {candidate.label}
            </option>
          ))}
        </select>
        <p className="mt-2 text-xs text-muted-foreground">
          {option.scope} · <code className="font-mono">{option.source}</code>
        </p>
        {state.notice !== null ? (
          <p
            role="alert"
            className="mt-3 rounded border border-border bg-muted px-3 py-2 text-sm text-foreground"
            data-area-selection-notice="true"
          >
            {state.notice}{" "}
            <a
              href={`${base}/explore`}
              className="font-bold text-[hsl(var(--teal))] underline underline-offset-4 hover:no-underline"
            >
              Open Explore
            </a>
          </p>
        ) : null}
      </div>

      <p className="mt-3 text-lg text-foreground">{priceNote}</p>
      {option.emptyNote !== null ? (
        <p className="mt-2 text-sm text-muted-foreground">{option.emptyNote}</p>
      ) : null}

      <dl className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-lg border border-border bg-card p-4">
          <dt className="text-xs font-bold uppercase tracking-[1.2px] text-muted-foreground">
            Median price
          </dt>
          <dd className="mt-1 text-2xl font-bold text-foreground" data-numeric>
            {formatPrice(values.medianPrice)}
          </dd>
        </div>
        <div className="rounded-lg border border-border bg-card p-4">
          <dt className="text-xs font-bold uppercase tracking-[1.2px] text-muted-foreground">
            Median PSF
          </dt>
          <dd className="mt-1 text-2xl font-bold text-foreground" data-numeric>
            {formatPsf(values.medianPsf)}
          </dd>
        </div>
        <div className="rounded-lg border border-border bg-card p-4">
          <dt className="text-xs font-bold uppercase tracking-[1.2px] text-muted-foreground">
            Transactions
          </dt>
          <dd className="mt-1 text-2xl font-bold text-foreground" data-numeric>
            {formatCount(values.volume)}
          </dd>
        </div>
      </dl>

      {comparison !== null && national !== null ? (
        <div className="mt-6 rounded-lg border border-border bg-card p-5">
          <p className="text-xl font-bold text-foreground">
            {comparison.difference === 0
              ? "At the national median. Not a like-for-like comparison."
              : comparison.difference > 0
                ? "Above the national median. Not a like-for-like premium."
                : "Below the national median. Not a like-for-like discount."}
          </p>
          <p className="mt-3 text-base text-foreground">
            The {areaName} median transaction price was{" "}
            <span data-numeric>{formatDifference(comparison.difference)}</span>{" "}
            {comparison.difference > 0
              ? "higher"
              : comparison.difference < 0
                ? "lower"
                : "level"}{" "}
            than the national median in this section
            {comparison.percent === 0
              ? "."
              : ` — a ${Math.abs(comparison.percent).toFixed(1)}% difference.`}
          </p>
          <p className="mt-2 text-sm text-muted-foreground">
            This difference may reflect the homes that sold, not location alone.
            The national figure counts transactions the area map excludes (for
            example Sungei Kadut), so area counts need not sum to it.
          </p>
        </div>
      ) : null}

      {baseline.status === "mismatch" ? (
        <div className="mt-6 rounded-lg border border-border bg-muted px-4 py-3 text-sm">
          <p className="font-bold text-foreground">
            Assets do not share one publication generation; national comparison
            withheld
          </p>
          <p className="mt-1 text-muted-foreground">
            The area figures above are published for{" "}
            <code className="font-mono">{option.source}</code> and are shown as
            they are. No national figure is shown, and none is computed from
            these area values.
          </p>
        </div>
      ) : !baseline.compatible ? (
        <div className="mt-6 rounded-lg border border-border bg-muted px-4 py-3 text-sm">
          <p className="font-bold text-foreground">
            National comparison could not be verified; withheld
          </p>
          <p className="mt-1 text-muted-foreground">
            This snapshot publishes no verified publication manifest for{" "}
            <code className="font-mono">{option.source}</code> and{" "}
            <code className="font-mono">{option.nationalSource ?? "—"}</code>{" "}
            (status: {baseline.status}). The area figures above are shown as
            published; no national figure and no difference is drawn from them.
          </p>
        </div>
      ) : null}

      <h3 className="mt-8 text-xl font-bold text-foreground">
        The numbers behind this fieldnote
      </h3>
      <p className="mt-1 text-sm text-muted-foreground">
        {option.scope} · <code className="font-mono">{option.source}</code>
      </p>

      <div className="mt-4 rounded-lg border border-border bg-card sm:hidden">
        <dl className="divide-y divide-border">
          <div className="flex items-baseline justify-between gap-4 px-4 py-3">
            <dt className="text-xs font-bold uppercase tracking-[1.2px] text-muted-foreground">
              Median price
            </dt>
            <dd className="text-lg font-bold text-foreground" data-numeric>
              {formatPrice(values.medianPrice)}
            </dd>
          </div>
          <div className="flex items-baseline justify-between gap-4 px-4 py-3">
            <dt className="text-xs font-bold uppercase tracking-[1.2px] text-muted-foreground">
              Median PSF
            </dt>
            <dd className="text-lg font-bold text-foreground" data-numeric>
              {formatPsf(values.medianPsf)}
            </dd>
          </div>
          <div className="flex items-baseline justify-between gap-4 px-4 py-3">
            <dt className="text-xs font-bold uppercase tracking-[1.2px] text-muted-foreground">
              Transactions
            </dt>
            <dd className="text-lg font-bold text-foreground" data-numeric>
              {formatCount(values.volume)}
            </dd>
          </div>
        </dl>
      </div>

      <div
        className="mt-4 hidden overflow-x-auto rounded-lg border border-border bg-card sm:block"
        role="region"
        aria-label={`Observed medians for ${areaName} and the national baseline`}
        tabIndex={0}
      >
        <table className="w-full border-collapse text-left text-sm">
          <caption className="sr-only">
            Observed medians for {areaName} in {option.source} and the national
            baseline
          </caption>
          <thead>
            <tr className="border-b border-border">
              <th
                scope="col"
                className="px-4 py-3 text-xs font-bold uppercase tracking-[1.2px]"
              >
                Area
              </th>
              <th
                scope="col"
                className="px-4 py-3 text-xs font-bold uppercase tracking-[1.2px]"
              >
                Median price
              </th>
              <th
                scope="col"
                className="px-4 py-3 text-xs font-bold uppercase tracking-[1.2px]"
              >
                Median PSF
              </th>
              <th
                scope="col"
                className="px-4 py-3 text-xs font-bold uppercase tracking-[1.2px]"
              >
                Transactions
              </th>
            </tr>
          </thead>
          <tbody>
            <tr className="border-b border-border">
              <th scope="row" className="px-4 py-3 font-bold text-foreground">
                {areaName}
              </th>
              <td className="px-4 py-3 text-foreground" data-numeric>
                {formatPrice(values.medianPrice)}
              </td>
              <td className="px-4 py-3 text-foreground" data-numeric>
                {formatPsf(values.medianPsf)}
              </td>
              <td className="px-4 py-3 text-foreground" data-numeric>
                {formatCount(values.volume)}
              </td>
            </tr>
            {comparison !== null && national !== null ? (
              <tr>
                <th scope="row" className="px-4 py-3 font-bold text-foreground">
                  Singapore
                </th>
                <td className="px-4 py-3 text-foreground" data-numeric>
                  {formatPrice(national.medianPrice)}
                </td>
                <td className="px-4 py-3 text-foreground" data-numeric>
                  {formatPsf(national.medianPsf)}
                </td>
                <td className="px-4 py-3 text-foreground" data-numeric>
                  {formatCount(national.volume)}
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>

      {comparison !== null && national !== null ? (
        <p className="mt-3 text-sm text-muted-foreground">
          {comparison.difference === 0 ? (
            <>This area’s median is the same as the national median.</>
          ) : (
            <>
              Difference to the national median:{" "}
              <span className="font-bold text-foreground" data-numeric>
                {formatDifference(comparison.difference)}
              </span>{" "}
              (
              {(comparison.percent > 0 ? "+" : "−") +
                Math.abs(comparison.percent).toFixed(1)}
              % of the national median).
            </>
          )}
        </p>
      ) : null}

      <p className="mt-3 text-xs text-muted-foreground">
        Fieldnote area {areaId} · national baseline{" "}
        <code className="font-mono">
          {option.nationalSource ?? "not published"}
        </code>
        .
      </p>
    </section>
  );
}
