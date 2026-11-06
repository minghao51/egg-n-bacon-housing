/**
 * Unit tests for the segment archive evidence contract
 * (src/components/dashboard/segments/lib/segment-evidence.ts).
 *
 * The point of this file is the cross-asset boundary: `segments_enhanced.json.gz`
 * is not part of the dashboard release manifest, so a segment surface may not
 * compare its numbers with dashboard medians. The test reads the *published*
 * manifest, so listing the archive there is a deliberate decision that fails
 * this test first.
 */

import { describe, expect, test } from "bun:test";
import { readFileSync } from "node:fs";

import {
  canCompareWithDashboardAssets,
  formatSegmentMetric,
  SEGMENT_ARCHIVE_NOTE,
  SEGMENT_ASSET_FILENAME,
  SEGMENT_GATED_NOTE,
  SEGMENT_INVESTIGATION_METRICS,
  SEGMENT_NOT_COMPARABLE_NOTE,
  segmentEvidenceStatus,
  segmentMetricEvidence,
} from "../../src/components/dashboard/segments/lib/segment-evidence";

interface ReleaseManifest {
  generation: string;
  assets: Array<{ path: string }>;
}

const manifest = JSON.parse(
  readFileSync(
    new URL("../../public/data/dashboard-release.json", import.meta.url),
    "utf8",
  ),
) as ReleaseManifest;

const manifestAssetPaths = manifest.assets.map((asset) => asset.path);

describe("published manifest boundary", () => {
  test("the dashboard release lists its seven dashboard assets", () => {
    expect(manifestAssetPaths).toHaveLength(7);
    expect(manifestAssetPaths).not.toContain(SEGMENT_ASSET_FILENAME);
  });

  test("the segment archive is unverified, so it cannot be cross-compared", () => {
    const status = segmentEvidenceStatus(manifestAssetPaths);
    expect(status).toBe("unverified-archive");
    expect(canCompareWithDashboardAssets(status)).toBe(false);
  });

  test("the gate is symmetric: listing the archive would flip the status", () => {
    const status = segmentEvidenceStatus([
      ...manifestAssetPaths,
      SEGMENT_ASSET_FILENAME,
    ]);
    expect(status).toBe("share-verified-generation");
    expect(canCompareWithDashboardAssets(status)).toBe(true);
  });

  test("the asset name the surface reads is the archive filename", () => {
    expect(SEGMENT_ASSET_FILENAME).toBe("segments_enhanced.json.gz");
  });
});

describe("field evidence", () => {
  test("only the stored average PSF is a non-gated field", () => {
    const open = SEGMENT_INVESTIGATION_METRICS.filter(
      (metric) => !segmentMetricEvidence(metric).gated,
    );
    expect(open).toEqual(["avgPricePsf"]);
  });

  test("every gated field carries a caveat that denies currentness", () => {
    SEGMENT_INVESTIGATION_METRICS.filter(
      (metric) => segmentMetricEvidence(metric).gated,
    ).forEach((metric) => {
      const evidence = segmentMetricEvidence(metric);
      expect(evidence.status).toBe("definition-unverified");
      expect(evidence.caveat.length).toBeGreaterThan(10);
      // `toMatch` is not in the shared `bun:test` ambient declarations
      // (tests/unit/bun-test.d.ts), so assert the pattern directly.
      expect(
        /not supplied|not a current|do not read|no supplied/.test(
          evidence.caveat.toLowerCase(),
        ),
      ).toBe(true);
    });
  });

  test("no metric label claims a current median", () => {
    SEGMENT_INVESTIGATION_METRICS.forEach((metric) => {
      expect(segmentMetricEvidence(metric).label.toLowerCase()).not.toContain(
        "median",
      );
    });
  });

  test("the shared copy names the manifest and the missing period", () => {
    expect(SEGMENT_NOT_COMPARABLE_NOTE).toContain("release manifest");
    expect(SEGMENT_ARCHIVE_NOTE.toLowerCase()).toContain("observation period");
    expect(SEGMENT_GATED_NOTE.toLowerCase()).toContain("not supplied");
  });
});

describe("formatSegmentMetric", () => {
  test("renders stored archive values with their unit", () => {
    expect(formatSegmentMetric(644, "avgPricePsf")).toBe("S$644");
    expect(formatSegmentMetric(5.54, "avgYield")).toBe("5.5%");
    expect(formatSegmentMetric(0.6, "persistenceProbability")).toBe("60.0%");
  });

  test("a missing value is N/A, never zero", () => {
    expect(formatSegmentMetric(null, "avgPricePsf")).toBe("N/A");
    expect(formatSegmentMetric(undefined, "mrtPremium")).toBe("N/A");
    expect(formatSegmentMetric(Number.NaN, "forecast6m")).toBe("N/A");
    expect(formatSegmentMetric(0, "avgPricePsf")).toBe("S$0");
  });
});
