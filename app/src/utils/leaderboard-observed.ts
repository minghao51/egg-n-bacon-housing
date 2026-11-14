/**
 * Pure observed-area ranking adapter for Compare Areas (`/dashboard/leaderboard`).
 *
 * Contract (RF01, decisions D04–D06):
 * - Price, PSF and volume come from the joint `map_metrics[era_property]`
 *   section via `readAreaObservation`. The leaderboard asset's
 *   `by_property_type` / `by_time_period` / top-level fields are property-only
 *   or period-only margins and are never read here.
 * - Geography uses the five planning regions actually published by the release.
 *   An unrecognised label resolves to `null` and is reported, not guessed.
 * - A row is ranked only when the selected window has at least
 *   `SAMPLE_CAUTION_THRESHOLD` sales. Thin rows stay visible and unranked; the
 *   threshold is a product caution rule, not a significance test.
 * - Metrics the release cannot scope jointly are unsupported: callers show the
 *   reason instead of a substituted number.
 * - No React, DOM, fetch or file access — safe for units, islands and tests.
 */

import type {
  LeaderboardControlsState,
  LeaderboardDisplayRow,
  LeaderboardEntry,
  LeaderboardMetric,
  PlanningRegion,
} from "@/types/leaderboard";
import { PLANNING_REGIONS } from "@/types/leaderboard";
import {
  canonicalAreaId,
  readAreaObservation,
  type EraId,
} from "./observed-data";
import {
  findObservation,
  isObservedPeriodId,
  scopeNote,
  type ObservationDisposition,
  type PeriodPack,
  type PropertyTypeId,
} from "./observed-periods";

/** Minimum sales in the selected window before a row may be ranked. */
export const SAMPLE_CAUTION_THRESHOLD = 150;

/** Metrics that the published joint sections actually support. */
export const SCOPED_RANK_METRICS = [
  "median_price",
  "median_psf",
  "volume",
] as const;

export type ScopedRankMetric = (typeof SCOPED_RANK_METRICS)[number];

/** Why each remaining legacy metric cannot be ranked on this release. */
export const UNSUPPORTED_METRIC_REASONS: Record<
  Exclude<LeaderboardMetric, ScopedRankMetric>,
  string
> = {
  yoy_growth_pct:
    "Year-over-year growth is only published as a whole-population margin, not per property type and period.",
  mom_change_pct:
    "Month-over-month change is only published as a whole-population margin, not per property type and period.",
  momentum:
    "Momentum is derived from unscoped growth margins, so it has no joint property-and-period value.",
  rental_yield_mean:
    "Mean rental yield repeats the same area-level value across property types and its gross-proxy method is under review.",
  rental_yield_median:
    "Median rental yield repeats the same area-level value across property types and its gross-proxy method is under review.",
  affordability_ratio:
    "Affordability repeats the same area-level income reference across property types, so it is not a property-specific observation.",
};

export function isScopedRankMetric(
  metric: LeaderboardMetric,
): metric is ScopedRankMetric {
  return (SCOPED_RANK_METRICS as readonly string[]).includes(metric);
}

export function unsupportedMetricReason(
  metric: LeaderboardMetric,
): string | null {
  return isScopedRankMetric(metric) ? null : UNSUPPORTED_METRIC_REASONS[metric];
}

export function isPlanningRegion(value: string): value is PlanningRegion {
  return (PLANNING_REGIONS as readonly string[]).includes(value);
}

/** `EAST REGION` -> `EAST REGION`; `CCR` and other unmapped labels -> `null`. */
export function resolvePlanningRegion(
  value: string | null | undefined,
): PlanningRegion | null {
  if (typeof value !== "string") return null;
  const candidate = value.trim().toUpperCase();
  return isPlanningRegion(candidate) ? candidate : null;
}

export function isThinSample(volume: number | null): boolean {
  return volume === null || volume < SAMPLE_CAUTION_THRESHOLD;
}

export interface ScopedAreaMetrics {
  medianPrice: number | null;
  medianPsf: number | null;
  volume: number | null;
  status: "available" | "missing" | "empty";
  isThinSample: boolean;
}

