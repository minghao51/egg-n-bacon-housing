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
  CATALOG_AUDIT_HISTORY,
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
  test("the regenerated catalog and the artifact now agree", () => {
    expect(audit.datasetId).toBe("unified_dataset");
    expect(audit.inspectedRowCount).toBe(1_236_310);
    expect(catalogRowCount("unified_dataset")).toBe(audit.inspectedRowCount);
    expect(audit.catalogRowCount).toBe(audit.inspectedRowCount);
    expect(audit.inspectedArtifact.endsWith(".parquet")).toBe(true);
    expect(/^[0-9a-f]{16}$/.test(audit.inspectedArtifactSha256)).toBe(true);
    expect(audit.recordedIn).toContain("rf11");
    expect(audit.note).toContain("same snapshot");
  });

  test("the earlier S0 finding is preserved, not overwritten", () => {
    expect(CATALOG_AUDIT_HISTORY).toHaveLength(1);
    const previous = CATALOG_AUDIT_HISTORY[0]!;
    expect(previous.inspectedRowCount).toBe(1_234_928);
    expect(previous.catalogRowCount).toBe(1_233_405);
    expect(previous.inspectedRowCount).not.toBe(previous.catalogRowCount);
    expect(previous.recordedIn).toContain("s0-baseline");
    expect(previous.note).toContain("Neither count replaced the other");
    // The history entry is evidence, never the live comparison.
    expect(previous).not.toBe(audit);
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
