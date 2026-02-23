import React, { useState, useMemo, useEffect } from 'react';

// Do NOT import react-leaflet at module level
// Import it dynamically only in the browser

interface TrendsMapProps {
  metricData: Record<string, number | { value: number; label: string }>;
  metricLabel: string;
  colorScale?: 'sequential' | 'diverging';
  showLegend?: boolean;
  hoverTooltip?: (town: string, value: number, rank: string) => string;
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
  };
}

// Color scales
const SEQUENTIAL_COLORS = ['#FFEDA0', '#FEB24C', '#FD8D3C', '#FC4E2A', '#E31A1C', '#BD0026', '#800026'];

const DIVERGING_COLORS: Record<string, string> = {
  'HH': '#d73027', // Dark red - hotspots
  'LL': '#4575b4', // Dark blue - coldspots
  'HL': '#fee08b', // Light orange - high surrounded by low
  'LH': '#d1e5f0', // Light cyan - low surrounded by high
};

const CLUSTER_LABELS: Record<string, string> = {
  'HH': 'High-High Hotspot',
  'LL': 'Low-Low Coldspot',
  'HL': 'High-Low Pioneer',
  'LH': 'Low-High Transition',
};

export default function TrendsMap({
  metricData,
  metricLabel,
  colorScale = 'sequential',
  showLegend = true,
  hoverTooltip,
}: TrendsMapProps) {
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
    fetch('/data/planning_areas.geojson.gz')
      .then(res => {
        const contentEncoding = res.headers.get('content-encoding');
        if (contentEncoding === 'gzip') {
          return res.arrayBuffer().then(buffer => {
            // Use browser's DecompressionStream if available, otherwise assume ungzip
            return new Response(buffer).json();
          });
        }
        return res.json();
      })
      .then(data => setGeoJsonData(data))
      .catch(err => console.error('Failed to load GeoJSON:', err));
  }, []);

  // Extract values and compute color scale
  const { minValue, maxValue, getColor, getRank } = useMemo(() => {
    if (colorScale === 'diverging') {
      return {
        minValue: 0,
        maxValue: 1,
        getColor: (value: any) => {
          if (typeof value === 'string') {
            return DIVERGING_COLORS[value] || '#cccccc';
          }
          return '#cccccc';
        },
        getRank: () => '',
      };
    }

    const values = Object.values(metricData).map(v =>
      typeof v === 'object' ? v.value : v
    );
    const validValues = values.filter(v => v !== null && v !== undefined && !isNaN(v));
    const min = validValues.length > 0 ? Math.min(...validValues) : 0;
    const max = validValues.length > 0 ? Math.max(...validValues) : 1;

    const getColor = (value: any) => {
      const numValue = typeof value === 'object' ? value.value : value;
      if (numValue === null || numValue === undefined || isNaN(numValue)) {
        return '#cccccc';
      }

      const normalized = (numValue - min) / (max - min);
      const colorIndex = Math.floor(normalized * (SEQUENTIAL_COLORS.length - 1));
      return SEQUENTIAL_COLORS[Math.min(colorIndex, SEQUENTIAL_COLORS.length - 1)];
    };

    const getRank = (value: any) => {
      const numValue = typeof value === 'object' ? value.value : value;
      if (numValue === null || numValue === undefined || isNaN(numValue)) {
        return 'N/A';
      }

      const normalized = (numValue - min) / (max - min);
      if (normalized >= 0.9) return 'Top 10%';
      if (normalized >= 0.75) return 'Top 25%';
      if (normalized >= 0.5) return 'Above Average';
      if (normalized >= 0.25) return 'Below Average';
      return 'Bottom 25%';
    };

    return { minValue: min, maxValue: max, getColor, getRank };
  }, [metricData, colorScale]);

  // Style function for GeoJSON
  const style = (feature: GeoJSONFeature) => {
    const rawName = feature.properties.pln_area_n || feature.properties.PLN_AREA_N;
    const name = rawName ? String(rawName).toUpperCase() : '';
    const value = metricData[name];

    return {
      fillColor: value ? getColor(value) : '#cccccc',
      weight: 1,
      opacity: 1,
      color: 'white',
      dashArray: '3',
      fillOpacity: 0.7,
    };
  };

  // Tooltip and hover handlers
  const onEachFeature = (feature: GeoJSONFeature, layer: unknown) => {
    const rawName = feature.properties.pln_area_n || feature.properties.PLN_AREA_N;
    const name = rawName ? String(rawName).toUpperCase() : 'Unknown Area';
    const value = metricData[name];

    const numValue = value && typeof value === 'object' ? value.value : value;
    const rank = getRank(value);
    const label = value && typeof value === 'object' ? value.label : undefined;

    // Build tooltip content
    let tooltipContent = `<div class="text-sm min-w-[200px]">`;
    tooltipContent += `<div class="font-bold border-b pb-1 mb-2 text-base">${name}</div>`;

    if (value !== null && value !== undefined) {
      if (colorScale === 'diverging' && typeof value === 'string') {
        tooltipContent += `<div class="grid grid-cols-2 gap-x-4 gap-y-1">`;
        tooltipContent += `<span class="text-muted-foreground">Cluster Type:</span>`;
        tooltipContent += `<span class="font-medium text-right">${value} - ${CLUSTER_LABELS[value] || value}</span>`;
        tooltipContent += `</div>`;
      } else {
        tooltipContent += `<div class="grid grid-cols-2 gap-x-4 gap-y-1">`;
        tooltipContent += `<span class="text-muted-foreground">${metricLabel}:</span>`;
        tooltipContent += `<span class="font-medium text-right">${numValue !== null && numValue !== undefined ? numValue.toFixed(2) : 'N/A'}</span>`;
        if (label) {
          tooltipContent += `<span class="text-muted-foreground">${label}:</span>`;
          tooltipContent += `<span class="font-medium text-right">${label}</span>`;
        }
        tooltipContent += `</div>`;
        tooltipContent += `<div class="mt-2 pt-2 border-t text-xs text-muted-foreground">Rank: ${rank}</div>`;
      }
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
      on: (events: { mouseover: (e: LeafletLayerEvent) => void; mouseout: (e: LeafletLayerEvent) => void }) => void;
    };
    typedLayer.on({
      mouseover: (e: LeafletLayerEvent) => {
        const layer = e.target;
        layer.setStyle({
          weight: 3,
          color: '#666',
          dashArray: '',
          fillOpacity: 0.9,
        });
        layer.bringToFront();
      },
      mouseout: (e: LeafletLayerEvent) => {
        const layer = e.target;
        layer.setStyle({
          weight: 1,
          color: 'white',
          dashArray: '3',
          fillOpacity: 0.7,
        });
      },
    });
  };

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
        aria-label={`Map showing ${metricLabel} by town`}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
        />
        <GeoJSON data={geoJsonData} style={style} onEachFeature={onEachFeature} />
      </MapContainer>

      {showLegend && colorScale === 'sequential' && (
        <div className="absolute bottom-4 right-4 bg-background/90 backdrop-blur p-3 rounded-lg border border-border text-xs z-[1000] shadow-lg">
          <div className="font-semibold mb-2 capitalize">{metricLabel}</div>
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
      )}

      {showLegend && colorScale === 'diverging' && (
        <div className="absolute bottom-4 right-4 bg-background/90 backdrop-blur p-3 rounded-lg border border-border text-xs z-[1000] shadow-lg">
          <div className="font-semibold mb-2">Cluster Type</div>
          <div className="flex flex-col gap-1">
            <div className="flex items-center gap-2">
              <span className="w-4 h-4 rounded bg-[#d73027]"></span>
              <span>HH (Hotspot)</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-4 h-4 rounded bg-[#fee08b]"></span>
              <span>HL (Pioneer)</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-4 h-4 rounded bg-[#d1e5f0]"></span>
              <span>LH (Transition)</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-4 h-4 rounded bg-[#4575b4]"></span>
              <span>LL (Coldspot)</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
