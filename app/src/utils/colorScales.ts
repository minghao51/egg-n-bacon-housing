/**
 * Color Scale Utilities
 *
 * Functions for generating color scales for map visualizations.
 */

import { ColorScaleType, LISAClusterType } from '../types/analytics';

// ==================== Color Scales ====================

/**
 * Diverging color scale (for hotspots, forecasts, etc.)
 */
export const DIVERGING_COLORS = {
  hotspot: [
    '#313695', // Dark Blue (coldspot 99%)
    '#4575b4', // Blue (coldspot 95%)
    '#fee090', // Light Yellow (not significant)
    '#d73027', // Orange (hotspot 95%)
    '#a50026', // Red (hotspot 99%)
  ],
  forecast: [
    '#d73027', // Dark Red (strong sell)
    '#f46d43', // Red (sell)
    '#ffffbf', // Gray/Yellow (hold)
    '#a6d96a', // Light Green (buy)
    '#1a9850', // Dark Green (strong buy)
  ],
  lease: [
    '#d73027', // Red (overvalued)
    '#f46d43', // Light Red
    '#ffffbf', // Yellow (fair value)
    '#a6d96a', // Light Green
    '#1a9850', // Dark Green (undervalued)
  ],
};

/**
 * Sequential color scale (for MRT impact, school quality, etc.)
 */
export const SEQUENTIAL_COLORS = {
  mrt: ['#ffffcc', '#a1dab4', '#41b6c4', '#2c7fb8', '#253494'],
  school: ['#ffffcc', '#c2e699', '#78c679', '#31a354', '#006837'],
  amenity: ['#ffffcc', '#fed976', '#feb24c', '#fd8d3c', '#f03b20'],
  policy: ['#31a354', '#addd8e', '#ffffcc', '#fee391', '#fec44f', '#fc4e2a'],
};

/**
 * Categorical color scale (for LISA clusters)
 */
export const LISA_CLUSTER_COLORS: Record<LISAClusterType, string> = {
  MATURE_HOTSPOT: '#a50026', // Dark Red
  EMERGING_HOTSPOT: '#f46d43', // Orange
  VALUE_OPPORTUNITY: '#a6d96a', // Light Green
  STABLE: '#d3d3d3', // Gray
  DECLINING: '#74add1', // Light Blue
  TRANSITIONAL: '#ffffbf', // Yellow
};

// ==================== Color Scale Functions ====================

/**
 * Diverging scale - maps values to a diverging color palette
 *
 * @param value - Value to map
 * @param min - Minimum value (maps to first color)
 * @param max - Maximum value (maps to last color)
 * @param colors - Array of hex colors (default: hotspot scale)
 * @returns Hex color string
 */
export function divergingScale(
  value: number,
  min: number,
  max: number,
  colors: string[] = DIVERGING_COLORS.hotspot
): string {
  if (value == null || isNaN(value)) {
    return '#cccccc'; // Gray for missing values
  }

  const normalized = (value - min) / (max - min);
  const index = Math.floor(normalized * (colors.length - 1));
  const clampedIndex = Math.max(0, Math.min(colors.length - 1, index));
  return colors[clampedIndex];
}

/**
 * Sequential scale - maps values to a sequential color palette
 *
 * @param value - Value to map
 * @param min - Minimum value (maps to first color)
 * @param max - Maximum value (maps to last color)
 * @param colorStart - Starting color (light)
 * @param colorEnd - Ending color (dark)
 * @returns Hex color string
 */
export function sequentialScale(
  value: number,
  min: number,
  max: number,
  colorStart: string = '#ffffcc',
  colorEnd: string = '#006837'
): string {
  if (value == null || isNaN(value)) {
    return '#cccccc';
  }

  const ratio = (value - min) / (max - min);
  return interpolateColor(colorStart, colorEnd, Math.max(0, Math.min(1, ratio)));
}

/**
 * Categorical scale - maps categories to colors
 *
 * @param category - Category string
 * @param colorMap - Mapping of categories to colors
 * @returns Hex color string
 */
export function categoricalScale(
  category: string,
  colorMap: Record<string, string>
): string {
  return colorMap[category] || '#cccccc';
}

/**
 * Linear interpolation between two colors
 *
 * @param color1 - Starting color (hex)
 * @param color2 - Ending color (hex)
 * @param ratio - Interpolation ratio (0-1)
 * @returns Hex color string
 */
export function interpolateColor(color1: string, color2: string, ratio: number): string {
  const c1 = hexToRgb(color1);
  const c2 = hexToRgb(color2);

  if (!c1 || !c2) {
    return '#cccccc';
  }

  const r = Math.round(c1.r + (c2.r - c1.r) * ratio);
  const g = Math.round(c1.g + (c2.g - c1.g) * ratio);
  const b = Math.round(c1.b + (c2.b - c1.b) * ratio);

  return rgbToHex(r, g, b);
}

/**
 * Get hotspot classification color
 */
export function getHotspotColor(zScore: number | null): string {
  if (zScore == null) return '#cccccc';

  const abs = Math.abs(zScore);
  if (abs >= 2.58) {
    return zScore > 0 ? '#a50026' : '#313695'; // 99% confidence
  } else if (abs >= 1.96) {
    return zScore > 0 ? '#d73027' : '#4575b4'; // 95% confidence
  }
  return '#fee090'; // Not significant
}

/**
 * Get forecast signal color
 */
export function getForecastSignalColor(signal: 'BUY' | 'HOLD' | 'SELL'): string {
  const colors = {
    BUY: '#1a9850',
    HOLD: '#ffffbf',
    SELL: '#d73027',
  };
  return colors[signal];
}

/**
 * Get policy risk color
 */
export function getPolicyRiskColor(riskLevel: 'LOW' | 'MODERATE' | 'HIGH'): string {
  const colors = {
    LOW: '#31a354',
    MODERATE: '#ffffcc',
    HIGH: '#fc4e2a',
  };
  return colors[riskLevel];
}

// ==================== Helper Functions ====================

/**
 * Convert hex color to RGB
 */
function hexToRgb(hex: string): { r: number; g: number; b: number } | null {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result
    ? {
        r: parseInt(result[1], 16),
        g: parseInt(result[2], 16),
        b: parseInt(result[3], 16),
      }
    : null;
}

/**
 * Convert RGB to hex color
 */
function rgbToHex(r: number, g: number, b: number): string {
  return '#' + [r, g, b].map((x) => {
    const hex = x.toString(16);
    return hex.length === 1 ? '0' + hex : hex;
  }).join('');
}

/**
 * Get color scale based on type
 */
export function getColorScale(
  scaleType: ColorScaleType,
  scaleName: string = 'default'
): string[] {
  if (scaleType === 'diverging') {
    return DIVERGING_COLORS[scaleName as keyof typeof DIVERGING_COLORS] || DIVERGING_COLORS.hotspot;
  } else if (scaleType === 'sequential') {
    return SEQUENTIAL_COLORS[scaleName as keyof typeof SEQUENTIAL_COLORS] || SEQUENTIAL_COLORS.mrt;
  }
  return [];
}
