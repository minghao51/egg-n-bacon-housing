/**
 * Dashboard release-manifest adapter.
 *
 * Mirrors the publication contract `scripts/export_app_data.py` writes to
 * `dashboard-release.json`: a schema version, one content-derived generation
 * id, a per-asset sha256/bytes/shape/metric-scope record, and the observation
 * range, period definitions, inclusion rules and source identities behind that
 * single exporter run. Verifying it proves the dashboard assets a page loads
 * came from one generation; a mismatch withholds cross-asset comparisons
 * (assets/svg/implementation-plan.md §3.2).
 *
 * Constraints:
 * - No React, no DOM, no module-scope `window`, no Node built-ins. Hashing uses
 *   Web Crypto (`globalThis.crypto.subtle`), which is why the digest APIs are
 *   async.
 * - The generation id must be byte-identical to `release_generation()` in
 *   `scripts/export_app_data.py`: canonical JSON (keys sorted ascending at every
 *   level, array order preserved, no whitespace), `generation` and `generatedAt`
 *   removed at the top level, UTF-8, then SHA-256 hex. JSON.stringify key order
 *   is never relied on.
 * - Reading a manifest never throws: an absent, unparseable or off-contract
 *   manifest resolves to a status, not an exception.
 */

export type ReleaseStatus = "verified" | "mismatch" | "unverified" | "absent";

export interface ReleaseManifestAsset {
  path: string;
  /** SHA-256 of the published `.gz` file bytes (used at build time). */
  sha256: string;
  /**
   * SHA-256 of the decompressed JSON text. Hosts that send
   * `Content-Encoding: gzip` for `.gz` assets hand the browser the decoded
   * body, so a browser verifies this value; the raw `sha256` is unreachable
   * there. Optional for manifests written before the field existed.
   */
  contentSha256?: string;
  bytes: number;
  shape: "object" | "array";
  metricScopes: string[];
}

export interface ReleaseManifest {
  schemaVersion: string;
  generation: string;
  generatedAt: string;
  observationRange: {
    startMonth: string;
    endMonth: string;
    completeYear: number | null;
  };
  periodDefinitions: Record<string, { label: string; filter: string }>;
  inclusionRules: Record<string, unknown>;
  provenance: { sources: Array<Record<string, unknown>> };
  assets: ReleaseManifestAsset[];
}

export interface ReleaseCheck {
  status: ReleaseStatus;
  manifest: ReleaseManifest | null;
  mismatches: string[];
}

/** The only manifest schema this build understands (RELEASE_SCHEMA_VERSION in the exporter). */
export const RELEASE_SCHEMA_VERSION = "1.0.0";

/** Top-level fields excluded from the generation id (wall-clock free by design). */
const GENERATION_EXCLUDED_KEYS: readonly string[] = [
  "generation",
  "generatedAt",
];

/** Narrow an `unknown` payload to a plain object (not an array, not null). */
function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isLowercaseHexDigest(value: unknown): value is string {
  return typeof value === "string" && /^[0-9a-f]{64}$/.test(value);
}

function isNonNegativeInteger(value: unknown): value is number {
  return typeof value === "number" && Number.isInteger(value) && value >= 0;
}

function toByteView(bytes: ArrayBuffer | Uint8Array): Uint8Array<ArrayBuffer> {
  // Copy into a fresh view so a subarray offset can never change the digest.
  return bytes instanceof Uint8Array
    ? new Uint8Array(bytes)
    : new Uint8Array(bytes);
}

function toHex(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let hex = "";
  for (const byte of bytes) {
    hex += byte.toString(16).padStart(2, "0");
  }
  return hex;
}

/** SHA-256 hex digest via Web Crypto (no Node `crypto` import). */
async function sha256Hex(bytes: Uint8Array<ArrayBuffer>): Promise<string> {
  const subtle = globalThis.crypto?.subtle;
  if (subtle === undefined) {
    throw new Error("SHA-256 is unavailable: Web Crypto subtle is not exposed");
  }
  return toHex(await subtle.digest("SHA-256", bytes));
}

