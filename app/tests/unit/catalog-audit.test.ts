/**
 * Drift guard for the recorded catalog audit observation (S9/S10).
 *
 * The catalog is a separate generation from the platinum artifact. These
 * assertions pin the two visible counts so regenerating either side forces an
 * explicit update to the constant, the page copy and the reports together.
 */

import { describe, expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import { gunzipSync } from "node:zlib";

import {
  CATALOG_AUDIT,
  catalogAuditFor,
  catalogGeneratedLabel,
} from "../../src/constants/catalog-audit";

const audit = CATALOG_AUDIT.unified_dataset;

function catalogRowCount(datasetId: string): number | null {
  const path = new URL("../../public/data/catalog.jsonl.gz", import.meta.url);
  const lines = gunzipSync(readFileSync(path))
    .toString("utf-8")
    .trim()
    .split("\n");
  for (const line of lines) {
    const entry = JSON.parse(line) as {
      id?: unknown;
      parquet?: { row_count?: unknown };
    };
    if (entry.id === datasetId) {
      return typeof entry.parquet?.row_count === "number"
        ? entry.parquet.row_count
        : null;
    }
  }
  return null;
}

describe("catalog audit", () => {
  test("records both generations and never collapses them", () => {
    expect(audit.datasetId).toBe("unified_dataset");
    expect(audit.inspectedRowCount).toBe(1_234_928);
    expect(catalogRowCount("unified_dataset")).toBe(1_233_405);
    expect(audit.inspectedRowCount).not.toBe(
      catalogRowCount("unified_dataset"),
    );
    expect(audit.inspectedArtifact.endsWith(".parquet")).toBe(true);
    expect(audit.recordedIn).toContain("s0-baseline");
    expect(audit.note).toContain("Neither count replaces the other");
  });

  test("lookup is exact and the date falls back closed", () => {
    expect(catalogAuditFor("unified_dataset")).toBe(audit);
    expect(catalogAuditFor("unknown_dataset")).toBeNull();
    expect(catalogGeneratedLabel("2026-09-12T00:00:00Z")).toBe("12 Sept 2026");
    expect(catalogGeneratedLabel(null)).toBe("generation time not supplied");
    expect(catalogGeneratedLabel("not-a-date")).toBe(
      "generation time not supplied",
    );
  });
});
