import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

interface TrendRecord {
  date: string;
  [key: string]: number | string;
}

interface PriceTrendsChartProps {
  data: TrendRecord[];
}

export default function PriceTrendsChart({ data }: PriceTrendsChartProps) {
  // Filter data to show only dates after 2021
  const filteredData = data.filter(record => record.date > '2021-12');

  return (
    <div className="bg-card p-6 rounded-lg border border-border">
      <h3 className="text-lg font-semibold mb-6 text-foreground">
        Price Trends (Median Transaction Price)
      </h3>
      <div className="h-[400px]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={filteredData}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis
              dataKey="date"
              className="text-xs"
              tick={{ fill: 'hsl(var(--foreground))' }}
              minTickGap={30}
            />
            <YAxis
              className="text-xs"
              tick={{ fill: 'hsl(var(--foreground))' }}
              tickFormatter={(value) => `$${value / 1000}k`}
            />
            <Tooltip
              contentStyle={{ backgroundColor: 'hsl(var(--card))', borderColor: 'hsl(var(--border))' }}
              itemStyle={{ color: 'hsl(var(--foreground))' }}
              labelStyle={{ color: 'hsl(var(--foreground))' }}
            />
            <Legend />
            <Line
              type="monotone"
              dataKey="Overall Price"
              stroke="#3b82f6"
              strokeWidth={3}
              dot={false}
            />
            <Line
              type="monotone"
              dataKey="Condominium Price"
              stroke="#ef4444"
              strokeWidth={2}
              dot={false}
            />
            <Line
              type="monotone"
              dataKey="HDB Price"
              stroke="#10b981"
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
