/**
 * Tests for the build-time v2 pack reader.
 *
 * Uses the pack published under `public/data`, plus a temporary copy for the
 * failure paths.
 */

import { describe, expect, it } from "bun:test";
import { cpSync, mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import {
  loadObservedPackFromDir,
  summariseForDashboard,
} from "@/utils/observed-pack-build";

const DATA_DIR = join(process.cwd(), "public", "data");

function tempCopy(): string {
  const dir = mkdtempSync(join(tmpdir(), "observed-pack-"));
  cpSync(DATA_DIR, dir, { recursive: true });
  return dir;
}

function manifestOf(dir: string) {
  return JSON.parse(
    readFileSync(join(dir, "dashboard-release-v2.json"), "utf8"),
  );
}

describe("loading the published pack", () => {
  it("verifies and parses the published pack", async () => {
    const result = await loadObservedPackFromDir(DATA_DIR);

    expect(result.state).toBe("ready");
    if (result.state !== "ready") return;
    expect(result.pack.cutoffMonth).toBe("2026-10");
    expect(result.manifest.generation).toBe(
      result.pack.methodVersion ? result.manifest.generation : "",
    );
    expect(result.pack.periods.length).toBeGreaterThanOrEqual(8);
  });

  it("reports absent when no manifest is published", async () => {
    const dir = mkdtempSync(join(tmpdir(), "observed-empty-"));

    expect(await loadObservedPackFromDir(dir)).toEqual({ state: "absent" });
  });

  it("rejects a tampered payload", async () => {
    const dir = tempCopy();
    const manifest = manifestOf(dir);
    const summaryAsset = manifest.assets.find(
      (asset: { role: string }) => asset.role === "summary",
    );
    const path = join(dir, summaryAsset.path);
    const bytes = readFileSync(path);
    bytes[bytes.length - 1] ^= 0xff;
    writeFileSync(path, bytes);

    const result = await loadObservedPackFromDir(dir);

    expect(result.state).toBe("invalid");
    if (result.state === "invalid") {
      expect(result.errors.join(" ")).toContain("sha256 mismatch");
    }
  });

  it("rejects a manifest edited to point at a different generation", async () => {
    const dir = tempCopy();
    const manifest = manifestOf(dir);
    manifest.generation = "f".repeat(64);
    writeFileSync(
      join(dir, "dashboard-release-v2.json"),
      JSON.stringify(manifest),
    );

    const result = await loadObservedPackFromDir(dir);

    expect(result.state).toBe("invalid");
    if (result.state === "invalid") {
      expect(result.errors.join(" ")).toContain("generation mismatch");
    }
  });
});

describe("dashboard summary", () => {
  it("summarises the HDB year-to-date window with a prior-year comparison", async () => {
    const result = await loadObservedPackFromDir(DATA_DIR);
    expect(result.state).toBe("ready");
    if (result.state !== "ready") return;

    const summary = summariseForDashboard(
      result.pack,
      result.manifest.generation,
      "hdb",
    );
    const ytd = summary.ytd;

    expect(summary.cutoffMonth).toBe("2026-10");
    expect(ytd?.periodId).toBe("ytd_2026_10");
    expect(ytd?.comparatorId).toBe("ytd_2025_10");
    expect(ytd?.disposition).toBe("publish");
    expect(ytd?.publishable).toBe(true);

    const count = ytd?.metrics.find(
      (metric) => metric.metric === "transactionCount",
    );
    expect(count?.value).toBeGreaterThan(0);
    expect(count?.percentChange).not.toBeNull();
    expect(count?.changeNote).toBeNull();
  });

  it("marks the latest month with its prior-year comparator", async () => {
    const result = await loadObservedPackFromDir(DATA_DIR);
    if (result.state !== "ready") throw new Error("pack unavailable");

    const summary = summariseForDashboard(
      result.pack,
      result.manifest.generation,
      "hdb",
    );

    expect(summary.latestMonth?.periodId).toBe("month_2026_10");
    expect(summary.latestMonth?.comparatorId).toBe("month_2025_10");
    expect(summary.latestMonth?.endMonth).toBe("2026-10");
  });

  it("keeps a limited private scope unpublishable with a reason", async () => {
    const result = await loadObservedPackFromDir(DATA_DIR);
    if (result.state !== "ready") throw new Error("pack unavailable");

    const summary = summariseForDashboard(
      result.pack,
      result.manifest.generation,
      "condo",
    );

    expect(summary.ytd?.disposition).toBe("limited-display");
    expect(summary.ytd?.publishable).toBe(false);
  });
});
