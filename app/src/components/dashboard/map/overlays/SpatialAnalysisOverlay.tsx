/**
 * Spatial Analysis Overlay Component
 *
 * Renders spatial analytics layers on the Leaflet map:
 * - Hotspot/Coldspot (Getis-Ord Gi* z-scores)
 * - LISA Clusters (6 cluster types)
 * - Neighborhood Effects (local Moran's I)
 */

import React, { useRef } from "react";
import { LayerGroup, GeoJSON } from "react-leaflet";
import type {
  SpatialAnalyticsData,
  LayerId,
  GeoJSONFeature,
  GeoJSONFeatureCollection,
} from "../../../../types/analytics";
import {
  getHotspotColor,
  LISA_CLUSTER_COLORS,
} from "../../../../utils/colorScales";
import { planningAreaName } from "../../../../utils/geometry";
import { formatNumber, formatPercent } from "../../../../utils/format";

interface SpatialAnalysisOverlayProps {
  active: boolean;
  data: SpatialAnalyticsData | null;
  loading: boolean;
  planningAreasGeoJSON: GeoJSONFeatureCollection | null;
  layerId: LayerId;
}

/**
 * Get hotspot style function
 */
function getHotspotStyle(feature: GeoJSONFeature, data: SpatialAnalyticsData) {
  const areaName = planningAreaName(feature.properties);
  const areaData = areaName ? data?.planning_areas?.[areaName] : undefined;

  if (!areaData?.hotspot) {
    return {
      fillColor: "#cccccc",
      weight: 2,
      opacity: 1,
      color: "white",
      dashArray: "3",
      fillOpacity: 0.3,
    };
  }

  const zScore = areaData.hotspot.z_score;
  const color = getHotspotColor(zScore);

  return {
    fillColor: color,
    weight: 2,
    opacity: 1,
    color: "white",
    dashArray: "3",
    fillOpacity: 0.7,
  };
}

/**
 * Get LISA cluster style function
 */
function getLISAClusterStyle(
  feature: GeoJSONFeature,
  data: SpatialAnalyticsData,
) {
  const areaName = planningAreaName(feature.properties);
  const areaData = areaName ? data?.planning_areas?.[areaName] : undefined;

  if (!areaData?.lisa_cluster) {
    return {
      fillColor: "#cccccc",
      weight: 2,
      opacity: 1,
      color: "white",
      dashArray: "3",
      fillOpacity: 0.3,
    };
  }

  const clusterType = areaData.lisa_cluster.type;
  const color = LISA_CLUSTER_COLORS[clusterType] || "#cccccc";

  return {
    fillColor: color,
    weight: 2,
    opacity: 1,
    color: "white",
    dashArray: "3",
    fillOpacity: 0.7,
  };
}

/**
 * Get neighborhood effect style function
 */
function getNeighborhoodStyle(
  feature: GeoJSONFeature,
  data: SpatialAnalyticsData,
) {
  const areaName = planningAreaName(feature.properties);
  const areaData = areaName ? data?.planning_areas?.[areaName] : undefined;

  if (!areaData?.neighborhood_effect) {
    return {
      fillColor: "#cccccc",
      weight: 2,
      opacity: 1,
      color: "white",
      dashArray: "3",
      fillOpacity: 0.3,
    };
  }

  const multiplier = areaData.neighborhood_effect.neighborhood_multiplier;
  if (multiplier === null) {
    return {
      fillColor: "#cccccc",
      weight: 2,
      opacity: 1,
      color: "white",
      dashArray: "3",
      fillOpacity: 0.3,
    };
  }
  // Color gradient from blue (low multiplier) to red (high multiplier)
  const intensity = Math.min(1, Math.max(0, (multiplier - 0.8) / 0.4));
  const r = Math.round(intensity * 255);
  const b = Math.round((1 - intensity) * 255);
  const color = `rgb(${r}, 0, ${b})`;

  return {
    fillColor: color,
    weight: 2,
    opacity: 1,
    color: "white",
    dashArray: "3",
    fillOpacity: 0.7,
  };
}

/**
 * Create tooltip content for hotspot layer
 */
function createHotspotTooltip(
  feature: GeoJSONFeature,
  data: SpatialAnalyticsData,
): string {
  const areaName = planningAreaName(feature.properties);
  const areaData = areaName ? data?.planning_areas?.[areaName] : undefined;
  const areaLabel = areaName ?? "Unknown planning area";

  if (!areaData?.hotspot) {
    return `<b>${areaLabel}</b><br>No hotspot data available`;
  }

  const { z_score, p_value, confidence, classification } = areaData.hotspot;

  return `
    <div class="text-sm">
      <h3 class="font-bold">${areaLabel}</h3>
      <h4 class="font-semibold mt-2">Hotspot Analysis</h4>
      <p><b>Z-Score:</b> ${z_score?.toFixed(2) || "N/A"}</p>
      <p><b>P-Value:</b> ${p_value?.toFixed(4) || "N/A"}</p>
      <p><b>Confidence:</b> ${confidence}</p>
      <p><b>Classification:</b> ${classification}</p>
    </div>
  `;
}

