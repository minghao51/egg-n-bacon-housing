/**
 * `/explore` observed-comparison workspace.
 *
 * Owns four things and nothing else: the selection (initialised from the
 * address bar, written back with `replaceState`), the list/map/table view
 * choice, the published assets the selection reads, and the release-generation
 * checks that decide whether a national baseline may be shown at all.
 *
 * Two data sources, one selection:
 *
 * - a legacy era (`whole`, `pre_covid`, `recent`, `year_2025`) reads
 *   `map_metrics.json.gz` plus `dashboard_overview.json.gz` and keeps its
 *   generation check;
 * - a concrete published period (`ttm_2026_10`, …) reads the v2 observed pack,
 *   which this island verifies itself (manifest, sizes, sha256, period parser)
 *   before building a row. An unpublished id is reported, never swapped for a
 *   different window.
 *
 * The URL is read once, before the first commit, exactly like `/dashboard/map`
 * after the S1 fix — so a deep link is never overwritten by defaults. State is
 * never derived from `window` during render.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import PublishedWindowsPanel from "@/components/observed/PublishedWindowsPanel";
import type { WindowsByType } from "@/utils/observed-pack-build";
import { type PackLoad } from "@/utils/observed-pack-loader";
import { useObservedPack } from "@/hooks/useObservedPack";
import { useGzipJson } from "@/hooks/useGzipJson";
import {
  EXPLORER_DEFAULTS,
  isConcretePeriod,
  isLegacyPeriod,
  parseExplorerSelection,
  serializeExplorerSelection,
  withSelection,
  type ExplorerPackPeriod,
  type ExplorerSelection,
} from "@/utils/explorer-selection";
import { buildPackExplorerDataset } from "@/utils/explorer-pack-rows";
import { publishedPeriodOptions } from "@/utils/observed-periods";
import {
  buildExplorerDataset,
  type ExplorerDataset,
} from "@/utils/observed-rows";
import {
  loadReleaseCheck,
  type ReleaseCheck,
  type ReleaseStatus,
} from "@/utils/release-manifest";
import ExplorerSettings, {
  explorerPeriodGroups,
  type ExplorerPeriodGroup,
} from "./ExplorerSettings";
import ExplorerView, {
  EXPLORER_VIEW_QUERY_KEY,
  parseExplorerView,
  serializeExplorerView,
  type ExplorerViewKind,
} from "./ExplorerView";

/**
 * Query keys this workspace owns. Mirrors the selection the serializer emits;
 * used only to drop a stale key of our own (for example `search` after a reset)
 * without touching parameters owned by other surfaces.
 */
const EXPLORER_QUERY_KEYS: readonly (keyof ExplorerSelection)[] = [
  "property",
  "period",
  "metric",
  "sort",
  "direction",
  "minSales",
  "search",
  "area",
  "page",
];

/** Read the incoming selection once, before the first render commit. */
function readSelectionFromUrl(
  defaultPeriodId: ExplorerPackPeriod | null,
): ExplorerSelection {
  if (typeof window === "undefined") {
    // A server render shows the documented default; the client island
    // initialises from the real address bar.
    return defaultPeriodId === null
      ? EXPLORER_DEFAULTS
      : { ...EXPLORER_DEFAULTS, period: defaultPeriodId };
  }

  const parsed = parseExplorerSelection(window.location.search);
  if (defaultPeriodId === null) return parsed;
  // Only a bare URL adopts the new default: an explicit `?period=` is the
  // reader's choice, whatever the default is.
  const hasPeriod = new URLSearchParams(window.location.search).has("period");
  return hasPeriod ? parsed : { ...parsed, period: defaultPeriodId };
}

/**
 * The "updated default" notice is for readers who arrived on a bare URL, and
 * only when a default actually moved. An explicit window never earns it.
 */
function readDefaultMigration(
  defaultPeriodId: ExplorerPackPeriod | null,
  previous: { label: string; query: string } | null,
): { label: string; query: string } | null {
  if (defaultPeriodId === null || previous === null) return null;
  if (typeof window === "undefined") return null;
  const params = new URLSearchParams(window.location.search);
  return params.has("period") ? null : previous;
}

/**
 * The view lives beside the selection, not inside it: `explorer-selection.ts`
 * owns the filter state its parsers and tests pin, and the representation is a
 * presentation choice with the same "unknown value falls back to the default"
 * rule. A server render shows the default; the client reads the address bar.
 */
