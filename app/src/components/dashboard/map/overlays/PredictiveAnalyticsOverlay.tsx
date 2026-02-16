/**
 * Predictive Analytics Overlay Component
 *
 * Renders predictive analytics layers on the Leaflet map:
 * - Price Forecasts (6-month projections with confidence intervals)
 * - Policy Risk (cooling measure sensitivity)
 * - Lease Arbitrage (theoretical vs market value)
 */

import React, { useRef } from 'react';
import { LayerGroup, GeoJSON } from 'react-leaflet';
import { PredictiveAnalyticsData, LayerId } from '../../../../types/analytics';
import { divergingScale, sequentialScale, getForecastSignalColor, getPolicyRiskColor } from '../../../../utils/colorScales';

interface PredictiveAnalyticsOverlayProps {
  active: boolean;
  data: PredictiveAnalyticsData | null;
  loading: boolean;
  planningAreasGeoJSON: any;
  layerId: LayerId;
}

/**
 * Get price forecast style function
 */
function getForecastStyle(feature: any, data: PredictiveAnalyticsData) {
  const areaName = feature.properties?.pln_area_n;
  const areaData = data?.planning_areas?.[areaName];

  if (!areaData?.price_forecast) {
    return {
      fillColor: '#cccccc',
      weight: 2,
      opacity: 1,
      color: 'white',
      dashArray: '3',
      fillOpacity: 0.3,
    };
  }

  const { price_forecast } = areaData;
  const projectedChange = price_forecast.projected_change_pct || 0;

  // Diverging scale: -10% to +10%
  const color = divergingScale(projectedChange, -10, 10);

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
 * Get policy risk style function
 */
function getPolicyRiskStyle(feature: any, data: PredictiveAnalyticsData) {
  const areaName = feature.properties?.pln_area_n;
  const areaData = data?.planning_areas?.[areaName];

  if (!areaData?.policy_risk) {
    return {
      fillColor: '#cccccc',
      weight: 2,
      opacity: 1,
      color: 'white',
      dashArray: '3',
      fillOpacity: 0.3,
    };
  }

  const { policy_risk } = areaData;
  const riskLevel = policy_risk.risk_level || 'MODERATE';

  return {
    fillColor: getPolicyRiskColor(riskLevel),
    weight: 2,
    opacity: 1,
    color: 'white',
    dashArray: '3',
    fillOpacity: 0.7,
  };
}

/**
 * Get lease arbitrage style function
 */
function getLeaseArbitrageStyle(feature: any, data: PredictiveAnalyticsData) {
  const areaName = feature.properties?.pln_area_n;
  const areaData = data?.planning_areas?.[areaName];

  if (!areaData?.lease_arbitrage) {
    return {
      fillColor: '#cccccc',
      weight: 2,
      opacity: 1,
      color: 'white',
      dashArray: '3',
      fillOpacity: 0.3,
    };
  }

  const { lease_arbitrage } = areaData;
  const arbitragePct = lease_arbitrage.arbitrage_pct || 0;

  // Diverging scale: -50% to +50%
  const color = divergingScale(arbitragePct, -50, 50);

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
 * Create tooltip content for price forecast layer
 */
function createForecastTooltip(feature: any, data: PredictiveAnalyticsData): string {
  const areaName = feature.properties?.pln_area_n;
  const areaData = data?.planning_areas?.[areaName];

  if (!areaData?.price_forecast) {
    return `<b>${areaName}</b><br>No forecast data available`;
  }

  const { price_forecast } = areaData;

  return `
    <div class="text-sm">
      <h3 class="font-bold">${areaName}</h3>
      <h4 class="font-semibold mt-2">Price Forecast</h4>
      <p><b>6-Month Projection:</b> ${price_forecast.projected_change_pct?.toFixed(1) || 'N/A'}%</p>
      <p><b>Confidence Interval:</b> ${price_forecast.confidence_interval_lower?.toFixed(1) || 'N/A'}% to ${price_forecast.confidence_interval_upper?.toFixed(1) || 'N/A'}%</p>
      <p><b>Model R²:</b> ${price_forecast.model_r2?.toFixed(3) || 'N/A'}</p>
      <p><b>Forecast Date:</b> ${price_forecast.forecast_date}</p>
      <p><b>Signal:</b> <span style="color: ${getForecastSignalColor(price_forecast.signal)}">${price_forecast.signal}</span></p>
    </div>
  `;
}

/**
 * Create tooltip content for policy risk layer
 */
function createPolicyRiskTooltip(feature: any, data: PredictiveAnalyticsData): string {
  const areaName = feature.properties?.pln_area_n;
  const areaData = data?.planning_areas?.[areaName];

  if (!areaData?.policy_risk) {
    return `<b>${areaName}</b><br>No policy risk data available`;
  }

  const { policy_risk } = areaData;

  return `
    <div class="text-sm">
      <h3 class="font-bold">${areaName}</h3>
      <h4 class="font-semibold mt-2">Policy Risk</h4>
      <p><b>Cooling Measure Sensitivity:</b> $${Math.abs(policy_risk.cooling_measure_sensitivity || 0).toLocaleString()}</p>
      <p><b>Market Segment:</b> ${policy_risk.market_segment}</p>
      <p><b>Elasticity:</b> ${policy_risk.elasticity?.toFixed(2) || 'N/A'}</p>
      <p><b>Risk Level:</b> <span style="color: ${getPolicyRiskColor(policy_risk.risk_level)}">${policy_risk.risk_level}</span></p>
    </div>
  `;
}

/**
 * Create tooltip content for lease arbitrage layer
 */
function createLeaseArbitrageTooltip(feature: any, data: PredictiveAnalyticsData): string {
  const areaName = feature.properties?.pln_area_n;
  const areaData = data?.planning_areas?.[areaName];

  if (!areaData?.lease_arbitrage) {
    return `<b>${areaName}</b><br>No lease arbitrage data available`;
  }

  const { lease_arbitrage } = areaData;

  return `
    <div class="text-sm">
      <h3 class="font-bold">${areaName}</h3>
      <h4 class="font-semibold mt-2">Lease Arbitrage (30-year)</h4>
      <p><b>Theoretical Value:</b> $${(lease_arbitrage.theoretical_value_30yr || 0).toLocaleString()}</p>
      <p><b>Market Value:</b> $${(lease_arbitrage.market_value_30yr || 0).toLocaleString()}</p>
      <p><b>Arbitrage:</b> ${lease_arbitrage.arbitrage_pct?.toFixed(1) || 'N/A'}%</p>
      <p><b>Recommendation:</b> <span style="color: ${getForecastSignalColor(lease_arbitrage.recommendation)}">${lease_arbitrage.recommendation}</span></p>
    </div>
  `;
}

/**
 * Predictive Analytics Overlay Component
 */
export default function PredictiveAnalyticsOverlay({
  active,
  data,
  loading,
  planningAreasGeoJSON,
  layerId,
}: PredictiveAnalyticsOverlayProps) {
  const layerGroupRef = React.useRef<L.LayerGroup | null>(null);

  // Don't render if not active
  if (!active) {
    return null;
  }

  // Show loading state
  if (loading) {
    return (
      <div className="fixed bottom-4 right-4 bg-white p-2 rounded shadow text-sm">
        Loading predictive analytics...
      </div>
    );
  }

  // Determine which sub-layer to render
  const getStyleFunction = () => {
    switch (layerId) {
      case 'predictive.forecast':
        return (feature: any) => getForecastStyle(feature, data!);
      case 'predictive.policy':
        return (feature: any) => getPolicyRiskStyle(feature, data!);
      case 'predictive.lease':
        return (feature: any) => getLeaseArbitrageStyle(feature, data!);
      default:
        return () => ({});
    }
  };

  const getTooltipFunction = () => {
    switch (layerId) {
      case 'predictive.forecast':
        return (feature: any) => createForecastTooltip(feature, data!);
      case 'predictive.policy':
        return (feature: any) => createPolicyRiskTooltip(feature, data!);
      case 'predictive.lease':
        return (feature: any) => createLeaseArbitrageTooltip(feature, data!);
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