function metricValue(
  record: ReturnType<typeof readAreaObservation>,
  metric: "median_price" | "median_psf" | "volume",
): number | null {
  if (record === null) return null;
  const observation = record.metrics.find((entry) => entry.metric === metric);
  return observation?.value ?? null;
}

/**
 * Read one area from the joint era x property section.
 *
 * Returns `null` when the section or the area is absent — the caller must treat
 * that as "not published for this scope", never as zero.
 */
export function readScopedAreaMetrics(
  mapMetrics: unknown,
  area: string,
  era: EraId,
  propertyType: LeaderboardControlsState["propertyType"],
): ScopedAreaMetrics | null {
  const record = readAreaObservation(mapMetrics, era, propertyType, area);
  if (record === null) return null;

  const medianPrice = metricValue(record, "median_price");
  const medianPsf = metricValue(record, "median_psf");
  const volume = metricValue(record, "volume");

  const status = record.metrics.some((entry) => entry.status === "available")
    ? "available"
    : record.metrics.every((entry) => entry.status === "empty")
      ? "empty"
      : "missing";

  return {
    medianPrice,
    medianPsf,
    volume,
    status,
    isThinSample: isThinSample(volume),
  };
}

export function scopedMetricValue(
  metrics: ScopedAreaMetrics,
  metric: ScopedRankMetric,
): number | null {
  if (metric === "median_price") return metrics.medianPrice;
  if (metric === "median_psf") return metrics.medianPsf;
  return metrics.volume;
}

function readMixVolume(
  mapMetrics: unknown,
  area: string,
  era: EraId,
  propertyType: "hdb" | "ec" | "condo",
): number | null {
  return (
    readScopedAreaMetrics(mapMetrics, area, era, propertyType)?.volume ?? null
  );
}

/**
 * Build the filtered, ranked rows for one legacy era x property scope from the
 * joint `map_metrics` section.
 *
 * Legacy eras are the labelled historical view, so they keep their existing
 * ranking behaviour; the publish/limited-display gate belongs to the ratified
 * v2 dispositions, which this asset does not carry.
 */
export function buildScopedRows(input: ScopedRankInput): RankedScope {
  const { mapMetrics, era, propertyType } = input;

  return buildRankRows(input, {
    rankable: true,
    readMetrics: (area) =>
      readScopedAreaMetrics(mapMetrics, area, era, propertyType),
    readMix: (area) => {
      const hdb = readMixVolume(mapMetrics, area, era, "hdb");
      const ec = readMixVolume(mapMetrics, area, era, "ec");
      const condo = readMixVolume(mapMetrics, area, era, "condo");
      if (hdb === null && ec === null && condo === null) return null;
      return { hdb, ec, condo, total: (hdb ?? 0) + (ec ?? 0) + (condo ?? 0) };
    },
  });
}

export interface ScopedRankInput {
  entries: readonly LeaderboardEntry[];
  /** Raw `map_metrics.json.gz` payload; `null` while it is still loading. */
  mapMetrics: unknown;
  era: EraId;
  propertyType: LeaderboardControlsState["propertyType"];
  metric: ScopedRankMetric;
  region: readonly PlanningRegion[];
  priceRange: readonly [number, number];
  search: string;
}

export interface ScopedRankResult {
  rows: LeaderboardDisplayRow[];
  /** Areas the selected property/period does not publish at all. */
  unpublishedAreas: string[];
  /** Areas dropped by the region / price / search filters. */
  filteredOut: number;
  rankedCount: number;
  unrankedCount: number;
}

/** A rank result plus whether ranking was allowed for the scope at all. */
export interface RankedScope extends ScopedRankResult {
  /**
   * False when the scope's ratified disposition forbids a rank
   * (`limited-display`): rows are then listed by name and every `rank` is null.
   */
  rankable: boolean;
}

/** How one window's metrics and property mix are read for an area. */
interface ScopedRowSource {
  readMetrics: (planningArea: string) => ScopedAreaMetrics | null;
  readMix: (planningArea: string) => LeaderboardDisplayRow["propertyMix"];
  rankable: boolean;
}

