// app/src/components/dashboard/leaderboard/LeaderboardMap.tsx
import React, { useState, useEffect, useMemo } from 'react';
import { LeaderboardEntry, LeaderboardMetric, MetricMeta } from '@/types/leaderboard';

// Define types locally to avoid circular dependencies
type PropertyType = 'HDB' | 'Condominium' | 'EC';
type TimeHorizon = 'short' | 'medium' | 'long';

interface FilterState {
  investmentGoal: string | null;
  budgetRange: [number, number];
  propertyTypes: PropertyType[];
  locations: string[];
  timeHorizon: TimeHorizon | null;
  hotspotFilter: string;
}

// Do NOT import react-leaflet at module level
// Import it dynamically only in the browser

async function decompressGzip(buffer: ArrayBuffer): Promise<string> {
  // Try to decode as text first (browser may have auto-decompressed)
  try {
    const text = new TextDecoder().decode(buffer);
    // If it looks like JSON, return it
    if (text.trim().startsWith('{') || text.trim().startsWith('[')) {
      return text;
    }
  } catch (e) {
    // Not text, continue to decompression
  }

  // Use DecompressionStream if available (modern browsers)
  if ('DecompressionStream' in window) {
    try {
      const stream = new Response(buffer).body;
      if (!stream) throw new Error('No stream available');

      const decompressedStream = stream.pipeThrough(
        new DecompressionStream('gzip')
      );

      const reader = decompressedStream.getReader();
      const chunks: Uint8Array[] = [];

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        chunks.push(value);
      }

      const decompressed = new Uint8Array(chunks.reduce((acc, chunk) => acc + chunk.length, 0));
      let offset = 0;
      for (const chunk of chunks) {
        decompressed.set(chunk, offset);
        offset += chunk.length;
      }

      return new TextDecoder().decode(decompressed);
    } catch (e) {
      // Decompression failed, try returning as text
      return new TextDecoder().decode(buffer);
    }
  }

  // Fallback: assume response was already decompressed by browser
  return new TextDecoder().decode(buffer);
}

interface LeaderboardMapProps {
  data: LeaderboardEntry[];
  selectedMetric: LeaderboardMetric;
  metricMeta: MetricMeta;
  filters: FilterState;
  highlightedArea: string | null;
  onAreaHover: (area: string | null) => void;
  onAreaClick: (area: string) => void;
}

interface GeoJSONFeature {
  properties: {
    pln_area_n?: string;
    PLN_AREA_N?: string;
  };
}

interface LeafletLayerEvent {
  target: {
    setStyle: (style: unknown) => void;
    bringToFront: () => void;
    resetStyle: (layer: unknown) => void;
  };
  layer: unknown;
}

// Color scales
const PRICE_COLORS = ['#EFF3FF', '#BDD7E7', '#6BAED6', '#3182BD', '#08519C'];
const GROWTH_COLORS = ['#D73027', '#F46D43', '#FDAE61', '#FEE08B', '#FFFFBF', '#D9EF8B', '#A6D96A', '#66BD63', '#1A9850'];
const YIELD_COLORS = ['#F7FCB5', '#ADDD8E', '#74C476', '#31A354', '#006D2C'];
const VOLUME_COLORS = ['#FEF0D9', '#FDCC8A', '#FC8D59', '#E34A33', '#B30000'];

function getColorScale(metric: LeaderboardMetric): string[] {
  if (metric.includes('price') || metric.includes('psf')) {
    return PRICE_COLORS;
  }
  if (metric.includes('growth') || metric.includes('momentum') || metric.includes('change')) {
    return GROWTH_COLORS;
  }
  if (metric.includes('yield')) {
    return YIELD_COLORS;
  }
  return VOLUME_COLORS;
}

/**
 * Get current metric value for a planning area based on filters
 */
function getCurrentMetricValue(
  entry: LeaderboardEntry,
  metricName: LeaderboardMetric,
  filters: FilterState
): number {
  // Determine if we should use property-type-specific metrics
  const usePropertyType = filters.propertyTypes.length === 1;
  const propTypeKey = usePropertyType
    ? (filters.propertyTypes[0] === 'HDB' ? 'hdb' : filters.propertyTypes[0] === 'EC' ? 'ec' : 'condo')
    : null;

  // Determine time period
  const timePeriod = filters.timeHorizon === 'short'
    ? 'year_2025'
    : filters.timeHorizon === 'medium'
    ? 'recent'
    : filters.timeHorizon === 'long'
    ? 'whole'
    : 'recent';

  // Navigate to correct nested object
  let source: any = entry;

  // If single property type selected and has data, use that type's metrics
  if (propTypeKey && usePropertyType) {
    const propMetrics = entry.by_property_type[propTypeKey as keyof typeof entry.by_property_type];
    if (propMetrics && propMetrics.median_price !== null && propMetrics.volume > 0) {
      source = propMetrics;
    }
  }

  // If time period is specified and not 'recent', use period-specific metrics
  if (timePeriod !== 'recent' && timePeriod !== 'whole') {
    const periodMetrics = entry.by_time_period[timePeriod as keyof typeof entry.by_time_period];
    if (periodMetrics && periodMetrics.median_price !== null) {
      source = periodMetrics;
    }
  }

  // Get metric value
  const value = (source as any)[metricName];

  // Handle null/undefined
  if (value === null || value === undefined) {
    // Fall back to overall metric
    const fallbackValue = (entry as any)[metricName];
    return fallbackValue ?? 0;
  }

  return value as number;
}