/**
 * Create tooltip content for LISA cluster layer
 */
function createLISATooltip(
  feature: GeoJSONFeature,
  data: SpatialAnalyticsData,
): string {
  const areaName = planningAreaName(feature.properties);
  const areaData = areaName ? data?.planning_areas?.[areaName] : undefined;
  const areaLabel = areaName ?? "Unknown planning area";

  if (!areaData?.lisa_cluster) {
    return `<b>${areaLabel}</b><br>No LISA data available`;
  }

  const { type, yoy_appreciation, persistence_rate, transition_probabilities } =
    areaData.lisa_cluster;

  return `
    <div class="text-sm">
      <h3 class="font-bold">${areaLabel}</h3>
      <h4 class="font-semibold mt-2">LISA Cluster</h4>
      <p><b>Type:</b> ${type}</p>
      <p><b>YoY Appreciation:</b> ${formatNumber(yoy_appreciation) === "N/A" ? "N/A" : `${formatNumber(yoy_appreciation)}%`}</p>
      <p><b>Persistence Rate:</b> ${formatPercent(persistence_rate)}</p>
      <p><b>Transition to Hotspot:</b> ${formatPercent(transition_probabilities.to_hotspot)}</p>
    </div>
  `;
}

/**
 * Create tooltip content for neighborhood effect layer
 */
function createNeighborhoodTooltip(
  feature: GeoJSONFeature,
  data: SpatialAnalyticsData,
): string {
  const areaName = planningAreaName(feature.properties);
  const areaData = areaName ? data?.planning_areas?.[areaName] : undefined;
  const areaLabel = areaName ?? "Unknown planning area";

  if (!areaData?.neighborhood_effect) {
    return `<b>${areaLabel}</b><br>No neighborhood data available`;
  }

  const { moran_i_local, spatial_lag, neighborhood_multiplier } =
    areaData.neighborhood_effect;

  return `
    <div class="text-sm">
      <h3 class="font-bold">${areaLabel}</h3>
      <h4 class="font-semibold mt-2">Neighborhood Effect</h4>
      <p><b>Local Moran's I:</b> ${moran_i_local?.toFixed(3) || "N/A"}</p>
      <p><b>Spatial Lag:</b> $${spatial_lag?.toLocaleString() || "N/A"}</p>
      <p><b>Neighborhood Multiplier:</b> ${neighborhood_multiplier?.toFixed(2) || "N/A"}x</p>
    </div>
  `;
}

/**
 * Spatial Analysis Overlay Component
 */
export default function SpatialAnalysisOverlay({
  active,
  data,
  loading,
  planningAreasGeoJSON,
  layerId,
}: SpatialAnalysisOverlayProps) {
  const layerGroupRef = useRef<L.LayerGroup | null>(null);

  // Don't render if not active
  if (!active) {
    return null;
  }

  // Show loading state
  if (loading) {
    return (
      <div className="fixed bottom-4 right-4 bg-white p-2 rounded shadow text-sm">
        Loading spatial analysis...
      </div>
    );
  }

  // Determine which sub-layer to render
  const getStyleFunction = () => {
    switch (layerId) {
      case "spatial.hotspot":
        return (feature: GeoJSONFeature) => getHotspotStyle(feature, data!);
      case "spatial.lisa":
        return (feature: GeoJSONFeature) => getLISAClusterStyle(feature, data!);
      case "spatial.neighborhood":
        return (feature: GeoJSONFeature) =>
          getNeighborhoodStyle(feature, data!);
      default:
        return () => ({});
    }
  };

  const getTooltipFunction = () => {
    switch (layerId) {
      case "spatial.hotspot":
        return (feature: GeoJSONFeature) =>
          createHotspotTooltip(feature, data!);
      case "spatial.lisa":
        return (feature: GeoJSONFeature) => createLISATooltip(feature, data!);
      case "spatial.neighborhood":
        return (feature: GeoJSONFeature) =>
          createNeighborhoodTooltip(feature, data!);
      default:
        return () => "";
    }
  };

  return (
    <LayerGroup ref={layerGroupRef}>
      <GeoJSON
        data={planningAreasGeoJSON}
        style={getStyleFunction()}
        onEachFeature={(feature, layer) => {
          const tooltip = getTooltipFunction();
          layer.bindTooltip(tooltip(feature), {
            sticky: true,
            direction: "top",
          });
        }}
      />
    </LayerGroup>
  );
}
