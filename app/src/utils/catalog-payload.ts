/**
 * Slim catalog projections for the `/catalog` islands (S10-F1).
 *
 * The catalog index used to hand both islands every parsed dataset — schema
 * fields, parquet columns, descriptions and lineage included — which made the
 * page ship 825 kB of SSR props. Each island only ever reads a handful of
 * fields, so the page projects the parsed catalog once, here, and passes the
 * projections. Dataset routes, slugs and the catalog snapshot itself are
 * unchanged; this is a transport projection, not a data rewrite.
 *
 * The helpers are pure and order-preserving so the table's unsorted order and
 * the DAG's per-layer vertical order stay exactly as generated.
 */

import type { CatalogDataset, LineageEdge } from "@/types/catalog";

/** One catalog table row: the columns `DatasetTable` renders. */
export interface CatalogTableRow {
  id: string;
  label: string;
  layer: string;
  status: CatalogDataset["status"];
  rowCount: number | null;
  columnCount: number | null;
  /** Parquet file size in bytes; `null` when the artifact was not observed. */
  bytes: number | null;
  /** Whether a declared Pydantic schema exists (the fields themselves are not sent). */
  hasSchema: boolean;
}

/** One lineage node: enough to place, label, colour and link it. */
export interface CatalogDagNode {
  id: string;
  layer: string;
  label: string;
}

/**
 * One lineage edge as a `[from, to]` node-id pair.
 *
 * A tuple rather than `{ from, to }`: the snapshot has 2,333 edges, and the
 * repeated key names were the largest remaining prop cost once datasets were
 * projected. Consumed only by `DagGraph`.
 */
export type CatalogDagEdge = readonly [from: string, to: string];

/**
 * Rows for the dataset table. Missing parquet statistics stay `null` so the
 * table can keep saying "not observed" rather than showing a fabricated zero.
 */
export function tableRows(
  datasets: readonly CatalogDataset[],
): CatalogTableRow[] {
  return datasets.map((dataset) => ({
    id: dataset.id,
    label: dataset.label,
    layer: dataset.layer,
    status: dataset.status,
    rowCount: dataset.parquet?.row_count ?? null,
    columnCount: dataset.parquet?.column_count ?? null,
    bytes: dataset.parquet?.file_size_bytes ?? null,
    hasSchema: dataset.schema !== null && dataset.schema !== undefined,
  }));
}

/** Nodes for the lineage graph, in the catalog's own dataset order. */
export function dagNodes(
  datasets: readonly CatalogDataset[],
): CatalogDagNode[] {
  return datasets.map((dataset) => ({
    id: dataset.id,
    layer: dataset.layer,
    label: dataset.label,
  }));
}

/** Edges for the lineage graph, in the catalog's own edge order. */
export function dagEdges(edges: readonly LineageEdge[]): CatalogDagEdge[] {
  return edges.map((edge) => [edge.from, edge.to] as const);
}
