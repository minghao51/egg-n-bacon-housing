// app/src/components/dashboard/segments/compare/ComparisonTable.tsx
import type { Segment } from '@/types/segments';

interface ComparisonTableProps {
  segments: Segment[];
  persona: string;
}

export function ComparisonTable({ segments, persona }: ComparisonTableProps) {
  if (segments.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        Select 2-4 segments to compare
      </div>
    );
  }

  const metrics = [
    { key: 'avgPricePsf', label: 'Price PSF', format: (v: number) => `$${v.toFixed(0)}` },
    { key: 'avgYield', label: 'Rental Yield', format: (v: number) => `${v.toFixed(1)}%` },
    { key: 'yoyGrowth', label: 'YoY Growth', format: (v: number) => `+${v.toFixed(1)}%` },
    { key: 'transactionCount', label: 'Transactions', format: (v: number) => v.toLocaleString() },
    { key: 'marketShare', label: 'Market Share', format: (v: number) => `${(v * 100).toFixed(1)}%` },
    { key: 'persistenceProbability', label: 'Persistence', format: (v: number) => `${(v * 100).toFixed(0)}%` },
  ];

  const getBestValue = (metricKey: string) => {
    const values = segments.map((s) => (s.metrics as any)[metricKey]);
    const isHigherBetter = ['avgYield', 'yoyGrowth', 'transactionCount', 'marketShare', 'persistenceProbability'].includes(metricKey);

    if (isHigherBetter) {
      return Math.max(...values);
    } else {
      return Math.min(...values);
    }
  };

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse">
        <thead>
          <tr className="border-b border-border">
            <th className="text-left p-3 font-semibold text-foreground">Metric</th>
            {segments.map((segment) => (
              <th key={segment.id} className="p-3 font-semibold text-foreground text-center min-w-[150px]">
                {segment.name}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {metrics.map((metric) => {
            const bestValue = getBestValue(metric.key);
            return (
              <tr key={metric.key} className="border-b border-border">
                <td className="p-3 text-sm text-muted-foreground">{metric.label}</td>
                {segments.map((segment) => {
                  const value = (segment.metrics as any)[metric.key];
                  const isBest = value === bestValue;
                  return (
                    <td
                      key={segment.id}
                      className={`p-3 text-center text-sm font-medium ${
                        isBest ? 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300' : ''
                      }`}
                    >
                      {metric.format(value)}
                    </td>
                  );
                })}
              </tr>
            );
          })}
          <tr className="border-b border-border">
            <td className="p-3 text-sm text-muted-foreground">Risk Level</td>
            {segments.map((segment) => (
              <td key={segment.id} className="p-3 text-center text-sm font-medium">
                {segment.characteristics.riskLevel}
              </td>
            ))}
          </tr>
          <tr>
            <td className="p-3 text-sm text-muted-foreground">Volatility</td>
            {segments.map((segment) => (
              <td key={segment.id} className="p-3 text-center text-sm font-medium">
                {segment.characteristics.volatility}
              </td>
            ))}
          </tr>
        </tbody>
      </table>
    </div>
  );
}
