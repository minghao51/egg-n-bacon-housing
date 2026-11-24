/**
 * Research-map → `/explore` handoff (WS-B2, UI-3).
 *
 * The map and the explorer share one scope vocabulary — a planning area, a
 * property type and a period — but the two routes used two different query
 * vocabularies, and the map's handoff wrote only `area` and `metric`. A reader
 * who arrived from `?area=TAMPINES&metric=median_price&timeBasis=pre_covid&propertyType=condo`
 * landed on `?area=TAMPINES&metric=median_price`, i.e. on the explorer's HDB /
 * 2025 defaults: a different property type and a different period, silently.
 *
 * This module is the single place that translates a map scope into the
 * explorer's query contract. It does **not** invent a vocabulary: it builds an
 * {@link ExplorerSelection} and hands it to the explorer's own
 * `serializeExplorerSelection`, so the two routes can never drift.
 *
 * Two properties of the destination matter and are handled explicitly:
 *
 * 1. **The period is pinned.** `serializeExplorerSelection` omits values equal
 *    to the route default, and under `PUBLIC_OBSERVED_RELEASE=v2` the explorer's
 *    default period is a published window rather than the legacy 2025 era. An
 *    omitted period would therefore let a reload (or the destination's own URL
 *    sync) open a different window than the map displayed, so the era is always
 *    written. It is still a legacy era id — `parseExplorerPeriod` keeps legacy
 *    ids on the legacy asset, so `period=year_2025` cannot be re-resolved onto
 *    a pack window.
 * 2. **The metric may have no equivalent.** The map publishes six metrics and
 *    the explorer compares three. A silent substitution is exactly the defect
 *    being fixed, so the mapping table records `null` for the unsupported ones
 *    and {@link buildMapHandoff} names the choice it made in a note the caller
 *    must render next to the link.
 */

import type {
  MetricType,
  PropertyTypeFilter,
  TemporalFilter,
} from "@/types/analytics";
import {
  EXPLORER_DEFAULTS,
  serializeExplorerSelection,
  type ExplorerMetric,
  type ExplorerPeriod,
  type ExplorerProperty,
  type ExplorerSelection,
} from "@/utils/explorer-selection";

/** Map property-type button → explorer `?property=` value. */
export const EXPLORER_PROPERTY_FOR_MAP_TYPE: Readonly<
  Record<PropertyTypeFilter, ExplorerProperty>
> = {
  all: "all",
  hdb: "hdb",
  ec: "ec",
  condo: "condo",
};

/**
 * Map period button → explorer `?period=` value.
 *
 * The two vocabularies are the same four legacy era ids, so this is an
 * identity map kept explicit: it fails to compile if either side gains a
 * member, which a bare pass-through would not.
 */
export const EXPLORER_PERIOD_FOR_MAP_TIME_BASIS: Readonly<
  Record<TemporalFilter, ExplorerPeriod>
> = {
  whole: "whole",
  pre_covid: "pre_covid",
  recent: "recent",
  year_2025: "year_2025",
};

/**
 * The explorer metric chosen for a map metric, or `null` when the explorer has
 * no equivalent. `null` is deliberate: it forces the caller through the
 * disclosed-fallback path instead of letting a `??` default hide the choice.
 */
export const EXPLORER_METRIC_FOR_MAP_METRIC: Readonly<
  Record<MetricType, ExplorerMetric | null>
> = {
  median_price: "median_price",
  median_psf: "median_psf",
  volume: "volume",
  rental_yield_median: null,
  yoy_change_pct: null,
  affordability_ratio: null,
};

/**
 * The metric used when the map's metric has no explorer equivalent.
 *
 * Median transaction price is the explorer's headline quantity and the map's
 * default, so it is the nearest comparison the destination can actually make.
 * It is only ever used together with {@link MapHandoff.metricSubstituted}.
 */
export const HANDOFF_FALLBACK_METRIC: ExplorerMetric = "median_price";

/** Human labels for the map's metric selector and for the handoff note. */
export const MAP_METRIC_LABELS: Readonly<Record<MetricType, string>> = {
  median_price: "Median Price",
  median_psf: "Median PSF",
  volume: "Volume",
  rental_yield_median: "Rental Yield",
  yoy_change_pct: "YoY Growth",
  affordability_ratio: "Affordability Ratio",
};

/** Labels the explorer uses for the three metrics it can compare. */
const EXPLORER_METRIC_LABELS: Readonly<Record<ExplorerMetric, string>> = {
  median_price: "Median transaction price",
  median_psf: "Median price per square foot",
  volume: "Transaction volume",
};

/** One map scope: exactly the state the handoff must preserve. */
export interface MapScope {
  area: string | null;
  metric: MetricType;
  timeBasis: TemporalFilter;
  propertyType: PropertyTypeFilter;
}

export interface MapHandoff {
  /** The map metric the reader is looking at. */
  requestedMetric: MetricType;
  /** The metric the destination will actually compare. */
  appliedMetric: ExplorerMetric;
  /** True when the two differ — i.e. the destination compares something else. */
  metricSubstituted: boolean;
  /**
   * Disclosure to render beside the link, naming both metrics. `null` when the
   * map metric mapped one-to-one and there is nothing to disclose.
   */
  note: string | null;
  /** Serialized query string, without the leading `?`. */
  query: string;
  /** Path below the deployment base path, e.g. `explore?area=TAMPINES`. */
  path: string;
}

/**
 * Map a map scope onto the explorer's selection type.
 *
 * Every field the explorer reads a scope from is set explicitly, so the result
 * can be serialized by the explorer's own serializer without a second mapping.
 */
export function explorerSelectionForMapScope(
  scope: MapScope,
): ExplorerSelection {
  const mapped = EXPLORER_METRIC_FOR_MAP_METRIC[scope.metric];
  const metric = mapped ?? HANDOFF_FALLBACK_METRIC;
  const area = scope.area === null ? "" : scope.area.trim().toUpperCase();

  return {
    ...EXPLORER_DEFAULTS,
    area: area.length > 0 ? area : null,
    metric,
    property: EXPLORER_PROPERTY_FOR_MAP_TYPE[scope.propertyType],
    period: EXPLORER_PERIOD_FOR_MAP_TIME_BASIS[scope.timeBasis],
  };
}

/**
 * Build the handoff for one map scope.
 *
 * Reproduces the reported URL exactly: `area=TAMPINES`, `property=condo`,
 * `period=pre_covid` and `metric=median_price` in the explorer's own key names.
 */
export function buildMapHandoff(scope: MapScope): MapHandoff {
  const selection = explorerSelectionForMapScope(scope);
  const params = serializeExplorerSelection(selection);

  // The period is the one field whose destination default is release-dependent
  // (see the module note), so it is never left implicit.
  if (!params.has("period")) {
    params.set("period", selection.period);
  }

  const query = params.toString();

  return {
    requestedMetric: scope.metric,
    appliedMetric: selection.metric,
    metricSubstituted: selection.metric !== scope.metric,
    note:
      selection.metric === scope.metric
        ? null
        : // Names all three things the reader needs: what the map shows, what
          // the explorer will show, and that the two differ. A substituted
          // metric is never silent.
          `The map's ${MAP_METRIC_LABELS[scope.metric]} has no observed-comparison equivalent. This link opens the explorer on ${EXPLORER_METRIC_LABELS[selection.metric]} (${MAP_METRIC_LABELS[selection.metric]} on the map) instead.`,
    query,
    path: `explore${query === "" ? "" : `?${query}`}`,
  };
}
