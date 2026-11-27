/**
 * UI-1 at the explorer's own data path: `loadVerifiedRelease`, which is what
 * `ExplorerWorkspace` renders from.
 *
 * The defect this pins: the workspace used to verify the assets with one set of
 * responses and then fetch the same URLs again for display, so a figure on
 * screen could come from a response no digest had covered while the page said
 * the generation was verified. These tests mock `fetch` per request, so the
 * second response for a URL can carry different bytes from the first — and
 * those bytes must never be rendered as verified, including after a refresh.
 */

import { beforeEach, describe, expect, test } from "bun:test";
import { createHash } from "node:crypto";

import {
  clearVerifiedPayloads,
  loadVerifiedRelease,
  readVerifiedPayload,
  verifiedPayloadKey,
} from "../../src/hooks/useGzipJson";
import {
  RELEASE_SCHEMA_VERSION,
  computeReleaseGeneration,
} from "../../src/utils/release-manifest";

const MANIFEST_URL = "https://example.test/data/dashboard-release.json";
const MAP_METRICS = "map_metrics.json.gz";
const OVERVIEW = "dashboard_overview.json.gz";
const ASSET_URLS: Record<string, string> = {
  [MAP_METRICS]: "https://example.test/data/map_metrics.json.gz",
  [OVERVIEW]: "https://example.test/data/dashboard_overview.json.gz",
};

/** Mirrors `releaseScope` in ExplorerWorkspace: one scope per manifest path. */
function scope(path: string): string {
  return `explore:${path}`;
}

function digest(bytes: Uint8Array): string {
  return createHash("sha256").update(bytes).digest("hex");
}

const encoder = new TextEncoder();

/** The payloads one release serves, as JSON text. */
const PAYLOAD_A: Record<string, string> = {
  [MAP_METRICS]: JSON.stringify({
    whole: { hdb: { TAMPINES: { volume: 3 } } },
  }),
  [OVERVIEW]: JSON.stringify({
    stats: { whole_hdb: { median_price: 628000 } },
  }),
};
/** A different release: same URLs, same shapes, different numbers. */
const PAYLOAD_B: Record<string, string> = {
  [MAP_METRICS]: JSON.stringify({
    whole: { hdb: { TAMPINES: { volume: 999 } } },
  }),
  [OVERVIEW]: JSON.stringify({
    stats: { whole_hdb: { median_price: 999999 } },
  }),
};

/** A manifest describing `payloads` exactly, with its content-derived id. */
async function manifestFor(
  payloads: Record<string, string>,
): Promise<Record<string, unknown>> {
  const assets = Object.entries(payloads).map(([path, text]) => {
    const bytes = encoder.encode(text);
    return {
      path,
      sha256: digest(bytes),
      contentSha256: digest(bytes),
      bytes: bytes.byteLength,
      shape: text.trimStart().startsWith("[") ? "array" : "object",
      metricScopes: [],
    };
  });
  const body: Record<string, unknown> = {
    schemaVersion: RELEASE_SCHEMA_VERSION,
    generatedAt: "2026-11-02T00:00:00Z",
    observationRange: {
      startMonth: "1990-01",
      endMonth: "2026-10",
      completeYear: 2025,
    },
    periodDefinitions: {},
    inclusionRules: {},
    provenance: { sources: [] },
    assets,
  };
  return { ...body, generation: await computeReleaseGeneration(body) };
}

/**
 * A mutable "server": `manifest` and `served` can be changed between requests,
 * so a test can make the second response for a URL carry different bytes.
 */
interface Server {
  manifest: Record<string, unknown> | null;
  served: Record<string, string>;
  failAssets: boolean;
  calls: string[];
}

function fetcherFor(server: Server): typeof fetch {
  return async (input) => {
    const url =
      typeof input === "string"
        ? input
        : input instanceof URL
          ? input.href
          : input.url;
    server.calls.push(url);

    if (url === MANIFEST_URL) {
      if (server.manifest === null) {
        return new Response("not found", { status: 404 });
      }
      return new Response(JSON.stringify(server.manifest), { status: 200 });
    }

    const path = Object.keys(ASSET_URLS).find(
      (candidate) => ASSET_URLS[candidate] === url,
    );
    if (path === undefined) return new Response("not found", { status: 404 });
    if (server.failAssets) throw new Error("network down");
    const text = server.served[path];
    if (text === undefined) return new Response("not found", { status: 404 });
    return new Response(encoder.encode(text), { status: 200 });
  };
}

function load(server: Server) {
  return loadVerifiedRelease({
    manifestUrl: MANIFEST_URL,
    assetUrls: ASSET_URLS,
    verifyOnly: [MAP_METRICS, OVERVIEW],
    scopeFor: scope,
    fetcher: fetcherFor(server),
  });
}

beforeEach(() => {
  clearVerifiedPayloads();
});