/**
 * Canonical JSON matching Python's
 * `json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`.
 *
 * - object keys are sorted ascending (Python sorts by code point; `sort()` on
 *   ASCII keys is identical, which covers every key the exporter writes);
 * - arrays keep their order;
 * - `undefined` object properties are dropped and `undefined` array entries
 *   become `null`, matching `JSON.stringify` and the absence of the value in a
 *   parsed document;
 * - non-finite numbers become `null`, mirroring `sanitize_for_json()`.
 *
 * Number formatting: the manifest records integers (`bytes`, `rows`,
 * `completeYear`, `excludedTransactions`) and `JSON.stringify` emits those
 * exactly as Python's `int` repr. A float would be formatted by the host's
 * shortest-round-trip rule, which differs from Python for exponents such as
 * `1e-7`; the exporter writes no float, so that case is out of contract.
 */
function canonicalJson(value: unknown): string {
  if (value === null || value === undefined) return "null";
  if (typeof value === "boolean") return value ? "true" : "false";
  if (typeof value === "number") {
    return Number.isFinite(value) ? JSON.stringify(value) : "null";
  }
  if (typeof value === "string") return JSON.stringify(value);
  if (Array.isArray(value)) {
    return `[${value.map((entry) => canonicalJson(entry)).join(",")}]`;
  }
  if (isRecord(value)) {
    const fields = Object.keys(value)
      .filter((key) => value[key] !== undefined)
      .sort()
      .map((key) => `${JSON.stringify(key)}:${canonicalJson(value[key])}`);
    return `{${fields.join(",")}}`;
  }
  // Functions and symbols never appear in a parsed JSON document.
  return "null";
}

/**
 * Validate a decoded `dashboard-release.json` payload.
 *
 * Returns `null` for anything that does not satisfy the 1.0.0 contract, so the
 * caller can fail closed instead of reading half a manifest. A manifest whose
 * `observationRange` months are `null` (the exporter writes that only when no
 * published month could be derived) is rejected rather than given a made-up
 * range.
 */
export function parseReleaseManifest(raw: unknown): ReleaseManifest | null {
  if (!isRecord(raw)) return null;
  if (raw["schemaVersion"] !== RELEASE_SCHEMA_VERSION) return null;

  const generation = raw["generation"];
  if (typeof generation !== "string" || generation === "") return null;

  const generatedAt = raw["generatedAt"];
  if (typeof generatedAt !== "string" || generatedAt === "") return null;

  const range = raw["observationRange"];
  if (!isRecord(range)) return null;
  const startMonth = range["startMonth"];
  const endMonth = range["endMonth"];
  const completeYear = range["completeYear"];
  if (typeof startMonth !== "string" || typeof endMonth !== "string")
    return null;
  if (completeYear !== null && !isNonNegativeInteger(completeYear)) return null;

  const rawPeriods = raw["periodDefinitions"];
  if (!isRecord(rawPeriods)) return null;
  const periodDefinitions: Record<string, { label: string; filter: string }> =
    {};
  for (const [era, definition] of Object.entries(rawPeriods)) {
    if (!isRecord(definition)) return null;
    const label = definition["label"];
    const filter = definition["filter"];
    if (typeof label !== "string" || typeof filter !== "string") return null;
    periodDefinitions[era] = { label, filter };
  }

  const inclusionRules = raw["inclusionRules"];
  if (!isRecord(inclusionRules)) return null;

  const provenance = raw["provenance"];
  if (!isRecord(provenance)) return null;
  const sources = provenance["sources"];
  if (!Array.isArray(sources) || !sources.every(isRecord)) return null;

  const rawAssets = raw["assets"];
  if (!Array.isArray(rawAssets)) return null;
  const assets: ReleaseManifestAsset[] = [];
  for (const entry of rawAssets) {
    if (!isRecord(entry)) return null;
    const path = entry["path"];
    const contentSha256 = entry["contentSha256"];
    const sha256 = entry["sha256"];
    const bytes = entry["bytes"];
    const shape = entry["shape"];
    const metricScopes = entry["metricScopes"];
    if (typeof path !== "string" || path === "") return null;
    if (!isLowercaseHexDigest(sha256)) return null;
    if (contentSha256 !== undefined && !isLowercaseHexDigest(contentSha256)) {
      return null;
    }
    if (!isNonNegativeInteger(bytes)) return null;
    if (shape !== "object" && shape !== "array") return null;
    if (!Array.isArray(metricScopes)) return null;
    const scopes: string[] = [];
    for (const scope of metricScopes) {
      if (typeof scope !== "string") return null;
      scopes.push(scope);
    }
    assets.push({
      path,
      sha256,
      ...(contentSha256 === undefined ? {} : { contentSha256 }),
      bytes,
      shape,
      metricScopes: scopes,
    });
  }

  return {
    schemaVersion: RELEASE_SCHEMA_VERSION,
    generation,
    generatedAt,
    observationRange: { startMonth, endMonth, completeYear },
    periodDefinitions,
    inclusionRules,
    provenance: { sources },
    assets,
  };
}

