import { useCallback, useEffect, useMemo, useState } from 'react';
import type { SegmentAreaRow, SegmentInvestigationMetric } from '@/types/segments';

interface SegmentAreaMapProps {
  rows: SegmentAreaRow[];
  selectedMetric: SegmentInvestigationMetric;
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
  };
}

async function decompressGzip(buffer: ArrayBuffer): Promise<string> {
  try {
    const text = new TextDecoder().decode(buffer);
    if (text.trim().startsWith('{') || text.trim().startsWith('[')) {
      return text;
    }
  } catch {
    // Ignore and fall back to browser decompression.
  }

  if ('DecompressionStream' in window) {
    const stream = new Response(buffer).body;
    if (stream) {
      const decompressedStream = stream.pipeThrough(new DecompressionStream('gzip'));
      const reader = decompressedStream.getReader();
      const chunks: Uint8Array[] = [];

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        chunks.push(value);
      }

      const total = chunks.reduce((sum, chunk) => sum + chunk.length, 0);
      const decompressed = new Uint8Array(total);
      let offset = 0;

      for (const chunk of chunks) {
        decompressed.set(chunk, offset);
        offset += chunk.length;
      }

      return new TextDecoder().decode(decompressed);
    }
  }

  return new TextDecoder().decode(buffer);
}

const COLORS = ['#e0f2fe', '#93c5fd', '#60a5fa', '#2563eb', '#1d4ed8'];

function metricLabel(metric: SegmentInvestigationMetric): string {
  switch (metric) {
    case 'avgPricePsf':
      return 'Average Price PSF';
    case 'avgYield':
      return 'Average Yield';
    case 'forecast6m':
      return '6M Forecast';
    case 'mrtPremium':
      return 'MRT Premium';
    case 'persistenceProbability':
      return 'Persistence Probability';
    default:
      return metric;
  }
}

function formatMetricValue(value: number, metric: SegmentInvestigationMetric): string {
  switch (metric) {
    case 'avgPricePsf':
    case 'mrtPremium':
      return `$${value.toFixed(0)}`;
    case 'avgYield':
    case 'forecast6m':
      return `${value.toFixed(1)}%`;
    case 'persistenceProbability':
      return `${(value * 100).toFixed(1)}%`;
    default:
      return value.toFixed(1);
  }
}

