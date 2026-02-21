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
import type { ChartData } from '@/utils/data-parser';

interface ComparisonChartProps {
  data: ChartData;
  width?: number;
  height?: number;
  horizontal?: boolean;
}

export default function ComparisonChart({
  data,
  width = 800,
  height = 400,
  horizontal = false,
}: ComparisonChartProps) {
  // Transform data for Recharts
  const chartData = data.labels.map((label, index) => {
    const point: Record<string, string | number> = { name: label };
    data.datasets.forEach((dataset) => {
      point[dataset.label] = dataset.data[index];
    });
    return point;
  });

  // Generate colors for each dataset
  const colors = [
    '#3b82f6', // blue
    '#10b981', // green
    '#f59e0b', // amber
    '#ef4444', // red
    '#8b5cf6', // violet
  ];

  return (
    <div className="w-full">
      <ResponsiveContainer width="100%" height={height}>
        <BarChart
          data={chartData}
          layout={horizontal ? 'horizontal' : 'vertical'}
        >
          <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
          <XAxis
            dataKey={horizontal ? undefined : 'name'}
            type={horizontal ? 'number' : 'category'}
            className="text-sm"
            tick={{ fill: 'hsl(var(--foreground))' }}
          />
          <YAxis
            dataKey={horizontal ? 'name' : undefined}
            type={horizontal ? 'category' : 'number'}
            className="text-sm"
            tick={{ fill: 'hsl(var(--foreground))' }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: 'hsl(var(--card))',
              border: '1px solid hsl(var(--border))',
              borderRadius: '0.5rem',
            }}
            itemStyle={{ color: 'hsl(var(--foreground))' }}
          />
          <Legend />
          {data.datasets.map((dataset, index) => (
            <Bar
              key={dataset.label}
              dataKey={dataset.label}
              fill={colors[index % colors.length]}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
