export interface CatalogMetadata {
  type: "metadata";
  generated_at: string;
  pipeline_version: string;
  generator: string;
}

export interface CatalogLayer {
  type: "layer";
  id: string;
  label: string;
  description: string;
  dataset_count: number;
  total_rows: number;
  total_size_bytes: number;
}

export interface FieldInfo {
  type: string;
  nullable: boolean;
  constraints: Record<string, number>;
  default: string;
  description?: string;
}

export interface SchemaInfo {
  model: string;
  doc: string;
  fields: Record<string, FieldInfo>;
}

export interface ParquetColumn {
  parquet_type: string;
  null_count?: number;
  null_pct: number | null;
  sample_value: string | null;
  description?: string;
}

export interface ParquetStats {
  file: string;
  row_count: number;
  column_count: number;
  file_size_bytes: number;
  columns: Record<string, ParquetColumn>;
}

export interface LineageInfo {
  upstream: string[];
  downstream: string[];
}

export interface CatalogDataset {
  type: "dataset";
  id: string;
  layer: string;
  label: string;
  description: string;
  source?: string;
  status: "available" | "missing" | "error";
  parquet: ParquetStats | null;
  schema: SchemaInfo | null;
  lineage: LineageInfo;
}

export interface LineageEdge {
  type: "edge";
  from: string;
  to: string;
}

export type CatalogEntry =
  | CatalogMetadata
  | CatalogLayer
  | CatalogDataset
  | LineageEdge;

export interface CatalogData {
  metadata: CatalogMetadata | null;
  layers: CatalogLayer[];
  datasets: CatalogDataset[];
  edges: LineageEdge[];
  datasetMap: Map<string, CatalogDataset>;
  layerMap: Map<string, CatalogLayer>;
}

export const LAYER_COLORS: Record<string, string> = {
  bronze: "#b45309",
  silver: "#64748b",
  gold: "#ca8a04",
  platinum: "#7c3aed",
};

export const LAYER_BG_COLORS: Record<string, string> = {
  bronze: "bg-amber-900/20",
  silver: "bg-slate-700/20",
  gold: "bg-yellow-700/20",
  platinum: "bg-purple-900/20",
};

export const LAYER_BORDER_COLORS: Record<string, string> = {
  bronze: "border-amber-700",
  silver: "border-slate-500",
  gold: "border-yellow-600",
  platinum: "border-purple-600",
};

export function parseCatalog(raw: string): CatalogData {
  const lines = raw.split("\n").filter(Boolean);
  const entries: CatalogEntry[] = [];
  for (const line of lines) {
    try {
      entries.push(JSON.parse(line) as CatalogEntry);
    } catch (e) {
      console.error("Skipping malformed catalog line:", e);
    }
  }

  let metadata: CatalogMetadata | null = null;
  const layers: CatalogLayer[] = [];
  const datasets: CatalogDataset[] = [];
  const edges: LineageEdge[] = [];

  for (const entry of entries) {
    switch (entry.type) {
      case "metadata":
        metadata = entry;
        break;
      case "layer":
        layers.push(entry);
        break;
      case "dataset":
        datasets.push(entry);
        break;
      case "edge":
        edges.push(entry);
        break;
    }
  }

  const datasetMap = new Map<string, CatalogDataset>();
  for (const ds of datasets) {
    datasetMap.set(ds.id, ds);
  }

  const layerMap = new Map<string, CatalogLayer>();
  for (const layer of layers) {
    layerMap.set(layer.id, layer);
  }

  return { metadata, layers, datasets, edges, datasetMap, layerMap };
}

export function humanSize(bytes: number): string {
  if (bytes === 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  let val = bytes;
  let unitIdx = 0;
  while (val >= 1024 && unitIdx < units.length - 1) {
    val /= 1024;
    unitIdx++;
  }
  return `${val.toFixed(1)} ${units[unitIdx]}`;
}

export function layerLabel(layer: string): string {
  const labels: Record<string, string> = {
    bronze: "Bronze",
    silver: "Silver",
    gold: "Gold",
    platinum: "Platinum",
  };
  return labels[layer] || layer;
}

/**
 * Encode a dataset ID into a URL-safe path segment.
 *
 * `external__cpi` -> `external/cpi` (nested route via [...dataset] rest param).
 * All other IDs pass through unchanged.
 *
 * Pairs with {@link slugToDatasetId} for the reverse conversion in getStaticPaths.
 */
export function datasetIdToSlug(id: string): string {
  return id.replace(/^external__/, "external/");
}

/**
 * Reverse of {@link datasetIdToSlug} — converts a URL slug back to a dataset ID.
 * Accepts either an array (rest param) or a pre-joined string.
 */
export function slugToDatasetId(slug: string | string[]): string {
  const joined = Array.isArray(slug) ? slug.join("/") : slug;
  return joined.replace(/^external\//, "external__");
}
