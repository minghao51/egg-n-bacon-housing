import React from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";
import type { ChartData } from "@/utils/data-parser";
import { CATEGORICAL } from "@/constants/palette";
import ClientChart from "./ClientChart";

interface ComparisonChartProps {
  data: ChartData;
  width?: number;
  height?: number;
  horizontal?: boolean;
}

export default function ComparisonChart({
  data,
  height = 400,
  horizontal = true,
}: ComparisonChartProps) {
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
        <BarChart
          width={width}
          height={height}
          data={chartData}
          // Recharts "horizontal" draws vertical bars. `horizontal` here means
          // horizontal bars, so the layout value is the inverse, matching the
          // numeric X axis / category Y axis configuration below.
          layout={horizontal ? "vertical" : "horizontal"}
        >
          <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
          <XAxis
            dataKey={horizontal ? undefined : "name"}
            type={horizontal ? "number" : "category"}
            className="text-sm"
            tick={{ fill: "hsl(var(--foreground))" }}
          />
          <YAxis
            dataKey={horizontal ? "name" : undefined}
            type={horizontal ? "category" : "number"}
            width={140}
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
            <Bar
              key={dataset.label}
              dataKey={dataset.label}
              fill={colors[index % colors.length]}
            />
          ))}
        </BarChart>
      )}
    </ClientChart>
  );
}
