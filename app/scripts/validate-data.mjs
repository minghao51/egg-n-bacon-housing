import { createHash } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
import { gunzipSync } from "node:zlib";

const root = new URL("../public/data/", import.meta.url);
const manifest = JSON.parse(
  readFileSync(new URL("manifest.json", root), "utf8"),
);

for (const asset of manifest.assets) {
  const url = new URL(asset.path, root);
  if (!existsSync(url))
    throw new Error(`Missing app data asset: ${asset.path}`);
  for (const field of [
    "logicalSource",
    "schemaVersion",
    "provenance",
    "shape",
  ]) {
    if (!(field in asset))
      throw new Error(`${asset.path}: manifest missing ${field}`);
  }
  if (asset.shape === "file") continue;
  let value;
  try {
    const bytes = readFileSync(url);
    const text = asset.path.endsWith(".gz")
      ? gunzipSync(bytes).toString("utf8")
      : bytes.toString("utf8");
    value =
      asset.shape === "jsonl"
        ? text
            .trim()
            .split("\n")
            .map((line) => JSON.parse(line))
        : JSON.parse(text);
  } catch (error) {
    throw new Error(`Invalid JSON asset ${asset.path}: ${error}`);
  }
  const shape =
    asset.shape === "geojson"
      ? value?.type === "FeatureCollection"
        ? "geojson"
        : "object"
      : asset.shape === "jsonl"
        ? "jsonl"
        : Array.isArray(value)
          ? "array"
          : value !== null && typeof value === "object"
            ? "object"
            : typeof value;
  if (shape !== asset.shape)
    throw new Error(`${asset.path}: expected ${asset.shape}, got ${shape}`);
  for (const key of asset.requiredKeys ?? []) {
    if (!(key in value))
      throw new Error(`${asset.path}: missing required key ${key}`);
  }
}

console.log(`Validated ${manifest.assets.length} app data assets`);

// ---------------------------------------------------------------------------
// Publication compatibility metadata
//
// scripts/export_app_data.py publishes dashboard-release.json after it replaces
// the seven dashboard payloads: schema version, one content-derived generation
// id, and a sha256/size record per asset. Verifying it here proves the seven
// files on disk are the ones that single exporter run produced. A tree that has
// not regenerated assets yet only warns, so the shape gate above keeps working.
// ---------------------------------------------------------------------------

const RELEASE_SCHEMA_VERSION = "1.0.0";
// dashboard-release.json must record exactly the seven assets the exporter owns.
// manifest.json does not tag them separately, so they are named explicitly.
const RELEASE_ASSETS = [
  "dashboard_overview.json.gz",
  "dashboard_trends.json.gz",
  "dashboard_segments.json.gz",
  "dashboard_leaderboard.json.gz",
  "map_metrics.json.gz",
  "hotspots.json.gz",
  "amenity_summary.json.gz",
];

function sha256(bytes) {
  return createHash("sha256").update(bytes).digest("hex");
}

// Canonical JSON matching the Python exporter: sorted keys, compact separators.
function canonicalJson(value) {
  if (Array.isArray(value))
    return `[${value.map((entry) => canonicalJson(entry)).join(",")}]`;
  if (value !== null && typeof value === "object") {
    const fields = Object.keys(value)
      .sort()
      .map((key) => `${JSON.stringify(key)}:${canonicalJson(value[key])}`);
    return `{${fields.join(",")}}`;
  }
  return JSON.stringify(value);
}

const releaseUrl = new URL("dashboard-release.json", root);
if (!existsSync(releaseUrl)) {
  console.warn(
    "Warning: dashboard-release.json is missing; dashboard assets have no verified single-generation identity (run scripts/export_app_data.py to publish one)",
  );
} else {
  const release = JSON.parse(readFileSync(releaseUrl, "utf8"));
  if (release === null || typeof release !== "object" || Array.isArray(release))
    throw new Error("dashboard-release.json: expected a JSON object");
  if (!Array.isArray(release.assets))
    throw new Error("dashboard-release.json: expected an assets array");
  if (release.schemaVersion !== RELEASE_SCHEMA_VERSION)
    throw new Error(
      `dashboard-release.json: schemaVersion ${release.schemaVersion} != ${RELEASE_SCHEMA_VERSION}`,
    );

  const recorded = new Map();
  for (const asset of release.assets) {
    if (!asset?.path || !asset.sha256 || !Number.isInteger(asset.bytes))
      throw new Error(
        `dashboard-release.json: malformed asset entry ${JSON.stringify(asset)}`,
      );
    recorded.set(asset.path, asset);
  }
  if (recorded.size !== RELEASE_ASSETS.length)
    throw new Error(
      `dashboard-release.json: records ${recorded.size} assets, expected ${RELEASE_ASSETS.length}`,
    );

  const manifestPaths = new Set(manifest.assets.map((asset) => asset.path));
  for (const path of RELEASE_ASSETS) {
    if (!manifestPaths.has(path))
      throw new Error(
        `dashboard-release.json: ${path} is not a manifest.json asset`,
      );
    const asset = recorded.get(path);
    if (!asset)
      throw new Error(`dashboard-release.json: missing asset entry ${path}`);
    const url = new URL(path, root);
    if (!existsSync(url))
      throw new Error(`dashboard-release.json: missing asset file ${path}`);
    const bytes = readFileSync(url);
    const digest = sha256(bytes);
    if (digest !== asset.sha256)
      throw new Error(
        `dashboard-release.json: ${path} hash ${digest} != recorded ${asset.sha256} (mixed release)`,
      );
    if (bytes.length !== asset.bytes)
      throw new Error(
        `dashboard-release.json: ${path} is ${bytes.length} bytes, recorded ${asset.bytes}`,
      );
  }
  for (const path of recorded.keys()) {
    if (!RELEASE_ASSETS.includes(path))
      throw new Error(`dashboard-release.json: unexpected asset ${path}`);
  }

  const content = { ...release };
  delete content.generation;
  delete content.generatedAt;
  const generation = sha256(Buffer.from(canonicalJson(content), "utf8"));
  if (generation !== release.generation)
    throw new Error(
      `dashboard-release.json: generation ${release.generation} does not match its content (${generation})`,
    );

  console.log(
    `Verified dashboard release ${String(release.generation).slice(0, 12)} (${recorded.size} assets)`,
  );
}
