import React, { useEffect, useMemo, useState } from "react";
import { MapContainer, TileLayer, GeoJSON } from "react-leaflet";
import { decompressGzip } from "@/utils/gzip";
import {
  EMPTY_MAP_SELECTION,
  MAP_LAYER_IDS,
  MAP_SELECTION_KEYS,
  isSameMapSelection,
  parseMapSelection,
  serializeMapSelection,
  type MapSelection,
} from "@/utils/map-url-state";
import "leaflet/dist/leaflet.css";

// Archive layer controls and inspection (S9). Analytical fills are withheld:
// the observed transaction metric remains the map's single fill.
import ArchiveLayerControl from "./map/ArchiveLayerControl";
import ArchiveInspector from "./map/ArchiveInspector";
import {
  archiveLayerStatuses,
  inspectArchiveArea,
  observedLegend,
} from "@/utils/map-archive";

// Import analytics hooks and types
import {
  useSpatialAnalytics,
  useFeatureImpact,
  usePredictiveAnalytics,
} from "../../hooks/useAnalyticsData";
import type {
  GeoJSONFeatureCollection,
  GeoJSONFeature,
  LayerId,
  MapData,
  MetricType,
  PropertyTypeFilter,
  TemporalFilter,
} from "../../types/analytics";

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
  /** Deployment base path, resolved once by the Astro shell. */
  baseUrl: string;
}
const MAP_PRESETS = [
  {
    id: "expensive",
    label: "Show expensive areas",
    metric: "median_price" as MetricType,
    layers: [] as LayerId[],
  },
  {
    id: "fastest-growth",
    label: "Show fastest-growing areas",
    metric: "yoy_change_pct" as MetricType,
    layers: ["predictive.forecast"] as LayerId[],
  },
  {
    id: "affordability",
    label: "Show affordability pockets",
    metric: "affordability_ratio" as MetricType,
    layers: [] as LayerId[],
  },
  {
    id: "forward-signals",
    label: "Inspect archived forecast / policy / lease",
    metric: "yoy_change_pct" as MetricType,
    layers: [
      "predictive.forecast",
      "predictive.policy",
      "predictive.lease",
    ] as LayerId[],
  },
];

/** Read the incoming map selection once, before the first render commit. */
function readMapSelectionFromUrl(): MapSelection {
  if (typeof window === "undefined") {
    // SSR renders the defaults; the client initialises from the real URL.
    return EMPTY_MAP_SELECTION;
  }
  return parseMapSelection(window.location.search);
}

/** Expand the parsed layer ids into the toggle record `LayerControl` expects. */
function layersFromSelection(
  layerIds: readonly LayerId[],
): Record<LayerId, boolean> {
  const layers = {} as Record<LayerId, boolean>;
  MAP_LAYER_IDS.forEach((layerId) => {
    layers[layerId] = layerIds.includes(layerId);
  });
  return layers;
}

