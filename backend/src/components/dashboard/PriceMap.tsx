import React, { useEffect, useState } from 'react';
import { MapContainer, TileLayer, GeoJSON, Tooltip as LeafletTooltip } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';

interface MapMetrics {
  [areaName: string]: {
    median_price: number;
    median_psf: number;
    volume: number;
  };
}

interface MapData {
  whole: MapMetrics;
  pre_covid: MapMetrics;
  recent: MapMetrics;
}

interface PriceMapProps {
  geoJsonUrl: string;
  metricsUrl: string;
}

export default function PriceMap({ geoJsonUrl, metricsUrl }: PriceMapProps) {
  const [geoJsonData, setGeoJsonData] = useState<any>(null);
  const [allMetrics, setAllMetrics] = useState<MapData | null>(null);
  const [era, setEra] = useState<'whole' | 'pre_covid' | 'recent'>('whole');
  const [metric, setMetric] = useState<'median_price' | 'median_psf' | 'volume'>('median_price');

  useEffect(() => {
    Promise.all([
      fetch(geoJsonUrl).then(res => res.json()),
      fetch(metricsUrl).then(res => res.json())
    ]).then(([geo, met]) => {
      setGeoJsonData(geo);
      setAllMetrics(met);
    });
  }, [geoJsonUrl, metricsUrl]);

  if (!geoJsonData || !allMetrics) {
    return <div className="h-[500px] flex items-center justify-center bg-muted/20">Loading Map Data...</div>;
  }

  const currentMetrics = allMetrics[era];

  // Dynamic Color Scale
  const getValues = () => {
    return Object.values(currentMetrics).map(m => m[metric]);
  };
  
  const values = getValues();
  const min = Math.min(...values);
  const max = Math.max(...values);

  const getColor = (val: number) => {
    if (!val) return '#FFEDA0';
    
    // Normalize value 0-1
    const norm = (val - min) / (max - min);
    
    // Color scale (Red to Yellow)
    // We can use discrete buckets based on normalized value
    return norm > 0.8 ? '#800026' :
           norm > 0.6 ? '#BD0026' :
           norm > 0.4 ? '#E31A1C' :
           norm > 0.2 ? '#FC4E2A' :
           norm > 0.1 ? '#FD8D3C' :
           norm > 0.05 ? '#FEB24C' :
                        '#FFEDA0';
  };

  const style = (feature: any) => {
    const name = feature.properties.PLN_AREA_N; 
    const data = currentMetrics[name];
    const value = data ? data[metric] : 0;
    
    return {
      fillColor: getColor(value),
      weight: 1,
      opacity: 1,
      color: 'white',
      dashArray: '3',
      fillOpacity: 0.7
    };
  };

  const onEachFeature = (feature: any, layer: any) => {
    const name = feature.properties.PLN_AREA_N;
    const data = currentMetrics[name];
    
    if (data) {
      const content = `
        <div class="text-sm">
          <div class="font-bold border-b pb-1 mb-1">${name}</div>
          <div class="grid grid-cols-2 gap-x-4 gap-y-1">
            <span class="text-muted-foreground">Price:</span>
            <span class="font-medium text-right">$${data.median_price.toLocaleString()}</span>
            
            <span class="text-muted-foreground">PSF:</span>
            <span class="font-medium text-right">$${data.median_psf.toLocaleString()}</span>
            
            <span class="text-muted-foreground">Volume:</span>
            <span class="font-medium text-right">${data.volume.toLocaleString()}</span>
          </div>
        </div>
      `;
      layer.bindTooltip(content, { 
        sticky: true,
        direction: 'top',
        className: 'custom-leaflet-tooltip'
      });
    } else {
      layer.bindTooltip(`${name}: No Data`, { sticky: true });
    }
    
    // Highlight on hover
    layer.on({
      mouseover: (e: any) => {
        const layer = e.target;
        layer.setStyle({
          weight: 3,
          color: '#666',
          dashArray: '',
          fillOpacity: 0.9
        });
        layer.bringToFront();
      },
      mouseout: (e: any) => {
        const layer = e.target;
        // Reset style (can't easily access original style function here without recalculating)
        // Simple reset:
        layer.setStyle({
          weight: 1,
          color: 'white',
          dashArray: '3',
          fillOpacity: 0.7
        });
      }
    });
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-4 justify-between items-center bg-card p-4 rounded-lg border border-border">
        {/* Metric Selector */}
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-muted-foreground">Metric:</span>
          <select 
            value={metric} 
            onChange={(e) => setMetric(e.target.value as any)}
            className="p-2 border border-border rounded bg-background text-foreground text-sm focus:ring-2 focus:ring-primary"
          >
            <option value="median_price">Median Price</option>
            <option value="median_psf">Median PSF</option>
            <option value="volume">Volume</option>
          </select>
        </div>

        {/* Era Selector */}
        <div className="flex space-x-1 bg-muted p-1 rounded-md">
          {(['whole', 'pre_covid', 'recent'] as const).map((key) => (
            <button
              key={key}
              onClick={() => setEra(key)}
              className={`px-3 py-1.5 text-xs font-medium rounded-sm transition-all ${
                era === key
                  ? 'bg-background text-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              {key === 'whole'
                ? 'All Time'
                : key === 'pre_covid'
                ? 'Pre-COVID'
                : 'Recent'}
            </button>
          ))}
        </div>
      </div>
      
      <div className="h-[600px] border border-border rounded-lg overflow-hidden relative z-0 bg-slate-50 dark:bg-slate-900">
        <MapContainer 
          center={[1.3521, 103.8198]} 
          zoom={11} 
          style={{ height: '100%', width: '100%' }}
          zoomControl={false}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
          />
          <GeoJSON 
            key={`${era}-${metric}`} // Force re-render when data changes
            data={geoJsonData} 
            style={style} 
            onEachFeature={onEachFeature} 
          />
        </MapContainer>
        
        {/* Legend Overlay */}
        <div className="absolute bottom-4 right-4 bg-background/90 backdrop-blur p-3 rounded-lg border border-border text-xs z-[1000] shadow-lg">
          <div className="font-semibold mb-2 capitalize">{metric.replace('_', ' ')}</div>
          <div className="flex flex-col gap-1">
            <div className="flex items-center gap-2">
              <span className="w-4 h-4 rounded bg-[#800026]"></span>
              <span>High</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-4 h-4 rounded bg-[#FD8D3C]"></span>
              <span>Medium</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-4 h-4 rounded bg-[#FFEDA0]"></span>
              <span>Low</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}