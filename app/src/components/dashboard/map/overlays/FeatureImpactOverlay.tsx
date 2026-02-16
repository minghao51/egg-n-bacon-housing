/**
 * Feature Impact Overlay Component
 *
 * Renders feature impact layers on the Leaflet map:
 * - MRT Sensitivity (price impact per 100m from MRT)
 * - School Quality (quality-weighted scores)
 * - Amenity Scores (hawker, mall, park accessibility)
 */

import React, { useRef } from 'react';
import { LayerGroup, GeoJSON } from 'react-leaflet';
import { FeatureImpactData, LayerId } from '../../../../types/analytics';
import { sequentialScale } from '../../../../utils/colorScales';

interface FeatureImpactOverlayProps {
  active: boolean;
  data: FeatureImpactData | null;
  loading: boolean;
  planningAreasGeoJSON: any;
  layerId: LayerId;
  propertyType?: 'hdb' | 'condo' | 'all';
}

/**
 * Get MRT sensitivity style function
 */
function getMRTStyle(feature: any, data: FeatureImpactData, propertyType: 'hdb' | 'condo' = 'hdb') {
  const areaName = feature.properties?.pln_area_n;
  const areaData = data?.planning_areas?.[areaName];

  if (!areaData?.mrt_impact) {
    return {
      fillColor: '#cccccc',
      weight: 2,
      opacity: 1,
      color: 'white',
      dashArray: '3',
      fillOpacity: 0.3,
    };
  }

  // Use property-type-specific sensitivity
  const sensitivity = propertyType === 'condo'
    ? (areaData.mrt_impact.condo_sensitivity_psf_per_100m || -20)
    : (areaData.mrt_impact.hdb_sensitivity_psf_per_100m || -5);

  // Color scale: -50 to 0 (more negative = higher impact)
  const color = sequentialScale(sensitivity, -50, 0, '#fee090', '#d73027');

  return {
    fillColor: color,
    weight: 2,
    opacity: 1,
    color: 'white',
    dashArray: '3',
    fillOpacity: 0.7,
  };
}

/**
 * Get school quality style function
 */
function getSchoolStyle(feature: any, data: FeatureImpactData) {
  const areaName = feature.properties?.pln_area_n;
  const areaData = data?.planning_areas?.[areaName];

  if (!areaData?.school_quality) {
    return {
      fillColor: '#cccccc',
      weight: 2,
      opacity: 1,
      color: 'white',
      dashArray: '3',
      fillOpacity: 0.3,
    };
  }

  const score = areaData.school_quality.weighted_score || 5;
  // Color scale: 0 to 10
  const color = sequentialScale(score, 0, 10, '#ffffcc', '#006837');

  return {
    fillColor: color,
    weight: 2,
    opacity: 1,
    color: 'white',
    dashArray: '3',
    fillOpacity: 0.7,
  };
}

/**
 * Get amenity score style function
 */
function getAmenityStyle(feature: any, data: FeatureImpactData) {
  const areaName = feature.properties?.pln_area_n;
  const areaData = data?.planning_areas?.[areaName];

  if (!areaData?.amenity_score) {
    return {
      fillColor: '#cccccc',
      weight: 2,
      opacity: 1,
      color: 'white',
      dashArray: '3',
      fillOpacity: 0.3,
    };
  }

  const score = areaData.amenity_score.optimal_combination_score || 5;
  // Color scale: 0 to 10
  const color = sequentialScale(score, 0, 10, '#ffffcc', '#006837');

  return {
    fillColor: color,
    weight: 2,
    opacity: 1,
    color: 'white',
    dashArray: '3',
    fillOpacity: 0.7,
  };
}

/**
 * Create tooltip content for MRT layer
 */