/**
 * Recompute the content-derived generation id.
 *
 * Pass the decoded manifest object (not the parsed interface) so fields this
 * build does not model still contribute to the hash, exactly as the Python
 * implementation hashes every key it is given.
 */
export async function computeReleaseGeneration(
  manifest: Record<string, unknown>,
): Promise<string> {
  const content: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(manifest)) {
    if (GENERATION_EXCLUDED_KEYS.includes(key)) continue;
    content[key] = value;
  }
  return sha256Hex(new TextEncoder().encode(canonicalJson(content)));
}

/**
 * Compare supplied asset bytes against the manifest's recorded sha256 and size.
 *
 * `only` limits the check to those paths (the manifest entries still decide the
 * expected values); the default checks every asset the manifest lists. Returns
 * one human-readable line per problem, empty when everything matches.
 */
export async function verifyReleaseAssets(
  manifest: ReleaseManifest,
  assets: Record<string, ArrayBuffer | Uint8Array>,
  only?: string[],
): Promise<string[]> {
  const targets = only ?? manifest.assets.map((asset) => asset.path);
  const recorded = new Map(
    manifest.assets.map((asset) => [asset.path, asset] as const),
  );
  const problems: string[] = [];

  for (const path of targets) {
    const entry = recorded.get(path);
    if (entry === undefined) {
      problems.push(`release manifest records no asset entry for ${path}`);
      continue;
    }
    const bytes = assets[path];
    if (bytes === undefined) {
      problems.push(`no bytes supplied for ${path}`);
      continue;
    }
    const view = toByteView(bytes);
    const rawSha = await sha256Hex(view);
    if (rawSha === entry.sha256) {
      if (view.byteLength !== entry.bytes) {
        problems.push(
          `size mismatch: ${path} (recorded ${entry.bytes}, actual ${view.byteLength})`,
        );
      }
      if (entry.contentSha256 !== undefined) {
        const content = await decodedContent(view);
        if (content === null) {
          problems.push(`content unreadable: ${path}`);
        } else if ((await sha256Hex(content)) !== entry.contentSha256) {
          problems.push(`content hash mismatch: ${path}`);
        }
      }
      continue;
    }

    // The served bytes are not the `.gz` file (the host decompressed it), so
    // verify the content hash the manifest records for the decoded text.
    if (entry.contentSha256 !== undefined) {
      const content = await decodedContent(view);
      if (
        content !== null &&
        (await sha256Hex(content)) === entry.contentSha256
      ) {
        continue;
      }
    }
    problems.push(
      `hash mismatch: ${path} (recorded ${entry.sha256}, actual ${rawSha})`,
    );
  }

  return problems;
}

/** Decode a response body that may or may not still be gzip-compressed. */
async function decodedContent(
  view: Uint8Array<ArrayBuffer>,
): Promise<Uint8Array<ArrayBuffer> | null> {
  const gzipMagic = view.byteLength > 1 && view[0] === 0x1f && view[1] === 0x8b;
  if (!gzipMagic) return view;
  if (typeof DecompressionStream === "undefined") return null;
  try {
    const stream = new Response(view).body;
    if (stream === null) return null;
    const reader = stream
      .pipeThrough(new DecompressionStream("gzip"))
      .getReader();
    const chunks: Uint8Array[] = [];
    let total = 0;
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      if (value !== undefined) {
        chunks.push(value);
        total += value.byteLength;
      }
    }
    const joined = new Uint8Array(new ArrayBuffer(total));
    let offset = 0;
    for (const chunk of chunks) {
      joined.set(chunk, offset);
      offset += chunk.byteLength;
    }
    return joined;
  } catch {
    return null;
  }
}

