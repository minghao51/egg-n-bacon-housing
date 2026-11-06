/**
 * Evidence contract for the four-tool workspace (slice S8).
 *
 * One module owns every caveat string, every archive-status decision and the
 * lease endpoint/label inspection, so no tool component invents a claim the
 * assets cannot support. The UI reads this module instead of hard-coding copy,
 * and `tests/unit/tool-evidence.test.ts` pins the contract against the real
 * published assets.
 *
 * Status vocabulary:
 * - `illustrative-arithmetic`: deterministic user-input arithmetic; no model,
 *   and no eligibility or recommendation claim.
 * - `stored-archive`: a stored statistic from an archive asset whose period,
 *   sample or extraction date is not supplied.
 * - `withheld`: a value the current model contract cannot support, shown as an
 *   explicit unavailable state rather than an estimate.
 */

import type { LeaseAsset, LeaseBand, MrtAsset } from "./tool-assets";

export type ToolId = "financing" | "lease" | "mrt" | "spatial";

/** Archive assets this workspace reads (none is in the release manifest). */
export const TOOL_ASSET_FILENAMES = {
  lease: "lease_decay_analysis.json.gz",
  mrt: "mrt_cbd_impact.json.gz",
  spatial: "spatial_hotspots.json.gz",
} as const;

export type ArchiveToolId = keyof typeof TOOL_ASSET_FILENAMES;

export type ToolArchiveStatus =
  | "unverified-archive"
  | "share-verified-generation";

/**
 * Research-asset status against a release manifest's asset paths.
 *
 * These assets only leave `unverified-archive` when `dashboard-release.json`
 * lists them, which it does not today. Listing one is an owner decision, not a
 * UI change.
 */
export function toolArchiveStatus(
  manifestAssetPaths: readonly string[],
  tool: ArchiveToolId,
): ToolArchiveStatus {
  return manifestAssetPaths.includes(TOOL_ASSET_FILENAMES[tool])
    ? "share-verified-generation"
    : "unverified-archive";
}

/** True when every archive tool asset shares the dashboard generation. */
export function toolAssetsVerified(
  manifestAssetPaths: readonly string[],
): boolean {
  return (Object.keys(TOOL_ASSET_FILENAMES) as ArchiveToolId[]).every(
    (tool) =>
      toolArchiveStatus(manifestAssetPaths, tool) ===
      "share-verified-generation",
  );
}

export const TOOL_ARCHIVE_LABEL =
  "Archive extraction · observation period, sample and model definition are not supplied";

export const TOOL_ARCHIVE_NOTE =
  "These research assets are not listed in the dashboard release manifest, so nothing here is compared with dashboard medians or counts. Open the observed explorer to switch evidence context explicitly.";

/* ------------------------------------------------------------------ *
 * Financing (illustrative arithmetic)
 * ------------------------------------------------------------------ */

export const FINANCING_ILLUSTRATIVE_NOTE =
  "The price is an observed aggregate from the published snapshot. Income and loan assumptions are illustrative user inputs, not household records.";

export const FINANCING_NOT_OFFER_NOTE =
  "Not a loan offer. Not an eligibility check. Excludes fees, insurance, taxes and grants, and no CPF, MSR or TDSR determination is made.";

export const FINANCING_LOCAL_NOTE =
  "Loan and income inputs stay in this browser tab: they are not written to the URL, analytics or logs. Reloading restores the named reference price, not your edits.";

export const FINANCING_REFERENCE_NOTE =
  "The reference price is copied from one joint 2025 section of map_metrics. Choosing another area or property type imports that area's published median; typing a different price stops applying the reference.";

/* ------------------------------------------------------------------ *
 * Lease bands (stored archive statistics)
 * ------------------------------------------------------------------ */

export const LEASE_LOOKUP_NOTE =
  "Lookup, not a fitted decay curve. Bands are stored statistics with an unknown extraction date and period, and their discounts are not monotonic in remaining lease.";

export const LEASE_SIGNED_NOTE =
  "Signed percentage: a negative value means the stored band statistic is a premium relative to the archive baseline, not a discount. It is not a projected loss or gain.";

export const LEASE_ENDPOINT_POLICY_NOTE =
  "The stored bands share endpoints and the archive resolves a shared endpoint with a first-match rule over its stored order. Which band a boundary year belongs to is therefore ambiguous; the workspace preserves the archive's first match and names every band that contains the year.";

export const LEASE_RISK_LABEL_NOTE =
  "The stored risk labels conflict with the archive's own insight prose and do not follow remaining-lease order. The workspace shows them as stored labels and withholds any safe/cliff recommendation until the source is reconciled.";

export const LEASE_WITHHELD_NOTE =
  "No projected price, loss or “best value” recommendation is shown. Those would require a repaired band definition (half-open intervals, extraction period and sample) that this archive does not supply.";

