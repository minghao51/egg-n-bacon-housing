/**
 * Research-map archive layer control (slice S9, SVG 17).
 *
 * Layer selection is retained for *inspection only*. No analytical polygon fill
 * is drawn from these extracts; the observed metric is the map's single fill.
 * Each row names its source asset, units and load status, and a failure in one
 * source is reported on its own rows.
 */

import { LAYER_CATEGORIES, LAYER_METADATA } from "@/types/analytics";
import type { LayerId } from "@/types/analytics";
import {
  ARCHIVE_LAYER_SOURCES,
  type ArchiveLayerStatus,
} from "@/utils/map-archive";

interface ArchiveLayerControlProps {
  activeLayers: Record<LayerId, boolean>;
  onToggleLayer: (layerId: LayerId) => void;
  onClearLayers: () => void;
  statuses: Record<LayerId, ArchiveLayerStatus>;
}

const STATUS_LABEL: Record<ArchiveLayerStatus["state"], string> = {
  loading: "Loading",
  available: "Ready",
  error: "Unavailable",
};

const STATUS_CLASS: Record<ArchiveLayerStatus["state"], string> = {
  loading: "border-border text-muted-foreground",
  available: "border-border text-foreground",
  error: "border-red-600 text-red-700 dark:text-red-300",
};

export default function ArchiveLayerControl({
  activeLayers,
  onToggleLayer,
  onClearLayers,
  statuses,
}: ArchiveLayerControlProps) {
  return (
    <section
      aria-labelledby="archive-layers-heading"
      className="rounded-2xl border border-border bg-card p-4"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="max-w-2xl">
          <h2
            id="archive-layers-heading"
            className="text-lg font-bold text-foreground"
          >
            Archive layer controls
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Select archived layers to inspect their stored fields for the chosen
            area. No analytical fill is drawn: the observed transaction metric
            remains the map&rsquo;s only fill.
          </p>
        </div>
        <button
          type="button"
          onClick={onClearLayers}
          className="rounded border border-input px-3 py-2 text-sm font-bold text-foreground transition-colors hover:bg-muted"
        >
          Clear layers
        </button>
      </div>

      <p
        role="note"
        className="mt-3 rounded border border-border bg-muted/30 p-3 text-sm text-foreground"
      >
        <span className="font-bold">
          Output gate — not validated for current use.
        </span>{" "}
        Archived layer data can be inspected, but current analytical shading is
        withheld. Uniform placeholder values and historical forecasts are
        labelled as such in the inspector.
      </p>

      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        {Object.entries(LAYER_CATEGORIES).map(([category, layerIds]) => (
          <details
            key={category}
            open
            className="rounded-xl border border-border bg-background p-3"
          >
            <summary className="cursor-pointer text-sm font-bold uppercase tracking-wider text-muted-foreground">
              {category === "feature"
                ? "Feature impact"
                : category === "predictive"
                  ? "Predictive archive"
                  : "Spatial"}
            </summary>
            <ul className="mt-3 space-y-2">
              {layerIds.map((layerId) => {
                const source = ARCHIVE_LAYER_SOURCES[layerId];
                const status = statuses[layerId];
                const inputId = `archive-layer-${layerId}`;
                return (
                  <li key={layerId} className="text-sm">
                    <div className="flex items-start gap-2">
                      <input
                        id={inputId}
                        type="checkbox"
                        checked={activeLayers[layerId] ?? false}
                        onChange={() => onToggleLayer(layerId)}
                        className="mt-1 h-4 w-4"
                      />
                      <div className="min-w-0 flex-1">
                        <label
                          htmlFor={inputId}
                          className="cursor-pointer font-medium text-foreground"
                        >
                          {LAYER_METADATA[layerId].name}
                        </label>
                        <p className="text-xs text-muted-foreground">
                          {source.unit}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          <code className="font-mono">{status.asset}</code>
                        </p>
                        <span
                          className={`mt-1 inline-block rounded-sm border px-1.5 py-0.5 text-xs font-bold ${STATUS_CLASS[status.state]}`}
                        >
                          {STATUS_LABEL[status.state]}
                        </span>
                        {status.state === "error" ? (
                          <p className="mt-1 text-xs text-red-700 dark:text-red-300">
                            {status.detail}
                          </p>
                        ) : null}
                      </div>
                    </div>
                  </li>
                );
              })}
            </ul>
          </details>
        ))}
      </div>
    </section>
  );
}
