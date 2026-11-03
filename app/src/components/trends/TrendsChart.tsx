/**
 * Self-contained SVG charts for `/research/trends`.
 *
 * Two readings of the same monthly series, one component:
 * - `metric="price"` draws a line whose y-domain is the data's own min/max
 *   padded by 5%. The axis is therefore **zoomed**, and the caption states the
 *   zoom plus the actual minimum and maximum.
 * - `metric="volume"` draws one bar per month on a **zero-based** axis that is
 *   never zoomed, so bar heights stay proportional to counts.
 *
 * Both break at `null`: a month with no published value leaves a gap and is
 * never interpolated across and never drawn as zero.
 *
 * No chart library and no new dependency — a fixed `viewBox` plus
 * `preserveAspectRatio` keeps the drawing responsive without measuring the DOM,
 * so the component is pure presentational and safe to render on the server.
 */

import type { ReactNode } from "react";

import { formatTrendNumber, type TrendPoint } from "@/utils/trend-series";

const WIDTH = 720;
const HEIGHT = 260;
const PLOT_LEFT = 86;
const PLOT_RIGHT = 702;
const PLOT_TOP = 18;
const PLOT_BOTTOM = 210;
const PLOT_WIDTH = PLOT_RIGHT - PLOT_LEFT;
const PLOT_HEIGHT = PLOT_BOTTOM - PLOT_TOP;

/** Point markers are only readable for a window of about a year. */
const DENSE_THRESHOLD = 31;

const MONTH_SHORT = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
];

const SERIES_COLOUR = "hsl(var(--teal))";
const GRID_COLOUR = "hsl(var(--border))";
const LABEL_COLOUR = "hsl(var(--muted-foreground))";

/** A 1–2–5 × 10ⁿ step covering `span` in roughly `target` intervals. */
function niceStep(span: number, target: number): number {
  if (!(span > 0) || !(target > 0)) return 1;
  const raw = span / target;
  const magnitude = Math.pow(10, Math.floor(Math.log10(raw)));
  const normalised = raw / magnitude;
  const factor =
    normalised <= 1 ? 1 : normalised <= 2 ? 2 : normalised <= 5 ? 5 : 10;
  return factor * magnitude;
}

/** Tick values inside `[min, max]`, always computed as whole multiples of the step. */
function axisTicks(min: number, max: number, target = 4): number[] {
  if (!(max > min)) return [min];
  const step = niceStep(max - min, target);
  const ticks: number[] = [];
  for (let index = Math.ceil(min / step); index * step <= max; index += 1) {
    ticks.push(index * step);
  }
  return ticks.length > 0 ? ticks : [min, max];
}

/** At most `max` evenly spaced indices, always including the first and last. */
function axisLabelIndices(count: number, max = 5): number[] {
  if (count <= 0) return [];
  if (count <= max) return Array.from({ length: count }, (_, index) => index);
  const indices: number[] = [];
  for (let step = 0; step < max; step += 1) {
    indices.push(Math.round((step * (count - 1)) / (max - 1)));
  }
  return Array.from(new Set(indices));
}

function monthLabel(month: string, singleYear: boolean): string {
  const year = month.slice(0, 4);
  const monthOfYear = Number(month.slice(5, 7));
  const short = MONTH_SHORT[monthOfYear - 1] ?? month;
  return singleYear ? short : `${short} ${year}`;
}

function plural(count: number, noun: string): string {
  return `${count} ${noun}${count === 1 ? "" : "s"}`;
}

export interface TrendsChartProps {
  metric: "price" | "volume";
  /** Visible chart heading, e.g. "HDB monthly median transaction price". */
  title: string;
  points: TrendPoint[];
  /** Unique id prefix for the title/description/heading elements. */
  idPrefix: string;
  /** Id of the element that lists every month (the page's table). */
  detailId?: string;
}

