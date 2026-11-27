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

/**
 * Digest evidence for one asset whose bytes were hashed during a load.
 *
 * This describes the exact response this call received, which is what the
 * digests below were taken from — not what the manifest predicted.
 */
export interface ReleaseAssetEvidence {
  /** SHA-256 of exactly the bytes served for the path. */
  sha256: string;
  /** SHA-256 of the decoded JSON text, when the raw digest was the one that matched. */
  contentSha256: string | null;
  /** Length of the served body (before any decompression). */
  byteLength: number;
}

/**
 * One release verification result.
 *
 * `status`, `manifest` and `mismatches` are the original contract every caller
 * already reads. `payloads` and `evidence` are the same bytes the digests were
 * taken from: a screen renders `payloads` instead of fetching the URL a second
 * time, so what is displayed is what was verified (UI-1).
 */
export interface ReleaseCheck {
  status: ReleaseStatus;
  manifest: ReleaseManifest | null;
  mismatches: string[];
  /**
   * Decoded payload per asset path, from the exact bytes that verified.
   *
   * Empty for every status other than `verified` — in particular a `mismatch`
   * exposes no payload at all, so a rejected response can never be rendered.
   */
  payloads: Record<string, unknown>;
  /** Digest/size evidence for the paths in `payloads`. */
  evidence: Record<string, ReleaseAssetEvidence>;
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
 * One asset whose served bytes matched the manifest, with the bytes retained.
 *
 * `content` is the same buffer the digests were taken from, so decoding it is
 * not a second chance to see different bytes: whatever a caller renders from
 * `content` is provably the response that verified (UI-1).
 */
interface VerifiedAssetBytes {
  sha256: string;
  contentSha256: string | null;
  byteLength: number;
  content: Uint8Array<ArrayBuffer>;
}

interface AssetVerification {
  problems: string[];
  verified: Map<string, VerifiedAssetBytes>;
}

/**
 * Compare supplied asset bytes against the manifest's recorded hashes and size.
 *
 * Returns the problem lines plus, for every path that matched, the digest
 * evidence and the decoded buffer those digests were taken from.
 */
async function verifyAssetsDetailed(
  manifest: ReleaseManifest,
  assets: Record<string, ArrayBuffer | Uint8Array>,
  only?: string[],
): Promise<AssetVerification> {
  const targets = only ?? manifest.assets.map((asset) => asset.path);
  const recorded = new Map(
    manifest.assets.map((asset) => [asset.path, asset] as const),
  );
  const problems: string[] = [];
  const verified = new Map<string, VerifiedAssetBytes>();

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
    // Decode once, so the digest and the payload a caller renders come from the
    // same buffer.
    const content = await decodedContent(view);
    const contentSha = content === null ? null : await sha256Hex(content);
    let ok = false;

    if (rawSha === entry.sha256) {
      if (view.byteLength !== entry.bytes) {
        problems.push(
          `size mismatch: ${path} (recorded ${entry.bytes}, actual ${view.byteLength})`,
        );
      } else if (
        entry.contentSha256 !== undefined &&
        contentSha !== entry.contentSha256
      ) {
        problems.push(
          content === null
            ? `content unreadable: ${path}`
            : `content hash mismatch: ${path}`,
        );
      } else {
        ok = true;
      }
    } else if (
      // The served bytes are not the `.gz` file (the host decompressed it), so
      // verify the content hash the manifest records for the decoded text.
      entry.contentSha256 !== undefined &&
      content !== null &&
      contentSha === entry.contentSha256
    ) {
      ok = true;
    } else {
      problems.push(
        `hash mismatch: ${path} (recorded ${entry.sha256}, actual ${rawSha})`,
      );
    }

    if (ok) {
      verified.set(path, {
        sha256: rawSha,
        contentSha256: contentSha,
        byteLength: view.byteLength,
        // `content` is only null when the digest path did not need it (a raw
        // match), in which case the served bytes are the JSON text.
        content: content ?? view,
      });
    }
  }

