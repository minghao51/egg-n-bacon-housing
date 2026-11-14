/**
 * Build-time loader for the `/areas/[slug]` fieldnotes (slice S6).
 *
 * BUILD-TIME ONLY. This module reads the published assets from
 * `app/public/data` with `node:fs` / `node:zlib` / `node:crypto`, so it must
 * only ever be imported from an Astro page's frontmatter or from a test — never
 * from a React island, a browser module or a client component.
 *
 * Constraints carried over from the observed adapter
 * (`src/utils/observed-data.ts`) and the publication contract
 * (`assets/svg/implementation-plan.md` §3.1/§3.2):
 * - Every section is a *joint* `map_metrics[era_property]` key. The
 *   property-only (`hdb`) and period-only (`year_2025`) blocks that also exist
 *   in the asset are never used as a fallback.
 * - A missing combination is `area: null` / `national: null`. Nothing is
 *   zero-filled and no value is derived from another combination.
 * - The national baseline is attached from `dashboard_overview.stats` but the
 *   page only *shows* it when the build-time release check proves both assets
 *   come from one generation.
 * - Numbers stay unrounded; formatting is the page's concern.
 *
 * Two functions are async although the slice brief sketched them as
 * synchronous: the generation id can only be recomputed with the shared
 * canonical-JSON + SHA-256 implementation in `release-manifest.ts`, whose
 * digest API is Web Crypto and therefore asynchronous. Duplicating that
 * canonical encoder here would create a second source of truth for the
 * publication identity, so the async signature is deliberate.
 */

import { createHash } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
import { isAbsolute, join, relative, resolve } from "node:path";
import { gunzipSync } from "node:zlib";

import {
  areaSlug,
  canonicalAreaId,
  formatAreaName,
  getSection,
  readAreaObservation,
  readNationalBaseline,
  sectionKey,
} from "@/utils/observed-data";
import { loadObservedPackFromDir } from "@/utils/observed-pack-build";
import { buildAreaActivity } from "@/utils/area-activity";
import {
  computeReleaseGeneration,
  parseReleaseManifest,
  type ReleaseStatus,
} from "@/utils/release-manifest";
import { AREA_PAGE_COMBINATIONS, type AreaPageData } from "./area-selection";

// Re-exported so the Astro page and the tests keep one import site.
export * from "./area-selection";


export interface BaselineVerdict {
  compatible: boolean;
  status: ReleaseStatus;
  generation: string | null;
  /** Short human-readable reason; `null` when nothing needs explaining. */
  reason: string | null;
}