describe("loadVerifiedRelease — verified bytes are the rendered bytes (UI-1)", () => {
  test("a later response for the same URL never renders as verified", async () => {
    const server: Server = {
      manifest: await manifestFor(PAYLOAD_A),
      served: { ...PAYLOAD_A },
      failAssets: false,
      calls: [],
    };

    // First load: the served bytes are the ones the manifest records.
    const first = await load(server);
    expect(first.check.status).toBe("verified");
    expect(first.payloads[MAP_METRICS].data).toEqual(
      JSON.parse(PAYLOAD_A[MAP_METRICS]),
    );
    expect(first.payloads[OVERVIEW].data).toEqual(
      JSON.parse(PAYLOAD_A[OVERVIEW]),
    );

    // The same URL now answers with different bytes. This is exactly the
    // response the old code fetched separately and rendered unchecked.
    server.served = { ...PAYLOAD_B };
    const refreshed = await load(server);

    // Nothing from the second response may be presented as verified.
    expect(refreshed.check.status).toBe("mismatch");
    expect(refreshed.payloads).toEqual({});
    expect(
      refreshed.check.mismatches.some((line) => line.includes("hash mismatch")),
    ).toBe(true);

    // The cached entry is still the payload that verified, never B.
    const generationA = first.check.manifest!.generation;
    const cachedA = readVerifiedPayload(scope(MAP_METRICS), generationA);
    expect(cachedA?.data).toEqual(JSON.parse(PAYLOAD_A[MAP_METRICS]));
    expect(cachedA?.sha256).toBe(
      digest(encoder.encode(PAYLOAD_A[MAP_METRICS])),
    );

    // And no key reaches B at all.
    const storedB = JSON.stringify(JSON.parse(PAYLOAD_B[MAP_METRICS]));
    for (const generation of [
      generationA,
      refreshed.check.manifest!.generation,
    ]) {
      const entry = readVerifiedPayload(scope(MAP_METRICS), generation);
      if (entry === null) continue;
      expect(JSON.stringify(entry.data)).not.toBe(storedB);
    }
  });

  test("a refresh re-verifies and replaces the payload under the new generation", async () => {
    const server: Server = {
      manifest: await manifestFor(PAYLOAD_A),
      served: { ...PAYLOAD_A },
      failAssets: false,
      calls: [],
    };

    const first = await load(server);
    const generationA = first.check.manifest!.generation;
    expect(first.check.status).toBe("verified");

    // A new publication: new manifest generation, new payload bytes.
    server.manifest = await manifestFor(PAYLOAD_B);
    server.served = { ...PAYLOAD_B };
    const refreshed = await load(server);

    expect(refreshed.check.status).toBe("verified");
    const generationB = refreshed.check.manifest!.generation;
    expect(generationB).not.toBe(generationA);
    expect(refreshed.payloads[OVERVIEW].data).toEqual(
      JSON.parse(PAYLOAD_B[OVERVIEW]),
    );

    // One generation-qualified key per payload: the old generation is no longer
    // readable, so A can never be shown as B.
    expect(readVerifiedPayload(scope(OVERVIEW), generationA)).toBeNull();
    expect(readVerifiedPayload(scope(OVERVIEW), generationB)?.data).toEqual(
      JSON.parse(PAYLOAD_B[OVERVIEW]),
    );
    expect(verifiedPayloadKey(scope(OVERVIEW), generationB)).toContain(
      generationB,
    );
    expect(verifiedPayloadKey(scope(OVERVIEW), generationA)).not.toBe(
      verifiedPayloadKey(scope(OVERVIEW), generationB),
    );
  });

  test("a payload verified for one generation is not readable under another", async () => {
    const server: Server = {
      manifest: await manifestFor(PAYLOAD_A),
      served: { ...PAYLOAD_A },
      failAssets: false,
      calls: [],
    };
    const result = await load(server);
    const generation = result.check.manifest!.generation;

    expect(readVerifiedPayload(scope(MAP_METRICS), generation)).not.toBeNull();
    // Any other generation is a different key, and has no payload.
    expect(readVerifiedPayload(scope(MAP_METRICS), "0".repeat(64))).toBeNull();
    expect(
      readVerifiedPayload(scope(MAP_METRICS), `${generation}-other`),
    ).toBeNull();
  });

  test("each URL is fetched once per load — no second fetch for display", async () => {
    const server: Server = {
      manifest: await manifestFor(PAYLOAD_A),
      served: { ...PAYLOAD_A },
      failAssets: false,
      calls: [],
    };

    await load(server);

    expect(server.calls).toEqual([
      MANIFEST_URL,
      ASSET_URLS[MAP_METRICS],
      ASSET_URLS[OVERVIEW],
    ]);
    expect(new Set(server.calls).size).toBe(server.calls.length);
  });

  test("a fetch failure stays unverified, never mismatch, and exposes no payload", async () => {
    const server: Server = {
      manifest: await manifestFor(PAYLOAD_A),
      served: { ...PAYLOAD_A },
      failAssets: true,
      calls: [],
    };

    const result = await load(server);

    // Downloading nothing proves nothing about the generation.
    expect(result.check.status).toBe("unverified");
    expect(result.payloads).toEqual({});
    expect(
      result.check.mismatches.some((line) =>
        line.includes("could not fetch map_metrics.json.gz"),
      ),
    ).toBe(true);
  });

  test("an absent manifest exposes no payload and stays absent", async () => {
    const server: Server = {
      manifest: null,
      served: { ...PAYLOAD_A },
      failAssets: false,
      calls: [],
    };

    const result = await load(server);

    expect(result.check.status).toBe("absent");
    expect(result.payloads).toEqual({});
    // Only the manifest was requested; nothing was rendered from an asset.
    expect(server.calls).toEqual([MANIFEST_URL]);
  });
});