export interface LeaseLookup {
  /** The band the archive's first-match rule selects. */
  band: LeaseBand;
  /** Every stored band containing this year, in stored order. */
  matchingBands: LeaseBand[];
  /** True when the year is an endpoint of more than one stored band. */
  sharedEndpoint: boolean;
}

/**
 * Resolve remaining lease to a stored band using the archive's own rule:
 * inclusive `min_lease_years <= year <= max_lease_years`, first match in the
 * asset's stored order. The ambiguity is exposed, not silently resolved.
 */
export function selectLeaseBand(
  bands: readonly LeaseBand[],
  remainingYears: number,
): LeaseLookup | null {
  if (!Number.isFinite(remainingYears)) return null;
  const matchingBands = bands.filter(
    (band) =>
      remainingYears >= band.min_lease_years &&
      remainingYears <= band.max_lease_years,
  );
  if (matchingBands.length === 0) return null;

  const [band] = matchingBands;
  return {
    band,
    matchingBands,
    sharedEndpoint:
      matchingBands.length > 1 &&
      matchingBands.some(
        (entry) =>
          entry.min_lease_years === remainingYears ||
          entry.max_lease_years === remainingYears,
      ),
  };
}

export interface LeaseGap {
  from: number;
  to: number;
}

/**
 * Remaining-lease ranges inside the stored domain that no band covers.
 * The published asset has a gap between its shortest band and the rest.
 */
export function leaseCoverageGaps(bands: readonly LeaseBand[]): LeaseGap[] {
  if (bands.length === 0) return [];
  const min = Math.min(...bands.map((band) => band.min_lease_years));
  const max = Math.max(...bands.map((band) => band.max_lease_years));
  const gaps: LeaseGap[] = [];

  let cursor = min;
  const sorted = [...bands].sort(
    (a, b) => a.min_lease_years - b.min_lease_years,
  );
  for (const band of sorted) {
    if (band.min_lease_years > cursor) {
      gaps.push({ from: cursor, to: band.min_lease_years });
    }
    cursor = Math.max(cursor, band.max_lease_years);
  }
  if (cursor < max) gaps.push({ from: cursor, to: max });
  return gaps;
}

/**
 * Stored labels that contradict the archive's own interval order or its
 * insight prose. Returns human-readable findings; empty when consistent.
 */
export function leaseLabelConflicts(asset: LeaseAsset): string[] {
  const conflicts: string[] = [];
  const safe = asset.bands.filter((band) => band.risk_zone === "safe");
  const cliff = asset.bands.filter((band) => band.risk_zone === "cliff");

  if (safe.length > 0 && cliff.length > 0) {
    const highestCliff = Math.max(...cliff.map((band) => band.max_lease_years));
    const lowestSafe = Math.min(...safe.map((band) => band.min_lease_years));
    if (lowestSafe < highestCliff) {
      conflicts.push(
        "The shortest remaining-lease band is labelled “safe” while bands with more remaining lease are labelled “cliff”.",
      );
    }
  }

  const safeZone = asset.insights.safe_zone;
  if (safeZone !== null) {
    const impliedFloor = /(\d{2,3})\+/.exec(safeZone.band);
    if (impliedFloor !== null) {
      const floor = Number(impliedFloor[1]);
      const band = selectLeaseBand(asset.bands, floor)?.band ?? null;
      if (band !== null && band.risk_zone !== "safe") {
        conflicts.push(
          `The insight text calls ${safeZone.band} the safe zone, while the band covering ${floor} years is stored as “${band.risk_zone}”.`,
        );
      }
    }
  }

  const maturity = asset.insights.maturity_cliff;
  if (maturity !== null && maturity.band !== "Not supplied") {
    const numbers = maturity.band.match(/\d{1,3}/g);
    if (numbers !== null && numbers.length >= 2) {
      const from = Number(numbers[0]);
      const to = Number(numbers[1]);
      const overlapping = asset.bands.filter(
        (band) => band.max_lease_years >= from && band.min_lease_years <= to,
      );
      if (
        overlapping.length > 0 &&
        overlapping.every((band) => band.risk_zone !== "cliff")
      ) {
        conflicts.push(
          `The insight text calls ${maturity.band} the maturity cliff, while no overlapping stored band is labelled “cliff”.`,
        );
      }
    }
  }

  return conflicts;
}

/* ------------------------------------------------------------------ *
 * MRT / CBD (withheld model)
 * ------------------------------------------------------------------ */

/** The archive's own stop in the stored formula; not a validated cap. */
export const MRT_STORED_DISTANCE_CAP_METRES = 500;
/** The archive's implicit floor-area multiplier in the stored formula. */
export const MRT_STORED_IMPLICIT_SQFT = 1000;

export const MRT_WITHHELD_NOTE =
  "Total-dollar premium is withheld. The stored formula multiplies a S$ per 100 m coefficient by 1,000 without declaring a floor-area basis, and its distance direction conflicts with the CBD term.";

