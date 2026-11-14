/**
 * Verified loader for the v2 observed-period pack.
 *
 * Reads the discovery manifest, verifies the **exact bytes it will display**
 * against the recorded sha256, recomputes the generation from the manifest
 * identity, and only then parses the payloads. There is no partial success and
 * no silent fallback to the v1 release: a caller receives either a verified
 * pack or an explicit state.
 *
 * States:
 * - `absent`  — no v2 manifest published yet; the caller shows the legacy view.
 * - `invalid` — manifest/payload missing, altered, or inconsistent. The caller
 *               must surface the failure and must not substitute v1 numbers.
 * - `ready`   — every byte verified; `pack` is safe to render.
 */

import {
  parsePeriodPack,
  type ParseResult,
  type PeriodPack,
} from "./observed-periods";
import { V2_SCHEMA_VERSION } from "./observed-periods";
import {
  MONTHLY_ROLES,
  monthlyRole,
  parseMonthlyHistory,
  type MonthlyHistory,
  type MonthlyRole,
} from "./observed-monthly";
import { decompressGzip } from "./gzip";

export const V2_MANIFEST_PATH = "data/dashboard-release-v2.json";
export { V2_SCHEMA_VERSION };

export const V2_CORE_ROLES = ["periods", "summary"] as const;
export type V2CoreRole = (typeof V2_CORE_ROLES)[number];
export const V2_MONTHLY_ROLES = MONTHLY_ROLES;
export type V2MonthlyRole = MonthlyRole;
export type V2Role = V2CoreRole | V2MonthlyRole;

export interface V2ManifestAsset {
  role: V2Role;
  path: string;
  bytes: number;
  sha256: string;
}

export interface V2ManifestIdentity {
  schemaVersion: string;
  methodVersion: string;
  cutoffMonth: string;
  inputs: Record<string, string>;
  roles: Record<string, string>;
}

export interface V2Manifest {
  schemaVersion: string;
  methodVersion: string;
  generation: string;
  cutoffMonth: string;
  cutoffSource: string;
  identity: V2ManifestIdentity;
  assets: V2ManifestAsset[];
}

export type ManifestParse =
  | { ok: true; manifest: V2Manifest }
  | { ok: false; errors: string[] };

export type PackLoad =
  | { state: "ready"; manifest: V2Manifest; pack: PeriodPack }
  | { state: "absent" }
  | { state: "invalid"; errors: string[] };

const SHA256_PATTERN = /^[0-9a-f]{64}$/;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isCoreRole(value: unknown): value is V2CoreRole {
  return (V2_CORE_ROLES as readonly string[]).includes(String(value));
}

function isMonthlyRole(value: unknown): value is V2MonthlyRole {
  return (V2_MONTHLY_ROLES as readonly string[]).includes(String(value));
}

function isRole(value: unknown): value is V2Role {
  return isCoreRole(value) || isMonthlyRole(value);
}

/** Canonical JSON: sorted keys, compact separators, no NaN. */
export function canonicalJson(value: unknown): string {
  if (value === null || typeof value !== "object") {
    if (typeof value === "number" && !Number.isFinite(value)) {
      throw new Error("canonicalJson refuses non-finite numbers");
    }
    return JSON.stringify(value);
  }
  if (Array.isArray(value)) {
    return `[${value.map((item) => canonicalJson(item)).join(",")}]`;
  }
  const entries = Object.keys(value as Record<string, unknown>)
    .sort((left, right) => left.localeCompare(right))
    .map(
      (key) =>
        `${JSON.stringify(key)}:${canonicalJson((value as Record<string, unknown>)[key])}`,
    );
  return `{${entries.join(",")}}`;
}

export async function sha256Hex(
  payload: Uint8Array | ArrayBuffer,
): Promise<string> {
  const source = payload instanceof Uint8Array ? payload : new Uint8Array(payload);
  // Copy into an ArrayBuffer-backed view so the digest input type is exact.
  const bytes = new Uint8Array(source.byteLength);
  bytes.set(source);
  if (!globalThis.crypto?.subtle) {
    throw new Error("Web Crypto is unavailable; cannot verify pack bytes");
  }
  const digest = await globalThis.crypto.subtle.digest("SHA-256", bytes.buffer);
  return [...new Uint8Array(digest)]
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}

/**
 * Generation = sha256(canonical identity). Mirrors
 * `scripts/v2_observed.py::compute_generation`, so a client can prove the
 * manifest was not edited around the payloads it ships.
 */