function readViewFromUrl(): ExplorerViewKind {
  if (typeof window === "undefined") return "list";
  return parseExplorerView(
    new URLSearchParams(window.location.search).get(EXPLORER_VIEW_QUERY_KEY),
  );
}

export interface ExplorerWorkspaceProps {
  mapMetricsUrl: string;
  overviewUrl: string;
  manifestUrl: string;
  /** Verified v2 windows; absent when no pack is published. */
  publishedWindows?: WindowsByType | null;
  observedCutoff?: { cutoffMonth: string; generation: string } | null;
  /** D03's bare-URL default while `PUBLIC_OBSERVED_RELEASE=v2`; else `null`. */
  observedDefault?: { periodId: string; label: string } | null;
  /** The window a bare URL used to open on, for the migration notice. */
  previousDefault?: { label: string; query: string } | null;
}

/**
 * Release identity is resolved before any data is fetched, so the datasets are
 * cached under the verified generation rather than an unqualified URL key.
 */
export default function ExplorerWorkspace({
  mapMetricsUrl,
  overviewUrl,
  manifestUrl,
  publishedWindows = null,
  observedCutoff = null,
  observedDefault = null,
  previousDefault = null,
}: ExplorerWorkspaceProps) {
  const [releaseCheck, setReleaseCheck] = useState<ReleaseCheck | null>(null);
  // `null` while the pack is still being verified; the v2 payloads are hashed
  // in this request, so nothing is rendered from an unverified response.
  const packLoad = useObservedPack();

  useEffect(() => {
    let cancelled = false;
    const assetUrls: Record<string, string> = {
      "map_metrics.json.gz": mapMetricsUrl,
      "dashboard_overview.json.gz": overviewUrl,
    };

    void loadReleaseCheck({
      manifestUrl,
      assetUrls,
      verifyOnly: Object.keys(assetUrls),
    })
      .then((check) => {
        if (!cancelled) setReleaseCheck(check);
      })
      .catch(() => {
        if (!cancelled) {
          setReleaseCheck({
            status: "unverified",
            manifest: null,
            mismatches: [],
          });
        }
      });

    return () => {
      cancelled = true;
    };
  }, [manifestUrl, mapMetricsUrl, overviewUrl]);

  if (releaseCheck === null) {
    return (
      <p
        role="status"
        className="mt-8 rounded-lg border border-border bg-card p-6 text-sm text-muted-foreground"
      >
        Checking whether the published assets share one generation&hellip;
        National comparison is withheld until that is known.
      </p>
    );
  }

  return (
    <ExplorerData
      mapMetricsUrl={mapMetricsUrl}
      overviewUrl={overviewUrl}
      releaseCheck={releaseCheck}
      packLoad={packLoad}
      publishedWindows={publishedWindows}
      observedCutoff={observedCutoff}
      observedDefault={observedDefault}
      previousDefault={previousDefault}
    />
  );
}

