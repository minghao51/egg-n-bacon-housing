/**
 * Generic Gzip JSON Data Hook
 *
 * Reusable hook for loading gzipped JSON data with caching and error handling.
 * Cache, retry, refresh and abort decisions come from `@/utils/request-state`;
 * this module only applies them to React state and the network request.
 */

import { useState, useEffect, useRef, useCallback } from "react";
import { fetchGzipJson } from "@/utils/gzip";
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
