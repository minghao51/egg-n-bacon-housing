import { useMemo } from "react";
import type {
  LeaderboardControlsState,
  LeaderboardDisplayRow,
  LeaderboardEntry,
  LeaderboardLegacyTimeBasis,
  LeaderboardTimeBasis,
} from "@/types/leaderboard";
import {
  LEADERBOARD_LEGACY_TIME_BASES,
  isLeaderboardLegacyTimeBasis,
} from "@/types/leaderboard";
import { useGzipJson } from "./useGzipJson";
import { useObservedPack } from "./useObservedPack";
import { DATA_URLS } from "@/constants/data-urls";
import { sectionKey } from "@/utils/observed-data";
import { publishedPeriodOptions } from "@/utils/observed-periods";
import {
  buildPackScopedRows,
  buildScopedRows,
  isScopedRankMetric,
  unsupportedMetricReason,
  type RankedScope,
} from "@/utils/leaderboard-observed";

/** Labels for the historical eras; published windows carry their own label. */
export const LEGACY_TIME_BASIS_LABELS: Record<
  LeaderboardLegacyTimeBasis,
  string
> = {
  recent: "2022 onward",
  whole: "All history",
  year_2025: "2025 complete year",
};

export interface LeaderboardDataResult {
  data: LeaderboardDisplayRow[];
  /** Areas the selected property/period does not publish. */
  unpublishedAreas: string[];
  rankedCount: number;
  unrankedCount: number;
  /** False when the scope may be read but not ranked (`limited-display`). */
  rankable: boolean;
  /** Human label for the active window, e.g. "12 months to 2026-10". */
  timeBasisLabel: string;
  /** The asset or payload the numbers came from. */
  sourceLabel: string;
  /** Coverage note that travels with a limited-display scope, or `null`. */
  windowNote: string | null;
  /** Why the selected window resolves to nothing, or `null` when it resolves. */
  windowUnavailable: string | null;
  /** True while a published window is still being verified in this request. */
  windowPending: boolean;
  /** Period choices for the control: published windows first, eras after. */
  timeBasisOptions: { value: LeaderboardTimeBasis; label: string }[];
  /** Why the selected metric cannot be ranked, or `null` when it can. */
  unsupportedReason: string | null;
  loading: boolean;
  error: string | null;
  refreshError: string | null;
  reload: () => void;
}

const EMPTY_SCOPE: RankedScope = {
  rows: [],
  unpublishedAreas: [],
  filteredOut: 0,
  rankedCount: 0,
  unrankedCount: 0,
  rankable: true,
};

/**
 * Observed ranking data for Compare Areas.
 *
 * Two sources, one row shape:
 *
 * - a legacy era (`recent`, `whole`, `year_2025`) reads the joint
 *   `map_metrics[era_property]` section as RF01 established;
 * - a concrete published period (`ttm_2026_10`, …) reads the v2 observed pack,
 *   which this hook verifies in the browser before any row is built.
 *
 * The leaderboard asset itself is only ever used for area identity, region
 * label and coordinates; no price, PSF or volume is read from it.
 *
 * A published window carries its own ratified disposition: only a `publish`
 * scope may be ranked, so EC/condo/All windows stay readable but unranked. An
 * unpublished or malformed id is reported instead of falling back to another
 * window.
 */