export async function computeV2Generation(
  identity: V2ManifestIdentity,
): Promise<string> {
  const canonical = canonicalJson({
    schemaVersion: identity.schemaVersion,
    methodVersion: identity.methodVersion,
    cutoffMonth: identity.cutoffMonth,
    inputs: Object.fromEntries(
      Object.entries(identity.inputs).sort(([a], [b]) => a.localeCompare(b)),
    ),
    roles: Object.fromEntries(
      Object.entries(identity.roles).sort(([a], [b]) => a.localeCompare(b)),
    ),
  });
  return sha256Hex(new TextEncoder().encode(canonical));
}

export function parseV2Manifest(raw: unknown): ManifestParse {
  const errors: string[] = [];

  if (!isRecord(raw)) return { ok: false, errors: ["manifest is not an object"] };
  if (raw.schemaVersion !== V2_SCHEMA_VERSION) {
    errors.push(`unsupported manifest schemaVersion ${String(raw.schemaVersion)}`);
  }
  if (typeof raw.generation !== "string" || !SHA256_PATTERN.test(raw.generation)) {
    errors.push("manifest generation is not a sha256");
  }
  if (typeof raw.cutoffMonth !== "string") {
    errors.push("manifest has no cutoffMonth");
  }

  const identity = raw.identity;
  if (!isRecord(identity)) {
    return { ok: false, errors: [...errors, "manifest has no identity"] };
  }
  if (
    typeof identity.schemaVersion !== "string" ||
    typeof identity.methodVersion !== "string" ||
    typeof identity.cutoffMonth !== "string" ||
    !isRecord(identity.inputs) ||
    !isRecord(identity.roles)
  ) {
    return { ok: false, errors: [...errors, "manifest identity is malformed"] };
  }

  const assets = raw.assets;
  if (!Array.isArray(assets)) {
    return { ok: false, errors: [...errors, "manifest has no assets"] };
  }

  const parsedAssets: V2ManifestAsset[] = [];
  const seenRoles = new Set<string>();
  for (const [index, asset] of assets.entries()) {
    if (!isRecord(asset)) {
      errors.push(`assets[${index}] is not an object`);
      continue;
    }
    if (!isRole(asset.role)) {
      errors.push(`assets[${index}] has an unknown role`);
      continue;
    }
    if (seenRoles.has(asset.role)) {
      errors.push(`duplicate role ${asset.role}`);
      continue;
    }
    if (typeof asset.path !== "string" || asset.path.includes("..")) {
      errors.push(`asset ${asset.role} has an unsafe path`);
      continue;
    }
    if (typeof asset.sha256 !== "string" || !SHA256_PATTERN.test(asset.sha256)) {
      errors.push(`asset ${asset.role} has no sha256`);
      continue;
    }
    if (typeof asset.bytes !== "number" || asset.bytes <= 0) {
      errors.push(`asset ${asset.role} has no byte count`);
      continue;
    }
    seenRoles.add(asset.role);
    parsedAssets.push({
      role: asset.role,
      path: asset.path,
      bytes: asset.bytes,
      sha256: asset.sha256,
    });
  }

  for (const role of V2_CORE_ROLES) {
    if (!seenRoles.has(role)) errors.push(`manifest is missing role ${role}`);
  }
  // RF09 publishes one complete pack: a manifest that declares the monthly
  // history for some property types but not others would let a reader compare
  // periods that never shared a generation.
  for (const role of V2_MONTHLY_ROLES) {
    if (!seenRoles.has(role)) errors.push(`manifest is missing role ${role}`);
  }

  const roleHashes = Object.fromEntries(
    parsedAssets.map((asset) => [asset.role, asset.sha256]),
  );
  const declaredRoles = identity.roles as Record<string, unknown>;
  for (const [role, hash] of Object.entries(roleHashes)) {
    if (declaredRoles[role] !== hash) {
      errors.push(`identity role ${role} does not match its asset hash`);
    }
  }

  if (errors.length > 0) return { ok: false, errors };

  return {
    ok: true,
    manifest: {
      schemaVersion: V2_SCHEMA_VERSION,
      methodVersion: identity.methodVersion,
      generation: String(raw.generation),
      cutoffMonth: String(raw.cutoffMonth),
      cutoffSource: typeof raw.cutoffSource === "string" ? raw.cutoffSource : "unknown",
      identity: {
        schemaVersion: identity.schemaVersion,
        methodVersion: identity.methodVersion,
        cutoffMonth: identity.cutoffMonth,
        inputs: Object.fromEntries(
          Object.entries(identity.inputs as Record<string, unknown>).map(([key, value]) => [
            key,
            String(value),
          ]),
        ),
        roles: Object.fromEntries(
          Object.entries(identity.roles as Record<string, unknown>).map(([key, value]) => [
            key,
            String(value),
          ]),
        ),
      },
      assets: parsedAssets,
    },
  };
}

