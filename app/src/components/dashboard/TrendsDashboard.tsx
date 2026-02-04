import React, { useState } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  BarChart,
  Bar,
} from 'recharts';

interface TrendRecord {
  date: string;
  [key: string]: number | string;
}

export default function TrendsDashboard({ data }: { data: TrendRecord[] }) {
  // data is array of objects: { date: '2020-01', 'Overall Price': 100, 'HDB Price': 50, ... }
  
  return (
    <div className="space-y-8">
      {/* Price Trend Chart */}
      <div className="bg-card p-6 rounded-lg border border-border">
        <h3 className="text-lg font-semibold mb-6 text-foreground">
          Price Trends (Median Transaction Price)
        </h3>
        <div className="h-[400px]">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data}>
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

      {/* Volume Chart */}
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
    </div>
  );
}