function matchesFilters(
  metrics: ScopedAreaMetrics,
  region: PlanningRegion | null,
  controls: Pick<ScopedRankInput, "region" | "priceRange" | "search">,
  planningArea: string,
): boolean {
  const regionActive = controls.region.length !== PLANNING_REGIONS.length;
  if (regionActive && (region === null || !controls.region.includes(region))) {
    return false;
  }

  const [minPrice, maxPrice] = controls.priceRange;
  if (metrics.medianPrice !== null) {
    if (metrics.medianPrice < minPrice || metrics.medianPrice > maxPrice) {
      return false;
    }
  }

  const query = controls.search.trim().toUpperCase();
  if (query && !planningArea.toUpperCase().includes(query)) {
    return false;
  }

  return true;
}

function compareQualified(
  a: { value: number; area: string },
  b: { value: number; area: string },
): number {
  if (b.value !== a.value) return b.value - a.value;
  return a.area.localeCompare(b.area);
}

function compareByArea(
  a: LeaderboardDisplayRow,
  b: LeaderboardDisplayRow,
): number {
  return a.planningArea.localeCompare(b.planningArea);
}

/**
 * Build the filtered, ranked rows for one joint scope.
 *
 * Ranking order: qualified rows by metric descending (area name breaks ties),
 * then thin/unranked rows by area name. `rank` is `null` for unranked rows.
 *
 * When the scope may not be ranked, every published row is returned in name
 * order with `rank: null` — the values stay readable, but the page cannot turn
 * them into a league table. The sample threshold is still reported so the
 * reader can see how many rows are thin.
 */
function buildRankRows(
  input: Omit<ScopedRankInput, "mapMetrics" | "era">,
  source: ScopedRowSource,
): RankedScope {
  const { entries, metric, region, priceRange, search } = input;

  const unpublishedAreas: string[] = [];
  const qualified: {
    value: number;
    area: string;
    row: LeaderboardDisplayRow;
  }[] = [];
  const unranked: LeaderboardDisplayRow[] = [];
  let filteredOut = 0;

  for (const entry of entries) {
    const areaKey = entry.planning_area.toUpperCase();
    const metrics = source.readMetrics(entry.planning_area);

    if (metrics === null) {
      unpublishedAreas.push(entry.planning_area);
      continue;
    }

    const areaRegion = resolvePlanningRegion(entry.region);
    if (
      !matchesFilters(
        metrics,
        areaRegion,
        { region, priceRange, search },
        entry.planning_area,
      )
    ) {
      filteredOut += 1;
      continue;
    }

    const value = scopedMetricValue(metrics, metric);
    const row: LeaderboardDisplayRow = {
      sourceEntry: entry,
      planningArea: entry.planning_area,
      areaKey,
      region: areaRegion,
      rank: null,
      rankMetric: metric,
      rankMetricValue: value,
      medianPrice: metrics.medianPrice,
      medianPsf: metrics.medianPsf,
      volume: metrics.volume,
      isThinSample: metrics.isThinSample,
      propertyMix: source.readMix(entry.planning_area),
    };

    if (source.rankable && value !== null && !metrics.isThinSample) {
      qualified.push({ value, area: entry.planning_area, row });
    } else {
      unranked.push(row);
    }
  }

  if (!source.rankable) {
    unranked.sort(compareByArea);
    return {
      rows: unranked,
      unpublishedAreas,
      filteredOut,
      rankedCount: 0,
      unrankedCount: unranked.length,
      rankable: false,
    };
  }

  qualified.sort(compareQualified);
  unranked.sort(compareByArea);

  const rows = [
    ...qualified.map((item, index) => ({ ...item.row, rank: index + 1 })),
    ...unranked,
  ];

  return {
    rows,
    unpublishedAreas,
    filteredOut,
    rankedCount: qualified.length,
    unrankedCount: unranked.length,
    rankable: true,
  };
}

/**
 * Read one area's metrics from the verified v2 pack.
 *
 * Returns `null` when the pack publishes no observation for that area, window
 * and property type — the caller reports the area as unpublished rather than
 * zero-filling it. A verified `no-sales` window keeps its `0` count with null
 * prices and is reported as `empty`, matching the legacy adapter's vocabulary.
 */
