/**
 * Generic Gzip JSON Data Hook
 *
 * Reusable hook for loading gzipped JSON data with caching and error handling.
 * Cache, retry, refresh and abort decisions come from `@/utils/request-state`;
 * this module only applies them to React state and the network request.
 *
 * It also owns the verified-release path (`useVerifiedRelease` and the payload
 * store below): bytes that were hashed are kept, so a screen renders the
 * response it verified instead of fetching the same URL again (UI-1).
 */

import { useState, useEffect, useRef, useCallback } from "react";
import { fetchGzipJson } from "@/utils/gzip";
import { loadReleaseCheck, type ReleaseCheck } from "@/utils/release-manifest";
import {
  cacheKey as buildCacheKey,
  createRequestTracker,
  isCacheFresh,
  resolveLoadIntent,
  type LoadMode,
} from "@/utils/request-state";

interface UseGzipJsonResult<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  /** A background refresh failed while published data stays on screen. */
  refreshError: string | null;
  reload: (options?: { mode?: LoadMode }) => Promise<void>;
}

interface GzipJsonCache {
  data: unknown;
  storedAt: number;
  generation: string | null;
}

const globalCache = new Map<string, GzipJsonCache>();
const CACHE_TTL = 5 * 60 * 1000; // 5 minutes

/**
 * Publication generation used for cache keys (default: no generation).
 *
 * Read at request time only, so changing it never triggers a refetch by itself.
 */
let dataGeneration: string | null = null;

/**
 * Declare the current publication generation so cache keys include it.
 *
 * @param generation - Release/hash identity, or null when unknown
 */
export function setDataGeneration(generation: string | null): void {
  dataGeneration = generation;
}

/**
 * Generic hook for loading gzipped JSON data
 *
 * @param url - URL of the gzipped JSON file
 * @param cacheKey - Optional cache key (defaults to URL)
 * @param cacheEnabled - Whether to enable caching (default: true)
 * @param initialData - Optional data already rendered (e.g. server-side props)
 */
