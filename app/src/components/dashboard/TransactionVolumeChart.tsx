import React from 'react';
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

interface TrendRecord {
  date: string;
  [key: string]: number | string;
}

interface TransactionVolumeChartProps {
  data: TrendRecord[];
}

export default function TransactionVolumeChart({ data }: TransactionVolumeChartProps) {
  return (
    <div className="bg-card p-6 rounded-lg border border-border">
      <h3 className="text-lg font-semibold mb-6 text-foreground">
        Transaction Volume
      </h3>
      <div className="h-[300px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data}>
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
            />
            <Tooltip
              cursor={{ fill: 'hsl(var(--muted)/0.2)' }}
              contentStyle={{ backgroundColor: 'hsl(var(--card))', borderColor: 'hsl(var(--border))' }}
              itemStyle={{ color: 'hsl(var(--foreground))' }}
            />
            <Legend />
            <Bar dataKey="HDB Volume" stackId="a" fill="#10b981" />
            <Bar dataKey="Condominium Volume" stackId="a" fill="#ef4444" />
            <Bar dataKey="EC Volume" stackId="a" fill="#f59e0b" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
