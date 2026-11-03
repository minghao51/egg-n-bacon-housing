/**
 * Observed-comparison map for `/explore`.
 *
 * Draws the 55 published planning-area polygons as a tile-free SVG choropleth.
 * The fills are quantile bins of the selected metric over the rows the list
 * currently shows, so the map, the legend and the table describe one dataset
 * rather than three approximations of it.
 *
 * Constraints:
 * - The geometry is a 2 MB published asset, so it is only requested when this
 *   component mounts — that is, when the reader first opens the map view. The
 *   gzip/JSON cache in `useGzipJson` keeps a revisit from re-downloading it.
 * - An area with no value (outside this section, below the sample threshold, or
 *   filtered out by the search) is never coloured from the data palette: it
 *   keeps `MAP_NO_DATA_FILL`, with a hatch pattern inside the section and
 *   reduced opacity outside it.
 * - Areas outside the current section have no fieldnote link here: the page set
 *   covers the areas published in *some* joint section, not all 55 geometries,
 *   and a link that 404s is worse than no link.
 * - No basemap, no tiles, no network beyond the two published assets.
 */

import { useMemo, useState, type ReactNode } from "react";
import { DATA_URLS } from "@/constants/data-urls";
import { useGzipJson } from "@/hooks/useGzipJson";
import { areaHref } from "@/utils/area-links";
import type {
  ExplorerMetric,
  ExplorerSelection,
} from "@/utils/explorer-selection";
import {
  MAP_NO_DATA_FILL,
  MAP_PALETTE,
  binIndex,
  projectPlanningAreas,
  quantileBins,
  type Bin,
  type ProjectedMap,
} from "@/utils/geo-projection";
import type { ExplorerDataset, ExplorerRow } from "@/utils/observed-rows";
import { METRIC_OPTIONS, periodLabel, propertyNoun } from "./ExplorerSettings";

/** Bin count for the choropleth; matches the five steps of `MAP_PALETTE`. */
const BIN_COUNT = 5;

/** Cache key for the geometry, so a revisit inside the TTL is free. */
const GEOMETRY_CACHE_KEY = "explore:planning_areas";

/** Hairline between areas and the outline of the selected area. */
const AREA_STROKE = "#F6F3EC";
const SELECTED_STROKE = "#B64426";
const FOCUS_STROKE = "#006B65";

const NO_VALUE_PATTERN_ID = "explorer-map-no-value-hatch";

/** `data-area-state` values; also the legend groups. */
type AreaState = "binned" | "filtered" | "no-value" | "outside";

interface MapShape {
  areaId: string;
  areaName: string;
  path: string;
  href: string | null;
  state: AreaState;
  fill: string;
  value: number | null;
  bin: number | null;
}

interface MapModel {
  width: number;
  height: number;
  shapes: MapShape[];
  bins: Bin[];
  binCounts: number[];
  noValueCount: number;
  filteredCount: number;
  outsideCount: number;
  binnedCount: number;
}

function rowValue(row: ExplorerRow, metric: ExplorerMetric): number | null {
  if (metric === "median_price") return row.medianPrice;
  if (metric === "median_psf") return row.medianPsf;
  return row.volume;
}

/** Thousands-separated magnitude with its currency where one applies. */
function formatBound(metric: ExplorerMetric, value: number): string {
  const digits = Math.round(value).toLocaleString("en-US");
  // A transaction count is not a currency amount, so it never gets an "S$".
  return metric === "volume" ? digits : `S$${digits}`;
}

function unitSuffix(metric: ExplorerMetric): string {
  if (metric === "median_psf") return " psf";
  if (metric === "volume") return " sales";
  return "";
}

/** One value as it appears in a tooltip/title, e.g. "S$499,000" or "971 sales". */
function valueLabel(metric: ExplorerMetric, value: number): string {
  return `${formatBound(metric, value)}${unitSuffix(metric)}`;
}

/**
 * One bin's range. Bins are half-open, so the upper bound is marked "under"
 * unless this is the last bin, which contains its maximum. A plain "min–max"
 * would imply the maximum belongs to this bin.
 */
