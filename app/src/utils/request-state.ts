/**
 * Request State Model
 *
 * Pure, framework-free decisions for the gzip JSON fetch lifecycle:
 * cache/retry/refresh intent, cache freshness, cache keys and stale-request
 * tokens. Nothing here touches React, `window` or `fetch`, so the decisions can
 * be unit tested without a browser.
 */

/** How a load was requested: first mount, user retry without data, or re-fetch with data displayed. */
export type LoadMode = "initial" | "retry" | "refresh";

/** What a single load attempt is allowed to do, resolved from the mode and current state. */
export type LoadIntent = {
  useCache: boolean;
  bypassCache: boolean;
  showLoading: boolean;
  clearDataOnFailure: boolean;
  surfaceError: boolean;
};

/**
 * Resolve the intent for one load attempt.
 *
 * `initial` tries a fresh cache and otherwise fetches with a blocking loading
 * state; `retry` always bypasses the cache; `refresh` always bypasses the cache
 * and never hides or clears already displayed data.
 */
export function resolveLoadIntent(input: {
  mode: LoadMode;
  hasData: boolean;
  cacheFresh: boolean;
}): LoadIntent {
  const { mode, hasData, cacheFresh } = input;

  if (mode === "refresh") {
    return {
      useCache: false,
      bypassCache: true,
      showLoading: false,
      clearDataOnFailure: false,
      surfaceError: !hasData,
    };
  }

  const bypassCache = mode === "retry" || !cacheFresh;

  return {
    useCache: mode === "initial" && cacheFresh,
    bypassCache,
    showLoading: bypassCache,
    clearDataOnFailure: true,
    surfaceError: true,
  };
}

/**
 * Build a cache key for a URL, namespaced by publication generation when known.
 *
 * The same URL under two generations produces two distinct keys; without a
 * generation the URL (or caller supplied key) is returned unchanged.
 */
export function cacheKey(url: string, generation?: string | null): string {
  if (generation === undefined || generation === null || generation === "") {
    return url;
  }

  return `${url}::generation::${generation}`;
}

/** True when a cache entry is still within its TTL at `now` (fresh at exactly `ttlMs`). */
export function isCacheFresh(
  entry: { storedAt: number } | undefined,
  now: number,
  ttlMs: number,
): boolean {
  if (!entry) {
    return false;
  }

  return now - entry.storedAt <= ttlMs;
}

/** Opaque handle for one load attempt. */
export type RequestToken = number;

/**
 * Create a token tracker so a superseded resolution can be ignored.
 *
 * Every load takes `next()`; anything that would mutate state first checks
 * `isCurrent(token)` and drops the result when a newer request has started.
 */
export function createRequestTracker(): {
  next: () => RequestToken;
  isCurrent: (token: RequestToken) => boolean;
} {
  let current: RequestToken = 0;

  return {
    next: () => {
      current += 1;
      return current;
    },
    isCurrent: (token: RequestToken) => token === current,
  };
}