export default function SegmentAreaMap({
  rows,
  selectedMetric,
  highlightedArea,
  onAreaHover,
  onAreaClick,
}: SegmentAreaMapProps) {
  const [isClient, setIsClient] = useState(false);
  const [MapContainer, setMapContainer] = useState<any>(null);
  const [TileLayer, setTileLayer] = useState<any>(null);
  const [GeoJSON, setGeoJSON] = useState<any>(null);
  const [geoJsonData, setGeoJsonData] = useState<any>(null);

  useEffect(() => {
    setIsClient(true);

    import('react-leaflet').then((modules) => {
      setMapContainer(() => modules.MapContainer);
      setTileLayer(() => modules.TileLayer);
      setGeoJSON(() => modules.GeoJSON);
    });

    import('leaflet/dist/leaflet.css');

    fetch(`${import.meta.env.BASE_URL}data/planning_areas.geojson.gz`)
      .then((response) => response.arrayBuffer())
      .then((buffer) => decompressGzip(buffer))
      .then((text) => JSON.parse(text))
      .then((parsed) => setGeoJsonData(parsed))
      .catch((error) => console.error('Failed to load planning area map:', error));
  }, []);

  const rowsByArea = useMemo(() => {
    const lookup: Record<string, SegmentAreaRow> = {};
    rows.forEach((row) => {
      lookup[row.areaKey] = row;
    });
    return lookup;
  }, [rows]);

  const values = useMemo(
    () => rows.map((row) => row[selectedMetric]).filter((value) => !Number.isNaN(value)),
    [rows, selectedMetric]
  );

  const minValue = values.length > 0 ? Math.min(...values) : 0;
  const maxValue = values.length > 0 ? Math.max(...values) : 1;

  const getColor = useCallback(
    (value: number) => {
      const normalized = (value - minValue) / (maxValue - minValue || 1);
      const index = Math.min(COLORS.length - 1, Math.floor(normalized * (COLORS.length - 1)));
      return COLORS[index];
    },
    [maxValue, minValue]
  );

  const style = useMemo(
    () => (feature: GeoJSONFeature) => {
      const rawName = feature.properties.pln_area_n || feature.properties.PLN_AREA_N;
      const areaKey = rawName ? String(rawName).toUpperCase() : '';
      const row = rowsByArea[areaKey];
      const isHighlighted = highlightedArea === areaKey;

      return {
        fillColor: row ? getColor(row[selectedMetric]) : '#e5e7eb',
        weight: isHighlighted ? 3 : 1,
        opacity: 1,
        color: isHighlighted ? '#1d4ed8' : '#ffffff',
        dashArray: isHighlighted ? '' : '3',
        fillOpacity: row ? (isHighlighted ? 0.95 : 0.8) : 0.2,
      };
    },
    [getColor, highlightedArea, rowsByArea, selectedMetric]
  );

  const onEachFeature = useMemo(
    () => (feature: GeoJSONFeature, layer: unknown) => {
      const rawName = feature.properties.pln_area_n || feature.properties.PLN_AREA_N;
      const areaKey = rawName ? String(rawName).toUpperCase() : '';
      const row = rowsByArea[areaKey];
      const leafletLayer = layer as {
        bindTooltip: (content: string, options: unknown) => void;
        on: (events: {
          mouseover: (event: LeafletLayerEvent) => void;
          mouseout: (event: LeafletLayerEvent) => void;
          click: () => void;
        }) => void;
      };

      const tooltip = row
        ? `
          <div class="text-sm min-w-[220px]">
            <div class="mb-2 border-b pb-1 text-base font-bold">${row.planningArea}</div>
            <div class="grid grid-cols-2 gap-x-3 gap-y-1">
              <span class="text-muted-foreground">Region</span>
              <span class="text-right font-medium">${row.region}</span>
              <span class="text-muted-foreground">${metricLabel(selectedMetric)}</span>
              <span class="text-right font-medium">${formatMetricValue(row[selectedMetric], selectedMetric)}</span>
              <span class="text-muted-foreground">Hotspot Confidence</span>
              <span class="text-right font-medium">${row.hotspotConfidence}</span>
            </div>
          </div>
        `
        : '<div class="text-sm">Outside the selected segment.</div>';

      leafletLayer.bindTooltip(tooltip, {
        sticky: true,
        direction: 'top',
        className: 'custom-leaflet-tooltip',
      });

      leafletLayer.on({
        mouseover: (event: LeafletLayerEvent) => {
          if (!row) {
            return;
          }
          event.target.setStyle({
            weight: 3,
            color: '#1d4ed8',
            dashArray: '',
            fillOpacity: 0.95,
          });
          event.target.bringToFront();
          onAreaHover(areaKey);
        },
        mouseout: (event: LeafletLayerEvent) => {
          if (!row) {
            return;
          }
          if (highlightedArea !== areaKey) {
            event.target.setStyle(style(feature));
          }
          onAreaHover(null);
        },
        click: () => {
          if (row) {
            onAreaClick(areaKey);
          }
        },
      });
    },
    [highlightedArea, onAreaClick, onAreaHover, rowsByArea, selectedMetric, style]
  );

  if (!isClient || !MapContainer || !geoJsonData) {
    return <div className="flex h-full items-center justify-center bg-muted/20">Loading Map Data...</div>;
  }

  return (
    <div className="relative h-full w-full">
      <MapContainer center={[1.3521, 103.8198]} zoom={11} style={{ width: '100%', height: '100%' }} zoomControl={false}>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
        />
        <GeoJSON data={geoJsonData} style={style} onEachFeature={onEachFeature} />
      </MapContainer>

      <div className="absolute bottom-4 right-4 z-[1000] rounded-2xl border border-border bg-background/95 p-3 text-xs shadow-lg backdrop-blur">
        <div className="mb-2 font-semibold">{metricLabel(selectedMetric)}</div>
        <div className="space-y-1">
          <LegendRow color={COLORS[COLORS.length - 1]} label={`High (${formatMetricValue(maxValue, selectedMetric)})`} />
          <LegendRow color={COLORS[Math.floor(COLORS.length / 2)]} label="Mid" />
          <LegendRow color={COLORS[0]} label={`Low (${formatMetricValue(minValue, selectedMetric)})`} />
          <LegendRow color="#e5e7eb" label="Outside segment" />
        </div>
      </div>
    </div>
  );
}

function LegendRow({ color, label }: { color: string; label: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className="h-4 w-4 rounded" style={{ backgroundColor: color }} />
      <span>{label}</span>
    </div>
  );
}
