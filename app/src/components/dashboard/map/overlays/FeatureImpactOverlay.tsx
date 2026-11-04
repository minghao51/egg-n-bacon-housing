/**
 * Feature Impact Overlay Component
 *
 * Renders feature impact layers on the Leaflet map:
 * - MRT Sensitivity (price impact per 100m from MRT)
 * - School Quality (quality-weighted scores)
 * - Amenity Scores (hawker, mall, park accessibility)
 */

import React, { useRef } from "react";
import { LayerGroup, GeoJSON } from "react-leaflet";
import type {
  FeatureImpactData,
  LayerId,
  GeoJSONFeature,
  GeoJSONFeatureCollection,
} from "../../../../types/analytics";
import { sequentialScale } from "../../../../utils/colorScales";
import { planningAreaName } from "../../../../utils/geometry";
import { formatNumber, formatPercent } from "../../../../utils/format";

interface FeatureImpactOverlayProps {
  active: boolean;
  data: FeatureImpactData | null;
  loading: boolean;
  planningAreasGeoJSON: GeoJSONFeatureCollection | null;
  layerId: LayerId;
  propertyType?: "hdb" | "condo" | "all";
}

/**
 * Get MRT sensitivity style function
 */
function getMRTStyle(
  feature: GeoJSONFeature,
  data: FeatureImpactData,
  propertyType: "hdb" | "condo" = "hdb",
) {
  const areaName = planningAreaName(feature.properties);
  const areaData = areaName ? data?.planning_areas?.[areaName] : undefined;

  if (!areaData?.mrt_impact) {
    return {
      fillColor: "#cccccc",
      weight: 2,
      opacity: 1,
      color: "white",
      dashArray: "3",
      fillOpacity: 0.3,
    };
  }

  // Use property-type-specific sensitivity; a missing value is not an impact.
  const sensitivity =
    propertyType === "condo"
      ? areaData.mrt_impact.condo_sensitivity_psf_per_100m
      : areaData.mrt_impact.hdb_sensitivity_psf_per_100m;

  // Color scale: -50 to 0 (more negative = higher impact)
  const color = sequentialScale(sensitivity, -50, 0, "#fee090", "#d73027");

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
 * Get school quality style function
 */
function getSchoolStyle(feature: GeoJSONFeature, data: FeatureImpactData) {
  const areaName = planningAreaName(feature.properties);
  const areaData = areaName ? data?.planning_areas?.[areaName] : undefined;

  if (!areaData?.school_quality) {
    return {
      fillColor: "#cccccc",
      weight: 2,
      opacity: 1,
      color: "white",
      dashArray: "3",
      fillOpacity: 0.3,
    };
  }

  const score = areaData.school_quality.weighted_score;
  // Color scale: 0 to 10
  const color = sequentialScale(score, 0, 10, "#ffffcc", "#006837");

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
 * Get amenity score style function
 */
function getAmenityStyle(feature: GeoJSONFeature, data: FeatureImpactData) {
  const areaName = planningAreaName(feature.properties);
  const areaData = areaName ? data?.planning_areas?.[areaName] : undefined;

  if (!areaData?.amenity_score) {
    return {
      fillColor: "#cccccc",
      weight: 2,
      opacity: 1,
      color: "white",
      dashArray: "3",
      fillOpacity: 0.3,
    };
  }

  const score = areaData.amenity_score.optimal_combination_score;
  // Color scale: 0 to 10
  const color = sequentialScale(score, 0, 10, "#ffffcc", "#006837");

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
 * Create tooltip content for MRT layer
 */
function createMRTTooltip(
  feature: GeoJSONFeature,
  data: FeatureImpactData,
  propertyType: "hdb" | "condo" = "hdb",
): string {
  const areaName = planningAreaName(feature.properties);
  const areaData = areaName ? data?.planning_areas?.[areaName] : undefined;
  const areaLabel = areaName ?? "Unknown planning area";

  if (!areaData?.mrt_impact) {
    return `<b>${areaLabel}</b><br>No MRT impact data available`;
  }

  const { mrt_impact } = areaData;
  const rawSensitivity =
    propertyType === "condo"
      ? mrt_impact.condo_sensitivity_psf_per_100m
      : mrt_impact.hdb_sensitivity_psf_per_100m;
  const sensitivityLabel =
    rawSensitivity === null || rawSensitivity === undefined
      ? "N/A"
      : `${rawSensitivity.toFixed(1)} PSF/100m`;

  return `
    <div class="text-sm">
      <h3 class="font-bold">${areaLabel}</h3>
      <h4 class="font-semibold mt-2">MRT Impact (${propertyType.toUpperCase()})</h4>
      <p><b>Sensitivity:</b> ${sensitivityLabel}</p>
      <p><b>CBD Distance:</b> ${formatNumber(mrt_impact.cbd_distance_km, 1) === "N/A" ? "N/A" : `${formatNumber(mrt_impact.cbd_distance_km, 1)} km`}</p>
      <p><b>CBD Explains Variance:</b> ${formatPercent(mrt_impact.cbd_explains_variance)}</p>
      <p><b>MRT vs CBD Ratio:</b> ${formatPercent(mrt_impact.mrt_vs_cbd_ratio)}</p>
    </div>
  `;
}

/**
 * Create tooltip content for school quality layer
 */
function createSchoolTooltip(
  feature: GeoJSONFeature,
  data: FeatureImpactData,
): string {
  const areaName = planningAreaName(feature.properties);
  const areaData = areaName ? data?.planning_areas?.[areaName] : undefined;
  const areaLabel = areaName ?? "Unknown planning area";

  if (!areaData?.school_quality) {
    return `<b>${areaLabel}</b><br>No school quality data available`;
  }

  const { school_quality } = areaData;

  return `
    <div class="text-sm">
      <h3 class="font-bold">${areaLabel}</h3>
      <h4 class="font-semibold mt-2">School Quality</h4>
      <p><b>Primary School Score:</b> ${school_quality.primary_school_score?.toFixed(1) || "N/A"}/10</p>
      <p><b>Secondary School Score:</b> ${school_quality.secondary_school_score?.toFixed(1) || "N/A"}/10</p>
      <p><b>Weighted Score:</b> ${school_quality.weighted_score?.toFixed(1) || "N/A"}/10</p>
      <p><b>Top Tier Schools:</b> ${school_quality.num_top_tier_schools ?? "N/A"}</p>
      <p><b>Predictive Power:</b> ${formatPercent(school_quality.predictive_power)}</p>
    </div>
  `;
}

/**
 * Create tooltip content for amenity score layer
 */
function createAmenityTooltip(
  feature: GeoJSONFeature,
  data: FeatureImpactData,
): string {
  const areaName = planningAreaName(feature.properties);
  const areaData = areaName ? data?.planning_areas?.[areaName] : undefined;
  const areaLabel = areaName ?? "Unknown planning area";

  if (!areaData?.amenity_score) {
    return `<b>${areaLabel}</b><br>No amenity score data available`;
  }

  const { amenity_score } = areaData;

  return `
    <div class="text-sm">
      <h3 class="font-bold">${areaLabel}</h3>
      <h4 class="font-semibold mt-2">Amenity Scores</h4>
      <p><b>Hawker Accessibility:</b> ${amenity_score.hawker_center_accessibility?.toFixed(1) || "N/A"}/10</p>
      <p><b>Mall Accessibility:</b> ${amenity_score.mall_accessibility?.toFixed(1) || "N/A"}/10</p>
      <p><b>Park Accessibility:</b> ${amenity_score.park_accessibility?.toFixed(1) || "N/A"}/10</p>
      <p><b>Optimal Combination:</b> ${amenity_score.optimal_combination_score?.toFixed(1) || "N/A"}/10</p>
      <p><b>Cluster Synergy:</b> ${amenity_score.amenity_cluster_synergy?.toFixed(1) || "N/A"} PSF</p>
    </div>
  `;
}

/**
 * Feature Impact Overlay Component
 */
export default function FeatureImpactOverlay({
  active,
  data,
  loading,
  planningAreasGeoJSON,
  layerId,
  propertyType = "hdb",
}: FeatureImpactOverlayProps) {
  const layerGroupRef = React.useRef<L.LayerGroup | null>(null);

  // Don't render if not active
  if (!active) {
    return null;
  }

  // Show loading state
  if (loading) {
    return (
      <div className="fixed bottom-4 right-4 bg-white p-2 rounded shadow text-sm">
        Loading feature impact data...
      </div>
    );
  }

  // Determine which sub-layer to render
  const getStyleFunction = () => {
    switch (layerId) {
      case "feature.mrt":
        return (feature: GeoJSONFeature) =>
          getMRTStyle(feature, data!, propertyType);
      case "feature.school":
        return (feature: GeoJSONFeature) => getSchoolStyle(feature, data!);
      case "feature.amenity":
        return (feature: GeoJSONFeature) => getAmenityStyle(feature, data!);
      default:
        return () => ({});
    }
  };

  const getTooltipFunction = () => {
    switch (layerId) {
      case "feature.mrt":
        return (feature: GeoJSONFeature) =>
          createMRTTooltip(feature, data!, propertyType);
      case "feature.school":
        return (feature: GeoJSONFeature) => createSchoolTooltip(feature, data!);
      case "feature.amenity":
        return (feature: GeoJSONFeature) =>
          createAmenityTooltip(feature, data!);
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
