import type { SegmentAreaRow, SegmentInvestigationMetric } from '@/types/segments';

interface SegmentAreaTableProps {
  rows: SegmentAreaRow[];
  selectedMetric: SegmentInvestigationMetric;
  highlightedArea: string | null;
  onRowHover: (area: string | null) => void;
  onRowClick: (area: string) => void;
}

function formatMetricValue(value: number, metric: SegmentInvestigationMetric): string {
  switch (metric) {
    case 'avgPricePsf':
      return `$${value.toFixed(0)}`;
    case 'avgYield':
    case 'forecast6m':
      return `${value.toFixed(1)}%`;
    case 'persistenceProbability':
      return `${(value * 100).toFixed(1)}%`;
    case 'mrtPremium':
      return `$${value.toFixed(0)}`;
    default:
      return value.toFixed(1);
  }
}

function metricLabel(metric: SegmentInvestigationMetric): string {
  switch (metric) {
    case 'avgPricePsf':
      return 'Avg PSF';
    case 'avgYield':
      return 'Avg Yield';
    case 'forecast6m':
      return '6M Forecast';
    case 'mrtPremium':
      return 'MRT Premium';
    case 'persistenceProbability':
      return 'Persistence';
    default:
      return metric;
  }
}

export default function SegmentAreaTable({
  rows,
  selectedMetric,
  highlightedArea,
  onRowHover,
  onRowClick,
}: SegmentAreaTableProps) {
  if (rows.length === 0) {
    return (
      <div className="rounded-2xl bg-muted/20 py-12 text-center">
        <p className="mb-2 text-muted-foreground">No candidate areas match the current constraints.</p>
        <p className="text-sm text-muted-foreground">
          Widen the price, region, or hotspot filters to restore the shortlist.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-foreground">Matching Areas</h3>
        <p className="text-sm text-muted-foreground">Sorted by {metricLabel(selectedMetric)}</p>
      </div>

      <div className="overflow-x-auto rounded-2xl border border-border">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-muted/60 text-xs uppercase tracking-wide text-muted-foreground">
            <tr>
              <th className="px-3 py-3 font-semibold">Planning Area</th>
              <th className="px-3 py-3 font-semibold">Region</th>
              <th className="px-3 py-3 font-semibold">Avg PSF</th>
              <th className="px-3 py-3 font-semibold">Avg Yield</th>
              <th className="px-3 py-3 font-semibold">6M Forecast</th>
              <th className="px-3 py-3 font-semibold">MRT Premium</th>
              <th className="px-3 py-3 font-semibold">Hotspot Confidence</th>
              <th className="px-3 py-3 font-semibold">Persistence</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {rows.map((row) => {
              const isHighlighted = highlightedArea === row.areaKey;

              return (
                <tr
                  key={row.areaKey}
                  className={`cursor-pointer transition-colors ${
                    isHighlighted ? 'bg-primary/10 ring-1 ring-inset ring-primary/20' : 'hover:bg-muted/40'
                  }`}
                  onMouseEnter={() => onRowHover(row.areaKey)}
                  onMouseLeave={() => onRowHover(null)}
                  onClick={() => onRowClick(row.areaKey)}
                >
                  <td className="px-3 py-3 font-medium text-foreground">{row.planningArea}</td>
                  <td className="px-3 py-3 text-muted-foreground">{row.region}</td>
                  <td className="px-3 py-3 text-foreground">{formatMetricValue(row.avgPricePsf, 'avgPricePsf')}</td>
                  <td className="px-3 py-3 text-foreground">{formatMetricValue(row.avgYield, 'avgYield')}</td>
                  <td className="px-3 py-3 text-foreground">{formatMetricValue(row.forecast6m, 'forecast6m')}</td>
                  <td className="px-3 py-3 text-foreground">{formatMetricValue(row.mrtPremium, 'mrtPremium')}</td>
                  <td className="px-3 py-3 text-foreground">{row.hotspotConfidence}</td>
                  <td className="px-3 py-3 text-foreground">
                    {formatMetricValue(row.persistenceProbability, 'persistenceProbability')}
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
