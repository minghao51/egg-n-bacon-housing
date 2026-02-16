/**
 * Layer Control Component
 *
 * Sidebar control for toggling analytics layers on/off.
 * Features hierarchical checkboxes (category > sub-layers).
 */

import React, { useState } from 'react';
import { LayerId, LAYER_CATEGORIES, LAYER_METADATA } from '../../../types/analytics';

interface LayerControlProps {
  activeLayers: Record<string, boolean>;
  onToggleLayer: (layerId: LayerId) => void;
  loadingLayers: Set<LayerId>;
}

interface CategorySectionProps {
  category: string;
  layers: LayerId[];
  activeLayers: Record<string, boolean>;
  onToggleLayer: (layerId: LayerId) => void;
  loadingLayers: Set<LayerId>;
}

/**
 * Category Section Component
 */
function CategorySection({
  category,
  layers,
  activeLayers,
  onToggleLayer,
  loadingLayers,
}: CategorySectionProps) {
  const [expanded, setExpanded] = useState(false);

  // Count active sub-layers
  const activeCount = layers.filter((layerId) => activeLayers[layerId]).length;

  // Toggle all layers in category
  const toggleCategory = () => {
    const shouldActivate = activeCount === 0;
    layers.forEach((layerId) => {
      if (shouldActivate !== activeLayers[layerId]) {
        onToggleLayer(layerId);
      }
    });
  };

  const categoryLabel = category.charAt(0).toUpperCase() + category.slice(1);

  return (
    <div className="mb-4">
      {/* Category Header */}
      <div className="flex items-center justify-between mb-2">
        <label className="flex items-center space-x-2 cursor-pointer">
          <input
            type="checkbox"
            className="form-checkbox h-4 w-4 text-blue-600 rounded"
            checked={activeCount > 0}
            onChange={toggleCategory}
            ref={(input) => {
              if (input) {
                input.indeterminate = activeCount > 0 && activeCount < layers.length;
              }
            }}
          />
          <span className="font-semibold text-sm">
            {categoryLabel} Analysis ({activeCount}/{layers.length})
          </span>
        </label>
        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          className="text-xs text-blue-600 hover:text-blue-800"
        >
          {expanded ? '▼' : '▶'}
        </button>
      </div>

      {/* Sub-layers */}
      {expanded && (
        <div className="ml-4 space-y-1">
          {layers.map((layerId) => {
            const metadata = LAYER_METADATA[layerId];
            const isLoading = loadingLayers.has(layerId);

            return (
              <label key={layerId} className="flex items-center space-x-2 cursor-pointer text-sm">
                <input
                  type="checkbox"
                  className="form-checkbox h-3 w-3 text-blue-600 rounded"
                  checked={activeLayers[layerId] || false}
                  onChange={() => onToggleLayer(layerId)}
                  disabled={activeCount === 0 && !activeLayers[layerId]}
                />
                <span className={activeCount === 0 && !activeLayers[layerId] ? 'text-gray-400' : ''}>
                  {metadata?.name || layerId}
                </span>
                {isLoading && (
                  <span className="text-xs text-blue-600 animate-spin">⌛</span>
                )}
              </label>
            );
          })}
        </div>
      )}
    </div>
  );
}

/**
 * Layer Control Component
 */
export default function LayerControl({
  activeLayers,
  onToggleLayer,
  loadingLayers,
}: LayerControlProps) {
  // Quick action buttons
  const handleSelectAll = () => {
    Object.keys(LAYER_METADATA).forEach((layerId) => {
      if (!activeLayers[layerId]) {
        onToggleLayer(layerId as LayerId);
      }
    });
  };

  const handleClearAll = () => {
    Object.keys(activeLayers).forEach((layerId) => {
      if (activeLayers[layerId]) {
        onToggleLayer(layerId as LayerId);
      }
    });
  };

  return (
    <div className="p-4 bg-white rounded shadow">
      <h3 className="font-bold text-lg mb-3">Analytics Layers</h3>

      {/* Quick Actions */}
      <div className="flex space-x-2 mb-4">
        <button
          type="button"
          onClick={handleSelectAll}
          className="text-xs px-2 py-1 bg-blue-100 text-blue-700 rounded hover:bg-blue-200"
        >
          Select All
        </button>
        <button
          type="button"
          onClick={handleClearAll}
          className="text-xs px-2 py-1 bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
        >
          Clear All
        </button>
      </div>

      {/* Category Sections */}
      {Object.entries(LAYER_CATEGORIES).map(([category, layers]) => (
        <CategorySection
          key={category}
          category={category}
          layers={layers}
          activeLayers={activeLayers}
          onToggleLayer={onToggleLayer}
          loadingLayers={loadingLayers}
        />
      ))}

      {/* Info Text */}
      <div className="mt-4 pt-3 border-t text-xs text-gray-600">
        <p>Click category names to expand/collapse.</p>
        <p className="mt-1">Toggle sub-layers to visualize on map.</p>
      </div>
    </div>
  );
}