export function useGzipJson<T>(
  url: string,
  cacheKey?: string,
  cacheEnabled: boolean = true,
  initialData?: T | null,
): UseGzipJsonResult<T> {
  const [data, setData] = useState<T | null>(initialData ?? null);
  const [loading, setLoading] = useState(!initialData);
  const [error, setError] = useState<string | null>(null);
  const [refreshError, setRefreshError] = useState<string | null>(null);

  const dataRef = useRef<T | null>(initialData ?? null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const trackerRef = useRef(createRequestTracker());
  const mountedRef = useRef(true);

  const key = cacheKey || url;

  const load = useCallback(
    async (requestedMode?: LoadMode) => {
      const hasData = dataRef.current !== null;
      // A bare `reload()` re-fetches: refreshing when data is shown, retrying
      // when it is not.
      const mode: LoadMode = requestedMode ?? (hasData ? "refresh" : "retry");
      const generation = dataGeneration;
      const entryKey = buildCacheKey(key, generation);
      const cached = cacheEnabled ? globalCache.get(entryKey) : undefined;
      const cacheFresh =
        cacheEnabled && isCacheFresh(cached, Date.now(), CACHE_TTL);

      const intent = resolveLoadIntent({ mode, hasData, cacheFresh });

      if (intent.useCache && cached) {
        // Serving cache still supersedes any request already in flight.
        abortControllerRef.current?.abort();
        abortControllerRef.current = null;
        trackerRef.current.next();

        dataRef.current = cached.data as T;
        setData(cached.data as T);
        setLoading(false);
        setError(null);
        return;
      }

      abortControllerRef.current?.abort();

      const controller = new AbortController();
      abortControllerRef.current = controller;
      const token = trackerRef.current.next();

      // A superseded or unmounted request must not mutate state at all.
      const isActive = (): boolean =>
        mountedRef.current && trackerRef.current.isCurrent(token);

      if (intent.showLoading) {
        setLoading(true);
      }
      if (intent.surfaceError) {
        setError(null);
      }
      if (!hasData) {
        setRefreshError(null);
      }

      try {
        const result = await fetchGzipJson<T>(url, controller.signal);

        if (!isActive()) {
          return;
        }

        if (cacheEnabled) {
          globalCache.set(entryKey, {
            data: result,
            storedAt: Date.now(),
            generation,
          });
        }

        dataRef.current = result;
        setData(result);
        setLoading(false);
        setError(null);
        setRefreshError(null);
      } catch (err) {
        if (err instanceof Error && err.name === "AbortError") {
          return;
        }
        if (!isActive()) {
          return;
        }

        const message =
          err instanceof Error ? err.message : "Failed to load data";

        if (intent.clearDataOnFailure) {
          dataRef.current = null;
          setData(null);
        }
        if (intent.surfaceError) {
          setError(message);
        }
        if (mode === "refresh" && hasData) {
          setRefreshError(message);
        }
        setLoading(false);
      }
    },
    [url, key, cacheEnabled],
  );

  useEffect(() => {
    mountedRef.current = true;

    // Data already on screen (server props) is revalidated without blocking or
    // clearing; an empty first load fetches with a loading state.
    void load(dataRef.current !== null ? "refresh" : "initial");

    return () => {
      mountedRef.current = false;
      abortControllerRef.current?.abort();
      abortControllerRef.current = null;
      trackerRef.current.next();
    };
  }, [load, initialData]);

  const reload = useCallback(
    async (options?: { mode?: LoadMode }) => {
      await load(options?.mode);
    },
    [load],
  );

  return { data, loading, error, refreshError, reload };
}

/**
 * Clear global cache (useful for testing or force refresh)
 */
export function clearGzipCache(): void {
  globalCache.clear();
}

/**
 * A payload whose bytes were hashed in this session.
 *
 * `key` is the only key the payload can be read under, and it carries the
 * generation, so a payload verified for one release can never be served as
 * another release's payload.
 */
export interface VerifiedPayload {
  /** `<scope>::generation::<generation>` — one cache entry per generation. */
  key: string;
  /** Logical name of the asset, generation-free (for example `explore:map_metrics.json.gz`). */
  scope: string;
  /** The verified publication generation these bytes belong to. */
  generation: string;
  /** SHA-256 of exactly the bytes that were decoded into `data`. */
  sha256: string;
  /** SHA-256 of the decoded JSON text, when that is what matched. */
  contentSha256: string | null;
  /** Length of the response body those digests were taken from. */
  byteLength: number;
  /** The decoded payload, parsed from the same bytes. */
  data: unknown;
}

/** Verified payloads, keyed by generation-qualified scope. */
const verifiedPayloadStore = new Map<string, VerifiedPayload>();

/** Build the single, generation-qualified cache key for one payload. */
export function verifiedPayloadKey(scope: string, generation: string): string {
  return buildCacheKey(scope, generation);
}

/**
 * Store one verified payload under its generation-qualified key.
 *
 * Entries for any *other* generation of the same scope are dropped, so the
 * store holds at most one verified generation per asset and an older
 * generation can never be read back as the current one.
 */
export function rememberVerifiedPayload(payload: VerifiedPayload): void {
  for (const [key, entry] of verifiedPayloadStore) {
    if (entry.scope === payload.scope && key !== payload.key) {
      verifiedPayloadStore.delete(key);
    }
  }
  verifiedPayloadStore.set(payload.key, payload);
}

/**
 * Read a verified payload for an exact scope and generation.
 *
 * Returns `null` for any other generation: there is no wildcard read, so a
 * caller always has to name the generation it is about to display.
 */
export function readVerifiedPayload(
  scope: string,
  generation: string,
): VerifiedPayload | null {
  return (
    verifiedPayloadStore.get(verifiedPayloadKey(scope, generation)) ?? null
  );
}

/** Clear the verified-payload store (tests, or a forced reload). */
export function clearVerifiedPayloads(): void {
  verifiedPayloadStore.clear();
}

/** Options for {@link useVerifiedRelease}. */
export interface VerifiedReleaseOptions {
  /** URL of the `dashboard-release.json` manifest. */
  manifestUrl: string;
  /** Manifest path → URL for every asset this screen reads. */
  assetUrls: Record<string, string>;
  /** Manifest paths to verify (default: every asset the manifest lists). */
  verifyOnly?: string[];
  /** Cache-key scope for one asset path (default: `release:<path>`). */
  scopeFor?: (path: string) => string;
  /** Injectable `fetch` (tests); defaults to the global one. */
  fetcher?: typeof fetch;
}

/** What one verified-release load exposes to a screen. */
export interface VerifiedReleaseLoad {
  /** The verification result; `null` until the first load finishes. */
  check: ReleaseCheck | null;
  /** Exactly the payloads whose bytes verified, keyed by manifest path. */
  payloads: Record<string, VerifiedPayload>;
  loading: boolean;
  /** Why nothing verified (first-load failure). */
  error: string | null;
  /** Why a refresh did not verify; the previous payloads are gone, not stale. */
  refreshError: string | null;
  /** Re-run verification from scratch (fresh manifest and asset responses). */
  reload: () => Promise<void>;
}

function defaultScope(path: string): string {
  return `release:${path}`;
}

/** The result of one verified-release load. */
export interface VerifiedReleaseResult {
  check: ReleaseCheck;
  /** Exactly the payloads whose bytes verified, keyed by manifest path. */
  payloads: Record<string, VerifiedPayload>;
}

/**
 * Turn a verified check into generation-qualified payload entries.
 *
 * Every entry is stored under its generation and read back from there, so the
 * entries a screen renders are the cached ones. A non-verified check yields no
 * entries at all, so a rejected release can never reach a render.
 */
function verifiedPayloadsFor(
  check: ReleaseCheck,
  scopeFor: (path: string) => string,
): Record<string, VerifiedPayload> {
  const payloads: Record<string, VerifiedPayload> = {};
  if (check.status !== "verified" || check.manifest === null) return payloads;

  const generation = check.manifest.generation;
  for (const [path, evidence] of Object.entries(check.evidence)) {
    if (!(path in check.payloads)) continue;
    const scope = scopeFor(path);
    rememberVerifiedPayload({
      key: verifiedPayloadKey(scope, generation),
      scope,
      generation,
      sha256: evidence.sha256,
      contentSha256: evidence.contentSha256,
      byteLength: evidence.byteLength,
      data: check.payloads[path],
    });
    // Read back through the generation-qualified key, so what is rendered is
    // provably the cached entry for this generation.
    const stored = readVerifiedPayload(scope, generation);
    if (stored !== null) payloads[path] = stored;
  }
  return payloads;
}

/**
 * Verify a release once and return the payloads it verified.
 *
 * Framework-free: the hook below is a thin state wrapper over this, and the
 * unit tests drive exactly this path with a mocked `fetch`. Verification always
 * fetches the manifest and every requested asset once, and only the bytes that
 * matched a recorded digest are ever returned as payloads.
 */
export async function loadVerifiedRelease(
  options: VerifiedReleaseOptions,
): Promise<VerifiedReleaseResult> {
  let check: ReleaseCheck;
  try {
    check = await loadReleaseCheck({
      manifestUrl: options.manifestUrl,
      assetUrls: options.assetUrls,
      verifyOnly: options.verifyOnly,
      fetcher: options.fetcher,
    });
  } catch (err) {
    // Verification never throws, but a hostile environment might: nothing was
    // proven, so the honest status is `unverified`, never `mismatch`.
    check = {
      status: "unverified",
      manifest: null,
      mismatches: [
        `release verification failed: ${err instanceof Error ? err.message : String(err)}`,
      ],
      payloads: {},
      evidence: {},
    };
  }

  return {
    check,
    payloads: verifiedPayloadsFor(check, options.scopeFor ?? defaultScope),
  };
}

/**
 * Verify a release and expose the decoded bytes it verified.
 *
 * This is the one load path for the legacy dashboard assets: the manifest and
 * every requested asset are fetched once, hashed, and decoded here, and the
 * screen renders `payloads` rather than re-fetching the same URLs. A refresh
 * re-verifies before it replaces anything on screen, so a response that arrived
 * later can never be displayed under the earlier verification (UI-1).
 */
export function useVerifiedRelease(
  options: VerifiedReleaseOptions,
): VerifiedReleaseLoad {
  const [check, setCheck] = useState<ReleaseCheck | null>(null);
  const [payloads, setPayloads] = useState<Record<string, VerifiedPayload>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshError, setRefreshError] = useState<string | null>(null);

  const mountedRef = useRef(true);
  const trackerRef = useRef(createRequestTracker());
  const hasPayloadsRef = useRef(false);
  /** Latest options, so a re-render cannot leave the last request stale. */
  const latestRef = useRef(options);
  latestRef.current = options;

  // Depends on the option *values*, not object identity: an inline literal from
  // a parent render must not restart the request on every render.
  const signature = JSON.stringify([
    options.manifestUrl,
    Object.entries(options.assetUrls).sort(),
    options.verifyOnly ?? null,
  ]);

  const load = useCallback(async () => {
    const token = trackerRef.current.next();
    const isActive = (): boolean =>
      mountedRef.current && trackerRef.current.isCurrent(token);

    const current = latestRef.current;
    const hadPayloads = hasPayloadsRef.current;
    if (!hadPayloads) setLoading(true);
    setError(null);
    setRefreshError(null);

    const { check: result, payloads: nextPayloads } =
      await loadVerifiedRelease(current);

    if (!isActive()) return;

    const failure =
      result.status === "verified" ? null : (result.mismatches[0] ?? null);

    hasPayloadsRef.current = Object.keys(nextPayloads).length > 0;
    setCheck(result);
    setPayloads(nextPayloads);
    setLoading(false);
    if (failure !== null) {
      if (hadPayloads) setRefreshError(failure);
      else setError(failure);
    }
  }, [signature]);

  useEffect(() => {
    mountedRef.current = true;
    void load();

    return () => {
      mountedRef.current = false;
      trackerRef.current.next();
    };
  }, [load]);

  const reload = useCallback(async () => {
    await load();
  }, [load]);

  return { check, payloads, loading, error, refreshError, reload };
}