/** Narrow an `unknown` payload to a plain object (not an array, not null). */
function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function describeError(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

/** Deterministic, locale-independent ordering for canonical area ids. */
function compareIds(a: string, b: string): number {
  if (a < b) return -1;
  if (a > b) return 1;
  return 0;
}

/**
 * Read and decompress one gzipped JSON asset from disk.
 *
 * Throws rather than returning an empty payload: a build with no area pages
 * would look like a working site, so a missing or corrupt asset must stop the
 * build instead of silently shipping an empty `/areas` route.
 */
function readGzipJson(filePath: string): unknown {
  if (!existsSync(filePath)) {
    throw new Error(`area page build needs ${filePath}`);
  }
  let text: string;
  try {
    text = gunzipSync(readFileSync(filePath)).toString("utf8");
  } catch (error) {
    throw new Error(
      `could not decompress ${filePath}: ${describeError(error)}`,
    );
  }
  try {
    return JSON.parse(text) as unknown;
  } catch (error) {
    throw new Error(`could not parse ${filePath}: ${describeError(error)}`);
  }
}

/** Resolve a manifest asset path inside the data directory, or `null` if it escapes it. */
function resolveAssetPath(dataDir: string, assetPath: string): string | null {
  const resolved = resolve(dataDir, assetPath);
  const rel = relative(dataDir, resolved);
  if (rel === "" || rel.startsWith("..") || isAbsolute(rel)) return null;
  return resolved;
}

/** The seven assets one exporter generation always publishes. */
export const RELEASE_ASSET_PATHS: readonly string[] = [
  "dashboard_overview.json.gz",
  "dashboard_trends.json.gz",
  "dashboard_segments.json.gz",
  "dashboard_leaderboard.json.gz",
  "map_metrics.json.gz",
  "hotspots.json.gz",
  "amenity_summary.json.gz",
];

/**
 * Verify that the published dashboard assets share the generation recorded in
 * `public/data/dashboard-release.json`.
 *
 * Status contract (same vocabulary as the browser check in `release-manifest.ts`):
 * - `absent`   — no manifest is published in this tree; nothing is proven.
 * - `mismatch` — the manifest parsed but a recorded hash/size or the generation
 *                id disagrees with the files on disk (a mixed release).
 * - `unverified` — the manifest is present but unusable (not JSON, off
 *                contract, an unreadable asset, an escaping path).
 * - `verified` — every recorded `sha256`, `bytes` and `contentSha256` matches
 *                and the generation id matches the manifest content.
 *
 * `compatible` is `true` only for `verified`.
 */
export async function verifyBaselineAtBuild(
  rootDir: string,
): Promise<BaselineVerdict> {
  const dataDir = join(rootDir, "public", "data");
  const manifestPath = join(dataDir, "dashboard-release.json");

  if (!existsSync(manifestPath)) {
    return {
      compatible: false,
      status: "absent",
      generation: null,
      reason: null,
    };
  }

  let raw: unknown;
  try {
    raw = JSON.parse(readFileSync(manifestPath, "utf8")) as unknown;
  } catch (error) {
    return {
      compatible: false,
      status: "unverified",
      generation: null,
      reason: `dashboard-release.json is not valid JSON: ${describeError(error)}`,
    };
  }

  const manifest = parseReleaseManifest(raw);
  if (manifest === null || !isRecord(raw)) {
    return {
      compatible: false,
      status: "unverified",
      generation: null,
      reason: "dashboard-release.json does not match the release contract",
    };
  }

  const problems: string[] = [];
  const recordedPaths = new Set(manifest.assets.map((asset) => asset.path));

  for (const required of RELEASE_ASSET_PATHS) {
    if (!recordedPaths.has(required)) {
      problems.push(`${required}: manifest records no digest for this asset`);
    }
  }

  for (const asset of manifest.assets) {
    const filePath = resolveAssetPath(dataDir, asset.path);
    if (filePath === null) {
      problems.push(`${asset.path}: path leaves the published data directory`);
      continue;
    }
    if (!existsSync(filePath)) {
      problems.push(`${asset.path}: recorded asset is not on disk`);
      continue;
    }

    let bytes: Buffer;
    try {
      bytes = readFileSync(filePath);
    } catch (error) {
      problems.push(
        `${asset.path}: recorded asset is unreadable (${describeError(error)})`,
      );
      continue;
    }
    const sha256 = createHash("sha256").update(bytes).digest("hex");
    if (sha256 !== asset.sha256) {
      problems.push(`${asset.path}: sha256 does not match the recorded digest`);
    } else if (bytes.length !== asset.bytes) {
      problems.push(
        `${asset.path}: ${bytes.length} bytes, recorded ${asset.bytes}`,
      );
    }

    if (asset.contentSha256 !== undefined) {
      try {
        const content = gunzipSync(bytes);
        const contentSha256 = createHash("sha256")
          .update(content)
          .digest("hex");
        if (contentSha256 !== asset.contentSha256) {
          problems.push(
            `${asset.path}: decompressed content hash does not match`,
          );
        }
      } catch (error) {
        problems.push(
          `${asset.path}: decompressed content unreadable (${describeError(error)})`,
        );
      }
    }
  }

  let generation: string | null = manifest.generation;
  try {
    const recomputed = await computeReleaseGeneration(raw);
    if (recomputed !== manifest.generation) {
      problems.push(
        `generation ${manifest.generation.slice(0, 12)} does not match the manifest content`,
      );
    }
  } catch (error) {
    generation = null;
    return {
      compatible: false,
      status: "unverified",
      generation,
      reason: `generation could not be recomputed: ${describeError(error)}`,
    };
  }

  if (problems.length > 0) {
    return {
      compatible: false,
      status: "mismatch",
      generation,
      reason: problems[0],
    };
  }

  return { compatible: true, status: "verified", generation, reason: null };
}

/**
 * Load every area fieldnote the published assets support.
 *
 * The page set is the union of planning areas present in any of the
 * {@link AREA_PAGE_COMBINATIONS} sections, so an area published only in a wider
 * window (all history) or only for EC still gets a page that says what is
 * missing. Each page carries all four combinations, plus the build-time
 * baseline verdict that decides whether a national row may be shown.
 */
export async function loadAreaPages(rootDir: string): Promise<AreaPageData[]> {
  const dataDir = join(rootDir, "public", "data");
  const mapMetrics = readGzipJson(join(dataDir, "map_metrics.json.gz"));
  const overview = readGzipJson(join(dataDir, "dashboard_overview.json.gz"));
  const baseline = await verifyBaselineAtBuild(rootDir);

  const areaIds = new Set<string>();
  for (const combination of AREA_PAGE_COMBINATIONS) {
    const section = getSection(
      mapMetrics,
      combination.era,
      combination.property,
    );
    if (section === null) continue;
    for (const key of Object.keys(section)) {
      const areaId = canonicalAreaId(key);
      if (areaId !== "") areaIds.add(areaId);
    }
  }

  // Current-window identities: the pack may publish an area the historical
  // sections do not (Mandai, Sungei Kadut, Central Water Catchment). A current
  // row without a historical one still owns its route; the page then says
  // which combinations are missing instead of the route disappearing.
  const packLoad = await loadObservedPackFromDir(dataDir);
  if (packLoad.state === "ready") {
    for (const observation of packLoad.pack.observations) {
      if (NON_AREA_GEOGRAPHIES.has(observation.geographyId)) continue;
      const areaId = canonicalAreaId(observation.geographyId);
      if (areaId !== "") areaIds.add(areaId);
    }
  }

  // Two identities that slug to one path would silently overwrite a fieldnote,
  // so the collision stops the build instead of dropping a route.
  const slugOwners = new Map<string, string>();
  for (const areaId of [...areaIds].sort(compareIds)) {
    const slug = areaSlug(areaId);
    const owner = slugOwners.get(slug);
    if (owner !== undefined && owner !== areaId) {
      throw new Error(
        `two planning areas share the fieldnote slug "${slug}": ${owner} and ${areaId}`,
      );
    }
    slugOwners.set(slug, areaId);
  }

  const pack = packLoad.state === "ready" ? packLoad.pack : null;

  return [...areaIds].sort(compareIds).map((areaId) => ({
    areaId,
    areaName: formatAreaName(areaId),
    slug: areaSlug(areaId),
    sections: AREA_PAGE_COMBINATIONS.map((combination) => ({
      era: combination.era,
      property: combination.property,
      section: sectionKey(combination.era, combination.property),
      area: readAreaObservation(
        mapMetrics,
        combination.era,
        combination.property,
        areaId,
      ),
      national: readNationalBaseline(
        overview,
        combination.era,
        combination.property,
      ),
    })),
    baselineCompatible: baseline.compatible,
    baselineStatus: baseline.status,
    generation: baseline.generation,
    // RF10: the rolling-quarter numbers come from the same verified pack the
    // identities came from, so the fieldnote needs no extra request for them.
    activity: pack === null ? null : buildAreaActivity(pack, areaId),
  }));
}

export { areaHref } from "./area-links";
export type { AreaHrefSelection } from "./area-links";

/* ------------------------------------------------------------------------- */
/* Fieldnote selection (RF06)                                                 */
/* ------------------------------------------------------------------------- */

/**
 * Geography ids the pack writes that are not planning areas: the national scope
 * and the exporter's "unassigned" bucket. Neither may become `/areas/<slug>`.
 */
const NON_AREA_GEOGRAPHIES: ReadonlySet<string> = new Set(["SG", "NONE"]);