export const MRT_DIRECTION_NOTE =
  "The stored formula increases the “premium” as distance to MRT grows, then stops changing above 500 m. It does not declare whether the distance means proximity or a change in distance, so neither direction can be presented as a finding.";

export const MRT_UNIT_NOTE =
  "Coefficients are shown exactly as supplied: a stored premium per 100 m (S$) and a stored CBD rate per km (S$). Neither declares a floor-area denominator, so they are not S$ per square foot.";

export const MRT_TOWN_KEY_NOTE =
  "Town keys are normalised before lookup. The stored key is uppercase; a title-case label resolves to the same canonical key and never to a fallback multiplier.";

export const MRT_FLOOR_AREA_NOTE =
  "Floor area is the S8 explicit input the archive never had. It is recorded so the missing basis is visible, but this archive cannot apply it — no total is computed from it.";

export const MRT_NO_FALLBACK_NOTE =
  "If a town or property-type coefficient is missing, the tool shows an unavailable state. It never substitutes a default coefficient that would look like matched area data.";

/** Canonical stored town key: trimmed, single-spaced, uppercase. */
export function normalizeTownKey(input: string): string {
  return input.trim().replace(/\s+/g, " ").toUpperCase();
}

/**
 * Resolve an input label to the asset's own key. Returns `null` when no key
 * matches, so a caller cannot fall back to a default multiplier.
 */
export function resolveTownKey(
  townMultipliers: Readonly<Record<string, number>>,
  input: string,
): string | null {
  const canonical = normalizeTownKey(input);
  if (canonical === "") return null;
  const match = Object.keys(townMultipliers).find(
    (key) => normalizeTownKey(key) === canonical,
  );
  return match ?? null;
}

export interface MrtStoredTerms {
  typeKey: string;
  typeCoefficient: { premium_per_100m: number; cbd_per_km: number } | null;
  townKey: string | null;
  townMultiplier: number | null;
  /** `premium_per_100m × town_multiplier`, as the archive's own town block. */
  effectivePremiumPer100m: number | null;
  distanceMetres: number | null;
  /** `min(distance, 500)` — the archive's silent stop. */
  appliedDistanceMetres: number | null;
  cbdKm: number | null;
  /** The MRT premium term with this scenario's numbers substituted. */
  formula: string | null;
  /**
   * The CBD term with this scenario's numbers substituted. It is disclosed
   * separately and never added to the MRT term, because the stored units and
   * distance direction are unresolved.
   */
  cbdFormula: string | null;
}

/**
 * Substitute the fixed assumptions into the stored formula **as written**.
 * This exists to disclose the model, not to produce a price effect.
 */
export function mrtStoredTerms(
  asset: MrtAsset,
  typeKey: string,
  townInput: string,
  distanceMetres: number | null,
  cbdKm: number | null,
): MrtStoredTerms {
  const typeCoefficient = asset.property_type_multipliers[typeKey] ?? null;
  const townKey = resolveTownKey(asset.town_multipliers, townInput);
  const townMultiplier =
    townKey === null ? null : asset.town_multipliers[townKey];
  const effectivePremiumPer100m =
    typeCoefficient === null || townMultiplier === null
      ? null
      : typeCoefficient.premium_per_100m * townMultiplier;
  const appliedDistanceMetres =
    distanceMetres === null
      ? null
      : Math.min(distanceMetres, MRT_STORED_DISTANCE_CAP_METRES);

  const formula =
    effectivePremiumPer100m !== null && appliedDistanceMetres !== null
      ? `(${appliedDistanceMetres} ÷ 100) × ${effectivePremiumPer100m} × ${MRT_STORED_IMPLICIT_SQFT}`
      : null;
  const cbdFormula =
    typeCoefficient !== null && cbdKm !== null
      ? `(${cbdKm} km × ${typeCoefficient.cbd_per_km} per km)`
      : null;

  return {
    typeKey,
    typeCoefficient,
    townKey,
    townMultiplier,
    effectivePremiumPer100m,
    distanceMetres,
    appliedDistanceMetres,
    cbdKm,
    formula,
    cbdFormula,
  };
}

/* ------------------------------------------------------------------ *
 * Spatial patterns (label inspection only)
 * ------------------------------------------------------------------ */

export const SPATIAL_ARCHIVE_NOTE =
  "Stored spatial labels from the archive. Sample size, analysis date and method are not supplied, and persistence is a stored label, not a probability of future returns.";

export const SPATIAL_LABEL_NOTE =
  "Cluster labels are reconstructed only from validated fields (towns[]). No five-year or per-square-foot figure is derived from a total price, and an undefined-period change is never compounded into an annual rate.";

export const SPATIAL_WITHHELD_NOTE =
  "Portfolio allocation, BUY/SELL prompts and return simulations are withheld. They need an independently reviewed source and model contract before this workspace may show them.";

export const SPATIAL_NO_AGGREGATE_NOTE =
  "The published snapshot supplies town records only. It has no aggregate clusters[] block, no analysis date and no methodology field, so no cluster-level average is displayed.";