export default function TrendsChart({
  metric,
  title,
  points,
  idPrefix,
  detailId,
}: TrendsChartProps) {
  const headingId = `${idPrefix}-heading`;
  const svgTitleId = `${idPrefix}-svg-title`;
  const descId = `${idPrefix}-desc`;

  const values = points.map((entry) =>
    metric === "price" ? entry.price : entry.volume,
  );
  const published = values.filter(
    (value): value is number => value !== null && Number.isFinite(value),
  );
  const missing = values.length - published.length;
  const first = points[0];
  const last = points[points.length - 1];

  const figure = (note: string, body: ReactNode, description: string) => (
    <figure className="m-0 rounded-lg border border-border bg-card p-5">
      <figcaption>
        <h2 id={headingId} className="text-xl font-bold text-foreground">
          {title}
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">{note}</p>
      </figcaption>
      {body}
      <p id={descId} className="sr-only">
        {description}
      </p>
    </figure>
  );

  if (published.length === 0 || first === undefined || last === undefined) {
    return figure(
      "Nothing is published for this window.",
      <p className="mt-4 text-sm text-foreground">
        The selected series publishes no{" "}
        {metric === "price" ? "median price" : "transaction count"} for the
        months in this window. That is not a value of zero.
      </p>,
      `${title}. No month in the selected window publishes a value.`,
    );
  }

  const minimum = Math.min(...published);
  const maximum = Math.max(...published);
  const span = maximum - minimum;
  // Padded by 5% of the data's own range; a flat or single-value series gets a
  // 5% band around its value so the line is not drawn on the frame edge.
  const pad = span > 0 ? span * 0.05 : Math.max(Math.abs(maximum) * 0.05, 1);
  const domainMin = metric === "price" ? minimum - pad : 0;
  const domainMax = metric === "price" ? maximum + pad : maximum;
  const scaleSpan = domainMax - domainMin || 1;

  const yFor = (value: number): number =>
    PLOT_BOTTOM - ((value - domainMin) / scaleSpan) * PLOT_HEIGHT;

  const band = PLOT_WIDTH / points.length;
  const xFor = (index: number): number => PLOT_LEFT + (index + 0.5) * band;

  const singleYear = points.every(
    (entry) => entry.month.slice(0, 4) === first.month.slice(0, 4),
  );

  const priceUnits = (value: number): string =>
    `${metric === "price" ? "S$" : ""}${formatTrendNumber(value)}`;

  const note =
    metric === "price"
      ? `Zoomed price axis: it does not start at zero. The line spans the published minimum ${priceUnits(minimum)} and maximum ${priceUnits(maximum)}, with 5% padding above and below.`
      : `Zero-based axis: the scale starts at 0 and is never zoomed. The tallest month in this window is ${formatTrendNumber(maximum)} transactions.`;

  const gapNote =
    missing > 0
      ? ` ${plural(missing, "month")} in this window publish no value and stay gaps — they are not zero and are not interpolated.`
      : "";

  const description = [
    title,
    `${plural(points.length, "month")} from ${first.month} to ${last.month}.`,
    `${published.length} of ${points.length} publish a value.`,
    metric === "price"
      ? `Median price ranges from ${priceUnits(minimum)} to ${priceUnits(maximum)}; the price axis is zoomed with 5% padding and does not start at zero.`
      : `Transaction volume ranges from ${formatTrendNumber(minimum)} to ${formatTrendNumber(maximum)} on a zero-based axis.`,
    missing > 0 ? `${plural(missing, "month")} publish no value.` : "",
    detailId === undefined ? "" : "Every month is listed in the monthly table.",
  ]
    .filter((part) => part !== "")
    .join(" ");

  const segments: { x: number; y: number }[][] = [];
  let current: { x: number; y: number }[] = [];

  points.forEach((entry, index) => {
    if (entry.price === null) {
      if (current.length > 0) {
        segments.push(current);
        current = [];
      }
      return;
    }
    current.push({ x: xFor(index), y: yFor(entry.price) });
  });
  if (current.length > 0) segments.push(current);

  const barWidth = Math.min(band * 0.62, 26);

  return figure(
    note + gapNote,
    <svg
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      className="mt-4 h-auto w-full"
      role="img"
      aria-labelledby={svgTitleId}
      aria-describedby={
        detailId === undefined ? descId : `${descId} ${detailId}`
      }
    >
      <title id={svgTitleId}>{title}</title>

      {axisTicks(domainMin, domainMax).map((tick) => (
        <g key={`tick-${tick}`}>
          <line
            x1={PLOT_LEFT}
            y1={yFor(tick)}
            x2={PLOT_RIGHT}
            y2={yFor(tick)}
            stroke={GRID_COLOUR}
            strokeWidth={1}
          />
          <text
            x={PLOT_LEFT - 8}
            y={yFor(tick) + 4}
            fontSize={11}
            textAnchor="end"
            fill={LABEL_COLOUR}
          >
            {formatTrendNumber(tick)}
          </text>
        </g>
      ))}

      {axisLabelIndices(points.length).map((index) => (
        <text
          key={`label-${points[index].month}`}
          x={xFor(index)}
          y={PLOT_BOTTOM + 18}
          fontSize={11}
          textAnchor="middle"
          fill={LABEL_COLOUR}
        >
          {monthLabel(points[index].month, singleYear)}
        </text>
      ))}

      {metric === "volume" ? (
        <>
          {points.map((entry, index) => {
            if (entry.volume === null) return null;
            const top = yFor(entry.volume);
            const height = Math.max(PLOT_BOTTOM - top, 0);
            return (
              <rect
                key={`bar-${entry.month}`}
                x={xFor(index) - barWidth / 2}
                y={height < 1 ? PLOT_BOTTOM - 1 : top}
                width={Math.max(barWidth, 1)}
                height={height < 1 ? 1 : height}
                fill={SERIES_COLOUR}
              />
            );
          })}
        </>
      ) : (
        <>
          {segments.map((segment) => (
            <path
              key={`segment-${segment[0].x}-${segment.length}`}
              d={segment
                .map(
                  (entry, index) =>
                    `${index === 0 ? "M" : "L"} ${entry.x.toFixed(1)} ${entry.y.toFixed(1)}`,
                )
                .join(" ")}
              fill="none"
              stroke={SERIES_COLOUR}
              strokeWidth={2.5}
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          ))}
          {points.length <= DENSE_THRESHOLD
            ? points.map((entry, index) =>
                entry.price === null ? null : (
                  <circle
                    key={`dot-${entry.month}`}
                    cx={xFor(index)}
                    cy={yFor(entry.price)}
                    r={3}
                    fill={SERIES_COLOUR}
                  />
                ),
              )
            : null}
        </>
      )}
    </svg>,
    description,
  );
}
