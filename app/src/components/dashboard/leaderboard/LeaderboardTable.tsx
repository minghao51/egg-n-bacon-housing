import React from "react";
import type {
  LeaderboardDisplayRow,
  LeaderboardMetric,
} from "@/types/leaderboard";
import { SAMPLE_CAUTION_THRESHOLD } from "@/utils/leaderboard-observed";
import { METRICS } from "./MetricHelpModal";

interface LeaderboardTableProps {
  data: LeaderboardDisplayRow[];
  selectedMetric: LeaderboardMetric;
  highlightedArea: string | null;
  onRowHover: (area: string | null) => void;
  onRowClick: (area: string) => void;
}

function formatNumber(value: number | null, digits: number = 1): string {
  if (value === null || Number.isNaN(value)) {
    return "—";
  }
  return value.toFixed(digits);
}

function formatCurrency(value: number | null): string {
  if (value === null) {
    return "—";
  }
  return `$${value.toLocaleString()}`;
}

function formatMetricValue(
  row: LeaderboardDisplayRow,
  metric: LeaderboardMetric,
): string {
  switch (metric) {
    case "median_price":
      return formatCurrency(row.medianPrice);
    case "median_psf":
      return formatCurrency(row.medianPsf);
    case "volume":
      return row.volume === null ? "—" : row.volume.toLocaleString();
    default:
      // Unsupported metrics are never substituted; the page shows the reason.
      return "—";
  }
}

export default function LeaderboardTable({
  data,
  selectedMetric,
  highlightedArea,
  onRowHover,
  onRowClick,
}: LeaderboardTableProps) {
  const selectedMetricMeta =
    METRICS.find((metric) => metric.key === selectedMetric) ?? METRICS[0];
  const showPriceColumn = selectedMetric !== "median_price";
  const showVolumeColumn = selectedMetric !== "volume";

  if (data.length === 0) {
    return (
      <div className="rounded-2xl bg-muted/20 py-12 text-center">
        <p className="mb-2 text-muted-foreground">
          No planning areas match the current filters.
        </p>
        <p className="text-sm text-muted-foreground">
          Adjust the filters or clear the search to expand the results.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-1 md:flex-row md:items-center md:justify-between">
        <h3 className="text-lg font-semibold text-foreground">
          Planning Area Rankings
        </h3>
        <p className="text-sm text-muted-foreground">
          Sorted by{" "}
          <span className="font-medium text-foreground">
            {selectedMetricMeta.label}
          </span>
        </p>
      </div>

      <div className="overflow-x-auto rounded-2xl border border-border">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-muted/60 text-xs uppercase tracking-wide text-muted-foreground">
            <tr>
              <th className="px-3 py-3 font-semibold">Rank</th>
              <th className="px-3 py-3 font-semibold">Planning Area</th>
              <th className="px-3 py-3 font-semibold">Region</th>
              <th className="px-3 py-3 font-semibold">
                {selectedMetricMeta.label}
              </th>
              {showPriceColumn && (
                <th className="px-3 py-3 font-semibold">Median Price</th>
              )}
              {showVolumeColumn && (
                <th className="hidden px-3 py-3 font-semibold lg:table-cell">
                  Sales
                </th>
              )}
              <th className="hidden px-3 py-3 font-semibold xl:table-cell">
                Property Mix
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {data.map((row) => {
              const isHighlighted = highlightedArea === row.areaKey;
              const selectedValue = formatMetricValue(row, selectedMetric);

              return (
                <tr
                  key={row.areaKey}
                  data-area={row.areaKey}
                  data-ranked={row.rank === null ? "false" : "true"}
                  className={`cursor-pointer transition-colors ${
                    isHighlighted
                      ? "bg-primary/10 ring-1 ring-inset ring-primary/20"
                      : "hover:bg-muted/40"
                  }`}
                  onMouseEnter={() => onRowHover(row.areaKey)}
                  onMouseLeave={() => onRowHover(null)}
                  onClick={() => onRowClick(row.areaKey)}
                >
                  <td className="px-3 py-3 font-semibold text-foreground">
                    {row.rank === null ? (
                      <span
                        className="text-muted-foreground"
                        title={`Not ranked: fewer than ${SAMPLE_CAUTION_THRESHOLD} sales in this window`}
                      >
                        —
                      </span>
                    ) : (
                      `#${row.rank}`
                    )}
                  </td>
                  <td className="px-3 py-3 font-medium text-foreground">
                    <span>{row.planningArea}</span>
                    {row.isThinSample && (
                      <span
                        className="ml-2 rounded-full border border-amber-500/40 bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-900 dark:bg-amber-950/30 dark:text-amber-200"
                        title={`Fewer than ${SAMPLE_CAUTION_THRESHOLD} sales in this window; shown but not ranked.`}
                      >
                        Thin sample
                      </span>
                    )}
                  </td>
                  <td className="px-3 py-3 text-muted-foreground">
                    {row.region ?? "Unmapped"}
                  </td>
                  <td className="px-3 py-3 font-semibold text-foreground">
                    {selectedValue}
                  </td>
                  {showPriceColumn && (
                    <td className="px-3 py-3 text-foreground">
                      {formatCurrency(row.medianPrice)}
                    </td>
                  )}
                  {showVolumeColumn && (
                    <td className="hidden px-3 py-3 text-foreground lg:table-cell">
                      {row.volume === null ? "—" : row.volume.toLocaleString()}
                    </td>
                  )}
                  <td className="hidden px-3 py-3 xl:table-cell">
                    {row.propertyMix && row.propertyMix.total > 0 ? (
                      <div className="flex h-3 w-24 overflow-hidden rounded-full bg-muted">
                        <div
                          className="bg-sky-500"
                          style={{
                            width: `${((row.propertyMix.hdb ?? 0) / row.propertyMix.total) * 100}%`,
                          }}
                          title={`HDB ${formatNumber(row.propertyMix.hdb, 0)}`}
                        />
                        <div
                          className="bg-amber-500"
                          style={{
                            width: `${((row.propertyMix.ec ?? 0) / row.propertyMix.total) * 100}%`,
                          }}
                          title={`EC ${formatNumber(row.propertyMix.ec, 0)}`}
                        />
                        <div
                          className="bg-emerald-500"
                          style={{
                            width: `${((row.propertyMix.condo ?? 0) / row.propertyMix.total) * 100}%`,
                          }}
                          title={`Condo ${formatNumber(row.propertyMix.condo, 0)}`}
                        />
                      </div>
                    ) : (
                      <span className="text-muted-foreground">—</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <p className="text-xs text-muted-foreground">
        Rows with fewer than {SAMPLE_CAUTION_THRESHOLD} sales in the selected
        window stay visible but are not ranked. Property mix uses the same
        period as the ranking.
      </p>
    </div>
  );
}
