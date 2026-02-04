import React, { useEffect, useState } from 'react';
import { MapContainer, TileLayer, GeoJSON, Tooltip as LeafletTooltip } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';

interface MapMetrics {
  [areaName: string]: {
    median_price: number;
    median_psf: number;
    volume: number;
    // New metrics (optional as they might be missing for some eras/areas)
    mom_change_pct?: number;
    yoy_change_pct?: number;
    momentum?: number;
    momentum_signal?: string;
    rental_yield_mean?: number;
    rental_yield_median?: number;
    rental_yield_std?: number;
    affordability_ratio?: number;
    affordability_class?: string;
    mortgage_to_income_pct?: number;
  };
}

interface MapData {
  // Temporal periods
  whole: MapMetrics;
  pre_covid: MapMetrics;
  recent: MapMetrics;
  year_2025: MapMetrics;
  // Property types (all time)
  hdb: MapMetrics;
  ec: MapMetrics;
  condo: MapMetrics;
  // Combined era + property type
  whole_hdb: MapMetrics;
  whole_ec: MapMetrics;
  whole_condo: MapMetrics;
  pre_covid_hdb: MapMetrics;
  pre_covid_ec: MapMetrics;
  pre_covid_condo: MapMetrics;
  recent_hdb: MapMetrics;
  recent_ec: MapMetrics;
  recent_condo: MapMetrics;
  year_2025_hdb: MapMetrics;
  year_2025_ec: MapMetrics;
  year_2025_condo: MapMetrics;
}

interface PriceMapProps {
  geoJsonUrl: string;
  metricsUrl: string;
}