export interface LoadPackOptions {
  /** Base URL including the trailing slash (e.g. `import.meta.env.BASE_URL`). */
  baseUrl: string;
  /** Returns bytes, or `null` for a 404 (no v2 published). */
  fetchBytes?: (url: string) => Promise<ArrayBuffer | null>;
  /** Decodes verified gzip bytes into an object. */
  decode?: (bytes: ArrayBuffer) => Promise<unknown>;
}

async function defaultFetchBytes(url: string): Promise<ArrayBuffer | null> {
  const response = await fetch(url, { cache: "no-store" });
  if (response.status === 404) return null;
  if (!response.ok) {
    throw new Error(`HTTP ${response.status} for ${url}`);
  }
  return response.arrayBuffer();
}

async function defaultDecode(bytes: ArrayBuffer): Promise<unknown> {
  const text = await decompressGzip(bytes);
  try {
    return JSON.parse(text);
  } catch (error) {
    throw new Error(`payload is not valid JSON: ${String(error)}`);
  }
}

/** True when the bytes start with the gzip magic number (`1f 8b`). */
function isGzipBytes(bytes: ArrayBuffer): boolean {
  const view = new Uint8Array(bytes, 0, Math.min(2, bytes.byteLength));
  return view.length === 2 && view[0] === 0x1f && view[1] === 0x8b;
}

/**
 * Load and verify the pack.
 *
 * The returned `pack` is produced from the bytes that were hashed in this call,
 * so a caller cannot accidentally render a different response from the same
 * URL.
 *
 * Asset paths in the manifest are relative to the manifest itself
 * (`observed/<generation>/periods.json.gz` beside `dashboard-release-v2.json`),
 * so they are resolved under the manifest's directory rather than the site
 * root.
 */
export type AssetLoad =
  | { state: "ready"; payload: unknown }
  | { state: "invalid"; errors: string[] };

/**
 * Fetch, verify and decode one manifest asset.
 *
 * The bytes are checked against the manifest's recorded length and sha256, and
 * only those bytes are decoded — the same guarantee the eager loader makes for
 * the period/summary pair. Monthly history uses this so a surface can verify
 * the one property payload it is about to display without downloading the
 * other three.
 */
export async function loadManifestAsset(
  manifest: V2Manifest,
  role: V2Role,
  options: LoadPackOptions,
): Promise<AssetLoad> {
  const fetchBytes = options.fetchBytes ?? defaultFetchBytes;
  const decode = options.decode ?? defaultDecode;
  const base = options.baseUrl.endsWith("/") ? options.baseUrl : `${options.baseUrl}/`;
  const manifestDir = V2_MANIFEST_PATH.slice(
    0,
    V2_MANIFEST_PATH.lastIndexOf("/") + 1,
  );

  const asset = manifest.assets.find((entry) => entry.role === role);
  if (asset === undefined) {
    return { state: "invalid", errors: [`manifest has no asset for role ${role}`] };
  }

  let bytes: ArrayBuffer | null;
  try {
    bytes = await fetchBytes(`${base}${manifestDir}${asset.path}`);
  } catch (error) {
    return {
      state: "invalid",
      errors: [`${asset.role}: ${error instanceof Error ? error.message : "fetch failed"}`],
    };
  }
  if (bytes === null) {
    return { state: "invalid", errors: [`missing asset ${asset.path}`] };
  }
  if (bytes.byteLength !== asset.bytes) {
    // A host that labels a stored `.gz` file with `Content-Encoding: gzip`
    // makes the browser inflate it, so the pinned bytes are no longer what
    // arrives. Say so rather than reporting a bare size mismatch.
    const hint = isGzipBytes(bytes)
      ? ""
      : " (the response was transport-decoded, so its pinned bytes cannot be checked; serve the payload without a Content-Encoding header)";
    return {
      state: "invalid",
      errors: [
        `${asset.path}: expected ${asset.bytes} bytes, received ${bytes.byteLength}${hint}`,
      ],
    };
  }
  const digest = await sha256Hex(bytes);
  if (digest !== asset.sha256) {
    return { state: "invalid", errors: [`${asset.path}: sha256 mismatch (${digest})`] };
  }
  try {
    return { state: "ready", payload: await decode(bytes) };
  } catch (error) {
    return {
      state: "invalid",
      errors: [`${asset.path}: ${error instanceof Error ? error.message : "decode failed"}`],
    };
  }
}

export type HistoryLoad =
  | { state: "ready"; history: MonthlyHistory }
  | { state: "invalid"; errors: string[] };

/**
 * Load one property type's monthly history through the verified manifest.
 *
 * The property type is derived from the manifest role, and the parsed payload
 * must declare the same type and cutoff: a pack cannot lend its generation to
 * a history for a different scope.
 */