export default function LeaderboardMap({
  data,
  selectedMetric,
  metricMeta,
  filters,
  highlightedArea,
  onAreaHover,
  onAreaClick,
}: LeaderboardMapProps) {
  const [isClient, setIsClient] = useState(false);
  const [MapContainer, setMapContainer] = useState<any>(null);
  const [TileLayer, setTileLayer] = useState<any>(null);
  const [GeoJSON, setGeoJSON] = useState<any>(null);
  const [geoJsonData, setGeoJsonData] = useState<any>(null);

  // Only load Leaflet on client side
  useEffect(() => {
    setIsClient(true);

    // Dynamic import of react-leaflet
    import('react-leaflet').then((modules) => {
      setMapContainer(() => modules.MapContainer);
      setTileLayer(() => modules.TileLayer);
      setGeoJSON(() => modules.GeoJSON);
    });

    // Load CSS
    import('leaflet/dist/leaflet.css');

    // Load GeoJSON data
    fetch(`${import.meta.env.BASE_URL}data/planning_areas.geojson.gz`)
      .then(res => {
        if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
        return res.arrayBuffer();
      })
      .then(async buffer => {
        const textStr = await decompressGzip(buffer);
        return JSON.parse(textStr);
      })
      .then(data => setGeoJsonData(data))
      .catch(err => console.error('Failed to load GeoJSON:', err));
  }, []);

  // Build metric data dictionary and compute color scale
  const { metricData, minValue, maxValue, getColor } = useMemo(() => {
    const dataDict: Record<string, number> = {};

    data.forEach(entry => {
      const value = getCurrentMetricValue(entry, selectedMetric, filters);
      dataDict[entry.planning_area.toUpperCase()] = value;
    });

    const values = Object.values(dataDict).filter(v => v !== null && v !== undefined && !isNaN(v));
    const min = values.length > 0 ? Math.min(...values) : 0;
    const max = values.length > 0 ? Math.max(...values) : 1;

    const colors = getColorScale(selectedMetric);

    const getColorFunc = (value: number) => {
      if (value === null || value === undefined || isNaN(value)) {
        return '#e5e7eb'; // Gray for missing data
      }

      // For diverging scale (growth/momentum)
      if (selectedMetric.includes('growth') || selectedMetric.includes('momentum') || selectedMetric.includes('change')) {
        const mid = 0;
        if (max <= mid) {
          // All negative values
          const normalized = (value - min) / (max - min || 1);
          const index = Math.floor(normalized * (colors.length / 2 - 1));
          return colors[Math.min(colors.length / 2 - 1 - index, colors.length / 2 - 1)];
        } else if (min >= mid) {
          // All positive values
          const normalized = (value - min) / (max - min || 1);
          const index = Math.floor(normalized * (colors.length / 2 - 1));
          return colors[Math.min(index + colors.length / 2, colors.length - 1)];
        } else {
          // Mixed values
          if (value >= mid) {
            const normalized = (value - mid) / (max - mid || 1);
            const index = Math.floor(normalized * (colors.length / 2 - 1));
            return colors[Math.min(index + colors.length / 2, colors.length - 1)];
          } else {
            const normalized = (value - min) / (mid - min || 1);
            const index = Math.floor(normalized * (colors.length / 2 - 1));
            return colors[Math.min(colors.length / 2 - 1 - index, colors.length / 2 - 1)];
          }
        }
      }

      // For sequential scale
      const normalized = (value - min) / (max - min || 1);
      const colorIndex = Math.floor(normalized * (colors.length - 1));
      return colors[Math.min(colorIndex, colors.length - 1)];
    };

    return { metricData: dataDict, minValue: min, maxValue: max, getColor: getColorFunc };
  }, [data, selectedMetric, filters]);

  // Style function for GeoJSON
  const style = useMemo(() => (feature: GeoJSONFeature) => {
    const rawName = feature.properties.pln_area_n || feature.properties.PLN_AREA_N;
    const name = rawName ? String(rawName).toUpperCase() : '';
    const value = metricData[name];
    const isHighlighted = highlightedArea === name;

    return {
      fillColor: value !== undefined ? getColor(value) : '#e5e7eb',
      weight: isHighlighted ? 3 : 1,
      opacity: 1,
      color: isHighlighted ? '#3b82f6' : 'white',
      dashArray: isHighlighted ? '' : '3',
      fillOpacity: isHighlighted ? 0.9 : 0.7,
    };
  }, [metricData, getColor, highlightedArea]);

  // Tooltip and hover handlers
  const onEachFeature = useMemo(() => (feature: GeoJSONFeature, layer: unknown) => {
    const rawName = feature.properties.pln_area_n || feature.properties.PLN_AREA_N;
    const name = rawName ? String(rawName).toUpperCase() : 'Unknown Area';
    const value = metricData[name];
    const entry = data.find(e => e.planning_area.toUpperCase() === name);

    // Build tooltip content
    let tooltipContent = `<div class="text-sm min-w-[200px]">`;
    tooltipContent += `<div class="font-bold border-b pb-1 mb-2 text-base">${name}</div>`;

    if (entry) {
      tooltipContent += `<div class="grid grid-cols-2 gap-x-4 gap-y-1">`;
      tooltipContent += `<span class="text-muted-foreground">Region:</span>`;
      tooltipContent += `<span class="font-medium text-right">${entry.region}</span>`;
      tooltipContent += `<span class="text-muted-foreground">${metricMeta.label}:</span>`;
      tooltipContent += `<span class="font-medium text-right">${value !== undefined ? value.toFixed(2) : 'N/A'} ${metricMeta.unit}</span>`;
      tooltipContent += `<span class="text-muted-foreground">Rank:</span>`;
      tooltipContent += `<span class="font-medium text-right">#${entry.rank_overall}</span>`;
      tooltipContent += `</div>`;
    } else {
      tooltipContent += `<div class="text-xs text-muted-foreground">No data available</div>`;
    }

    tooltipContent += `</div>`;

    // Bind tooltip
    const leafletLayer = layer as { bindTooltip: (content: string, options: unknown) => void };
    leafletLayer.bindTooltip(tooltipContent, {
      sticky: true,
      direction: 'top',
      className: 'custom-leaflet-tooltip',
    });

    // Add hover effects
    const typedLayer = layer as {
      on: (events: {
        mouseover: (e: LeafletLayerEvent) => void;
        mouseout: (e: LeafletLayerEvent) => void;
        click: (e: LeafletLayerEvent) => void;
      }) => void;
    };

    typedLayer.on({
      mouseover: (e: LeafletLayerEvent) => {
        const layer = e.target;
        layer.setStyle({
          weight: 3,
          color: '#3b82f6',
          dashArray: '',
          fillOpacity: 0.9,
        });
        layer.bringToFront();
        onAreaHover(name);
      },
      mouseout: (e: LeafletLayerEvent) => {
        if (highlightedArea !== name) {
          const layer = e.target;
          layer.setStyle(style(feature));
        }
        onAreaHover(null);
      },
      click: (e: LeafletLayerEvent) => {
        onAreaClick(name);
      },
    });
  }, [metricData, data, metricMeta, highlightedArea, style, onAreaHover, onAreaClick]);

  // Fallback for SSR or during loading
  if (!isClient || !MapContainer || !geoJsonData) {
    return (
      <div className="h-full flex items-center justify-center bg-muted/20 rounded-lg">
        Loading Map Data...
      </div>
    );
  }

  return (
    <div className="relative w-full h-full">
      <MapContainer
        center={[1.3521, 103.8198]}
        zoom={11}
        style={{ height: '100%', width: '100%' }}
        zoomControl={false}
        aria-label={`Map showing ${metricMeta.label} by planning area`}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
        />
        <GeoJSON data={geoJsonData} style={style} onEachFeature={onEachFeature} />
      </MapContainer>

      {/* Legend */}
      <div className="absolute bottom-4 right-4 bg-background/90 backdrop-blur p-3 rounded-lg border border-border text-xs z-[1000] shadow-lg">
        <div className="font-semibold mb-2">{metricMeta.label} ({metricMeta.unit})</div>
        <div className="flex flex-col gap-1">
          {selectedMetric.includes('growth') || selectedMetric.includes('momentum') || selectedMetric.includes('change') ? (
            <>
              <div className="flex items-center gap-2">
                <span className="w-4 h-4 rounded" style={{ backgroundColor: GROWTH_COLORS[GROWTH_COLORS.length - 1] }}></span>
                <span>High Positive</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-4 h-4 rounded" style={{ backgroundColor: GROWTH_COLORS[Math.floor(GROWTH_COLORS.length / 2)] }}></span>
                <span>Neutral</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-4 h-4 rounded" style={{ backgroundColor: GROWTH_COLORS[0] }}></span>
                <span>High Negative</span>
              </div>
            </>
          ) : (
            <>
              <div className="flex items-center gap-2">
                <span className="w-4 h-4 rounded" style={{ backgroundColor: getColorScale(selectedMetric)[getColorScale(selectedMetric).length - 1] }}></span>
                <span>High ({maxValue.toFixed(1)})</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-4 h-4 rounded" style={{ backgroundColor: getColorScale(selectedMetric)[Math.floor(getColorScale(selectedMetric).length / 2)] }}></span>
                <span>Medium</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-4 h-4 rounded" style={{ backgroundColor: getColorScale(selectedMetric)[0] }}></span>
                <span>Low ({minValue.toFixed(1)})</span>
              </div>
            </>
          )}
        </div>
        <div className="mt-2 pt-2 border-t text-muted-foreground">
          Click an area to highlight
        </div>
      </div>
    </div>
  );
}