function createMRTTooltip(feature: any, data: FeatureImpactData, propertyType: 'hdb' | 'condo' = 'hdb'): string {
  const areaName = feature.properties?.pln_area_n;
  const areaData = data?.planning_areas?.[areaName];

  if (!areaData?.mrt_impact) {
    return `<b>${areaName}</b><br>No MRT impact data available`;
  }

  const { mrt_impact } = areaData;
  const sensitivity = propertyType === 'condo'
    ? (mrt_impact.condo_sensitivity_psf_per_100m || -20)
    : (mrt_impact.hdb_sensitivity_psf_per_100m || -5);

  return `
    <div class="text-sm">
      <h3 class="font-bold">${areaName}</h3>
      <h4 class="font-semibold mt-2">MRT Impact (${propertyType.toUpperCase()})</h4>
      <p><b>Sensitivity:</b> ${sensitivity.toFixed(1)} PSF/100m</p>
      <p><b>CBD Distance:</b> ${mrt_impact.cbd_distance_km?.toFixed(1) || 'N/A'} km</p>
      <p><b>CBD Explains Variance:</b> ${(mrt_impact.cbd_explains_variance * 100).toFixed(1) || 'N/A'}%</p>
      <p><b>MRT vs CBD Ratio:</b> ${(mrt_impact.mrt_vs_cbd_ratio * 100).toFixed(1) || 'N/A'}%</p>
    </div>
  `;
}

/**
 * Create tooltip content for school quality layer
 */
function createSchoolTooltip(feature: any, data: FeatureImpactData): string {
  const areaName = feature.properties?.pln_area_n;
  const areaData = data?.planning_areas?.[areaName];

  if (!areaData?.school_quality) {
    return `<b>${areaName}</b><br>No school quality data available`;
  }

  const { school_quality } = areaData;

  return `
    <div class="text-sm">
      <h3 class="font-bold">${areaName}</h3>
      <h4 class="font-semibold mt-2">School Quality</h4>
      <p><b>Primary School Score:</b> ${school_quality.primary_school_score?.toFixed(1) || 'N/A'}/10</p>
      <p><b>Secondary School Score:</b> ${school_quality.secondary_school_score?.toFixed(1) || 'N/A'}/10</p>
      <p><b>Weighted Score:</b> ${school_quality.weighted_score?.toFixed(1) || 'N/A'}/10</p>
      <p><b>Top Tier Schools:</b> ${school_quality.num_top_tier_schools || 0}</p>
      <p><b>Predictive Power:</b> ${(school_quality.predictive_power * 100).toFixed(1) || 'N/A'}%</p>
    </div>
  `;
}

/**
 * Create tooltip content for amenity score layer
 */
function createAmenityTooltip(feature: any, data: FeatureImpactData): string {
  const areaName = feature.properties?.pln_area_n;
  const areaData = data?.planning_areas?.[areaName];

  if (!areaData?.amenity_score) {
    return `<b>${areaName}</b><br>No amenity score data available`;
  }

  const { amenity_score } = areaData;

  return `
    <div class="text-sm">
      <h3 class="font-bold">${areaName}</h3>
      <h4 class="font-semibold mt-2">Amenity Scores</h4>
      <p><b>Hawker Accessibility:</b> ${amenity_score.hawker_center_accessibility?.toFixed(1) || 'N/A'}/10</p>
      <p><b>Mall Accessibility:</b> ${amenity_score.mall_accessibility?.toFixed(1) || 'N/A'}/10</p>
      <p><b>Park Accessibility:</b> ${amenity_score.park_accessibility?.toFixed(1) || 'N/A'}/10</p>
      <p><b>Optimal Combination:</b> ${amenity_score.optimal_combination_score?.toFixed(1) || 'N/A'}/10</p>
      <p><b>Cluster Synergy:</b> ${amenity_score.amenity_cluster_synergy?.toFixed(1) || 'N/A'} PSF</p>
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
  propertyType = 'hdb',
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
      case 'feature.mrt':
        return (feature: any) => getMRTStyle(feature, data!, propertyType);
      case 'feature.school':
        return (feature: any) => getSchoolStyle(feature, data!);
      case 'feature.amenity':
        return (feature: any) => getAmenityStyle(feature, data!);
      default:
        return () => ({});
    }
  };

  const getTooltipFunction = () => {
    switch (layerId) {
      case 'feature.mrt':
        return (feature: any) => createMRTTooltip(feature, data!, propertyType);
      case 'feature.school':
        return (feature: any) => createSchoolTooltip(feature, data!);
      case 'feature.amenity':
        return (feature: any) => createAmenityTooltip(feature, data!);
      default:
        return () => '';
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
            direction: 'top',
          });
        }}
      />
    </LayerGroup>
  );
}