function ExplorerData({
  mapMetricsUrl,
  overviewUrl,
  releaseCheck,
  packLoad,
  publishedWindows,
  observedCutoff,
  observedDefault,
  previousDefault,
}: {
  mapMetricsUrl: string;
  overviewUrl: string;
  releaseCheck: ReleaseCheck;
  packLoad: PackLoad | null;
  publishedWindows: WindowsByType | null;
  observedCutoff: { cutoffMonth: string; generation: string } | null;
  observedDefault: { periodId: string; label: string } | null;
  previousDefault: { label: string; query: string } | null;
}) {
  const defaultPeriodId =
    observedDefault !== null && isConcretePeriod(observedDefault.periodId)
      ? observedDefault.periodId
      : null;

  const [selection, setSelection] = useState<ExplorerSelection>(() =>
    readSelectionFromUrl(defaultPeriodId),
  );
  const [view, setView] = useState<ExplorerViewKind>(readViewFromUrl);
  const [defaultMigration] = useState(() =>
    readDefaultMigration(defaultPeriodId, previousDefault),
  );

  /**
   * The defaults this route actually uses. In v2 mode the bare URL opens on a
   * published window, so a legacy selection must stay in the address bar;
   * comparing against the legacy constant would drop it and a reload would
   * silently switch the reader's window.
   */
  const activeDefaults = useMemo<ExplorerSelection>(
    () =>
      defaultPeriodId === null
        ? EXPLORER_DEFAULTS
        : { ...EXPLORER_DEFAULTS, period: defaultPeriodId },
    [defaultPeriodId],
  );

  const generationKey =
    releaseCheck.status === "verified" && releaseCheck.manifest !== null
      ? releaseCheck.manifest.generation
      : `${releaseCheck.status}-unverified`;

  const mapMetrics = useGzipJson<unknown>(
    mapMetricsUrl,
    `explore:map_metrics:${generationKey}`,
  );
  const overview = useGzipJson<unknown>(
    overviewUrl,
    `explore:dashboard_overview:${generationKey}`,
  );

  const update = useCallback((patch: Partial<ExplorerSelection>) => {
    setSelection((current) => withSelection(current, patch));
  }, []);

  const reset = useCallback(() => {
    setSelection(
      defaultPeriodId === null
        ? { ...EXPLORER_DEFAULTS }
        : { ...EXPLORER_DEFAULTS, period: defaultPeriodId },
    );
  }, [defaultPeriodId]);

  const releaseStatus: ReleaseStatus = releaseCheck.status;

  const period = selection.period;
  const legacyPeriod = isLegacyPeriod(period) ? period : null;

  // The legacy builder only runs for a legacy era; a published period never
  // falls back to `map_metrics`. Both builders share `finaliseExplorerRows`,
  // so ordering, the sample threshold and the search behave identically.
  const legacyDataset = useMemo(
    () =>
      legacyPeriod === null
        ? null
        : buildExplorerDataset({
            mapMetrics: mapMetrics.data,
            overviewStats: overview.data,
            selection: {
              property: selection.property,
              period: legacyPeriod,
              minSales: selection.minSales,
              search: selection.search,
              sort: selection.sort,
              direction: selection.direction,
            },
            baselineCompatible: releaseStatus === "verified",
          }),
    [legacyPeriod, mapMetrics.data, overview.data, selection, releaseStatus],
  );

  const packResult = useMemo(
    () =>
      legacyPeriod !== null || packLoad === null || packLoad.state !== "ready"
        ? null
        : buildPackExplorerDataset({
            pack: packLoad.pack,
            generation: packLoad.manifest.generation,
            periodId: period,
            property: selection.property,
            minSales: selection.minSales,
            search: selection.search,
            sort: selection.sort,
            direction: selection.direction,
          }),
    [legacyPeriod, packLoad, period, selection],
  );

  /**
   * What the selected window resolves to. `unavailable` is a first-class
   * state: an unpublished id is reported with the id and the published list,
   * not replaced by another window's numbers.
   */
  type WindowView =
    | { state: "ready"; dataset: ExplorerDataset }
    | { state: "pending"; message: string }
    | { state: "unavailable"; message: string };

  let windowView: WindowView;
  if (legacyDataset !== null) {
    windowView = { state: "ready", dataset: legacyDataset };
  } else if (packLoad === null) {
    windowView = {
      state: "pending",
      message: `Verifying the published ${period} window against its manifest\u2026`,
    };
  } else if (packLoad.state === "absent") {
    windowView = {
      state: "unavailable",
      message: `This build publishes no verified observed-period pack, so ${period} cannot be shown here. The historical windows below still resolve from map_metrics.`,
    };
  } else if (packLoad.state === "invalid") {
    windowView = {
      state: "unavailable",
      message: `The published observed-period pack did not verify (${packLoad.errors.join("; ")}), so ${period} is not shown. The historical windows below still resolve from map_metrics.`,
    };
  } else if (packResult !== null && !packResult.ok) {
    windowView = { state: "unavailable", message: packResult.reason };
  } else if (packResult !== null && packResult.ok) {
    windowView = { state: "ready", dataset: packResult.dataset };
  } else {
    windowView = {
      state: "pending",
      message: `Reading the published ${period} window\u2026`,
    };
  }

  /**
   * Period choices: the pack's published descriptors first (when this build has
   * a verified pack), then the legacy eras as their own labelled group.
   */
  const periodGroups: readonly ExplorerPeriodGroup[] = useMemo(
    () =>
      explorerPeriodGroups(
        packLoad !== null && packLoad.state === "ready"
          ? publishedPeriodOptions(packLoad.pack)
          : [],
      ),
    [packLoad],
  );

  // Keep the address bar in step with the selection and the view. A deep link
  // is already reflected in state, so the first run only rewrites the URL when
  // the selection serialises differently (the serialiser omits default values,
  // so an explicit `?property=hdb&period=year_2025` link is canonicalised
  // rather than treated as new state). Parameters this workspace does not own
  // are left untouched.
  useEffect(() => {
    if (typeof window === "undefined") return;

    const next = serializeExplorerSelection(selection, activeDefaults);
    const url = new URL(window.location.href);
    let changed = false;

    for (const key of EXPLORER_QUERY_KEYS) {
      if (!next.has(key) && url.searchParams.has(key)) {
        url.searchParams.delete(key);
        changed = true;
      }
    }
    next.forEach((value, key) => {
      if (url.searchParams.get(key) !== value) {
        url.searchParams.set(key, value);
        changed = true;
      }
    });

    // `view` is not part of the selection, so it is written (or dropped when it
    // is the default) here rather than in the selection serialiser.
    const nextView = serializeExplorerView(view);
    const currentView = url.searchParams.get(EXPLORER_VIEW_QUERY_KEY);
    if (nextView === null) {
      if (currentView !== null) {
        url.searchParams.delete(EXPLORER_VIEW_QUERY_KEY);
        changed = true;
      }
    } else if (currentView !== nextView) {
      url.searchParams.set(EXPLORER_VIEW_QUERY_KEY, nextView);
      changed = true;
    }

    if (!changed) return;
    window.history.replaceState({}, "", url.toString());
  }, [selection, view, activeDefaults]);

  // Back/forward: the URL is the source of truth, so re-apply it.
  useEffect(() => {
    if (typeof window === "undefined") return;

    const handlePopState = () => {
      setSelection(parseExplorerSelection(window.location.search));
      setView(readViewFromUrl());
    };

    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  const loadingData = mapMetrics.loading && mapMetrics.data === null;
  const dataError = mapMetrics.error;

  const reloadMapMetrics = mapMetrics.reload;
  const reloadOverview = overview.reload;

  const retryAll = useCallback(() => {
    void reloadMapMetrics();
    void reloadOverview();
  }, [reloadMapMetrics, reloadOverview]);

  const retryNational = useCallback(() => {
    void reloadOverview();
  }, [reloadOverview]);

  return (
    <div className="mt-8">
      {defaultMigration !== null && observedDefault !== null ? (
        <p
          className="mt-8 rounded-lg border border-border bg-muted px-4 py-3 text-sm text-foreground"
          data-observed-default-notice="true"
        >
          <span className="font-bold">Updated default.</span> This page now
          opens on {observedDefault.label}. The earlier default was{" "}
          {defaultMigration.label} &mdash;{" "}
          <a
            href={`${import.meta.env.BASE_URL.replace(/\/$/, "")}/explore?${defaultMigration.query}`}
            className="font-bold text-[hsl(var(--teal))] underline underline-offset-4 hover:no-underline"
          >
            open that view
          </a>
          .
        </p>
      ) : null}

      {publishedWindows && observedCutoff ? (
        <PublishedWindowsPanel
          windows={publishedWindows}
          series={selection.property}
          cutoffMonth={observedCutoff.cutoffMonth}
          generation={observedCutoff.generation}
          intro={
            legacyPeriod === null
              ? `National figures for the published windows. The area table below reads the same verified pack for the window you select, and the historical eras stay listed separately.`
              : `National figures for the published windows. The area table below compares planning areas on the legacy era selection, which is labelled separately.`
          }
        />
      ) : null}

      {legacyPeriod !== null && loadingData ? (
        <div
          role="status"
          aria-live="polite"
          className="rounded-lg border border-border bg-card p-6 text-sm text-muted-foreground"
        >
          <p className="font-bold text-foreground">
            Loading published transaction data
          </p>
          <p className="mt-2">
            Reading <code className="font-mono">map_metrics</code>
            &hellip;
          </p>
        </div>
      ) : null}

      {legacyPeriod !== null && dataError !== null ? (
        <div
          role="alert"
          className="rounded-lg border border-border bg-card p-6 text-sm"
        >
          <p className="font-bold text-foreground">
            The observed transaction data could not be loaded
          </p>
          <p className="mt-2 text-muted-foreground">{dataError}</p>
          <button
            type="button"
            onClick={retryAll}
            className="mt-3 rounded border border-input px-3 py-2 font-bold text-foreground"
          >
            Try again
          </button>
        </div>
      ) : null}

      {legacyPeriod === null || mapMetrics.data !== null ? (
        <>
          <div className="grid gap-6 lg:grid-cols-[280px_minmax(0,1fr)] lg:items-start lg:gap-8">
            <ExplorerSettings
              selection={selection}
              periodGroups={periodGroups}
              summary={
                windowView.state === "ready"
                  ? {
                      shown: windowView.dataset.filtered.length,
                      total: windowView.dataset.totalAreas,
                      thin: windowView.dataset.thinCount,
                    }
                  : null
              }
              onChange={update}
              onReset={reset}
            />
            {windowView.state === "ready" ? (
              <ExplorerView
                view={view}
                onViewChange={setView}
                dataset={windowView.dataset}
                selection={selection}
                releaseStatus={releaseStatus}
                nationalLoading={overview.loading && overview.data === null}
                nationalError={overview.error}
                onRetryNational={retryNational}
                onChange={update}
                onReset={reset}
              />
            ) : (
              <div
                role={windowView.state === "pending" ? "status" : "alert"}
                className="rounded-lg border border-border bg-card p-6 text-sm"
              >
                <p className="font-bold text-foreground">
                  {windowView.state === "pending"
                    ? `Checking the published ${period} window`
                    : `${period} is not available in this build`}
                </p>
                <p className="mt-2 text-muted-foreground">
                  {windowView.message}
                </p>
              </div>
            )}
          </div>

          <footer className="mt-10 border-t border-border pt-4 text-xs text-muted-foreground">
            {windowView.state === "ready" &&
            windowView.dataset.kind === "pack" ? (
              <>
                <p>
                  Area values: the verified{" "}
                  <code className="font-mono">observed pack</code> &mdash;{" "}
                  <code className="font-mono">
                    {windowView.dataset.periodId}
                  </code>{" "}
                  ({windowView.dataset.label}), generation{" "}
                  <code className="font-mono">
                    {windowView.dataset.generation}
                  </code>{" "}
                  &mdash; one row per planning area, read from the payload this
                  page verified.
                </p>
                <p className="mt-1">
                  National value: the pack's own{" "}
                  <code className="font-mono">SG</code> scope for the same
                  window &mdash; read from the national aggregate, never
                  computed from these area rows.
                </p>
                <p className="mt-1">
                  The manifest, payload sizes and sha256 digests were checked
                  before these numbers were read. The legacy{" "}
                  <code className="font-mono">map_metrics</code> assets were not
                  used for this view.
                </p>
              </>
            ) : null}
            {windowView.state === "ready" &&
            windowView.dataset.kind === "legacy" ? (
              <>
                <p>
                  Area values:{" "}
                  <code className="font-mono">
                    map_metrics.{windowView.dataset.section}
                  </code>{" "}
                  &mdash; one row per planning area in that joint period and
                  property section.
                </p>
                {windowView.dataset.baselineCompatible &&
                windowView.dataset.national !== null ? (
                  <p className="mt-1">
                    National value:{" "}
                    <code className="font-mono">
                      dashboard_overview.stats.{windowView.dataset.section}
                    </code>{" "}
                    &mdash; read from the national aggregate, never computed
                    from these area rows.
                  </p>
                ) : null}
                {releaseStatus === "verified" ? (
                  <p className="mt-1">
                    Publication generation verified for{" "}
                    <code className="font-mono">map_metrics</code> and{" "}
                    <code className="font-mono">dashboard_overview</code> (the
                    two assets this screen compares). The other dashboard files
                    were not checked by this screen.
                  </p>
                ) : (
                  <p className="mt-1">
                    Release generation could not be verified (status:{" "}
                    {releaseStatus}). National comparison stays withheld until
                    one publication generation is proven.
                  </p>
                )}
              </>
            ) : null}
            <p className="mt-1">
              Observed sale records from the published snapshot, not asking
              prices, live listings or a valuation.
            </p>
          </footer>
        </>
      ) : null}
    </div>
  );
}
