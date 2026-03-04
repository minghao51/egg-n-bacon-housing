import React, { useEffect, useState } from 'react';
import { MapContainer, TileLayer, GeoJSON, Tooltip as LeafletTooltip } from 'react-leaflet';
import { decompressGzip } from '@/utils/gzip';
import 'leaflet/dist/leaflet.css';

// Import analytics components
import LayerControl from './map/LayerControl';
import SpatialAnalysisOverlay from './map/overlays/SpatialAnalysisOverlay';
import FeatureImpactOverlay from './map/overlays/FeatureImpactOverlay';
import PredictiveAnalyticsOverlay from './map/overlays/PredictiveAnalyticsOverlay';

// Import analytics hooks and types
import { useSpatialAnalytics, useFeatureImpact, usePredictiveAnalytics } from '../../hooks/useAnalyticsData';
import {
  LAYER_METADATA,
} from '../../types/analytics';
import type {
  GeoJSONFeatureCollection,
  GeoJSONFeature,
  LayerId,
  MapData,
  MetricType,
  PropertyTypeFilter,
  TemporalFilter,
} from '../../types/analytics';

// Type for Leaflet layer events
interface LeafletLayerEvent {
  target: {
    setStyle: (style: unknown) => void;
    bringToFront: () => void;
  };
}

interface PriceMapProps {
  geoJsonUrl: string;
  metricsUrl: string;
}

const MAX_ACTIVE_LAYERS = 5;
const MAP_PRESETS = [
  {
    id: 'expensive',
    label: 'Show expensive areas',
    metric: 'median_price' as MetricType,
    layers: [] as LayerId[],
  },
  {
    id: 'fastest-growth',
    label: 'Show fastest-growing areas',
    metric: 'yoy_change_pct' as MetricType,
    layers: ['predictive.forecast'] as LayerId[],
  },
  {
    id: 'affordability',
    label: 'Show affordability pockets',
    metric: 'affordability_ratio' as MetricType,
    layers: [] as LayerId[],
  },
  {
    id: 'forward-signals',
    label: 'Show forecast / policy / lease overlays',
    metric: 'yoy_change_pct' as MetricType,
    layers: ['predictive.forecast', 'predictive.policy', 'predictive.lease'] as LayerId[],
  },
];

