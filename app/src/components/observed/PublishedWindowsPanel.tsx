/**
 * Published-window panel shared by `/research/trends` and `/explore`.
 *
 * The figures arrive pre-extracted from the build-time v2 reader, so this
 * component never fetches and never derives a number from a legacy series. It
 * also never decides what is publishable: the disposition travels with each
 * window and only changes the note, not the number.
 */

import { useState } from "react";
import type { WindowsByType } from "@/utils/observed-pack-build";

export type PanelSeries = "hdb" | "ec" | "condo" | "all";

const SERIES_LABELS: Record<PanelSeries, string> = {
  hdb: "HDB",
  ec: "EC",
  condo: "Condo",
  all: "All property types",
};

type WindowKey = "latest" | "ytd" | "ttm";

const WINDOW_CHOICES: readonly { id: WindowKey; label: string }[] = [
  { id: "latest", label: "Latest month" },
  { id: "ytd", label: "Year to date" },
  { id: "ttm", label: "Trailing 12 months" },
];

function formatCount(value: number | null): string {
  return value === null ? "not published" : value.toLocaleString("en-SG");
}

function formatPrice(value: number | null): string {
  return value === null
    ? "not published"
    : `S$${Math.round(value).toLocaleString("en-SG")}`;
}

function formatChange(value: number | null): string {
  if (value === null) return "no comparison";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(1)}% vs prior year`;
}

export interface PublishedWindowsPanelProps {
  windows: WindowsByType;
  series: PanelSeries;
  cutoffMonth: string;
  generation: string;
  /** Optional extra sentence shown under the panel heading. */
  intro?: string;
}

export default function PublishedWindowsPanel({
  windows,
  series,
  cutoffMonth,
  generation,
  intro,
}: PublishedWindowsPanelProps) {
  const [windowKey, setWindowKey] = useState<WindowKey>("ttm");
  const active = windows[series][windowKey];
  const sales = active?.metrics.find(
    (metric) => metric.metric === "transactionCount",
  );
  const price = active?.metrics.find(
    (metric) => metric.metric === "medianPrice",
  );

  return (
    <section
      aria-labelledby="published-windows-heading"
      data-published-window={active?.periodId ?? "none"}
      data-observed-cutoff={cutoffMonth}
      className="mt-6 rounded-lg border border-border bg-card p-5"
    >
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2
          id="published-windows-heading"
          className="text-xs font-bold uppercase tracking-[1.6px] text-muted-foreground"
        >
          Published windows
        </h2>
        <p className="text-xs text-muted-foreground">
          cutoff {cutoffMonth} · generation{" "}
          <code className="font-mono">{generation.slice(0, 12)}</code>
        </p>
      </div>

      {intro ? (
        <p className="mt-2 text-sm text-muted-foreground">{intro}</p>
      ) : null}

      <div className="mt-3 flex flex-wrap gap-2">
        {WINDOW_CHOICES.map((choice) => (
          <button
            key={choice.id}
            type="button"
            onClick={() => setWindowKey(choice.id)}
            aria-pressed={windowKey === choice.id}
            className={`rounded border px-3 py-1.5 text-sm font-medium ${
              windowKey === choice.id
                ? "border-[hsl(var(--teal))] font-bold text-[hsl(var(--teal))]"
                : "border-input bg-card text-foreground"
            }`}
          >
            {choice.label}
          </button>
        ))}
      </div>

      {active ? (
        <dl className="mt-4 grid gap-4 sm:grid-cols-3">
          <div>
            <dt className="text-xs uppercase tracking-wide text-muted-foreground">
              Window
            </dt>
            <dd className="text-sm font-semibold text-foreground">
              {active.label}
            </dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wide text-muted-foreground">
              Sales
            </dt>
            <dd className="text-sm font-semibold text-foreground">
              {formatCount(sales?.value ?? null)}
            </dd>
            <dd className="text-xs text-muted-foreground">
              {formatChange(sales?.percentChange ?? null)}
            </dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wide text-muted-foreground">
              Median price
            </dt>
            <dd className="text-sm font-semibold text-foreground">
              {formatPrice(price?.value ?? null)}
            </dd>
            <dd className="text-xs text-muted-foreground">
              {formatChange(price?.percentChange ?? null)}
            </dd>
          </div>
        </dl>
      ) : (
        <p className="mt-4 text-sm text-muted-foreground">
          This window is not published for {SERIES_LABELS[series]}.
        </p>
      )}

      {active && active.disposition !== "publish" ? (
        <p className="mt-4 border-t border-border pt-3 text-sm text-muted-foreground">
          {SERIES_LABELS[series]} 2026 counts are under coverage review: read
          them as records with their dates, not as a growth story.
        </p>
      ) : null}
    </section>
  );
}