export default function PriceMap({ geoJsonUrl, metricsUrl }: PriceMapProps) {
  const [geoJsonData, setGeoJsonData] = useState<any>(null);
  const [allMetrics, setAllMetrics] = useState<MapData | null>(null);
  // Independent temporal and property type filters
  const [temporalFilter, setTemporalFilter] = useState<'whole' | 'pre_covid' | 'recent' | 'year_2025'>('whole');
  const [propertyTypeFilter, setPropertyTypeFilter] = useState<'all' | 'hdb' | 'ec' | 'condo'>('all');
  const [metric, setMetric] = useState<'median_price' | 'median_psf' | 'volume' | 'rental_yield_median' | 'yoy_change_pct' | 'affordability_ratio'>('median_price');

  useEffect(() => {
    async function loadData() {
      try {
        const [geo, met] = await Promise.all([
          fetch(geoJsonUrl).then(res => res.json()),
          fetch(metricsUrl).then(async res => {
            const text = await res.text();
            // JSON spec doesn't allow NaN, but Python's json.dump might output it if not careful.
            // We sanitize it here just in case.
            const sanitized = text.replace(/:\s*NaN/g, ': null');
            return JSON.parse(sanitized);
          })
        ]);
        setGeoJsonData(geo);
        setAllMetrics(met);
      } catch (error) {
        console.error("Failed to load map data:", error);
      }
    }
    loadData();
  }, [geoJsonUrl, metricsUrl]);

  if (!geoJsonData || !allMetrics) {
    return <div className="h-[500px] flex items-center justify-center bg-muted/20">Loading Map Data...</div>;
  }

  // Determine data key based on temporal and property type filters
  const dataKey = propertyTypeFilter === 'all'
    ? temporalFilter
    : `${temporalFilter}_${propertyTypeFilter}` as keyof MapData;
  const currentMetrics = allMetrics[dataKey];

  // Dynamic Color Scale
  const getValues = () => {
    return Object.values(currentMetrics).map(m => m[metric] || 0);
  };

  const values = getValues();
  // Filter out zero values for better geometric color scale if needed
  // For growth (yoy_change_pct), values can be negative, so we adjust filter logic
  const validValues = values.filter(v => v !== 0 && v !== undefined && !isNaN(v));
  const min = validValues.length > 0 ? Math.min(...validValues) : 0;
  const max = Math.max(...values);

  const getColor = (val: number | undefined) => {
    if (val === undefined || val === null || (metric !== 'yoy_change_pct' && val === 0)) return '#FFEDA0';

    // Special handling for Affordability (Lower is better usually, but sticking to High Value = Hot Color for consistency)
    // Or Growth (Negative is cold, Positive is hot)

    // Simple normalization for now
    const normalized = (val - min) / (max - min);

    // Custom buckets based on distribution
    // High-end areas shouldn't drown out the differences in the mid-range
    return val > max * 0.9 ? '#800026' :
      val > max * 0.7 ? '#BD0026' :
        val > max * 0.5 ? '#E31A1C' :
          val > max * 0.35 ? '#FC4E2A' :
            val > max * 0.2 ? '#FD8D3C' :
              val > max * 0.1 ? '#FEB24C' :
                '#FFEDA0';
  };

  const style = (feature: any) => {
    // FIX: GeoJSON uses 'pln_area_n' (lowercase) but we were looking for 'PLN_AREA_N'
    // Also normalize to uppercase for the metrics lookup just in case
    const rawName = feature.properties.pln_area_n || feature.properties.PLN_AREA_N;
    const name = rawName ? rawName.toUpperCase() : '';

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
    const rawName = feature.properties.pln_area_n || feature.properties.PLN_AREA_N;
    const name = rawName ? rawName.toUpperCase() : 'Unknown Area';
    const data = currentMetrics[name];

    // Format label for metric selector
    const metricLabels: Record<string, string> = {
      median_price: 'Price',
      median_psf: 'PSF',
      volume: 'Volume',
      rental_yield_median: 'Yield',
      yoy_change_pct: 'Growth',
      affordability_ratio: 'Affordability'
    };
    const metricLabel = metricLabels[metric] || metric;

    if (data) {
      const growthColor = (data.yoy_change_pct || 0) >= 0 ? 'text-green-600' : 'text-red-600';
      const momentumSignal = data.momentum_signal || 'N/A';

      const content = `
        <div class="text-sm min-w-[200px]">
          <div class="font-bold border-b pb-1 mb-2 text-base flex justify-between">
            <span>${name}</span>
            <span class="text-xs font-normal text-muted-foreground self-center">${data.affordability_class || ''}</span>
          </div>
          <div class="grid grid-cols-2 gap-x-4 gap-y-1">
            <span class="text-muted-foreground">Price:</span>
            <span class="font-medium text-right">$${data.median_price.toLocaleString()}</span>
            
            <span class="text-muted-foreground">PSF:</span>
            <span class="font-medium text-right">$${data.median_psf.toLocaleString()}</span>
            
            <span class="text-muted-foreground">Volume:</span>
            <span class="font-medium text-right">${data.volume.toLocaleString()}</span>

            <span class="text-muted-foreground">Rental Yield:</span>
            <span class="font-medium text-right">${data.rental_yield_median ? data.rental_yield_median + '%' : '-'}</span>

            <span class="text-muted-foreground">YoY Growth:</span>
            <span class="font-medium text-right ${growthColor}">${data.yoy_change_pct ? data.yoy_change_pct + '%' : '-'}</span>
            
            <span class="text-muted-foreground">Affordability:</span>
            <span class="font-medium text-right">${data.affordability_ratio ? data.affordability_ratio + 'x' : '-'}</span>
          </div>
          
          ${data.momentum_signal ? `
          <div class="mt-2 text-xs bg-muted/50 p-1 rounded flex justify-between items-center">
             <span>Momentum:</span>
             <span class="font-semibold ${momentumSignal === 'Bullish' ? 'text-green-600' : momentumSignal === 'Bearish' ? 'text-red-600' : 'text-yellow-600'}">
               ${momentumSignal}
             </span>
          </div>
          ` : ''}
          
          <div class="mt-2 pt-2 border-t text-xs text-muted-foreground text-center">
             ${metricLabel} Rank: ${getColor(data[metric]) === '#800026' ? 'Top Tier' : 'Standard'}
          </div>
        </div>
      `;
      layer.bindTooltip(content, {
        sticky: true,
        direction: 'top',
        className: 'custom-leaflet-tooltip'
      });
    } else {
      layer.bindTooltip(`<div class="font-bold">${name}</div><div class="text-xs text-muted-foreground">No transaction data available</div>`, { sticky: true });
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
        // Reset style
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
            <option value="rental_yield_median">Rental Yield</option>
            <option value="yoy_change_pct">YoY Growth</option>
            <option value="affordability_ratio">Affordability Ratio</option>
          </select>
        </div>

        {/* Temporal & Property Type Filters */}
        <div className="flex flex-wrap gap-2">
          {/* Temporal Filter */}
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-muted-foreground">Period:</span>
            <div className="flex space-x-1 bg-muted p-1 rounded-md">
              {(['whole', 'pre_covid', 'recent', 'year_2025'] as const).map((key) => (
                <button
                  key={key}
                  onClick={() => setTemporalFilter(key)}
                  className={`px-3 py-1.5 text-xs font-medium rounded-sm transition-all whitespace-nowrap ${temporalFilter === key
                    ? 'bg-background text-foreground shadow-sm'
                    : 'text-muted-foreground hover:text-foreground'
                    }`}
                >
                  {key === 'whole' ? 'All Time' :
                    key === 'pre_covid' ? 'Pre-COVID' :
                      key === 'recent' ? 'Recent' :
                        key === 'year_2025' ? '2025' : key}
                </button>
              ))}
            </div>
          </div>

          {/* Property Type Filter */}
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-muted-foreground">Type:</span>
            <div className="flex space-x-1 bg-muted p-1 rounded-md">
              {(['all', 'hdb', 'ec', 'condo'] as const).map((key) => (
                <button
                  key={key}
                  onClick={() => setPropertyTypeFilter(key)}
                  className={`px-3 py-1.5 text-xs font-medium rounded-sm transition-all whitespace-nowrap ${propertyTypeFilter === key
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
            key={`${dataKey}-${metric}`} // Force re-render when data changes
            data={geoJsonData}
            style={style}
            onEachFeature={onEachFeature}
          />
        </MapContainer>

        {/* Legend Overlay */}
        <div className="absolute bottom-4 right-4 bg-background/90 backdrop-blur p-3 rounded-lg border border-border text-xs z-[1000] shadow-lg">
          <div className="font-semibold mb-2 capitalize">{metric.replace(/_/g, ' ')}</div>
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