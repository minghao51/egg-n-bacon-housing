import { existsSync, readFileSync } from "node:fs";
import { gunzipSync } from "node:zlib";

const root = new URL("../public/data/", import.meta.url);
const manifest = JSON.parse(readFileSync(new URL("manifest.json", root), "utf8"));

for (const asset of manifest.assets) {
  const url = new URL(asset.path, root);
  if (!existsSync(url)) throw new Error(`Missing app data asset: ${asset.path}`);
  for (const field of ["logicalSource", "schemaVersion", "provenance", "shape"]) {
    if (!(field in asset)) throw new Error(`${asset.path}: manifest missing ${field}`);
  }
  if (asset.shape === "file") continue;
  let value;
  try {
    const bytes = readFileSync(url);
    const text = asset.path.endsWith(".gz")
      ? gunzipSync(bytes).toString("utf8")
      : bytes.toString("utf8");
    value = asset.shape === "jsonl"
      ? text.trim().split("\n").map((line) => JSON.parse(line))
      : JSON.parse(text);
  } catch (error) {
    throw new Error(`Invalid JSON asset ${asset.path}: ${error}`);
  }
  const shape = asset.shape === "geojson"
    ? value?.type === "FeatureCollection" ? "geojson" : "object"
    : asset.shape === "jsonl"
      ? "jsonl"
      : Array.isArray(value) ? "array" : value !== null && typeof value === "object" ? "object" : typeof value;
  if (shape !== asset.shape) throw new Error(`${asset.path}: expected ${asset.shape}, got ${shape}`);
  for (const key of asset.requiredKeys ?? []) {
    if (!(key in value)) throw new Error(`${asset.path}: missing required key ${key}`);
  }
}

console.log(`Validated ${manifest.assets.length} app data assets`);