function describeError(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

/**
 * Load, validate and verify one release manifest against the assets on offer.
 *
 * Status contract:
 * - `absent` — the manifest is not published (HTTP 404). Nothing is wrong with
 *   the assets; there is simply no generation identity to prove.
 * - `unverified` — the manifest could not be fetched, is not JSON, is off
 *   contract, or hashing is unavailable. Never throws.
 * - `mismatch` — the manifest parsed but a recorded hash, size or the
 *   generation id disagrees with what was served (a mixed release).
 * - `verified` — every requested asset matches and the generation id matches
 *   its content.
 *
 * `verifyOnly` narrows the asset check (a page that loads three of the seven
 * assets); the generation id is always recomputed.
 */
export async function loadReleaseCheck(options: {
  manifestUrl: string;
  assetUrls: Record<string, string>;
  verifyOnly?: string[];
  fetcher?: typeof fetch;
}): Promise<ReleaseCheck> {
  const doFetch: typeof fetch = options.fetcher ?? globalThis.fetch;

  let manifestResponse: Response;
  try {
    manifestResponse = await doFetch(options.manifestUrl);
  } catch (error) {
    return {
      status: "unverified",
      manifest: null,
      mismatches: [
        `release manifest could not be fetched: ${describeError(error)}`,
      ],
    };
  }

  if (manifestResponse.status === 404) {
    return { status: "absent", manifest: null, mismatches: [] };
  }
  if (!manifestResponse.ok) {
    return {
      status: "unverified",
      manifest: null,
      mismatches: [
        `release manifest request failed with HTTP ${manifestResponse.status}`,
      ],
    };
  }

  let raw: unknown;
  try {
    raw = JSON.parse(await manifestResponse.text());
  } catch (error) {
    return {
      status: "unverified",
      manifest: null,
      mismatches: [
        `release manifest is not valid JSON: ${describeError(error)}`,
      ],
    };
  }

  const manifest = parseReleaseManifest(raw);
  if (manifest === null || !isRecord(raw)) {
    const recordedVersion = isRecord(raw) ? raw["schemaVersion"] : undefined;
    return {
      status: "unverified",
      manifest: null,
      mismatches: [
        typeof recordedVersion === "string"
          ? `release manifest schemaVersion ${recordedVersion} != ${RELEASE_SCHEMA_VERSION}`
          : "release manifest does not match the release manifest contract",
      ],
    };
  }

  try {
    const targets = options.verifyOnly ?? manifest.assets.map((a) => a.path);
    const supplied: Record<string, ArrayBuffer> = {};
    const fetchedTargets: string[] = [];
    const mismatches: string[] = [];
    const fetchProblems: string[] = [];

    for (const path of targets) {
      const url = options.assetUrls[path];
      if (url === undefined) {
        fetchProblems.push(`no asset URL provided for ${path}`);
        continue;
      }
      try {
        const response = await doFetch(url);
        if (!response.ok) {
          fetchProblems.push(
            `could not fetch ${path} (HTTP ${response.status})`,
          );
          continue;
        }
        supplied[path] = await response.arrayBuffer();
        fetchedTargets.push(path);
      } catch (error) {
        fetchProblems.push(`could not fetch ${path} (${describeError(error)})`);
      }
    }

    if (fetchProblems.length > 0) {
      // Not being able to download the assets proves nothing about whether the
      // published generation is mixed, so it must not read as incompatibility.
      return {
        status: "unverified",
        manifest,
        mismatches: fetchProblems,
      };
    }

    mismatches.push(
      ...(await verifyReleaseAssets(manifest, supplied, fetchedTargets)),
    );

    const recomputed = await computeReleaseGeneration(raw);
    if (recomputed !== manifest.generation) {
      mismatches.push(
        `generation ${manifest.generation} does not match the manifest content (${recomputed})`,
      );
    }

    return {
      status: mismatches.length === 0 ? "verified" : "mismatch",
      manifest,
      mismatches,
    };
  } catch (error) {
    return {
      status: "unverified",
      manifest,
      mismatches: [`release verification failed: ${describeError(error)}`],
    };
  }
}
