import React from 'react';
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import type { ChartData } from '@/utils/data-parser';

interface StatisticalPlotProps {
  data: ChartData;
  height?: number;
}

export default function StatisticalPlot({
  data,
  height = 400,
}: StatisticalPlotProps) {
  // Transform data for scatter plot (distribution view)
  const plotData: any[] = [];

  data.datasets.forEach((dataset, datasetIndex) => {
    const colors = [
      '#3b82f6',
      '#10b981',
      '#f59e0b',
      '#ef4444',
      '#8b5cf6',
    ];

    dataset.data.forEach((value, valueIndex) => {
      if (value !== null) {
        plotData.push({
          x: valueIndex,
          y: value,
          name: dataset.label,
          color: colors[datasetIndex % colors.length],
        });
      }
    });
  });

  // Group by dataset for better visualization
  const groupedData = data.labels.map((label, index) => {
    const point: any = { name: label };
    data.datasets.forEach((dataset) => {
      point[dataset.label] = dataset.data[index];
    });
    return point;
  });

  return (
    <div className="w-full">
      <ResponsiveContainer width="100%" height={height}>
        <ScatterChart data={groupedData}>
          <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
          <XAxis
            dataKey="name"
            className="text-sm"
            tick={{ fill: 'hsl(var(--foreground))' }}
          />
          <YAxis
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
          {data.datasets.map((dataset, index) => {
            const colors = [
              '#3b82f6',
              '#10b981',
              '#f59e0b',
              '#ef4444',
              '#8b5cf6',
            ];
            return (
              <Scatter
                key={dataset.label}
                name={dataset.label}
                dataKey={dataset.label}
                fill={colors[index % colors.length]}
                shape="circle"
              />
            );
          })}
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}
