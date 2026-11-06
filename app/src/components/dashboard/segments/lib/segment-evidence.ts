/**
 * Evidence contract for the stored research segment archive.
 *
 * `segments_enhanced.json.gz` is **not** part of the dashboard release manifest
 * (`dashboard-release.json`), so it has no verified publication generation and
 * none of its numbers may be compared with the dashboard assets column of the
 * same release. This module is the single place that decides which fields are
 * safe to present and how; the UI reads it instead of hard-coding labels, and
 * `tests/unit/segment-evidence.test.ts` pins the contract against the real
 * published manifest.
 *
 * Status vocabulary:
 * - `stored-average`: a stored average that is still an archive value (the
 *   observation period and sample are not supplied by the asset).
 * - `definition-unverified`: a model output whose definition, units, cap or
 *   sample is not supplied. Inspectable, never a current recommendation.
 */

import type { SegmentInvestigationMetric } from "@/types/segments";

/** File name of the research asset this surface reads. */
export const SEGMENT_ASSET_FILENAME = "segments_enhanced.json.gz";

export type SegmentFieldStatus = "stored-average" | "definition-unverified";

export type SegmentEvidenceStatus =
  | "unverified-archive"
  | "share-verified-generation";

/**
 * Copy used wherever the archive is described. Kept in one place so a page
 * cannot claim a verified generation the asset does not have.
 */
export const SEGMENT_ARCHIVE_NOTE =
  "Stored research averages from the segment archive. The extraction time is not an observation period, and no sample count is supplied.";

export const SEGMENT_GATED_NOTE =
  "Yield, growth, forecast, MRT-premium and persistence fields come from the same archive. Their definitions, units, distance caps and observation periods are not supplied, so they are shown as stored archive fields - never as current recommendations or as comparable with dashboard medians.";

export const SEGMENT_NOT_COMPARABLE_NOTE =
  "This asset is not listed in the dashboard release manifest, so nothing here is compared with dashboard medians or counts. Open the observed explorer to switch evidence context explicitly.";

export interface SegmentMetricEvidence {
  key: SegmentInvestigationMetric;
  /** Label used in tables, maps and legends. */
  label: string;
  /** Unit shown next to the field, or null when the field is a count. */
  unit: string | null;
  status: SegmentFieldStatus;
  /** True when the field may not be shown as a current value. */
  gated: boolean;
  caveat: string;
}

const METRIC_EVIDENCE = {
  avgPricePsf: {
    key: "avgPricePsf",
    label: "Stored avg PSF",
    unit: "SGD/sqft",
    status: "stored-average",
    gated: false,
    caveat:
      "Stored average of the archive's planning-area values. Observation period and sample are not supplied, so this is not a 2025 filtered transaction median.",
  },
  avgYield: {
    key: "avgYield",
    label: "Stored avg yield",
    unit: "%",
    status: "definition-unverified",
    gated: true,
    caveat:
      "Rental-yield definition, period and sample are not supplied; inspectable only.",
  },
  forecast6m: {
    key: "forecast6m",
    label: "Stored 6M forecast",
    unit: "%",
    status: "definition-unverified",
    gated: true,
    caveat:
      "A historical archive forecast with no supplied model definition or vintage. Not a current prediction.",
  },
  mrtPremium: {
    key: "mrtPremium",
    label: "Stored MRT premium",
    unit: "SGD",
    status: "definition-unverified",
    gated: true,
    caveat:
      "Model units, baseline, distance cap and area scaling are not supplied; do not read as a current premium.",
  },
  persistenceProbability: {
    key: "persistenceProbability",
    label: "Stored persistence label",
    unit: "%",
    status: "definition-unverified",
    gated: true,
    caveat:
      "Stored confidence label from an unreproduced hotspot model; do not read as a probability of future returns.",
  },
} satisfies Record<SegmentInvestigationMetric, SegmentMetricEvidence>;

export const SEGMENT_INVESTIGATION_METRICS: readonly SegmentInvestigationMetric[] =
  [
    "avgPricePsf",
    "avgYield",
    "forecast6m",
    "mrtPremium",
    "persistenceProbability",
  ];

export function segmentMetricEvidence(
  metric: SegmentInvestigationMetric,
): SegmentMetricEvidence {
  return METRIC_EVIDENCE[metric];
}

/**
 * Format a stored archive value. Missing values stay `N/A` so an absent field
 * is never rendered as a plausible zero.
 */
export function formatSegmentMetric(
  value: number | null | undefined,
  metric: SegmentInvestigationMetric,
): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return "N/A";
  }
  switch (metric) {
    case "avgPricePsf":
    case "mrtPremium":
      return `S$${value.toFixed(0)}`;
    case "avgYield":
    case "forecast6m":
      return `${value.toFixed(1)}%`;
    case "persistenceProbability":
      return `${(value * 100).toFixed(1)}%`;
    default:
      return value.toFixed(1);
  }
}

/**
 * Evidence status of the segment archive for a given release manifest.
 *
 * The archive only leaves `unverified-archive` when the manifest lists it as a
 * published asset — which today it does not, and which is an owner decision
 * (see the decision register in `assets/svg/implementation-plan.md` §6).
 */
export function segmentEvidenceStatus(
  manifestAssetPaths: readonly string[],
): SegmentEvidenceStatus {
  return manifestAssetPaths.includes(SEGMENT_ASSET_FILENAME)
    ? "share-verified-generation"
    : "unverified-archive";
}

/** Cross-asset comparison is only legitimate inside one verified generation. */
export function canCompareWithDashboardAssets(
  status: SegmentEvidenceStatus,
): boolean {
  return status === "share-verified-generation";
}