  return { problems, verified };
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
  return (await verifyAssetsDetailed(manifest, assets, only)).problems;
}

/**
 * Decode a verified payload from the bytes its digest was taken from.
 *
 * Returns `null` when those bytes are not JSON. The bytes are still verified —
 * this only says they cannot be rendered, so the caller gets no payload rather
 * than an unchecked substitute.
 */
function decodePayload(content: Uint8Array<ArrayBuffer>): {
  ok: boolean;
  value: unknown;
} {
  try {
    return {
      ok: true,
      value: JSON.parse(new TextDecoder().decode(content)) as unknown,
    };
  } catch {
    return { ok: false, value: null };
  }
}

/** The status/evidence shape every non-verified return shares. */
function unverifiedCheck(
  status: ReleaseStatus,
  mismatches: string[],
  manifest: ReleaseManifest | null,
): ReleaseCheck {
  return { status, manifest, mismatches, payloads: {}, evidence: {} };
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
 *
 * The returned `payloads` are decoded from exactly the response bodies the
 * digests were taken from, so a caller renders the verified bytes instead of
 * fetching the same URL again (UI-1). Every non-`verified` status returns an
 * empty `payloads` map.
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
    return unverifiedCheck(
      "unverified",
      [`release manifest could not be fetched: ${describeError(error)}`],
      null,
    );
  }

  if (manifestResponse.status === 404) {
    return unverifiedCheck("absent", [], null);
  }
  if (!manifestResponse.ok) {
    return unverifiedCheck(
      "unverified",
      [`release manifest request failed with HTTP ${manifestResponse.status}`],
      null,
    );
  }

  let raw: unknown;
  try {
    raw = JSON.parse(await manifestResponse.text());
  } catch (error) {
    return unverifiedCheck(
      "unverified",
      [`release manifest is not valid JSON: ${describeError(error)}`],
      null,
    );
  }

  const manifest = parseReleaseManifest(raw);
  if (manifest === null || !isRecord(raw)) {
    const recordedVersion = isRecord(raw) ? raw["schemaVersion"] : undefined;
    return unverifiedCheck(
      "unverified",
      [
        typeof recordedVersion === "string"
          ? `release manifest schemaVersion ${recordedVersion} != ${RELEASE_SCHEMA_VERSION}`
          : "release manifest does not match the release manifest contract",
      ],
      null,
    );
  }

  try {
    const targets = options.verifyOnly ?? manifest.assets.map((a) => a.path);
    const supplied: Record<string, ArrayBuffer> = {};
    const fetchedTargets: string[] = [];
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
      return unverifiedCheck("unverified", fetchProblems, manifest);
    }

    const { problems, verified } = await verifyAssetsDetailed(
      manifest,
      supplied,
      fetchedTargets,
    );
    const mismatches: string[] = [...problems];

    const recomputed = await computeReleaseGeneration(raw);
    if (recomputed !== manifest.generation) {
      mismatches.push(
        `generation ${manifest.generation} does not match the manifest content (${recomputed})`,
      );
    }

    if (mismatches.length > 0) {
      // A rejected release exposes no payload: nothing from it may be rendered
      // under a "verified" claim.
      return unverifiedCheck("mismatch", mismatches, manifest);
    }

    const payloads: Record<string, unknown> = {};
    const evidence: Record<string, ReleaseAssetEvidence> = {};
    for (const [path, bytes] of verified) {
      evidence[path] = {
        sha256: bytes.sha256,
        contentSha256: bytes.contentSha256,
        byteLength: bytes.byteLength,
      };
      const decoded = decodePayload(bytes.content);
      if (decoded.ok) payloads[path] = decoded.value;
    }

    return {
      status: "verified",
      manifest,
      mismatches: [],
      payloads,
      evidence,
    };
  } catch (error) {
    return unverifiedCheck(
      "unverified",
      [`release verification failed: ${describeError(error)}`],
      manifest,
    );
  }
}
