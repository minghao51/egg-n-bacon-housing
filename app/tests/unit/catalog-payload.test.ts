/**
 * Unit tests for the S10-F1 catalog projections
 * (`src/utils/catalog-payload.ts`).
 *
 * The `/catalog` islands used to receive every parsed dataset, which put 825 kB
 * of SSR props on the page. These tests pin both halves of the fix: the
 * projections carry only the fields each island renders, and the serialised
 * result is materially smaller than the catalog they came from.
 */

import { describe, expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import { gunzipSync } from "node:zlib";

import { parseCatalog, type CatalogDataset } from "../../src/types/catalog";
import { dagEdges, dagNodes, tableRows } from "../../src/utils/catalog-payload";

const catalog = parseCatalog(
  gunzipSync(
    readFileSync(
      new URL("../../public/data/catalog.jsonl.gz", import.meta.url),
    ),
  ).toString("utf-8"),
);

function bytes(value: unknown): number {
  return Buffer.byteLength(JSON.stringify(value), "utf8");
}

describe("catalog table rows", () => {
  test("carry only the six rendered fields", () => {
    const rows = tableRows(catalog.datasets);
    expect(rows).toHaveLength(catalog.datasets.length);
    expect(Object.keys(rows[0]).sort()).toEqual([
      "bytes",
      "columnCount",
      "hasSchema",
      "id",
      "label",
      "layer",
      "rowCount",
      "status",
    ]);
    // No schema fields, parquet columns, descriptions or lineage are shipped.
    const serialised = JSON.stringify(rows);
    expect(serialised).not.toContain("parquet_type");
    expect(serialised).not.toContain("upstream");
    expect(serialised).not.toContain('"fields"');
  });

  test("preserve catalog order and values", () => {
    const rows = tableRows(catalog.datasets);
    for (const [index, dataset] of catalog.datasets.entries()) {
      const row = rows[index];
      expect(row.id).toBe(dataset.id);
      expect(row.label).toBe(dataset.label);
      expect(row.layer).toBe(dataset.layer);
      expect(row.status).toBe(dataset.status);
      expect(row.rowCount).toBe(dataset.parquet?.row_count ?? null);
      expect(row.columnCount).toBe(dataset.parquet?.column_count ?? null);
      expect(row.bytes).toBe(dataset.parquet?.file_size_bytes ?? null);
      expect(row.hasSchema).toBe(dataset.schema !== null);
    }
  });

  test("an unobserved parquet stays null rather than becoming zero", () => {
    const synthetic: CatalogDataset = {
      type: "dataset",
      id: "no_parquet",
      layer: "bronze",
      label: "No parquet",
      description: "synthetic",
      status: "missing",
      parquet: null,
      schema: null,
      lineage: { upstream: [], downstream: [] },
    };
    const [row] = tableRows([synthetic]);
    expect(row.rowCount).toBeNull();
    expect(row.columnCount).toBeNull();
    expect(row.bytes).toBeNull();
    expect(row.hasSchema).toBe(false);
  });

  test("is a projection: the source datasets are not mutated", () => {
    const before = JSON.stringify(catalog.datasets[0]);
    tableRows(catalog.datasets);
    dagNodes(catalog.datasets);
    dagEdges(catalog.edges);
    expect(JSON.stringify(catalog.datasets[0])).toBe(before);
  });
});

describe("catalog DAG projections", () => {
  test("nodes keep id, layer and label in catalog order", () => {
    const nodes = dagNodes(catalog.datasets);
    expect(nodes).toHaveLength(catalog.datasets.length);
    expect(Object.keys(nodes[0]).sort()).toEqual(["id", "label", "layer"]);
    for (const [index, dataset] of catalog.datasets.entries()) {
      expect(nodes[index]).toEqual({
        id: dataset.id,
        layer: dataset.layer,
        label: dataset.label,
      });
    }
  });

  test("edges keep every endpoint pair in catalog order", () => {
    const edges = dagEdges(catalog.edges);
    expect(edges).toHaveLength(catalog.edges.length);
    // Tuples, not objects: the pair is positional and both entries are strings.
    for (const [index, edge] of catalog.edges.entries()) {
      expect(edges[index]).toEqual([edge.from, edge.to]);
    }
    // Every endpoint is a dataset id, so the graph can still link each node.
    const ids = new Set(catalog.datasets.map((dataset) => dataset.id));
    expect(edges.every(([from, to]) => ids.has(from) && ids.has(to))).toBe(
      true,
    );
  });
});

describe("catalog payload size", () => {
  test("is materially smaller than the full catalog records", () => {
    const rows = tableRows(catalog.datasets);
    const nodes = dagNodes(catalog.datasets);
    const edges = dagEdges(catalog.edges);

    const rowBytes = bytes(rows);
    const nodeBytes = bytes(nodes);
    const edgeBytes = bytes(edges);
    const fullBytes = bytes(catalog.datasets) + bytes(catalog.edges);

    // Bounds chosen against the published snapshot (21.0 kB / 10.4 kB /
    // 125.1 kB) with headroom for a modest data refresh.
    expect(rowBytes).toBeLessThan(40_000);
    expect(nodeBytes).toBeLessThan(25_000);
    expect(edgeBytes).toBeLessThan(160_000);

    // Well over half of what the islands used to receive is dropped; the
    // lineage edges are the only part that barely shrinks.
    const projected = rowBytes + nodeBytes + edgeBytes;
    expect(projected).toBeLessThan(fullBytes * 0.4);
    expect(projected / fullBytes).toBeLessThan(0.4);
    // Dataset-derived projections (table + nodes) drop by more than 85%.
    expect((rowBytes + nodeBytes) / bytes(catalog.datasets)).toBeLessThan(0.15);
  });
});
