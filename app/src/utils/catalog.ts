import fs from "fs";
import path from "path";
import zlib from "zlib";
import { parseCatalog, type CatalogData } from "@/types/catalog";

let cached: CatalogData | null = null;

export function loadCatalog(): CatalogData | null {
  if (cached) return cached;

  try {
    const raw = fs.readFileSync(path.resolve("public/data/catalog.jsonl.gz"));
    const decompressed = zlib.gunzipSync(raw).toString("utf-8");
    cached = parseCatalog(decompressed);
    return cached;
  } catch (error) {
    console.error("Failed to load catalog:", error);
    return null;
  }
}
