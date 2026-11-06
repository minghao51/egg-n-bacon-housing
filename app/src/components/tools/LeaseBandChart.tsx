/**
 * Signed lease-band marks (slice S8, SVG 18).
 *
 * Each stored band is drawn as an interval on the remaining-lease axis and a
 * signed bar against the zero line: a stored discount is positive, a premium is
 * negative. Nothing is smoothed or fitted — this is a lookup table drawn to
 * scale. The accompanying table in `LeaseBands.tsx` is the accessible
 * equivalent, so the chart is decorative-but-described (`role="img"`).
 */

import type { LeaseBand } from "./lib/tool-assets";

interface LeaseBandChartProps {
  bands: readonly LeaseBand[];
  selected: LeaseBand | null;
}

const WIDTH = 640;
const HEIGHT = 260;
const MARGIN = { top: 16, right: 16, bottom: 40, left: 48 };
const PLOT_WIDTH = WIDTH - MARGIN.left - MARGIN.right;
const PLOT_HEIGHT = HEIGHT - MARGIN.top - MARGIN.bottom;
const X_MAX = 100;

function tickValues(min: number, max: number, step: number): number[] {
  const ticks: number[] = [];
  for (let value = min; value <= max; value += step) ticks.push(value);
  return ticks;
}

export default function LeaseBandChart({
  bands,
  selected,
}: LeaseBandChartProps) {
  if (bands.length === 0) return null;

  const discounts = bands.map((band) => band.discount_percent);
  const yMin = Math.min(-10, Math.floor(Math.min(...discounts) / 10) * 10);
  const yMax = Math.max(10, Math.ceil(Math.max(...discounts) / 10) * 10);

  const x = (years: number) =>
    MARGIN.left + (Math.max(0, Math.min(years, X_MAX)) / X_MAX) * PLOT_WIDTH;
  const y = (value: number) =>
    MARGIN.top + ((yMax - value) / (yMax - yMin)) * PLOT_HEIGHT;

  const yTicks = tickValues(yMin, yMax, 10);
  const xTicks = tickValues(0, X_MAX, 20);
  const zeroY = y(0);

  return (
    <figure className="mt-4">
      <svg
        role="img"
        aria-label="Stored lease-band statistics by remaining lease, signed percentage. Negative values are premiums."
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        className="h-auto w-full"
      >
        <title>Stored lease-band statistics, signed</title>
        {yTicks.map((tick) => (
          <g key={`y-${tick}`}>
            <line
              x1={MARGIN.left}
              x2={WIDTH - MARGIN.right}
              y1={y(tick)}
              y2={y(tick)}
              style={{ stroke: "hsl(var(--border))" }}
              strokeWidth={tick === 0 ? 1.5 : 0.5}
            />
            <text
              x={MARGIN.left - 8}
              y={y(tick) + 3}
              textAnchor="end"
              fontSize={10}
              style={{ fill: "hsl(var(--muted-foreground))" }}
            >
              {tick}
            </text>
          </g>
        ))}

        {xTicks.map((tick) => (
          <g key={`x-${tick}`}>
            <line
              x1={x(tick)}
              x2={x(tick)}
              y1={MARGIN.top}
              y2={HEIGHT - MARGIN.bottom}
              style={{ stroke: "hsl(var(--border))" }}
              strokeWidth={0.5}
            />
            <text
              x={x(tick)}
              y={HEIGHT - MARGIN.bottom + 14}
              textAnchor="middle"
              fontSize={10}
              style={{ fill: "hsl(var(--muted-foreground))" }}
            >
              {tick}
            </text>
          </g>
        ))}

        {bands.map((band) => {
          const isSelected =
            selected !== null &&
            band.lease_age_band === selected.lease_age_band;
          const left = x(band.min_lease_years);
          const right = x(band.max_lease_years);
          const top = y(Math.max(0, band.discount_percent));
          const bottom = y(Math.min(0, band.discount_percent));
          return (
            <g key={band.lease_age_band}>
              <rect
                x={left}
                y={top}
                width={Math.max(1, right - left)}
                height={Math.max(1, bottom - top)}
                style={{
                  fill: isSelected
                    ? "hsl(var(--rust))"
                    : band.discount_percent < 0
                      ? "hsl(var(--muted-foreground))"
                      : "hsl(var(--border))",
                  opacity: isSelected ? 1 : 0.85,
                }}
              />
              {isSelected ? (
                <text
                  x={(left + right) / 2}
                  y={band.discount_percent >= 0 ? top - 4 : bottom + 12}
                  textAnchor="middle"
                  fontSize={10}
                  fontWeight={700}
                  style={{ fill: "hsl(var(--foreground))" }}
                >
                  {band.lease_age_band}
                </text>
              ) : null}
            </g>
          );
        })}

        <text
          x={WIDTH - MARGIN.right}
          y={HEIGHT - 4}
          textAnchor="end"
          fontSize={10}
          style={{ fill: "hsl(var(--muted-foreground))" }}
        >
          Remaining lease / years
        </text>
        <text
          x={8}
          y={MARGIN.top + 4}
          fontSize={10}
          style={{ fill: "hsl(var(--muted-foreground))" }}
        >
          %
        </text>
        <line
          x1={MARGIN.left}
          x2={WIDTH - MARGIN.right}
          y1={zeroY}
          y2={zeroY}
          style={{ stroke: "hsl(var(--foreground))" }}
          strokeWidth={1}
        />
      </svg>
      <figcaption className="mt-2 text-xs text-muted-foreground">
        Signed percentage per stored band. Bar width is the band&rsquo;s stored
        remaining-lease interval; bar height is the stored statistic. Positive
        is a discount, negative is a premium. Not a fitted decay curve.
      </figcaption>
    </figure>
  );
}
