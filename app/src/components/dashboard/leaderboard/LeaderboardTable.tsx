import React from 'react';
import type { LeaderboardDisplayRow, LeaderboardMetric } from '@/types/leaderboard';
import { METRICS } from './MetricHelpModal';

interface LeaderboardTableProps {
  data: LeaderboardDisplayRow[];
  selectedMetric: LeaderboardMetric;
  highlightedArea: string | null;
  onRowHover: (area: string | null) => void;
  onRowClick: (area: string) => void;
}

function formatNumber(value: number | null | undefined, digits: number = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return '—';
  }
  return value.toFixed(digits);
}

function formatCurrency(value: number | null): string {
  if (value === null || value === undefined) {
    return '—';
  }
  return `$${value.toLocaleString()}`;
}

function formatMetricValue(row: LeaderboardDisplayRow, metric: LeaderboardMetric): string {
  switch (metric) {
    case 'median_price':
      return formatCurrency(row.medianPrice);
    case 'median_psf':
      return row.medianPsf === null ? '—' : `$${row.medianPsf.toLocaleString()}`;
    case 'rental_yield_mean':
      return `${formatNumber(row.rentalYieldMean)}%`;
    case 'rental_yield_median':
      return `${formatNumber(row.rentalYieldMedian)}%`;
    case 'yoy_growth_pct':
      return `${row.yoyGrowthPct && row.yoyGrowthPct > 0 ? '+' : ''}${formatNumber(row.yoyGrowthPct)}%`;
    case 'mom_change_pct':
      return `${row.momChangePct && row.momChangePct > 0 ? '+' : ''}${formatNumber(row.momChangePct)}%`;
    case 'momentum':
      return `${row.momentum && row.momentum > 0 ? '+' : ''}${formatNumber(row.momentum)}`;
    case 'volume':
      return row.volume.toLocaleString();
    case 'affordability_ratio':
      return formatNumber(row.affordabilityRatio, 2);
    default:
      return '—';
  }
}

function metricTone(metric: LeaderboardMetric, value: string): string {
  if (metric === 'volume' || metric === 'median_price' || metric === 'median_psf' || metric === 'affordability_ratio') {
    return 'text-foreground';
  }

  if (value.startsWith('+')) {
    return 'text-emerald-600';
  }

  if (value.startsWith('-')) {
    return 'text-rose-600';
  }

  return 'text-foreground';
}

export default function LeaderboardTable({
  data,
  selectedMetric,
  highlightedArea,
  onRowHover,
  onRowClick,
}: LeaderboardTableProps) {
  const selectedMetricMeta = METRICS.find((metric) => metric.key === selectedMetric) || METRICS[0];
  const showPriceColumn = selectedMetric !== 'median_price';
  const showVolumeColumn = selectedMetric !== 'volume';

  if (data.length === 0) {
    return (
      <div className="rounded-2xl bg-muted/20 py-12 text-center">
        <p className="mb-2 text-muted-foreground">No planning areas match the current filters.</p>
        <p className="text-sm text-muted-foreground">Adjust the filters or clear the search to expand the results.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-1 md:flex-row md:items-center md:justify-between">
        <h3 className="text-lg font-semibold text-foreground">Planning Area Rankings</h3>
        <p className="text-sm text-muted-foreground">
          Sorted by <span className="font-medium text-foreground">{selectedMetricMeta.label}</span>
        </p>
      </div>

      <div className="overflow-x-auto rounded-2xl border border-border">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-muted/60 text-xs uppercase tracking-wide text-muted-foreground">
            <tr>
              <th className="px-3 py-3 font-semibold">Rank</th>
              <th className="px-3 py-3 font-semibold">Planning Area</th>
              <th className="px-3 py-3 font-semibold">Region</th>
              <th className="px-3 py-3 font-semibold">{selectedMetricMeta.label}</th>
              {showPriceColumn && <th className="px-3 py-3 font-semibold">Median Price</th>}
              {showVolumeColumn && <th className="hidden px-3 py-3 font-semibold lg:table-cell">Volume</th>}
              <th className="hidden px-3 py-3 font-semibold xl:table-cell">Property Mix</th>
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
                  className={`cursor-pointer transition-colors ${
                    isHighlighted ? 'bg-primary/10 ring-1 ring-inset ring-primary/20' : 'hover:bg-muted/40'
                  }`}
                  onMouseEnter={() => onRowHover(row.areaKey)}
                  onMouseLeave={() => onRowHover(null)}
                  onClick={() => onRowClick(row.areaKey)}
                >
                  <td className="px-3 py-3 font-semibold text-foreground">#{row.rank}</td>
                  <td className="px-3 py-3 font-medium text-foreground">{row.planningArea}</td>
                  <td className="px-3 py-3 text-muted-foreground">{row.region}</td>
                  <td className={`px-3 py-3 font-semibold ${metricTone(selectedMetric, selectedValue)}`}>{selectedValue}</td>
                  {showPriceColumn && <td className="px-3 py-3 text-foreground">{formatCurrency(row.medianPrice)}</td>}
                  {showVolumeColumn && (
                    <td className="hidden px-3 py-3 text-foreground lg:table-cell">{row.volume.toLocaleString()}</td>
                  )}
                  <td className="hidden px-3 py-3 xl:table-cell">
                    <div className="flex h-3 w-24 overflow-hidden rounded-full bg-muted">
                      {row.propertyMix.total > 0 && (
                        <>
                          <div
                            className="bg-sky-500"
                            style={{ width: `${(row.propertyMix.hdb / row.propertyMix.total) * 100}%` }}
                            title={`HDB ${row.propertyMix.hdb}`}
                          />
                          <div
                            className="bg-amber-500"
                            style={{ width: `${(row.propertyMix.ec / row.propertyMix.total) * 100}%` }}
                            title={`EC ${row.propertyMix.ec}`}
                          />
                          <div
                            className="bg-emerald-500"
                            style={{ width: `${(row.propertyMix.condo / row.propertyMix.total) * 100}%` }}
                            title={`Condo ${row.propertyMix.condo}`}
                          />
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
