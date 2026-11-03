/**
 * Unit tests for the pure request/cache lifecycle model.
 *
 * Run with: bun test tests/unit/request-state.test.ts
 */

import { describe, expect, it } from "bun:test";
import {
  cacheKey,
  createRequestTracker,
  isCacheFresh,
  resolveLoadIntent,
  type RequestToken,
} from "../../src/utils/request-state";

describe("resolveLoadIntent", () => {
  it("uses a fresh cache for an initial load without showing loading", () => {
    const intent = resolveLoadIntent({
      mode: "initial",
      hasData: false,
      cacheFresh: true,
    });

    expect(intent.useCache).toBe(true);
    expect(intent.bypassCache).toBe(false);
    expect(intent.showLoading).toBe(false);
  });

  it("bypasses a stale cache for an initial load and shows loading", () => {
    const intent = resolveLoadIntent({
      mode: "initial",
      hasData: false,
      cacheFresh: false,
    });

    expect(intent.useCache).toBe(false);
    expect(intent.bypassCache).toBe(true);
    expect(intent.showLoading).toBe(true);
    expect(intent.clearDataOnFailure).toBe(true);
    expect(intent.surfaceError).toBe(true);
  });

  it("never uses the cache for a retry, even when it is fresh", () => {
    const intent = resolveLoadIntent({
      mode: "retry",
      hasData: false,
      cacheFresh: true,
    });

    expect(intent.useCache).toBe(false);
    expect(intent.bypassCache).toBe(true);
    expect(intent.showLoading).toBe(true);
  });

  it("refreshes displayed data without blocking loading or clearing on failure", () => {
    const intent = resolveLoadIntent({
      mode: "refresh",
      hasData: true,
      cacheFresh: true,
    });

    expect(intent.useCache).toBe(false);
    expect(intent.bypassCache).toBe(true);
    expect(intent.showLoading).toBe(false);
    expect(intent.clearDataOnFailure).toBe(false);
    expect(intent.surfaceError).toBe(false);
  });

  it("surfaces a refresh error when nothing is displayed", () => {
    const intent = resolveLoadIntent({
      mode: "refresh",
      hasData: false,
      cacheFresh: false,
    });

    expect(intent.surfaceError).toBe(true);
    expect(intent.clearDataOnFailure).toBe(false);
  });
});

describe("cacheKey", () => {
  it("differs per generation and is stable for the same inputs", () => {
    const url = "/data/dashboard_leaderboard.json.gz";

    const first = cacheKey(url, "gen-a");
    const firstAgain = cacheKey(url, "gen-a");
    const second = cacheKey(url, "gen-b");
    const noGeneration = cacheKey(url);

    expect(first).toBe(firstAgain);
    expect(first).not.toBe(second);
    expect(first).not.toBe(noGeneration);
    expect(noGeneration).not.toBe(second);
    expect(first).toContain(url);
  });

  it("treats an absent or empty generation as no generation", () => {
    const url = "leaderboard";

    expect(cacheKey(url)).toBe(url);
    expect(cacheKey(url, null)).toBe(url);
    expect(cacheKey(url, undefined)).toBe(url);
    expect(cacheKey(url, "")).toBe(url);
  });
});

describe("isCacheFresh", () => {
  it("is fresh at exactly the ttl and stale one millisecond later", () => {
    const ttl = 5 * 60 * 1000;
    const storedAt = 1_000_000;
    const entry = { storedAt };

    expect(isCacheFresh(entry, storedAt, ttl)).toBe(true);
    expect(isCacheFresh(entry, storedAt + ttl, ttl)).toBe(true);
    expect(isCacheFresh(entry, storedAt + ttl + 1, ttl)).toBe(false);
  });

  it("treats a missing entry as stale", () => {
    expect(isCacheFresh(undefined, 1_000, 5_000)).toBe(false);
  });
});

describe("createRequestTracker", () => {
  it("makes an older token stale once a newer request starts", () => {
    const tracker = createRequestTracker();

    const oldToken = tracker.next();
    expect(tracker.isCurrent(oldToken)).toBe(true);

    const newToken = tracker.next();
    expect(tracker.isCurrent(newToken)).toBe(true);
    expect(tracker.isCurrent(oldToken)).toBe(false);
  });

  it("ignores an old result that resolves after a new request starts", () => {
    const tracker = createRequestTracker();
    const applied: string[] = [];

    // Only the current request may mutate state.
    const apply = (token: RequestToken, value: string): void => {
      if (!tracker.isCurrent(token)) {
        return;
      }
      applied.push(value);
    };

    const oldToken = tracker.next();
    const newToken = tracker.next();

    apply(newToken, "new");
    apply(oldToken, "old"); // stale resolution arriving late

    expect(applied).toEqual(["new"]);
  });
});
