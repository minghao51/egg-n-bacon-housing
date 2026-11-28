import React from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";
import type { ChartData } from "@/utils/data-parser";
import { CATEGORICAL } from "@/constants/palette";
import ClientChart from "./ClientChart";

interface TimeSeriesChartProps {
  data: ChartData;
  width?: number;
  height?: number;
}

export default function TimeSeriesChart({
  data,
  height = 400,
}: TimeSeriesChartProps) {
  // Transform data for Recharts
  const chartData = data.labels.map((label, index) => {
    const point: Record<string, string | number | null> = { name: label };
    data.datasets.forEach((dataset) => {
      point[dataset.label] = dataset.data[index];
    });
    return point;
  });

  // Dataset series are arbitrary categories, not property types.
  const colors = CATEGORICAL;

  return (
    <ClientChart className="w-full" style={{ height }}>
      {({ width }) => (
        <LineChart width={width} height={height} data={chartData}>
          <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
          <XAxis
            dataKey="name"
            className="text-sm"
            tick={{ fill: "hsl(var(--foreground))" }}
          />
          <YAxis
            className="text-sm"
            tick={{ fill: "hsl(var(--foreground))" }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "hsl(var(--card))",
              border: "1px solid hsl(var(--border))",
              borderRadius: "0.5rem",
            }}
            itemStyle={{ color: "hsl(var(--foreground))" }}
          />
          <Legend />
          {data.datasets.map((dataset, index) => (
            <Line
              key={dataset.label}
              type="monotone"
              dataKey={dataset.label}
              stroke={colors[index % colors.length]}
              strokeWidth={2}
              dot={{ r: 4 }}
              activeDot={{ r: 6 }}
            />
          ))}
        </LineChart>
      )}
    </ClientChart>
  );
}
