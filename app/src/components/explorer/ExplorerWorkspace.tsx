/**
 * `/explore` observed-comparison workspace.
 *
 * Owns four things and nothing else: the selection (initialised from the
 * address bar, written back with `replaceState`), the list/map/table view
 * choice, the two published assets the selection reads, and the
 * release-generation check that decides whether a national baseline may be
 * shown at all.
 *
 * The URL is read once, before the first commit, exactly like `/dashboard/map`
 * after the S1 fix — so a deep link is never overwritten by defaults. State is
 * never derived from `window` during render.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { useGzipJson } from "@/hooks/useGzipJson";
import {
  EXPLORER_DEFAULTS,
  parseExplorerSelection,
  serializeExplorerSelection,
  withSelection,
  type ExplorerSelection,
} from "@/utils/explorer-selection";
import { buildExplorerDataset } from "@/utils/observed-rows";
import {
  loadReleaseCheck,
  type ReleaseCheck,
  type ReleaseStatus,
} from "@/utils/release-manifest";
import ExplorerSettings from "./ExplorerSettings";
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
function readSelectionFromUrl(): ExplorerSelection {
  if (typeof window === "undefined") {
    // A server render shows the documented default; the client island
    // initialises from the real address bar.
    return EXPLORER_DEFAULTS;
  }
  return parseExplorerSelection(window.location.search);
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
}

/**
 * Release identity is resolved before any data is fetched, so the datasets are
 * cached under the verified generation rather than an unqualified URL key.
 */
export default function ExplorerWorkspace({
  mapMetricsUrl,
  overviewUrl,
  manifestUrl,
}: ExplorerWorkspaceProps) {
  const [releaseCheck, setReleaseCheck] = useState<ReleaseCheck | null>(null);

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
          setReleaseCheck({ status: "unverified", manifest: null, mismatches: [] });
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
    />
  );
}

function ExplorerData({
  mapMetricsUrl,
  overviewUrl,
  releaseCheck,
}: {
  mapMetricsUrl: string;
  overviewUrl: string;
  releaseCheck: ReleaseCheck;
}) {
  const [selection, setSelection] =
    useState<ExplorerSelection>(readSelectionFromUrl);
  const [view, setView] = useState<ExplorerViewKind>(readViewFromUrl);

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
    setSelection({ ...EXPLORER_DEFAULTS });
  }, []);

  const releaseStatus: ReleaseStatus = releaseCheck.status;

  const dataset = useMemo(
    () =>
      buildExplorerDataset({
        mapMetrics: mapMetrics.data,
        overviewStats: overview.data,
        selection,
        baselineCompatible: releaseStatus === "verified",
      }),
    [mapMetrics.data, overview.data, selection, releaseStatus],
  );

  // Keep the address bar in step with the selection and the view. A deep link
  // is already reflected in state, so the first run only rewrites the URL when
  // the selection serialises differently (the serialiser omits default values,
  // so an explicit `?property=hdb&period=year_2025` link is canonicalised
  // rather than treated as new state). Parameters this workspace does not own
  // are left untouched.
  useEffect(() => {
    if (typeof window === "undefined") return;

    const next = serializeExplorerSelection(selection);
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
  }, [selection, view]);

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
      {loadingData ? (
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

      {dataError !== null ? (
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

      {mapMetrics.data !== null ? (
        <>
          <div className="grid gap-6 lg:grid-cols-[280px_minmax(0,1fr)] lg:items-start lg:gap-8">
            <ExplorerSettings
              selection={selection}
              summary={{
                shown: dataset.filtered.length,
                total: dataset.totalAreas,
                thin: dataset.thinCount,
              }}
              onChange={update}
              onReset={reset}
            />
            <ExplorerView
              view={view}
              onViewChange={setView}
              dataset={dataset}
              selection={selection}
              releaseStatus={releaseStatus}
              nationalLoading={overview.loading && overview.data === null}
              nationalError={overview.error}
              onRetryNational={retryNational}
              onChange={update}
              onReset={reset}
            />
          </div>

          <footer className="mt-10 border-t border-border pt-4 text-xs text-muted-foreground">
            <p>
              Area values:{" "}
              <code className="font-mono">map_metrics.{dataset.section}</code>{" "}
              &mdash; one row per planning area in that joint period and
              property section.
            </p>
            {dataset.baselineCompatible && dataset.national !== null ? (
              <p className="mt-1">
                National value:{" "}
                <code className="font-mono">
                  dashboard_overview.stats.{dataset.section}
                </code>{" "}
                &mdash; read from the national aggregate, never computed from
                these area rows.
              </p>
            ) : null}
            {releaseStatus === "verified" ? (
              <p className="mt-1">
                Publication generation verified for{" "}
                <code className="font-mono">map_metrics</code> and{" "}
                <code className="font-mono">dashboard_overview</code> (the two
                assets this screen compares). The other dashboard files were not
                checked by this screen.
              </p>
            ) : (
              <p className="mt-1">
                Release generation could not be verified (status:{" "}
                {releaseStatus}). National comparison stays withheld until one
                publication generation is proven.
              </p>
            )}
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
