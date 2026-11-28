import React from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import ClientChart from "@/components/charts/ClientChart";
import { PROPERTY_COLOURS } from "@/constants/palette";

interface TrendRecord {
  date: string;
  [key: string]: number | string;
}

interface PriceTrendsChartProps {
  data: TrendRecord[];
}

export default function PriceTrendsChart({ data }: PriceTrendsChartProps) {
  // Filter data to show only dates after 2021
  const filteredData = data.filter((record) => record.date > "2021-12");

  return (
    <div className="bg-card p-6 rounded-lg border border-border">
      <h3 className="text-lg font-semibold mb-6 text-foreground">
        Price Trends (Median Transaction Price)
      </h3>
      <ClientChart className="h-[400px]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={filteredData}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis
              dataKey="date"
              className="text-xs"
              tick={{ fill: "hsl(var(--foreground))" }}
              minTickGap={30}
            />
            <YAxis
              className="text-xs"
              tick={{ fill: "hsl(var(--foreground))" }}
              tickFormatter={(value) => `$${value / 1000}k`}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "hsl(var(--card))",
                borderColor: "hsl(var(--border))",
              }}
              itemStyle={{ color: "hsl(var(--foreground))" }}
              labelStyle={{ color: "hsl(var(--foreground))" }}
            />
            <Legend />
            <Line
              type="monotone"
              dataKey="Overall Price"
              stroke={PROPERTY_COLOURS.all}
              strokeWidth={3}
              dot={false}
            />
            <Line
              type="monotone"
              dataKey="Condominium Price"
              stroke={PROPERTY_COLOURS.condo}
              strokeWidth={2}
              dot={false}
            />
            <Line
              type="monotone"
              dataKey="HDB Price"
              stroke={PROPERTY_COLOURS.hdb}
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </ClientChart>
    </div>
  );
}
