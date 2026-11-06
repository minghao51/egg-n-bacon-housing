/**
 * Catalog audit observations (slice S9).
 *
 * The published catalog (`catalog.jsonl.gz`) is a *separate generation* from
 * the current platinum artifacts. The S0 audit compared one artifact with the
 * catalog metadata and found a different row count. Both numbers must stay
 * visible with their own labels: the catalog is never rewritten to match the
 * artifact, and the artifact count is never presented as catalog metadata.
 *
 * The observation below is a recorded audit finding, not a live pipeline read
 * (a static Astro build must not depend on local parquet files being present).
 * Provenance: docs/implementation/s0-baseline.md ("Catalog row count ...
 * belongs to a different snapshot than the current platinum").
 */

export interface CatalogAuditObservation {
  datasetId: string;
  /** Row count in the inspected platinum artifact. */
  inspectedRowCount: number;
  /** Repo-relative path of the inspected artifact. */
  inspectedArtifact: string;
  /** Where the observation was recorded. */
  recordedIn: string;
  note: string;
}

export const CATALOG_AUDIT: Readonly<Record<string, CatalogAuditObservation>> =
  {
    unified_dataset: {
      datasetId: "unified_dataset",
      inspectedRowCount: 1_234_928,
      inspectedArtifact: "data/pipeline/04_platinum/unified_dataset.parquet",
      recordedIn: "docs/implementation/s0-baseline.md",
      note: "The catalog was generated from an earlier snapshot. Neither count replaces the other, and no raw records are exposed.",
    },
  };

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
