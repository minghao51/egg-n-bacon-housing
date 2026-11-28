import React, { useCallback, useEffect, useMemo, useState } from "react";
import { MAP_TILES_ATTRIBUTION, MAP_TILES_URL } from "@/config/map-tiles";
import {
  DIVERGING_RAMP,
  MAP_OUTLINE,
  NO_DATA,
  SEQUENTIAL_RAMP,
  SURFACE,
} from "@/constants/palette";
import type {
  LeaderboardDisplayRow,
  LeaderboardMetric,
  MetricMeta,
} from "@/types/leaderboard";

async function decompressGzip(buffer: ArrayBuffer): Promise<string> {
  try {
    const text = new TextDecoder().decode(buffer);
    if (text.trim().startsWith("{") || text.trim().startsWith("[")) {
      return text;
    }
  } catch {
    // Fall through to browser decompression.
  }

  if ("DecompressionStream" in window) {
    const stream = new Response(buffer).body;
    if (stream) {
      const decompressedStream = stream.pipeThrough(
        new DecompressionStream("gzip"),
      );
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

interface LeaderboardMapProps {
  data: LeaderboardDisplayRow[];
  selectedMetric: LeaderboardMetric;
  metricMeta: MetricMeta;
  highlightedArea: string | null;
  onAreaHover: (area: string | null) => void;
  onAreaClick: (area: string) => void;
  /**
   * Whether areas may be coloured by the metric. A `limited-display` scope may
   * be read but not ranked, and a value choropleth is a rank in colour, so the
   * fill stays neutral and the values remain in the table.
   */
  colourable?: boolean;
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

/**
 * Signed metrics are the only ones that may use the diverging ramp: they carry
 * a direction as well as a magnitude. Everything else is a magnitude.
 */
function isSignedMetric(metric: LeaderboardMetric): boolean {
  return (
    metric.includes("growth") ||
    metric.includes("momentum") ||
    metric.includes("change")
  );
}

function getColorScale(metric: LeaderboardMetric): readonly string[] {
  if (metric.includes("price") || metric.includes("psf")) {
    return SEQUENTIAL_RAMP;
  }
  if (metric.includes("yield")) {
    return SEQUENTIAL_RAMP;
  }
  if (isSignedMetric(metric)) {
    return DIVERGING_RAMP;
  }
  return SEQUENTIAL_RAMP;
}

export default function LeaderboardMap({
  data,
  selectedMetric,
  metricMeta,
  highlightedArea,
  onAreaHover,
  onAreaClick,
  colourable = true,
}: LeaderboardMapProps) {
  const [isClient, setIsClient] = useState(false);
  const [MapContainer, setMapContainer] = useState<any>(null);
  const [TileLayer, setTileLayer] = useState<any>(null);
  const [GeoJSON, setGeoJSON] = useState<any>(null);
  const [geoJsonData, setGeoJsonData] = useState<any>(null);

  useEffect(() => {
    setIsClient(true);

    import("react-leaflet").then((modules) => {
      setMapContainer(() => modules.MapContainer);
      setTileLayer(() => modules.TileLayer);
      setGeoJSON(() => modules.GeoJSON);
    });

    import("leaflet/dist/leaflet.css");

    const loadGeoJson = async () => {
      try {
        const compressed = await fetch(
          `${import.meta.env.BASE_URL}data/planning_areas.geojson.gz`,
        );
        if (compressed.ok) {
          const buffer = await compressed.arrayBuffer();
          const text = await decompressGzip(buffer);
          setGeoJsonData(JSON.parse(text));
          return;
        }
      } catch {
        // Fall back to the plain JSON file in environments that do not serve the gzip asset cleanly.
      }

      try {
        const plain = await fetch(
          `${import.meta.env.BASE_URL}data/planning_areas.geojson`,
        );
        if (!plain.ok) {
          throw new Error(`HTTP ${plain.status}: ${plain.statusText}`);
        }
        setGeoJsonData(await plain.json());
      } catch (err) {
        console.error("Failed to load GeoJSON:", err);
      }
    };

    loadGeoJson();
  }, []);

  const handleAreaHover = useCallback(
    (area: string | null) => {
      onAreaHover(area);
    },
    [onAreaHover],
  );

  const handleAreaClick = useCallback(
    (area: string) => {
      onAreaClick(area);
    },
    [onAreaClick],
  );

  const { metricData, minValue, maxValue, getColor } = useMemo(() => {
    const dataDict: Record<string, number> = {};

    if (!colourable) {
      // No fill: the map still locates the areas and the table carries the
      // values, but nothing is coloured by a metric that may not be ranked.
      return {
        metricData: dataDict,
        minValue: 0,
        maxValue: 1,
        getColor: () => NO_DATA,
      };
    }

    data.forEach((row) => {
      if (row.rankMetricValue !== null) {
        dataDict[row.areaKey] = row.rankMetricValue;
      }
    });

    const values = Object.values(dataDict).filter(
      (value) => !Number.isNaN(value),
    );
    const min = values.length > 0 ? Math.min(...values) : 0;
    const max = values.length > 0 ? Math.max(...values) : 1;
    const colors = getColorScale(selectedMetric);

    const getColorForValue = (value: number) => {
      if (Number.isNaN(value)) {
        return NO_DATA;
      }

      if (isSignedMetric(selectedMetric)) {
        const midpoint = 0;
        if (value >= midpoint) {
          const positiveRange = max - midpoint || 1;
          const normalized = (value - midpoint) / positiveRange;
          const index = Math.min(
            colors.length - 1,
            Math.floor(
              (colors.length - 1) / 2 + normalized * ((colors.length - 1) / 2),
            ),
          );
          return colors[index];
        }

        const negativeRange = midpoint - min || 1;
        const normalized = (value - min) / negativeRange;
        const index = Math.max(
          0,
          Math.floor(normalized * ((colors.length - 1) / 2)),
        );
        return colors[index];
      }

      const normalized = (value - min) / (max - min || 1);
      const index = Math.min(
        colors.length - 1,
        Math.floor(normalized * (colors.length - 1)),
      );
      return colors[index];
    };

    return {
      metricData: dataDict,
      minValue: min,
      maxValue: max,
      getColor: getColorForValue,
    };
  }, [colourable, data, selectedMetric]);

  const style = useMemo(
    () => (feature: GeoJSONFeature) => {
      const rawName =
        feature.properties.pln_area_n || feature.properties.PLN_AREA_N;
      const name = rawName ? String(rawName).toUpperCase() : "";
      const value = metricData[name];
      const isHighlighted = highlightedArea === name;

      return {
        fillColor: value !== undefined ? getColor(value) : NO_DATA,
        weight: isHighlighted ? MAP_OUTLINE.selected.weight : 1,
        opacity: 1,
        color: isHighlighted ? MAP_OUTLINE.selected.color : SURFACE.card,
        dashArray: isHighlighted ? "" : "3",
        fillOpacity: isHighlighted ? 0.95 : 0.75,
      };
    },
    [getColor, highlightedArea, metricData],
  );

  const onEachFeature = useMemo(
    () => (feature: GeoJSONFeature, layer: unknown) => {
      const rawName =
        feature.properties.pln_area_n || feature.properties.PLN_AREA_N;
      const name = rawName ? String(rawName).toUpperCase() : "UNKNOWN";
      const row = data.find((entry) => entry.areaKey === name);

      const leafletLayer = layer as {
        bindTooltip: (content: string, options: unknown) => void;
        on: (events: {
          mouseover: (event: LeafletLayerEvent) => void;
          mouseout: (event: LeafletLayerEvent) => void;
          click: () => void;
        }) => void;
      };

      const metricValueLabel = !row
        ? "—"
        : row.rankMetricValue === null
          ? "—"
          : `${row.rankMetricValue.toFixed(2)} ${metricMeta.unit}`;
      const rankLabel =
        row && row.rank !== null ? `#${row.rank}` : "Not ranked";

      const tooltip = row
        ? `
          <div class="text-sm min-w-[220px]">
            <div class="mb-2 border-b pb-1 text-base font-bold">${row.planningArea}</div>
            <div class="grid grid-cols-2 gap-x-3 gap-y-1">
              <span class="text-muted-foreground">Region</span>
              <span class="text-right font-medium">${row.region ?? "Unmapped"}</span>
              <span class="text-muted-foreground">${metricMeta.label}</span>
              <span class="text-right font-medium">${metricValueLabel}</span>
              <span class="text-muted-foreground">Rank</span>
              <span class="text-right font-medium">${rankLabel}</span>
            </div>
          </div>
        `
        : `<div class="text-sm">No leaderboard data for this area.</div>`;

      leafletLayer.bindTooltip(tooltip, {
        sticky: true,
        direction: "top",
        className: "custom-leaflet-tooltip",
      });

      leafletLayer.on({
        mouseover: (event: LeafletLayerEvent) => {
          event.target.setStyle({
            weight: MAP_OUTLINE.selected.weight,
            color: MAP_OUTLINE.selected.color,
            dashArray: "",
            fillOpacity: 0.95,
          });
          event.target.bringToFront();
          handleAreaHover(name);
        },
        mouseout: (event: LeafletLayerEvent) => {
          if (highlightedArea !== name) {
            event.target.setStyle(style(feature));
          }
          handleAreaHover(null);
        },
        click: () => {
          handleAreaClick(name);
        },
      });
    },
    [
      data,
      handleAreaClick,
      handleAreaHover,
      highlightedArea,
      metricMeta.label,
      metricMeta.unit,
      style,
    ],
  );

  if (!isClient || !MapContainer || !geoJsonData) {
    return (
      <div className="flex h-full items-center justify-center bg-muted/20">
        Loading Map Data...
      </div>
    );
  }

  return (
    <div className="relative h-full w-full">
      <MapContainer
        center={[1.3521, 103.8198]}
        zoom={11}
        style={{ width: "100%", height: "100%" }}
        zoomControl={false}
        aria-label={`Map showing ${metricMeta.label} by planning area`}
      >
        <TileLayer attribution={MAP_TILES_ATTRIBUTION} url={MAP_TILES_URL} />
        <GeoJSON
          data={geoJsonData}
          style={style}
          onEachFeature={onEachFeature}
        />
      </MapContainer>

      <div className="absolute bottom-4 right-4 z-[1000] rounded-2xl border border-border bg-background/95 p-3 text-xs shadow-lg backdrop-blur">
        <div className="mb-2 font-semibold">
          {metricMeta.label} {metricMeta.unit ? `(${metricMeta.unit})` : ""}
        </div>
        {isSignedMetric(selectedMetric) ? (
          <div className="space-y-1">
            {/* A diverging ramp reuses the property hues for direction, so the
                legend has to say the direction in words. The labels stay
                direction-only: the metric name is already the legend heading,
                and a legacy metric id falls back to another metric's heading,
                which would make "higher median price" out of a growth ramp. */}
            <LegendRow
              color={DIVERGING_RAMP[DIVERGING_RAMP.length - 1]}
              label="Above zero"
            />
            <LegendRow
              color={DIVERGING_RAMP[Math.floor(DIVERGING_RAMP.length / 2)]}
              label="At zero"
            />
            <LegendRow color={DIVERGING_RAMP[0]} label="Below zero" />
          </div>
        ) : (
          <div className="space-y-1">
            <LegendRow
              color={
                getColorScale(selectedMetric)[
                  getColorScale(selectedMetric).length - 1
                ]
              }
              label={`High (${maxValue.toFixed(1)})`}
            />
            <LegendRow
              color={
                getColorScale(selectedMetric)[
                  Math.floor(getColorScale(selectedMetric).length / 2)
                ]
              }
              label="Mid"
            />
            <LegendRow
              color={getColorScale(selectedMetric)[0]}
              label={`Low (${minValue.toFixed(1)})`}
            />
          </div>
        )}
        <div className="mt-2 border-t border-border pt-2 text-muted-foreground">
          Click an area to lock the highlight.
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