export default function PriceMap({
  geoJsonUrl,
  metricsUrl,
  baseUrl,
}: PriceMapProps) {
  const [geoJsonData, setGeoJsonData] =
    useState<GeoJSONFeatureCollection | null>(null);
  const [allMetrics, setAllMetrics] = useState<MapData | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loadAttempt, setLoadAttempt] = useState(0);

  // Existing filters — initialised from the incoming URL on the client so the
  // first commit already reflects a shared link. SSR keeps the defaults.
  const [initialSelection] = useState<MapSelection>(readMapSelectionFromUrl);
  const [temporalFilter, setTemporalFilter] = useState<TemporalFilter>(
    () => initialSelection.timeBasis ?? "whole",
  );
  const [propertyTypeFilter, setPropertyTypeFilter] =
    useState<PropertyTypeFilter>(() => initialSelection.propertyType ?? "all");
  const [metric, setMetric] = useState<MetricType>(
    () => initialSelection.metric ?? "median_price",
  );
  const [selectedArea, setSelectedArea] = useState<string | null>(
    () => initialSelection.area,
  );

  // NEW: Analytics layers state — also initialised from the URL
  const [activeLayers, setActiveLayers] = useState<Record<LayerId, boolean>>(
    () => layersFromSelection(initialSelection.layers),
  );

  // Load analytics data (lazy loading with caching). Each group is independent:
  // one source failure marks only its own layers, never the observed map.
  const spatialData = useSpatialAnalytics();
  const featureData = useFeatureImpact();
  const predictiveData = usePredictiveAnalytics();

  const archiveStatuses = useMemo(
    () =>
      archiveLayerStatuses({
        spatial: spatialData,
        feature: featureData,
        predictive: predictiveData,
      }),
    [spatialData, featureData, predictiveData],
  );

  // Sync the selection to the URL. State is initialised from the URL above, so
  // the first run is a no-op for a shared link and never overwrites it; the
  // guard also avoids redundant history writes. Params owned by other features
  // are preserved.
  useEffect(() => {
    if (typeof window === "undefined") return;

    const nextSelection: MapSelection = {
      metric,
      timeBasis: temporalFilter,
      propertyType: propertyTypeFilter,
      area: selectedArea,
      layers: MAP_LAYER_IDS.filter((layerId) => activeLayers[layerId]),
    };

    if (
      isSameMapSelection(
        parseMapSelection(window.location.search),
        nextSelection,
      )
    ) {
      return;
    }

    const serialized = serializeMapSelection(nextSelection);
    const url = new URL(window.location.href);
    MAP_SELECTION_KEYS.forEach((key) => {
      const value = serialized.get(key);
      if (value === null) {
        url.searchParams.delete(key);
      } else {
        url.searchParams.set(key, value);
      }
    });

    // Update URL without page reload
    window.history.replaceState({}, "", url.toString());
  }, [activeLayers, metric, propertyTypeFilter, selectedArea, temporalFilter]);

  // Browser back/forward: the URL is the source of truth, so re-apply it.
  useEffect(() => {
    if (typeof window === "undefined") return;

    const handlePopState = () => {
      const selection = parseMapSelection(window.location.search);

      setMetric(selection.metric ?? "median_price");
      setTemporalFilter(selection.timeBasis ?? "whole");
      setPropertyTypeFilter(selection.propertyType ?? "all");
      setSelectedArea(selection.area);
      setActiveLayers(layersFromSelection(selection.layers));
    };

    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function loadData() {
      setLoadError(null);
      try {
        const [geo, met] = await Promise.all([
          fetch(geoJsonUrl).then((res) => res.json()),
          fetch(metricsUrl).then(async (res) => {
            const buffer = await res.arrayBuffer();
            const text = await decompressGzip(buffer);

            // JSON spec doesn't allow NaN, but Python's json.dump might output it if not careful.
            // We sanitize it here just in case.
            const sanitized = text.replace(/:\s*NaN/g, ": null");
            return JSON.parse(sanitized);
          }),
        ]);
        if (cancelled) return;
        setGeoJsonData(geo);
        setAllMetrics(met);
      } catch (error) {
        if (cancelled) return;
        console.error("Failed to load map data:", error);
        setLoadError(
          "The observed map data could not be loaded. The archive layer list stays available, and no transaction value is invented.",
        );
      }
    }
    void loadData();
    return () => {
      cancelled = true;
    };
  }, [geoJsonUrl, metricsUrl, loadAttempt]);

  // Layer selection is inspection-only, so there is no fill-count limit and no
  // modal interruption. Every selected layer is listed in the inspector.
  const handleToggleLayer = (layerId: LayerId) => {
    setActiveLayers((prev) => ({
      ...prev,
      [layerId]: !prev[layerId],
    }));
  };

  const handleClearLayers = () => {
    setActiveLayers(layersFromSelection([]));
  };

  const inspectedLayers = MAP_LAYER_IDS.filter(
    (layerId) => activeLayers[layerId],
  );

  if (!geoJsonData || !allMetrics) {
    return (
      <div className="rounded-2xl border border-border bg-card p-6">
        {loadError ? (
          <div role="alert" className="text-sm">
            <p className="font-bold text-foreground">
              The observed map could not be loaded
            </p>
            <p className="mt-2 text-muted-foreground">{loadError}</p>
            <button
              type="button"
              onClick={() => {
                setGeoJsonData(null);
                setAllMetrics(null);
                setLoadAttempt((attempt) => attempt + 1);
              }}
              className="mt-3 rounded border border-input px-3 py-2 font-bold text-foreground hover:bg-muted"
            >
              Try again
            </button>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">
            Loading the observed map data and the archive layer list…
          </p>
        )}
      </div>
    );
  }

  // Determine data key based on temporal and property type filters
  const dataKey =
    propertyTypeFilter === "all"
      ? temporalFilter
      : (`${temporalFilter}_${propertyTypeFilter}` as keyof MapData);
  const currentMetrics = allMetrics[dataKey];
  const rankedAreas = Object.entries(currentMetrics)
    .filter(([, metricData]) => typeof metricData?.[metric] === "number")
    .sort((a, b) => (b[1]?.[metric] ?? 0) - (a[1]?.[metric] ?? 0));
  const selectedAreaMetrics = selectedArea
    ? currentMetrics[selectedArea]
    : null;
  const selectedAreaRank = selectedArea
    ? rankedAreas.findIndex(([areaName]) => areaName === selectedArea) + 1
    : 0;

  // Dynamic Color Scale
  const getValues = () => {
    return Object.values(currentMetrics).map((m) => m[metric] || 0);
  };

  const values = getValues();
  // Filter out zero values for better geometric color scale if needed
  // For growth (yoy_change_pct), values can be negative, so we adjust filter logic
  const validValues = values.filter(
    (v) => v !== 0 && v !== undefined && !isNaN(v),
  );
  const min = validValues.length > 0 ? Math.min(...validValues) : 0;
  const max = Math.max(...values);

  const hasObservedValue = (val: unknown): val is number =>
    typeof val === "number" &&
    Number.isFinite(val) &&
    // The exporter writes an all-zero block when a subset has no rows, and this
    // asset carries no separate empty marker, so zero is rendered as "no
    // observed value" rather than as a lowest-bin observation. A genuine zero
    // count cannot be distinguished from an empty block here.
    (val !== 0 || metric === "yoy_change_pct");

  const getColor = (val: number | undefined) => {
    if (!hasObservedValue(val)) return "#cccccc";

    // Simple normalization for now
    const normalized = (val - min) / (max - min);

    // Custom buckets based on distribution
    // High-end areas shouldn't drown out the differences in the mid-range
    return val > max * 0.9
      ? "#800026"
      : val > max * 0.7
        ? "#BD0026"
        : val > max * 0.5
          ? "#E31A1C"
          : val > max * 0.35
            ? "#FC4E2A"
            : val > max * 0.2
              ? "#FD8D3C"
              : val > max * 0.1
                ? "#FEB24C"
                : "#FFEDA0";
  };

  // Leaflet's style callback receives its own (wider) feature type or
  // `undefined`, so accept `unknown` and narrow locally. S9 touched this file;
  // this removes one pre-existing baseline error without changing behaviour.
  const style = (feature?: unknown) => {
    // GeoJSON uses 'pln_area_n' (lowercase); normalize to uppercase for lookup.
    const properties = (feature as GeoJSONFeature | undefined)?.properties;
    const rawName = properties?.pln_area_n ?? properties?.PLN_AREA_N;
    const name = rawName ? String(rawName).toUpperCase() : "";

    const data = currentMetrics[name];
    const value = data ? data[metric] : undefined;
    const isSelected = selectedArea === name;

    return {
      fillColor: getColor(value),
      weight: isSelected ? 3 : 1,
      opacity: 1,
      color: isSelected ? "#2563eb" : "white",
      dashArray: isSelected ? "" : "3",
      fillOpacity: isSelected ? 0.9 : 0.7,
    };
  };

  const onEachFeature = (feature: GeoJSONFeature, layer: unknown) => {
    const rawName =
      feature.properties.pln_area_n || feature.properties.PLN_AREA_N;
    const name = rawName ? String(rawName).toUpperCase() : "Unknown Area";
    const data = currentMetrics[name];

    // Format label for metric selector
    const metricLabels: Record<string, string> = {
      median_price: "Price",
      median_psf: "PSF",
      volume: "Volume",
      rental_yield_median: "Yield",
      yoy_change_pct: "Growth",
      affordability_ratio: "Affordability",
    };
    const metricLabel = metricLabels[metric] || metric;

    if (data) {
      const growthColor =
        (data.yoy_change_pct || 0) >= 0 ? "text-green-600" : "text-red-600";
      const momentumSignal = data.momentum_signal || "N/A";

      const content = `
        <div class="text-sm min-w-[200px]">
          <div class="font-bold border-b pb-1 mb-2 text-base flex justify-between">
            <span>${name}</span>
            <span class="text-xs font-normal text-muted-foreground self-center">${data.affordability_class || ""}</span>
          </div>
          <div class="grid grid-cols-2 gap-x-4 gap-y-1">
            <span class="text-muted-foreground">Price:</span>
            <span class="font-medium text-right">${formatTooltipValue(data.median_price, "sgd")}</span>

            <span class="text-muted-foreground">PSF:</span>
            <span class="font-medium text-right">${formatTooltipValue(data.median_psf, "sgd")}</span>

            <span class="text-muted-foreground">Volume:</span>
            <span class="font-medium text-right">${formatTooltipValue(data.volume, "count")}</span>

            <span class="text-muted-foreground">Rental Yield:</span>
            <span class="font-medium text-right">${formatTooltipValue(data.rental_yield_median, "pct")}</span>

            <span class="text-muted-foreground">YoY Growth:</span>
            <span class="font-medium text-right ${growthColor}">${formatTooltipValue(data.yoy_change_pct, "pct")}</span>

            <span class="text-muted-foreground">Affordability:</span>
            <span class="font-medium text-right">${formatTooltipValue(data.affordability_ratio, "ratio")}</span>
          </div>

          ${
            data.momentum_signal
              ? `
          <div class="mt-2 text-xs bg-muted/50 p-1 rounded flex justify-between items-center">
             <span>Momentum:</span>
             <span class="font-semibold ${momentumSignal === "Bullish" ? "text-green-600" : momentumSignal === "Bearish" ? "text-red-600" : "text-yellow-600"}">
               ${momentumSignal}
             </span>
          </div>
          `
              : ""
          }

          <div class="mt-2 pt-2 border-t text-xs text-muted-foreground text-center">
             ${metricLabel} Rank: ${getColor(data[metric]) === "#800026" ? "Top Tier" : "Standard"}
          </div>
        </div>
      `;

      // Type assertion for Leaflet layer
      const leafletLayer = layer as {
        bindTooltip: (content: string, options: unknown) => void;
      };
      leafletLayer.bindTooltip(content, {
        sticky: true,
        direction: "top",
        className: "custom-leaflet-tooltip",
      });
    } else {
      const leafletLayer = layer as {
        bindTooltip: (content: string, options: unknown) => void;
      };
      leafletLayer.bindTooltip(
        `<div class="font-bold">${name}</div><div class="text-xs text-muted-foreground">No transaction data available</div>`,
        { sticky: true },
      );
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
          color: "#666",
          dashArray: "",
          fillOpacity: 0.9,
        });
        layer.bringToFront();
      },
      mouseout: (e: LeafletLayerEvent) => {
        const layer = e.target;
        // Reset style
        layer.setStyle({
          weight: 1,
          color: "white",
          dashArray: "3",
          fillOpacity: 0.7,
        });
      },
      click: () => {
        if (name) {
          setSelectedArea(name);
        }
      },
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

  const inspectedPropertyType: "hdb" | "condo" =
    propertyTypeFilter === "condo" ? "condo" : "hdb";

  // Computed directly rather than with `useMemo`: it sits after the map's
  // loading early-return, and a conditional hook would break the render order.
  const archiveInspection = inspectArchiveArea({
    spatial: spatialData.data,
    feature: featureData.data,
    predictive: predictiveData.data,
    selectedArea,
    activeLayers: inspectedLayers,
    propertyType: inspectedPropertyType,
    mapFeatureCount: geoJsonData.features?.length ?? 0,
  });

  const periodLabel: Record<TemporalFilter, string> = {
    whole: "All history",
    pre_covid: "Through 2021",
    recent: "2022 onward",
    year_2025: "2025 complete year",
  };
  const propertyLabel: Record<PropertyTypeFilter, string> = {
    all: "All property types",
    hdb: "HDB",
    ec: "EC",
    condo: "Condominium",
  };
  const observedLegendValues = observedLegend(
    metric,
    periodLabel[temporalFilter],
    propertyLabel[propertyTypeFilter],
  );

  const selectedAreaSummary =
    selectedArea && selectedAreaMetrics
      ? {
          metricValue: selectedAreaMetrics[metric],
          momentumSignal: selectedAreaMetrics.momentum_signal || "Unspecified",
          affordabilityClass:
            selectedAreaMetrics.affordability_class || "Unspecified",
          growth: selectedAreaMetrics.yoy_change_pct,
          volume: selectedAreaMetrics.volume,
        }
      : null;

  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-border bg-card p-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h2 className="text-lg font-semibold text-foreground">
              Question-led presets
            </h2>
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
          <span className="text-sm font-medium text-muted-foreground">
            Metric:
          </span>
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
            <span className="text-sm font-medium text-muted-foreground">
              Period:
            </span>
            <div className="flex space-x-1 bg-muted p-1 rounded-md">
              {(["whole", "pre_covid", "recent", "year_2025"] as const).map(
                (key) => (
                  <button
                    key={key}
                    onClick={() => setTemporalFilter(key)}
                    className={`px-3 py-1.5 text-xs font-medium rounded-sm transition-all whitespace-nowrap ${
                      temporalFilter === key
                        ? "bg-background text-foreground shadow-sm"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    {key === "whole"
                      ? "All Time"
                      : key === "pre_covid"
                        ? "Pre-COVID"
                        : key === "recent"
                          ? "Recent"
                          : key === "year_2025"
                            ? "2025"
                            : key}
                  </button>
                ),
              )}
            </div>
          </div>

          {/* Property Type Filter */}
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-muted-foreground">
              Type:
            </span>
            <div className="flex space-x-1 bg-muted p-1 rounded-md">
              {(["all", "hdb", "ec", "condo"] as const).map((key) => (
                <button
                  key={key}
                  onClick={() => setPropertyTypeFilter(key)}
                  className={`px-3 py-1.5 text-xs font-medium rounded-sm transition-all whitespace-nowrap ${
                    propertyTypeFilter === key
                      ? "bg-background text-foreground shadow-sm"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {key === "all" ? "All" : key.toUpperCase()}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      <ArchiveLayerControl
        activeLayers={activeLayers}
        onToggleLayer={handleToggleLayer}
        onClearLayers={handleClearLayers}
        statuses={archiveStatuses}
      />

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
        <div className="h-[600px] border border-border rounded-lg overflow-hidden relative z-0 bg-slate-50 dark:bg-slate-900">
          <MapContainer
            center={[1.3521, 103.8198]}
            zoom={11}
            style={{ height: "100%", width: "100%" }}
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

          <div className="absolute bottom-4 right-4 max-w-[260px] bg-background/95 backdrop-blur p-3 rounded-lg border border-border text-xs z-[1000] shadow-lg">
            <div className="font-semibold text-foreground">
              {observedLegendValues.quantity}
            </div>
            <p className="mt-1 text-muted-foreground">
              Unit: {observedLegendValues.unit}
            </p>
            <p className="text-muted-foreground">
              Period: {observedLegendValues.period}
            </p>
            <p className="text-muted-foreground">
              Evidence: {observedLegendValues.status} ·{" "}
              <code className="font-mono">map_metrics</code>
            </p>
            <div className="mt-2 flex flex-col gap-1">
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
              <div className="flex items-center gap-2">
                <span className="w-4 h-4 rounded bg-[#cccccc] border border-border"></span>
                <span>No observed value</span>
              </div>
            </div>
          </div>
        </div>

        <aside className="rounded-2xl border border-border bg-card p-4 shadow-sm">
          <h2 className="text-lg font-semibold text-foreground">
            Area Inspector
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Click a planning area to lock the highlight and hand it off to the
            ranking or segment pages.
          </p>

          {selectedAreaSummary ? (
            <div className="mt-4 space-y-4">
              <div>
                <div className="text-xs uppercase tracking-wide text-muted-foreground">
                  Selected Area
                </div>
                <div className="mt-1 text-base font-semibold text-foreground">
                  {selectedArea}
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <InspectorItem
                  label="Current Metric"
                  value={formatInspectorValue(
                    selectedAreaSummary.metricValue,
                    metric,
                  )}
                />
                <InspectorItem
                  label="Rank"
                  value={selectedAreaRank > 0 ? `#${selectedAreaRank}` : "N/A"}
                />
                <InspectorItem
                  label="YoY Growth"
                  value={`${selectedAreaSummary.growth?.toFixed(1) ?? "—"}%`}
                />
                <InspectorItem
                  label="Volume"
                  value={selectedAreaSummary.volume?.toLocaleString() ?? "—"}
                />
                <InspectorItem
                  label="Momentum"
                  value={selectedAreaSummary.momentumSignal}
                />
                <InspectorItem
                  label="Affordability"
                  value={selectedAreaSummary.affordabilityClass}
                />
              </div>
              <div className="grid gap-2">
                <a
                  href={`${baseUrl}explore?area=${encodeURIComponent(selectedArea ?? "")}&metric=${encodeURIComponent(metric)}`}
                  className="rounded-xl border border-border px-3 py-2 text-sm font-medium text-foreground transition-colors hover:bg-muted/40"
                >
                  Open observed comparison
                </a>
                <a
                  href={`${baseUrl}research/segments?area=${encodeURIComponent(selectedArea ?? "")}`}
                  className="rounded-xl border border-border px-3 py-2 text-sm font-medium text-foreground transition-colors hover:bg-muted/40"
                >
                  Open research segments
                </a>
              </div>
            </div>
          ) : (
            <div className="mt-4 rounded-2xl bg-muted/20 p-4 text-sm text-muted-foreground">
              No area selected yet. Start with a preset, then click an area on
              the map.
            </div>
          )}
        </aside>
      </div>

      <ArchiveInspector
        inspection={archiveInspection}
        activeLayerCount={inspectedLayers.length}
        baseUrl={baseUrl}
      />
    </div>
  );
}

function formatTooltipValue(
  value: number | null | undefined,
  kind: "sgd" | "count" | "pct" | "ratio",
): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return "N/A";
  if (kind === "sgd") return `S$${value.toLocaleString("en-SG")}`;
  if (kind === "count") return value.toLocaleString("en-SG");
  if (kind === "ratio") return `${value.toFixed(2)}×`;
  return `${value.toFixed(1)}%`;
}

function formatInspectorValue(
  value: number | undefined,
  metric: MetricType,
): string {
  if (value === undefined || value === null || Number.isNaN(value)) {
    return "—";
  }

  if (metric === "median_price" || metric === "median_psf") {
    return `$${value.toLocaleString()}`;
  }

  if (metric === "volume") {
    return value.toLocaleString();
  }

  if (metric === "affordability_ratio") {
    return `${value.toFixed(2)}x`;
  }

  return `${value.toFixed(1)}%`;
}

function InspectorItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-muted/30 p-3">
      <div className="text-xs uppercase tracking-wide text-muted-foreground">
        {label}
      </div>
      <div className="mt-1 font-medium text-foreground">{value}</div>
    </div>
  );
}
