import React, { useState } from 'react';
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  ZAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine
} from 'recharts';

interface SegmentData {
  name: string;
  x: number; // Price PSF
  y: number; // Rental Yield
  z: number; // Volume
  category: string;
}

interface SegmentsData {
  whole: SegmentData[];
  pre_covid: SegmentData[];
  recent: SegmentData[];
  year_2025: SegmentData[];
  whole_hdb: SegmentData[];
  whole_ec: SegmentData[];
  whole_condo: SegmentData[];
  pre_covid_hdb: SegmentData[];
  pre_covid_ec: SegmentData[];
  pre_covid_condo: SegmentData[];
  recent_hdb: SegmentData[];
  recent_ec: SegmentData[];
  recent_condo: SegmentData[];
  year_2025_hdb: SegmentData[];
  year_2025_ec: SegmentData[];
  year_2025_condo: SegmentData[];
}

const COLORS = {
  "HDB": "#10b981",
  "Condominium": "#3b82f6",
  "EC": "#f59e0b"
};

export default function SegmentsAnalysis({ data }: { data: SegmentsData }) {
  const [temporalFilter, setTemporalFilter] = useState<'whole' | 'pre_covid' | 'recent' | 'year_2025'>('recent');
  const [propertyTypeFilter, setPropertyTypeFilter] = useState<'all' | 'hdb' | 'ec' | 'condo'>('all');

  // Determine data key based on filters
  const dataKey = propertyTypeFilter === 'all'
    ? temporalFilter
    : `${temporalFilter}_${propertyTypeFilter}` as keyof SegmentsData;
  const currentData = data[dataKey] || [];

  // Split data by category for better legend/coloring
  const hdbData = currentData.filter(d => d.category === 'HDB');
  const condoData = currentData.filter(d => d.category === 'Condominium');
  const ecData = currentData.filter(d => d.category === 'EC');

  return (
    <div className="bg-card p-6 rounded-lg border border-border">
      {/* Header and Filters */}
      <div className="flex flex-wrap justify-between items-start gap-4 mb-6">
        <div>
          <h3 className="text-lg font-semibold text-foreground">Market Segmentation</h3>
          <p className="text-sm text-muted-foreground mt-1">
            Price PSF vs Rental Yield. Bubble size represents transaction volume.
          </p>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-2">
          {/* Temporal Filter */}
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-muted-foreground">Period:</span>
            <div className="flex space-x-1 bg-muted p-1 rounded-md">
              {(['whole', 'pre_covid', 'recent', 'year_2025'] as const).map((key) => (
                <button
                  key={key}
                  onClick={() => setTemporalFilter(key)}
                  className={`px-2 py-1 text-xs font-medium rounded-sm transition-all ${temporalFilter === key
                    ? 'bg-background text-foreground shadow-sm'
                    : 'text-muted-foreground hover:text-foreground'
                    }`}
                >
                  {key === 'whole'
                    ? 'All Time'
                    : key === 'pre_covid'
                      ? 'Pre-COVID'
                      : key === 'recent'
                        ? 'Recent'
                        : '2025'}
                </button>
              ))}
            </div>
          </div>

          {/* Property Type Filter */}
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-muted-foreground">Type:</span>
            <div className="flex space-x-1 bg-muted p-1 rounded-md">
              {(['all', 'hdb', 'ec', 'condo'] as const).map((key) => (
                <button
                  key={key}
                  onClick={() => setPropertyTypeFilter(key)}
                  className={`px-2 py-1 text-xs font-medium rounded-sm transition-all ${propertyTypeFilter === key
                    ? 'bg-background text-foreground shadow-sm'
                    : 'text-muted-foreground hover:text-foreground'
                    }`}
                >
                  {key === 'all' ? 'All' : key.toUpperCase()}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
      
      <div className="h-[600px]">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis 
              type="number" 
              dataKey="x" 
              name="Price PSF" 
              unit="$" 
              className="text-xs" 
              tick={{ fill: 'hsl(var(--foreground))' }}
              label={{ value: 'Price PSF ($)', position: 'bottom', offset: 0, fill: 'hsl(var(--foreground))' }}
            />
            <YAxis 
              type="number" 
              dataKey="y" 
              name="Rental Yield" 
              unit="%" 
              className="text-xs"
              tick={{ fill: 'hsl(var(--foreground))' }}
              label={{ value: 'Rental Yield (%)', angle: -90, position: 'left', fill: 'hsl(var(--foreground))' }}
            />
            <ZAxis type="number" dataKey="z" range={[50, 1000]} name="Volume" />
            <Tooltip
              cursor={{ strokeDasharray: '3 3' }}
              contentStyle={{ backgroundColor: 'hsl(var(--card))', borderColor: 'hsl(var(--border))', color: 'hsl(var(--foreground))' }}
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  const data = payload[0].payload as SegmentData;
                  return (
                    <div className="bg-card border border-border p-3 rounded-lg shadow-lg">
                      <div className="font-bold text-foreground border-b border-border pb-1 mb-2">{data.name}</div>
                      <div className="text-sm space-y-1">
                        <div className="flex justify-between gap-4">
                          <span className="text-muted-foreground">Price PSF:</span>
                          <span className="font-medium text-foreground">${data.x.toFixed(0)}</span>
                        </div>
                        <div className="flex justify-between gap-4">
                          <span className="text-muted-foreground">Rental Yield:</span>
                          <span className="font-medium text-foreground">{data.y.toFixed(2)}%</span>
                        </div>
                        <div className="flex justify-between gap-4">
                          <span className="text-muted-foreground">Volume:</span>
                          <span className="font-medium text-foreground">{data.z.toLocaleString()}</span>
                        </div>
                        <div className="flex justify-between gap-4">
                          <span className="text-muted-foreground">Type:</span>
                          <span className="font-medium text-foreground">{data.category}</span>
                        </div>
                      </div>
                    </div>
                  );
                }
                return null;
              }}
            />
            <Legend />
            
            {hdbData.length > 0 && (
              <Scatter name="HDB" data={hdbData} fill={COLORS.HDB} shape="circle" />
            )}
            {condoData.length > 0 && (
              <Scatter name="Condominium" data={condoData} fill={COLORS.Condominium} shape="circle" />
            )}
            {ecData.length > 0 && (
              <Scatter name="EC" data={ecData} fill={COLORS.EC} shape="circle" />
            )}
            
            <ReferenceLine y={4} stroke="red" strokeDasharray="3 3" label={{ value: "4% Yield Target", position: 'insideTopRight', fill: 'red' }} />
          </ScatterChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