export function useLeaderboardData(
  controls: LeaderboardControlsState,
  initialData?: LeaderboardEntry[],
  initialMetrics?: unknown,
): LeaderboardDataResult {
  const leaderboard = useGzipJson<LeaderboardEntry[]>(
    DATA_URLS.leaderboard,
    "leaderboard",
    true,
    initialData ?? null,
  );
  const mapMetrics = useGzipJson<unknown>(
    DATA_URLS.mapMetrics,
    "map_metrics",
    true,
    initialMetrics ?? null,
  );
  const packLoad = useObservedPack();

  const legacyBasis = isLeaderboardLegacyTimeBasis(controls.timeBasis)
    ? controls.timeBasis
    : null;

  const metric = isScopedRankMetric(controls.rankMetric)
    ? controls.rankMetric
    : "median_price";

  const legacyScope = useMemo(() => {
    if (legacyBasis === null || !leaderboard.data || !mapMetrics.data) {
      return null;
    }
    return buildScopedRows({
      entries: leaderboard.data,
      mapMetrics: mapMetrics.data,
      era: legacyBasis,
      propertyType: controls.propertyType,
      metric,
      region: controls.region,
      priceRange: controls.priceRange,
      search: controls.search,
    });
  }, [legacyBasis, leaderboard.data, mapMetrics.data, controls, metric]);

  const packOutcome = useMemo(() => {
    if (
      legacyBasis !== null ||
      !leaderboard.data ||
      packLoad === null ||
      packLoad.state !== "ready"
    ) {
      return null;
    }
    return buildPackScopedRows({
      entries: leaderboard.data,
      pack: packLoad.pack,
      periodId: controls.timeBasis,
      propertyType: controls.propertyType,
      metric,
      region: controls.region,
      priceRange: controls.priceRange,
      search: controls.search,
    });
  }, [legacyBasis, leaderboard.data, packLoad, controls, metric]);

  const timeBasisOptions = useMemo(() => {
    const options: { value: LeaderboardTimeBasis; label: string }[] = [];
    if (packLoad !== null && packLoad.state === "ready") {
      for (const period of publishedPeriodOptions(packLoad.pack)) {
        options.push({ value: period.value, label: period.label });
      }
    }
    for (const basis of LEADERBOARD_LEGACY_TIME_BASES) {
      options.push({ value: basis, label: LEGACY_TIME_BASIS_LABELS[basis] });
    }
    return options;
  }, [packLoad]);

  const resolveWindow = (): Omit<
    LeaderboardDataResult,
    | "timeBasisOptions"
    | "unsupportedReason"
    | "loading"
    | "error"
    | "refreshError"
    | "reload"
  > => {
    if (legacyBasis !== null) {
      const scope = legacyScope ?? EMPTY_SCOPE;
      return {
        data: scope.rows,
        unpublishedAreas: scope.unpublishedAreas,
        rankedCount: scope.rankedCount,
        unrankedCount: scope.unrankedCount,
        rankable: true,
        timeBasisLabel: LEGACY_TIME_BASIS_LABELS[legacyBasis],
        sourceLabel: `map_metrics.${sectionKey(legacyBasis, controls.propertyType)}`,
        windowNote: null,
        windowUnavailable: null,
        windowPending: false,
      };
    }

    const empty = {
      data: [] as LeaderboardDisplayRow[],
      unpublishedAreas: [] as string[],
      rankedCount: 0,
      unrankedCount: 0,
      rankable: true,
      timeBasisLabel: controls.timeBasis,
      sourceLabel: "observed pack",
      windowNote: null,
      windowUnavailable: null,
      windowPending: false,
    };

    if (packLoad === null) {
      return {
        ...empty,
        windowPending: true,
      };
    }
    if (packLoad.state === "absent") {
      return {
        ...empty,
        windowUnavailable: `This build publishes no verified observed-period pack, so ${controls.timeBasis} cannot be shown here. The historical time bases above still resolve from map_metrics.`,
      };
    }
    if (packLoad.state === "invalid") {
      return {
        ...empty,
        windowUnavailable: `The published observed-period pack did not verify (${packLoad.errors.join("; ")}), so ${controls.timeBasis} is not shown.`,
      };
    }
    if (packOutcome === null) {
      return empty;
    }
    if (!packOutcome.ok) {
      return { ...empty, windowUnavailable: packOutcome.reason };
    }

    return {
      data: packOutcome.scope.rows,
      unpublishedAreas: packOutcome.scope.unpublishedAreas,
      rankedCount: packOutcome.scope.rankedCount,
      unrankedCount: packOutcome.scope.unrankedCount,
      rankable: packOutcome.scope.rankable,
      timeBasisLabel: packOutcome.periodLabel,
      sourceLabel: `observed pack · ${controls.timeBasis} · ${packLoad.manifest.generation}`,
      windowNote: packOutcome.note,
      windowUnavailable: null,
      windowPending: false,
    };
  };

  const reload = () => {
    void leaderboard.reload();
    void mapMetrics.reload();
  };

  return {
    ...resolveWindow(),
    timeBasisOptions,
    unsupportedReason: unsupportedMetricReason(controls.rankMetric),
    loading:
      (leaderboard.loading && !leaderboard.data) ||
      (mapMetrics.loading && !mapMetrics.data),
    error: leaderboard.error ?? mapMetrics.error,
    refreshError: leaderboard.refreshError ?? mapMetrics.refreshError,
    reload,
  };
}