export default function PriceMap({ geoJsonUrl, metricsUrl }: PriceMapProps) {
  const [geoJsonData, setGeoJsonData] = useState<GeoJSONFeatureCollection | null>(null);
  const [allMetrics, setAllMetrics] = useState<MapData | null>(null);

  // Existing filters
  const [temporalFilter, setTemporalFilter] = useState<TemporalFilter>('whole');
  const [propertyTypeFilter, setPropertyTypeFilter] = useState<PropertyTypeFilter>('all');
  const [metric, setMetric] = useState<MetricType>('median_price');
  const [selectedArea, setSelectedArea] = useState<string | null>(null);

  // NEW: Analytics layers state
  const [activeLayers, setActiveLayers] = useState<Record<LayerId, boolean>>(() => {
    // Initialize from URL params using native URL API
    if (typeof window !== 'undefined') {
      const urlParams = new URLSearchParams(window.location.search);
      const layersParam = urlParams.get('layers');
      const initialLayers: Record<LayerId, boolean> = {} as Record<LayerId, boolean>;

      // Initialize all layers to false
      Object.keys(LAYER_METADATA).forEach((layerId) => {
        initialLayers[layerId as LayerId] = false;
      });

      if (layersParam) {
        const requestedLayers = layersParam.split(',');
        requestedLayers.forEach((layerId) => {
          if (layerId in LAYER_METADATA) {
            initialLayers[layerId as LayerId] = true;
          }
        });
      }

      return initialLayers;
    }

    // Default state for SSR
    const initialLayers: Record<LayerId, boolean> = {} as Record<LayerId, boolean>;
    Object.keys(LAYER_METADATA).forEach((layerId) => {
      initialLayers[layerId as LayerId] = false;
    });
    return initialLayers;
  });

  // Load analytics data (lazy loading with caching)
  const spatialData = useSpatialAnalytics();
  const featureData = useFeatureImpact();
  const predictiveData = usePredictiveAnalytics();

  // Track which layers are currently loading
  const loadingLayers = new Set<LayerId>();
  if (spatialData.loading) {
    loadingLayers.add('spatial.hotspot');
    loadingLayers.add('spatial.lisa');
    loadingLayers.add('spatial.neighborhood');
  }
  if (featureData.loading) {
    loadingLayers.add('feature.mrt');
    loadingLayers.add('feature.school');
    loadingLayers.add('feature.amenity');
  }
  if (predictiveData.loading) {
    loadingLayers.add('predictive.policy');
    loadingLayers.add('predictive.lease');
    loadingLayers.add('predictive.forecast');
  }

  // Sync active layers to URL
  useEffect(() => {
    if (typeof window === 'undefined') return;
    const url = new URL(window.location.href);
    const activeLayerIds = Object.entries(activeLayers)
      .filter(([_, active]) => active)
      .map(([layerId, _]) => layerId);

    url.searchParams.set('metric', metric);
    url.searchParams.set('timeBasis', temporalFilter);
    url.searchParams.set('propertyType', propertyTypeFilter);

    if (activeLayerIds.length > 0) {
      url.searchParams.set('layers', activeLayerIds.join(','));
    } else {
      url.searchParams.delete('layers');
    }

    if (selectedArea) {
      url.searchParams.set('area', selectedArea);
    } else {
      url.searchParams.delete('area');
    }

    // Update URL without page reload
    window.history.replaceState({}, '', url.toString());
  }, [activeLayers, metric, propertyTypeFilter, selectedArea, temporalFilter]);

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const urlParams = new URLSearchParams(window.location.search);
    const metricParam = urlParams.get('metric');
    const timeBasisParam = urlParams.get('timeBasis');
    const propertyTypeParam = urlParams.get('propertyType');
    const areaParam = urlParams.get('area');

    if (metricParam && ['median_price', 'median_psf', 'volume', 'rental_yield_median', 'yoy_change_pct', 'affordability_ratio'].includes(metricParam)) {
      setMetric(metricParam as MetricType);
    }

    if (timeBasisParam && ['whole', 'pre_covid', 'recent', 'year_2025'].includes(timeBasisParam)) {
      setTemporalFilter(timeBasisParam as TemporalFilter);
    }

    if (propertyTypeParam && ['all', 'hdb', 'ec', 'condo'].includes(propertyTypeParam)) {
      setPropertyTypeFilter(propertyTypeParam as PropertyTypeFilter);
    }

    if (areaParam) {
      setSelectedArea(areaParam.toUpperCase());
    }
  }, []);

  useEffect(() => {
    async function loadData() {
      try {
        const [geo, met] = await Promise.all([
          fetch(geoJsonUrl).then(res => res.json()),
          fetch(metricsUrl).then(async res => {
            const buffer = await res.arrayBuffer();
            const text = await decompressGzip(buffer);

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

  // Handle layer toggle
  const handleToggleLayer = (layerId: LayerId) => {
    // Check if we're activating a new layer
    if (!activeLayers[layerId]) {
      // Count currently active layers
      const activeCount = Object.values(activeLayers).filter(Boolean).length;

      // Limit to MAX_ACTIVE_LAYERS
      if (activeCount >= MAX_ACTIVE_LAYERS) {
        alert(`Maximum ${MAX_ACTIVE_LAYERS} layers allowed. Please disable a layer first.`);
        return;
      }
    }

    // Toggle the layer
    setActiveLayers((prev) => ({
      ...prev,
      [layerId]: !prev[layerId],
    }));
  };

  if (!geoJsonData || !allMetrics) {
    return <div className="h-[500px] flex items-center justify-center bg-muted/20">Loading Map Data...</div>;
  }

  // Determine data key based on temporal and property type filters
  const dataKey = propertyTypeFilter === 'all'
    ? temporalFilter
    : `${temporalFilter}_${propertyTypeFilter}` as keyof MapData;
  const currentMetrics = allMetrics[dataKey];
  const rankedAreas = Object.entries(currentMetrics)
    .filter(([, metricData]) => typeof metricData?.[metric] === 'number')
    .sort((a, b) => (b[1]?.[metric] ?? 0) - (a[1]?.[metric] ?? 0));
  const selectedAreaMetrics = selectedArea ? currentMetrics[selectedArea] : null;
  const selectedAreaRank = selectedArea
    ? rankedAreas.findIndex(([areaName]) => areaName === selectedArea) + 1
    : 0;

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

  const style = (feature: GeoJSONFeature) => {
    // FIX: GeoJSON uses 'pln_area_n' (lowercase) but we were looking for 'PLN_AREA_N'
    // Also normalize to uppercase for the metrics lookup just in case
    const rawName = feature.properties.pln_area_n || feature.properties.PLN_AREA_N;
    const name = rawName ? String(rawName).toUpperCase() : '';

    const data = currentMetrics[name];
    const value = data ? data[metric] : 0;
    const isSelected = selectedArea === name;

    return {
      fillColor: getColor(value),
      weight: isSelected ? 3 : 1,
      opacity: 1,
      color: isSelected ? '#2563eb' : 'white',
      dashArray: isSelected ? '' : '3',
      fillOpacity: isSelected ? 0.9 : 0.7
    };
  };

  const onEachFeature = (feature: GeoJSONFeature, layer: unknown) => {
    const rawName = feature.properties.pln_area_n || feature.properties.PLN_AREA_N;
    const name = rawName ? String(rawName).toUpperCase() : 'Unknown Area';
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

      // Type assertion for Leaflet layer
      const leafletLayer = layer as { bindTooltip: (content: string, options: unknown) => void };
      leafletLayer.bindTooltip(content, {
        sticky: true,
        direction: 'top',
        className: 'custom-leaflet-tooltip'
      });
    } else {
      const leafletLayer = layer as { bindTooltip: (content: string, options: unknown) => void };
      leafletLayer.bindTooltip(`<div class="font-bold">${name}</div><div class="text-xs text-muted-foreground">No transaction data available</div>`, { sticky: true });
    }

    // Highlight on hover
    const typedLayer = layer as {
      on: (events: {
        mouseover: (e: LeafletLayerEvent) => void;
        mouseout: (e: LeafletLayerEvent) => void;
        click: () => void;
      }) => void;
    };
    typedLayer.on({
      mouseover: (e: LeafletLayerEvent) => {
        const layer = e.target;
        layer.setStyle({
          weight: 3,
          color: '#666',
          dashArray: '',
          fillOpacity: 0.9
        });
        layer.bringToFront();
      },
      mouseout: (e: LeafletLayerEvent) => {
        const layer = e.target;
        // Reset style
        layer.setStyle({
          weight: 1,
          color: 'white',
          dashArray: '3',
          fillOpacity: 0.7
        });
      },
      click: () => {
        if (name) {
          setSelectedArea(name);
        }
      }
    });
  };

  const applyPreset = (presetId: string) => {
    const preset = MAP_PRESETS.find((entry) => entry.id === presetId);
    if (!preset) {
      return;
    }

    setMetric(preset.metric);
    setActiveLayers((prev) => {
      const next = { ...prev };
      Object.keys(next).forEach((layerId) => {
        next[layerId as LayerId] = preset.layers.includes(layerId as LayerId);
      });
      return next;
    });
  };

  const selectedAreaSummary =
    selectedArea && selectedAreaMetrics
      ? {
          metricValue: selectedAreaMetrics[metric],
          momentumSignal: selectedAreaMetrics.momentum_signal || 'Unspecified',
          affordabilityClass: selectedAreaMetrics.affordability_class || 'Unspecified',
          growth: selectedAreaMetrics.yoy_change_pct,
          volume: selectedAreaMetrics.volume,
        }
      : null;

  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-border bg-card p-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h2 className="text-lg font-semibold text-foreground">Question-led presets</h2>
            <p className="text-sm text-muted-foreground">
              Start with a saved lens instead of stacking layers manually.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {MAP_PRESETS.map((preset) => (
              <button
                key={preset.id}
                type="button"
                onClick={() => applyPreset(preset.id)}
                className="rounded-full border border-border px-3 py-1.5 text-sm font-medium text-foreground transition-colors hover:bg-muted/40"
              >
                {preset.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="flex flex-wrap gap-4 justify-between items-center bg-card p-4 rounded-lg border border-border">
        {/* Metric Selector */}
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-muted-foreground">Metric:</span>
          <select
            value={metric}
            onChange={(e) => setMetric(e.target.value as MetricType)}
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

      {/* NEW: Analytics Layer Control */}
      <LayerControl
        activeLayers={activeLayers}
        onToggleLayer={handleToggleLayer}
        loadingLayers={loadingLayers}
      />

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
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

            <SpatialAnalysisOverlay
              active={activeLayers['spatial.hotspot']}
              data={spatialData.data}
              loading={spatialData.loading}
              planningAreasGeoJSON={geoJsonData}
              layerId="spatial.hotspot"
            />
            <SpatialAnalysisOverlay
              active={activeLayers['spatial.lisa']}
              data={spatialData.data}
              loading={spatialData.loading}
              planningAreasGeoJSON={geoJsonData}
              layerId="spatial.lisa"
            />
            <SpatialAnalysisOverlay
              active={activeLayers['spatial.neighborhood']}
              data={spatialData.data}
              loading={spatialData.loading}
              planningAreasGeoJSON={geoJsonData}
              layerId="spatial.neighborhood"
            />

            <FeatureImpactOverlay
              active={activeLayers['feature.mrt']}
              data={featureData.data}
              loading={featureData.loading}
              planningAreasGeoJSON={geoJsonData}
              layerId="feature.mrt"
              propertyType={propertyTypeFilter === 'all' ? 'hdb' : propertyTypeFilter}
            />
            <FeatureImpactOverlay
              active={activeLayers['feature.school']}
              data={featureData.data}
              loading={featureData.loading}
              planningAreasGeoJSON={geoJsonData}
              layerId="feature.school"
            />
            <FeatureImpactOverlay
              active={activeLayers['feature.amenity']}
              data={featureData.data}
              loading={featureData.loading}
              planningAreasGeoJSON={geoJsonData}
              layerId="feature.amenity"
            />

            <PredictiveAnalyticsOverlay
              active={activeLayers['predictive.forecast']}
              data={predictiveData.data}
              loading={predictiveData.loading}
              planningAreasGeoJSON={geoJsonData}
              layerId="predictive.forecast"
            />
            <PredictiveAnalyticsOverlay
              active={activeLayers['predictive.policy']}
              data={predictiveData.data}
              loading={predictiveData.loading}
              planningAreasGeoJSON={geoJsonData}
              layerId="predictive.policy"
            />
            <PredictiveAnalyticsOverlay
              active={activeLayers['predictive.lease']}
              data={predictiveData.data}
              loading={predictiveData.loading}
              planningAreasGeoJSON={geoJsonData}
              layerId="predictive.lease"
            />
          </MapContainer>

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

        <aside className="rounded-2xl border border-border bg-card p-4 shadow-sm">
          <h2 className="text-lg font-semibold text-foreground">Area Inspector</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Click a planning area to lock the highlight and hand it off to the ranking or segment pages.
          </p>

          {selectedAreaSummary ? (
            <div className="mt-4 space-y-4">
              <div>
                <div className="text-xs uppercase tracking-wide text-muted-foreground">Selected Area</div>
                <div className="mt-1 text-base font-semibold text-foreground">{selectedArea}</div>
              </div>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <InspectorItem
                  label="Current Metric"
                  value={formatInspectorValue(selectedAreaSummary.metricValue, metric)}
                />
                <InspectorItem
                  label="Rank"
                  value={selectedAreaRank > 0 ? `#${selectedAreaRank}` : 'N/A'}
                />
                <InspectorItem label="YoY Growth" value={`${selectedAreaSummary.growth?.toFixed(1) ?? '—'}%`} />
                <InspectorItem label="Volume" value={selectedAreaSummary.volume?.toLocaleString() ?? '—'} />
                <InspectorItem label="Momentum" value={selectedAreaSummary.momentumSignal} />
                <InspectorItem label="Affordability" value={selectedAreaSummary.affordabilityClass} />
              </div>
              <div className="grid gap-2">
                <a
                  href={`${import.meta.env.BASE_URL}dashboard/leaderboard?area=${encodeURIComponent(selectedArea ?? '')}&metric=${encodeURIComponent(metric)}`}
                  className="rounded-xl border border-border px-3 py-2 text-sm font-medium text-foreground transition-colors hover:bg-muted/40"
                >
                  Open in compare areas
                </a>
                <a
                  href={`${import.meta.env.BASE_URL}dashboard/segments?area=${encodeURIComponent(selectedArea ?? '')}`}
                  className="rounded-xl border border-border px-3 py-2 text-sm font-medium text-foreground transition-colors hover:bg-muted/40"
                >
                  Open in discover segments
                </a>
              </div>
            </div>
          ) : (
            <div className="mt-4 rounded-2xl bg-muted/20 p-4 text-sm text-muted-foreground">
              No area selected yet. Start with a preset, then click an area on the map.
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}

function formatInspectorValue(value: number | undefined, metric: MetricType): string {
  if (value === undefined || value === null || Number.isNaN(value)) {
    return '—';
  }

  if (metric === 'median_price' || metric === 'median_psf') {
    return `$${value.toLocaleString()}`;
  }

  if (metric === 'volume') {
    return value.toLocaleString();
  }

  if (metric === 'affordability_ratio') {
    return `${value.toFixed(2)}x`;
  }

  return `${value.toFixed(1)}%`;
}

function InspectorItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-muted/30 p-3">
      <div className="text-xs uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className="mt-1 font-medium text-foreground">{value}</div>
    </div>
  );
}
