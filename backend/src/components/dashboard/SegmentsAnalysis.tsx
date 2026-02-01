import React from 'react';
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

const COLORS = {
  "HDB": "#10b981",
  "Condominium": "#3b82f6",
  "EC": "#f59e0b"
};

export default function SegmentsAnalysis({ data }: { data: SegmentData[] }) {
  // Split data by category for better legend/coloring
  const hdbData = data.filter(d => d.category === 'HDB');
  const condoData = data.filter(d => d.category === 'Condominium');
  const ecData = data.filter(d => d.category === 'EC');

  return (
    <div className="bg-card p-6 rounded-lg border border-border">
      <h3 className="text-lg font-semibold mb-2 text-foreground">Market Segmentation</h3>
      <p className="text-sm text-muted-foreground mb-6">
        Price PSF vs Rental Yield. Bubble size represents transaction volume.
      </p>
      
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