export function readPackAreaMetrics(
  pack: PeriodPack,
  area: string,
  periodId: string,
  propertyType: PropertyTypeId,
): ScopedAreaMetrics | null {
  const observation = findObservation(
    pack,
    canonicalAreaId(area),
    propertyType,
    periodId,
  );
  if (observation === null) return null;

  const medianPrice = observation.metrics.medianPrice.value;
  const medianPsf = observation.metrics.medianPsf.value;
  const volume = observation.metrics.transactionCount.value;

  const status: ScopedAreaMetrics["status"] =
    observation.status === "no-sales"
      ? "empty"
      : medianPrice !== null || medianPsf !== null || volume !== null
        ? "available"
        : "missing";

  return {
    medianPrice,
    medianPsf,
    volume,
    status,
    isThinSample: isThinSample(volume),
  };
}

/** Per-property volumes for one area in the same published window. */
function readPackMix(
  pack: PeriodPack,
  area: string,
  periodId: string,
): LeaderboardDisplayRow["propertyMix"] {
  const areaId = canonicalAreaId(area);
  const volumeFor = (propertyType: PropertyTypeId): number | null =>
    findObservation(pack, areaId, propertyType, periodId)?.metrics
      .transactionCount.value ?? null;

  const hdb = volumeFor("hdb");
  const ec = volumeFor("ec");
  const condo = volumeFor("condo");
  if (hdb === null && ec === null && condo === null) return null;
  return { hdb, ec, condo, total: (hdb ?? 0) + (ec ?? 0) + (condo ?? 0) };
}

export interface PackScopedRankInput {
  entries: readonly LeaderboardEntry[];
  /** Already-verified pack; the caller never passes an unverified payload. */
  pack: PeriodPack;
  /** Concrete published period id, e.g. `ttm_2026_10`. */
  periodId: string;
  propertyType: PropertyTypeId;
  metric: ScopedRankMetric;
  region: readonly PlanningRegion[];
  priceRange: readonly [number, number];
  search: string;
}

export type PackScopedRankOutcome =
  | {
      ok: true;
      scope: RankedScope;
      periodLabel: string;
      disposition: ObservationDisposition;
      /** Coverage note that travels with a limited-display scope, or `null`. */
      note: string | null;
    }
  | { ok: false; period: string; reason: string };

/**
 * Build the filtered rows for one property x published-period selection.
 *
 * The disposition is ratified per scope, so one observation settles it for the
 * section: `publish` scopes may be ranked, `limited-display` scopes may be read
 * with their dates but not ranked, and `withhold` publishes nothing. An
 * unpublished or malformed id is reported with the published list instead of
 * rendering another window.
 */
export function buildPackScopedRows(
  input: PackScopedRankInput,
): PackScopedRankOutcome {
  if (!isObservedPeriodId(input.periodId)) {
    return {
      ok: false,
      period: input.periodId,
      reason: `${input.periodId} is not a concrete observed-period id (for example ttm_2026_10).`,
    };
  }

  const period = input.pack.periodsById.get(input.periodId);
  if (period === undefined) {
    return {
      ok: false,
      period: input.periodId,
      reason: `This build does not publish a period with the id ${input.periodId}. Published periods: ${input.pack.periods
        .map((entry) => entry.id)
        .join(", ")}.`,
    };
  }

  const scopeObservation =
    findObservation(input.pack, "SG", input.propertyType, period.id) ??
    input.pack.observations.find(
      (observation) =>
        observation.periodId === period.id &&
        observation.propertyType === input.propertyType,
    ) ??
    null;

  const disposition: ObservationDisposition =
    scopeObservation?.disposition ?? "withhold";

  const scope = buildRankRows(input, {
    rankable: disposition === "publish",
    readMetrics: (area) =>
      readPackAreaMetrics(input.pack, area, period.id, input.propertyType),
    readMix: (area) => readPackMix(input.pack, area, period.id),
  });

  return {
    ok: true,
    scope,
    periodLabel: period.label,
    disposition,
    note: scopeObservation === null ? null : scopeNote(scopeObservation),
  };
}
