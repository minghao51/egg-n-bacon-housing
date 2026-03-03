// app/src/components/dashboard/segments/compare/ComparisonCharts.tsx
import type { Segment } from '@/types/segments';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

interface ComparisonChartsProps {
  segments: Segment[];
}

export function ComparisonCharts({ segments }: ComparisonChartsProps) {
  if (segments.length < 2) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        Select at least 2 segments to view comparisons
      </div>
    );
  }

  // Prepare data for bar chart
  const barData = segments.map((segment) => ({
    name: segment.name,
    'Price PSF': segment.metrics.avgPricePsf,
    'Yield %': segment.metrics.avgYield,
    'YoY Growth %': segment.metrics.yoyGrowth,
  }));

  return (
    <div className="space-y-8">
      <div>
        <h3 className="text-lg font-semibold text-foreground mb-4">Key Metrics Comparison</h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={barData}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis dataKey="name" className="text-xs" tick={{ fill: 'hsl(var(--foreground))' }} />
            <YAxis className="text-xs" tick={{ fill: 'hsl(var(--foreground))' }} />
            <Tooltip
              contentStyle={{
                backgroundColor: 'hsl(var(--card))',
                borderColor: 'hsl(var(--border))',
                color: 'hsl(var(--foreground))',
              }}
            />
            <Legend />
            <Bar dataKey="Price PSF" fill="hsl(var(--primary))" />
            <Bar dataKey="Yield %" fill="#10b981" />
            <Bar dataKey="YoY Growth %" fill="#f59e0b" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
