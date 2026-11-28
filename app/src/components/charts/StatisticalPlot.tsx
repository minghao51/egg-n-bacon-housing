import React from "react";
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";
import type { ChartData } from "@/utils/data-parser";
import { CATEGORICAL } from "@/constants/palette";
import ClientChart from "./ClientChart";

interface StatisticalPlotProps {
  data: ChartData;
  height?: number;
}

export default function StatisticalPlot({
  data,
  height = 400,
}: StatisticalPlotProps) {
  // Transform data for scatter plot (distribution view)
  const plotData: Record<string, string | number>[] = [];

  data.datasets.forEach((dataset, datasetIndex) => {
    dataset.data.forEach((value, valueIndex) => {
      if (value !== null) {
        plotData.push({
          x: valueIndex,
          y: value,
          name: dataset.label,
          color: CATEGORICAL[datasetIndex % CATEGORICAL.length],
        });
      }
    });
  });

  // Group by dataset for better visualization
  const groupedData = data.labels.map((label, index) => {
    const point: Record<string, string | number | null> = { name: label };
    data.datasets.forEach((dataset) => {
      point[dataset.label] = dataset.data[index];
    });
    return point;
  });

  return (
    <ClientChart className="w-full" style={{ height }}>
      {({ width }) => (
        <ScatterChart width={width} height={height} data={groupedData}>
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
          {data.datasets.map((dataset, index) => {
            return (
              <Scatter
                key={dataset.label}
                name={dataset.label}
                dataKey={dataset.label}
                fill={CATEGORICAL[index % CATEGORICAL.length]}
                shape="circle"
              />
            );
          })}
        </ScatterChart>
      )}
    </ClientChart>
  );
}
