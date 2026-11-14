/**
 * Catalog audit observations (slice S9, reconciled in RF11).
 *
 * The published catalog (`catalog.jsonl.gz`) is a *separate generation* from
 * the current platinum artifacts. Before RF11 the S0 audit compared one
 * artifact with the catalog metadata and found a different row count; RF11
 * regenerated the catalog from the current platinum build, so the two now agree
 * — and the earlier discrepancy stays recorded as evidence instead of being
 * deleted.
 *
 * These are recorded audit findings, not live pipeline reads (a static Astro
 * build must not depend on local parquet files being present). Each entry
 * carries the artifact hash it measured, because "same row count" is not the
 * same claim as "same bytes".
 *
 * Provenance: docs/implementation/2026-11-13-rf11-catalog-report.md (current)
 * and docs/implementation/s0-baseline.md (previous).
 */

export interface CatalogAuditObservation {
  datasetId: string;
  /** Row count in the inspected platinum artifact. */
  inspectedRowCount: number;
  /** Repo-relative path of the inspected artifact. */
  inspectedArtifact: string;
  /** sha256 of the inspected artifact bytes, first 16 hex characters. */
  inspectedArtifactSha256: string;
  /** Row count the catalog generation recorded for the same dataset. */
  catalogRowCount: number;
  /** Catalog generation time the comparison used, or `null` when unknown. */
  catalogGeneratedAt: string | null;
  /** Where the observation was recorded. */
  recordedIn: string;
  note: string;
}

export const CATALOG_AUDIT: Readonly<Record<string, CatalogAuditObservation>> =
  {
    unified_dataset: {
      datasetId: "unified_dataset",
      inspectedRowCount: 1_236_310,
      inspectedArtifact: "data/pipeline/04_platinum/unified_dataset.parquet",
      inspectedArtifactSha256: "39d234f703c9d6e0",
      catalogRowCount: 1_236_310,
      catalogGeneratedAt: "2026-11-14T04:51:14.764426+00:00",
      recordedIn: "docs/implementation/2026-11-13-rf11-catalog-report.md",
      note: "The catalog and the inspected artifact describe the same snapshot. Regenerated after the rental-yield rerun: `rental_yield` now records 1,749 rows instead of 3,623, while the inspected `unified_dataset` bytes and count did not change. The earlier disagreement stays recorded below rather than being deleted.",
    },
  };

/**
 * Earlier observations, preserved as evidence.
 *
 * RF11 regenerated the catalog, which resolved the S0 discrepancy; the finding
 * itself stays here so the reports can still cite what was true then.
 */
export const CATALOG_AUDIT_HISTORY: readonly CatalogAuditObservation[] = [
  {
    datasetId: "unified_dataset",
    inspectedRowCount: 1_234_928,
    inspectedArtifact: "data/pipeline/04_platinum/unified_dataset.parquet",
    inspectedArtifactSha256: "unknown: not recorded in the S0 baseline",
    catalogRowCount: 1_233_405,
    catalogGeneratedAt: "2026-09-12T08:05:07.301419+00:00",
    recordedIn: "docs/implementation/s0-baseline.md",
    note: "The catalog was generated from an earlier snapshot. Neither count replaced the other, and no raw records are exposed.",
  },
];

/** The audit observation for a dataset, or `null` when none was recorded. */
export function catalogAuditFor(
  datasetId: string,
): CatalogAuditObservation | null {
  return CATALOG_AUDIT[datasetId] ?? null;
}

/** Human-readable catalog generation time, or a fail-closed label. */
export function catalogGeneratedLabel(
  generatedAt: string | null | undefined,
): string {
  if (!generatedAt) return "generation time not supplied";
  const parsed = new Date(generatedAt);
  if (Number.isNaN(parsed.getTime())) return "generation time not supplied";
  return parsed.toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  });
}