function binRangeLabel(metric: ExplorerMetric, bin: Bin): string {
  const unit = unitSuffix(metric);
  const min = `${formatBound(metric, bin.min)}${unit}`;
  const max = `${formatBound(metric, bin.max)}${unit}`;
  return bin.upperInclusive === true
    ? `${min} to ${max}`
    : `${min} to under ${max}`;
}

function areaHrefFor(slug: string, selection: ExplorerSelection): string {
  const base = import.meta.env.BASE_URL.replace(/\/$/, "");
  return `${base}${areaHref(slug, selection)}`;
}

/**
 * Bind the dataset to the geometry: which area is in which bin, which has no
 * value, and which is outside the selection entirely.
 */
function buildModel(
  projected: ProjectedMap,
  dataset: ExplorerDataset,
  selection: ExplorerSelection,
): MapModel {
  const inSection = new Map<string, ExplorerRow>();
  for (const row of dataset.rows) inSection.set(row.areaId, row);

  const shown = new Map<string, ExplorerRow>();
  const values: number[] = [];
  for (const row of dataset.filtered) {
    shown.set(row.areaId, row);
    const value = rowValue(row, selection.metric);
    if (value !== null) values.push(value);
  }

  const bins = quantileBins(values, BIN_COUNT);
  const binCounts = bins.map(() => 0);

  const placed = new Map<string, { index: number; value: number }>();
  for (const [areaId, row] of shown) {
    const value = rowValue(row, selection.metric);
    if (value === null) continue;
    const index = binIndex(value, bins);
    if (index === null) continue;
    placed.set(areaId, { index, value });
  }

  let noValueCount = 0;
  let filteredCount = 0;
  let outsideCount = 0;

  const shapes: MapShape[] = projected.areas.map((area) => {
    const position = placed.get(area.areaId);
    if (position !== undefined) {
      const index = Math.min(position.index, MAP_PALETTE.length - 1);
      binCounts[position.index] = (binCounts[position.index] ?? 0) + 1;
      return {
        areaId: area.areaId,
        areaName: area.areaName,
        path: area.path,
        href: areaHrefFor(area.slug, selection),
        state: "binned",
        fill: MAP_PALETTE[index] ?? MAP_NO_DATA_FILL,
        value: position.value,
        bin: position.index,
      };
    }

    // Inside the section but not drawn. Two different reasons, and they must
    // not be conflated: the area may be hidden by the current sample threshold
    // or search (its values exist), or the section may publish no value for the
    // selected metric.
    const row = inSection.get(area.areaId);
    if (row !== undefined) {
      const hiddenByFilters = rowValue(row, selection.metric) !== null;
      if (hiddenByFilters) {
        filteredCount += 1;
      } else {
        noValueCount += 1;
      }
      return {
        areaId: area.areaId,
        areaName: area.areaName,
        path: area.path,
        href: areaHrefFor(row.slug, selection),
        state: hiddenByFilters ? "filtered" : "no-value",
        fill: MAP_NO_DATA_FILL,
        value: null,
        bin: null,
      };
    }

    outsideCount += 1;
    return {
      areaId: area.areaId,
      areaName: area.areaName,
      path: area.path,
      href: null,
      state: "outside",
      fill: MAP_NO_DATA_FILL,
      value: null,
      bin: null,
    };
  });

  return {
    width: projected.width,
    height: projected.height,
    shapes,
    bins,
    binCounts,
    noValueCount,
    filteredCount,
    outsideCount,
    binnedCount: placed.size,
  };
}

function areaTitle(shape: MapShape, metric: ExplorerMetric): string {
  if (shape.state === "binned" && shape.value !== null) {
    return `${shape.areaName} — ${valueLabel(metric, shape.value)}`;
  }
  if (shape.state === "filtered") {
    return `${shape.areaName} — hidden by the current sample threshold or search; its published value is not drawn`;
  }
  if (shape.state === "no-value") {
    return `${shape.areaName} — this section publishes no value for this metric`;
  }
  return `${shape.areaName} — outside this selection`;
}

export interface ExplorerMapProps {
  dataset: ExplorerDataset;
  selection: ExplorerSelection;
}

