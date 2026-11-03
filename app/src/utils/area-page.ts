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
  type ObservedAreaRecord,
  type ObservedObservation,
} from "@/utils/observed-data";
import {
  computeReleaseGeneration,
  parseReleaseManifest,
  type ReleaseStatus,
} from "@/utils/release-manifest";

/** The four era labels a fieldnote reports on (a subset of `EraId`). */
export type AreaPageEra = "year_2025" | "recent" | "pre_covid" | "whole";

/** The property subsets a fieldnote reports on, including the all-property aggregate. */
export type AreaPageProperty = "all" | "hdb" | "ec" | "condo";

export interface AreaPageCombination {
  era: AreaPageEra;
  property: AreaPageProperty;
  /** Reader-facing label, e.g. "2025 complete year · HDB". */
  label: string;
}

/**
 * Every joint section the exporter publishes, in reading order. A fieldnote
 * covers the whole matrix so an area that only appears for condominiums or only
 * in the all-property aggregate still gets a page, and the availability panel
 * can say precisely which combinations are missing.
 */
const AREA_PAGE_ERAS: readonly AreaPageEra[] = [
  "year_2025",
  "whole",
  "recent",
  "pre_covid",
];

const AREA_PAGE_PROPERTIES: readonly AreaPageProperty[] = [
  "hdb",
  "ec",
  "condo",
  "all",
];

const ERA_PAGE_LABELS: Record<AreaPageEra, string> = {
  year_2025: "2025 complete year",
  whole: "All history",
  recent: "2022 onward",
  pre_covid: "Through 2021",
};

const PROPERTY_PAGE_LABELS: Record<AreaPageProperty, string> = {
  hdb: "HDB",
  ec: "EC",
  condo: "Condominium",
  all: "All property types",
};

export const AREA_PAGE_COMBINATIONS: readonly AreaPageCombination[] =
  AREA_PAGE_ERAS.flatMap((era) =>
    AREA_PAGE_PROPERTIES.map((property) => ({
      era,
      property,
      label: `${ERA_PAGE_LABELS[era]} · ${PROPERTY_PAGE_LABELS[property]}`,
    })),
  );

/** Reader-facing scope sentence for the era a fieldnote is anchored on. */
export function areaEraScope(era: AreaPageEra): string {
  if (era === "year_2025") {
    return "the 2025 complete year (2025-01-01 through 2025-12-31)";
  }
  if (era === "whole") return "all published history (no period filter)";
  if (era === "recent") return "transactions from 2022 onward";
  return "transactions dated on or before 2021-12-31";
}

/** Reader-facing headline label, e.g. "HDB resale · All history". */
export function areaSectionScope(
  era: AreaPageEra,
  property: AreaPageProperty,
): string {
  const noun =
    property === "hdb"
      ? "HDB resale"
      : property === "ec"
        ? "Executive condominium"
        : property === "condo"
          ? "Condominium"
          : "All property types";
  return `${noun} · ${ERA_PAGE_LABELS[era]}`;
}

/** Combinations that decide the headline of a fieldnote, most specific first. */
export const AREA_PRIMARY_PREFERENCE: readonly {
  era: AreaPageEra;
  property: AreaPageProperty;
}[] = [
  { era: "year_2025", property: "hdb" },
  { era: "year_2025", property: "condo" },
  { era: "year_2025", property: "all" },
  { era: "year_2025", property: "ec" },
  { era: "whole", property: "hdb" },
  { era: "whole", property: "condo" },
  { era: "whole", property: "all" },
  { era: "whole", property: "ec" },
];

export interface AreaPageSection {
  era: AreaPageEra;
  property: AreaPageProperty;
  /** Exact asset section identity, e.g. `map_metrics.year_2025_hdb`'s key. */
  section: string;
  /** The area record for this combination, or `null` when not published. */
  area: ObservedAreaRecord | null;
  /** The national baseline for this combination, or `null` when not published. */
  national: ObservedObservation[] | null;
}

export interface AreaPageData {
  areaId: string;
  areaName: string;
  slug: string;
  sections: AreaPageSection[];
  baselineCompatible: boolean;
  baselineStatus: string;
  generation: string | null;
}

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
    throw new Error(`could not decompress ${filePath}: ${describeError(error)}`);
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
        const contentSha256 = createHash("sha256").update(content).digest("hex");
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
  }));
}

export { areaHref } from "./area-links";
export type { AreaHrefSelection } from "./area-links";