export async function loadObservedHistory(
  manifest: V2Manifest,
  propertyType: Parameters<typeof monthlyRole>[0],
  options: LoadPackOptions,
): Promise<HistoryLoad> {
  const loaded = await loadManifestAsset(manifest, monthlyRole(propertyType), options);
  if (loaded.state !== "ready") return loaded;

  const parsed = parseMonthlyHistory(loaded.payload, {
    propertyType,
    cutoffMonth: manifest.cutoffMonth,
  });
  if (!parsed.ok) return { state: "invalid", errors: parsed.errors };
  return { state: "ready", history: parsed.history };
}

/**
 * Load and verify the pack.
 *
 * The returned `pack` is produced from the bytes that were hashed in this call,
 * so a caller cannot accidentally render a different response from the same
 * URL.
 *
 * Asset paths in the manifest are relative to the manifest itself
 * (`observed/<generation>/periods.json.gz` beside `dashboard-release-v2.json`),
 * so they are resolved under the manifest's directory rather than the site
 * root.
 */
export async function loadObservedPack(options: LoadPackOptions): Promise<PackLoad> {
  const fetchBytes = options.fetchBytes ?? defaultFetchBytes;
  const decode = options.decode ?? defaultDecode;
  const base = options.baseUrl.endsWith("/") ? options.baseUrl : `${options.baseUrl}/`;
  const manifestDir = V2_MANIFEST_PATH.slice(
    0,
    V2_MANIFEST_PATH.lastIndexOf("/") + 1,
  );

  let manifestBytes: ArrayBuffer | null;
  try {
    manifestBytes = await fetchBytes(`${base}${V2_MANIFEST_PATH}`);
  } catch (error) {
    return {
      state: "invalid",
      errors: [error instanceof Error ? error.message : "manifest fetch failed"],
    };
  }
  if (manifestBytes === null) return { state: "absent" };

  let rawManifest: unknown;
  try {
    rawManifest = JSON.parse(new TextDecoder().decode(manifestBytes));
  } catch (error) {
    return {
      state: "invalid",
      errors: [`manifest is not valid JSON: ${String(error)}`],
    };
  }

  const parsed = parseV2Manifest(rawManifest);
  if (!parsed.ok) return { state: "invalid", errors: parsed.errors };
  const manifest = parsed.manifest;

  const recomputed = await computeV2Generation(manifest.identity);
  if (recomputed !== manifest.generation) {
    return {
      state: "invalid",
      errors: [
        `generation mismatch: manifest ${manifest.generation}, recomputed ${recomputed}`,
      ],
    };
  }

  const payloads: Partial<Record<V2Role, unknown>> = {};
  for (const asset of manifest.assets) {
    // Monthly history is large and per-property: it is verified and decoded on
    // demand by `loadObservedHistory`, against this same manifest generation.
    if (isMonthlyRole(asset.role)) continue;
    let bytes: ArrayBuffer | null;
    try {
      bytes = await fetchBytes(`${base}${manifestDir}${asset.path}`);
    } catch (error) {
      return {
        state: "invalid",
        errors: [
          `${asset.role}: ${error instanceof Error ? error.message : "fetch failed"}`,
        ],
      };
    }
    if (bytes === null) {
      return { state: "invalid", errors: [`missing asset ${asset.path}`] };
    }
    if (bytes.byteLength !== asset.bytes) {
      // A host that labels a stored `.gz` file with `Content-Encoding: gzip`
      // makes the browser inflate it, so the pinned bytes are no longer what
      // arrives. Say so rather than reporting a bare size mismatch.
      const hint = isGzipBytes(bytes)
        ? ""
        : " (the response was transport-decoded, so its pinned bytes cannot be checked; serve the payload without a Content-Encoding header)";
      return {
        state: "invalid",
        errors: [
          `${asset.path}: expected ${asset.bytes} bytes, received ${bytes.byteLength}${hint}`,
        ],
      };
    }
    const digest = await sha256Hex(bytes);
    if (digest !== asset.sha256) {
      return {
        state: "invalid",
        errors: [`${asset.path}: sha256 mismatch (${digest})`],
      };
    }
    try {
      payloads[asset.role] = await decode(bytes);
    } catch (error) {
      return {
        state: "invalid",
        errors: [
          `${asset.path}: ${error instanceof Error ? error.message : "decode failed"}`,
        ],
      };
    }
  }

  const packResult: ParseResult = parsePeriodPack(
    payloads.periods,
    payloads.summary,
  );
  if (!packResult.ok) return { state: "invalid", errors: packResult.errors };

  if (packResult.pack.cutoffMonth !== manifest.cutoffMonth) {
    return {
      state: "invalid",
      errors: ["pack cutoff does not match the manifest"],
    };
  }

  return { state: "ready", manifest, pack: packResult.pack };
}