export default function ExplorerMap({ dataset, selection }: ExplorerMapProps) {
  const geometry = useGzipJson<unknown>(
    DATA_URLS.planningAreas,
    GEOMETRY_CACHE_KEY,
  );
  const [focusedArea, setFocusedArea] = useState<string | null>(null);

  // Projection is the only step that can fail on a payload that parsed as
  // JSON, so a throw is caught here and reported as a geometry failure.
  const projection = useMemo<{
    map: ProjectedMap | null;
    error: string | null;
  }>(() => {
    if (geometry.data === null) return { map: null, error: null };
    try {
      return { map: projectPlanningAreas(geometry.data), error: null };
    } catch (cause) {
      return {
        map: null,
        error:
          cause instanceof Error
            ? cause.message
            : "The planning-area geometry could not be read.",
      };
    }
  }, [geometry.data]);

  const model = useMemo<MapModel | null>(() => {
    if (projection.map === null) return null;
    return buildModel(projection.map, dataset, selection);
  }, [projection.map, dataset, selection]);

  const metricOption =
    METRIC_OPTIONS.find((option) => option.value === selection.metric) ??
    METRIC_OPTIONS[0];

  const scopeLabel = `${periodLabel(dataset.period)} ${propertyNoun(
    dataset.property,
  )} ${metricOption.noun}`;

  const geometryLoading = geometry.loading && geometry.data === null;
  const geometryError = geometry.error ?? projection.error ?? null;

  let body: ReactNode;
  if (dataset.filtered.length === 0) {
    // An empty dataset must not render as an empty map: there is nothing to
    // colour, and the reason belongs in words.
    body = (
      <p className="mt-4 rounded border border-border bg-muted px-3 py-2 text-sm text-muted-foreground">
        No planning areas match these settings, so there is nothing to map.
        Widen the period, clear the search or lower the sample threshold — the
        table view stays available.
      </p>
    );
  } else if (geometryLoading) {
    body = (
      <p
        role="status"
        className="mt-4 rounded border border-border bg-muted px-3 py-2 text-sm text-muted-foreground"
      >
        Loading the published planning-area boundaries&hellip;
      </p>
    );
  } else if (geometryError !== null || model === null) {
    body = (
      <div
        role="alert"
        className="mt-4 rounded border border-border bg-card px-3 py-2 text-sm"
      >
        <p className="font-bold text-foreground">
          The planning-area boundaries could not be drawn
        </p>
        <p className="mt-1 text-muted-foreground">
          {geometryError ??
            "The published geometry did not contain any usable planning area."}{" "}
          The observed values are unaffected: the table view lists every area in
          this selection with its published figures.
        </p>
        <button
          type="button"
          onClick={() => void geometry.reload()}
          className="mt-2 rounded border border-input px-3 py-1 text-sm font-bold text-foreground"
        >
          Try loading the boundaries again
        </button>
      </div>
    );
  } else {
    const {
      width,
      height,
      shapes,
      bins,
      binCounts,
      noValueCount,
      filteredCount,
      outsideCount,
    } = model;
    body = (
      <>
        <svg
          viewBox={`0 0 ${width} ${height}`}
          role="group"
          aria-labelledby="explorer-map-svg-title"
          className="mt-4 h-auto w-full max-w-full"
        >
          <title id="explorer-map-svg-title">
            {`Planning-area map: ${scopeLabel}. ${model.binnedCount} areas coloured, ${filteredCount} hidden by the current filters, ${noValueCount} with no value for this metric, ${outsideCount} outside this selection.`}
          </title>
          <defs>
            <pattern
              id={NO_VALUE_PATTERN_ID}
              width="6"
              height="6"
              patternUnits="userSpaceOnUse"
              patternTransform="rotate(45)"
            >
              <rect width="6" height="6" fill={MAP_NO_DATA_FILL} />
              <line
                x1="0"
                y1="0"
                x2="0"
                y2="6"
                stroke="#7A8583"
                strokeWidth="1"
              />
            </pattern>
          </defs>

          {shapes.map((shape) => {
            const selected =
              selection.area !== null && selection.area === shape.areaId;
            const focused = focusedArea === shape.areaId;
            const stroke = focused
              ? FOCUS_STROKE
              : selected
                ? SELECTED_STROKE
                : AREA_STROKE;

            const path = (
              <path
                d={shape.path}
                fillRule="evenodd"
                fill={
                  shape.state === "no-value" || shape.state === "filtered"
                    ? `url(#${NO_VALUE_PATTERN_ID})`
                    : shape.fill
                }
                fillOpacity={shape.state === "outside" ? 0.5 : 1}
                stroke={stroke}
                strokeWidth={focused ? 3 : selected ? 1.6 : 0.75}
                vectorEffect="non-scaling-stroke"
                data-area-state={shape.state}
                data-bin={shape.bin ?? undefined}
              >
                <title>{areaTitle(shape, selection.metric)}</title>
              </path>
            );

            if (shape.href === null) {
              return (
                <g key={shape.areaId} data-area-id={shape.areaId}>
                  {path}
                </g>
              );
            }

            return (
              <a
                key={shape.areaId}
                href={shape.href}
                aria-label={`${areaTitle(shape, selection.metric)} — open fieldnote`}
                aria-current={selected ? "true" : undefined}
                onFocus={() => setFocusedArea(shape.areaId)}
                onBlur={() => setFocusedArea(null)}
                data-area-id={shape.areaId}
              >
                {path}
              </a>
            );
          })}
        </svg>

        <ul
          aria-label="Map legend"
          className="mt-4 flex flex-wrap gap-x-6 gap-y-2 text-sm"
        >
          {bins.map((bin, index) => (
            <li key={bin.label} className="flex items-center gap-2">
              <span
                aria-hidden="true"
                className="inline-block h-4 w-4 shrink-0 rounded-sm border border-border"
                style={{
                  backgroundColor:
                    MAP_PALETTE[Math.min(index, MAP_PALETTE.length - 1)],
                }}
              />
              <span className="text-foreground">
                {binRangeLabel(selection.metric, bin)}
              </span>
              <span className="text-muted-foreground">
                {`${binCounts[index] ?? 0} ${
                  (binCounts[index] ?? 0) === 1 ? "area" : "areas"
                }`}
              </span>
            </li>
          ))}

          <li className="flex items-center gap-2">
            <span
              aria-hidden="true"
              className="inline-block h-4 w-4 shrink-0 rounded-sm border border-border"
              style={{
                backgroundColor: MAP_NO_DATA_FILL,
                backgroundImage:
                  "repeating-linear-gradient(45deg, #7A8583 0 1px, transparent 1px 4px)",
              }}
            />
            <span className="text-foreground">
              {`Hidden by the current filters: ${filteredCount} ${
                filteredCount === 1 ? "area" : "areas"
              }`}
            </span>
          </li>

          <li className="flex items-center gap-2">
            <span
              aria-hidden="true"
              className="inline-block h-4 w-4 shrink-0 rounded-sm border border-border"
              style={{ backgroundColor: MAP_NO_DATA_FILL, opacity: 0.5 }}
            />
            <span className="text-foreground">
              {`No value for this metric: ${noValueCount} ${
                noValueCount === 1 ? "area" : "areas"
              }`}
            </span>
          </li>

          <li className="flex items-center gap-2">
            <span
              aria-hidden="true"
              className="inline-block h-4 w-4 shrink-0 rounded-sm border border-border"
              style={{ backgroundColor: MAP_NO_DATA_FILL, opacity: 0.5 }}
            />
            <span className="text-foreground">
              {`Outside this selection: ${outsideCount} ${
                outsideCount === 1 ? "area" : "areas"
              }`}
            </span>
          </li>
        </ul>

        <p className="mt-3 text-xs text-muted-foreground">
          {`Bins are quantiles of the ${model.binnedCount} ${
            model.binnedCount === 1 ? "area" : "areas"
          } currently shown, not a scientific classification. Areas hidden by the sample threshold or the search, areas with no value for this metric, and areas outside this section keep a neutral fill and are never coloured.`}
        </p>
      </>
    );
  }

  return (
    <figure className="mt-0 min-w-0 rounded-lg border border-border bg-card p-4 sm:p-5">
      <figcaption className="text-sm">
        <span className="block font-bold text-foreground">{scopeLabel}</span>
        <span className="mt-1 block text-muted-foreground">
          Planning-area boundaries from the published geometry. No map tiles are
          requested for this view.
        </span>
      </figcaption>

      {body}

      <p className="mt-3 border-t border-border pt-3 text-xs text-muted-foreground">
        Data: <code className="font-mono">map_metrics.{dataset.section}</code>{" "}
        &mdash; the same joint section as the list and the table.
      </p>
    </figure>
  );
}
