/**
 * Unit tests for the release-manifest adapter (src/utils/release-manifest.ts).
 *
 * Hermetic: the only fixture read from the world is the inline copy of a real
 * `dashboard-release.json` at the bottom of this file. Nothing touches the
 * network, the 1.2M-row payloads or the filesystem.
 *
 * Provenance of `REAL_MANIFEST_JSON`: produced on 2026-11-02 from the repo root
 * /home/howt/work/egg-n-bacon-housing with
 *
 *   uv run python scripts/export_app_data.py --output-dir /tmp/s5/manifest-fixture
 *
 * and only `dashboard-release.json` was copied into this file. The exporter's
 * own recorded generation is b2afd46d90b5368498138dcb930a0a59346bc24d152d3f86e1cfe0530b4e4ba0;
 * the independent Python reference for the same bytes is
 *
 *   content = {k: v for k, v in manifest.items() if k not in {"generation", "generatedAt"}}
 *   hashlib.sha256(json.dumps(content, sort_keys=True, separators=(",", ":"),
 *                             ensure_ascii=False).encode("utf-8")).hexdigest()
 *
 * which is the same string. The second fixture (`SYNTHETIC_MANIFEST`) is a
 * hand-built manifest with nested arrays/objects, unicode and nulls whose
 * reference generation was produced by the exporter's own `release_generation()`
 * (and independently by the plain `json.dumps(...)` above):
 * 184ad66c14a5a7498ecad13ca97168db912834e9be8f375c9b7c838b0a3f735d.
 *
 * The fixture deliberately contains no JSON boolean: `sanitize_for_json()` in
 * the exporter matches `bool` with its `int` branch, so a `true` in a manifest
 * would hash as `1` there while this adapter (and `app/scripts/validate-data.mjs`)
 * hashes `true`. The published manifest contains no boolean, so the two agree on
 * every real release; the case is recorded in the S5a report as a residual risk
 * rather than mirrored here.
 */

import { describe, expect, test } from "bun:test";

import {
  RELEASE_SCHEMA_VERSION,
  computeReleaseGeneration,
  loadReleaseCheck,
  parseReleaseManifest,
  verifyReleaseAssets,
  type ReleaseManifest,
} from "../../src/utils/release-manifest";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function decodeManifest(json: string): Record<string, unknown> {
  const value: unknown = JSON.parse(json);
  if (!isRecord(value)) throw new Error("fixture is not a JSON object");
  return value;
}

function requireManifest(raw: unknown): ReleaseManifest {
  const manifest = parseReleaseManifest(raw);
  if (manifest === null)
    throw new Error("expected a parseable release manifest");
  return manifest;
}

/** Decoded lazily: the verbatim manifest fixture is declared at the bottom. */
function realManifest(): Record<string, unknown> {
  return decodeManifest(REAL_MANIFEST_JSON);
}

const REAL_GENERATION =
  "b2afd46d90b5368498138dcb930a0a59346bc24d152d3f86e1cfe0530b4e4ba0";
const SYNTHETIC_GENERATION =
  "184ad66c14a5a7498ecad13ca97168db912834e9be8f375c9b7c838b0a3f735d";

// Well-known SHA-256 test vectors, so the asset checks do not lean on the
// implementation under test to produce their expected values.
const SHA256_EMPTY =
  "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855";
const SHA256_ABC =
  "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad";

const SYNTHETIC_MANIFEST: Record<string, unknown> = {
  schemaVersion: "1.0.0",
  generation: SYNTHETIC_GENERATION,
  generatedAt: "2026-01-02T03:04:05Z",
  observationRange: {
    startMonth: "1990-01",
    endMonth: "2026-10",
    completeYear: null,
  },
  periodDefinitions: {
    whole: { label: "all history (no period filter)", filter: "all" },
    year_2025: {
      label: "2025 complete year (year == 2025)",
      filter: "year == 2025",
    },
  },
  inclusionRules: {
    globalAggregates:
      "keeps every transaction row — including non-residential areas",
    areaSurfaces: "drops S$ artefacts 🏚 and reserves",
    excludedAreas: ["CENTRAL WATER CATCHMENT", "MANDAI", "SUNGEI KADUT"],
    excludedTransactions: null,
    nested: {
      Zeta: 1,
      alpha: [1, 2, { z: "kept", y: null, x: [] }],
      Émile: {},
      empty: [],
    },
  },
  provenance: {
    sources: [
      {
        name: "unified_dataset",
        bytes: 78165729,
        rows: 1234928,
        columns: ["month", "town"],
        sourcePublishedAt: null,
      },
    ],
  },
  assets: [
    {
      path: "a.json.gz",
      sha256: SHA256_EMPTY,
      bytes: 0,
      shape: "array",
      metricScopes: [],
    },
    {
      path: "b.json.gz",
      sha256: SHA256_ABC,
      bytes: 3,
      shape: "object",
      metricScopes: ["median_psf", "volume"],
    },
  ],
};

/** Fake `fetch` that serves fixed responses and records every requested URL. */
function makeFetcher(
  routes: Record<string, () => Response>,
  calls: string[] = [],
): { fetcher: typeof fetch; calls: string[] } {
  const fetcher: typeof fetch = async (input) => {
    const url =
      typeof input === "string"
        ? input
        : input instanceof URL
          ? input.href
          : input.url;
    calls.push(url);
    const route = routes[url];
    if (route === undefined) return new Response("not found", { status: 404 });
    return route();
  };
  return { fetcher, calls };
}

const MANIFEST_URL = "https://example.test/data/dashboard-release.json";
const ASSET_URLS: Record<string, string> = {
  "a.json.gz": "https://example.test/data/a.json.gz",
  "b.json.gz": "https://example.test/data/b.json.gz",
};

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), { status: 200 });
}

function bytesResponse(bytes: Uint8Array<ArrayBuffer>): Response {
  return new Response(bytes, { status: 200 });
}

describe("computeReleaseGeneration", () => {
  test("recomputes the exporter's recorded generation from a real manifest", async () => {
    const generation = await computeReleaseGeneration(realManifest());
    expect(generation).toBe(REAL_GENERATION);
    expect(generation).toBe(realManifest()["generation"]);
  });

  test("canonicalizes nested, unicode and null values exactly like Python", async () => {
    expect(await computeReleaseGeneration(SYNTHETIC_MANIFEST)).toBe(
      SYNTHETIC_GENERATION,
    );
  });

  test("excludes generatedAt from the id but not published content", async () => {
    const base = await computeReleaseGeneration(SYNTHETIC_MANIFEST);
    const otherClock = await computeReleaseGeneration({
      ...SYNTHETIC_MANIFEST,
      generatedAt: "2031-12-31T23:59:59Z",
    });
    expect(otherClock).toBe(base);

    const assets = SYNTHETIC_MANIFEST["assets"];
    if (!Array.isArray(assets)) throw new Error("fixture has no assets array");
    const [first] = assets;
    if (!isRecord(first)) throw new Error("fixture asset is not an object");
    const tampered = await computeReleaseGeneration({
      ...SYNTHETIC_MANIFEST,
      assets: [{ ...first, sha256: "0".repeat(64) }, ...assets.slice(1)],
    });
    expect(tampered).not.toBe(base);
  });
});

describe("parseReleaseManifest", () => {
  test("accepts the real exporter manifest", () => {
    expect(RELEASE_SCHEMA_VERSION).toBe("1.0.0");
    const manifest = requireManifest(realManifest());

    expect(manifest.schemaVersion).toBe("1.0.0");
    expect(manifest.generation).toBe(REAL_GENERATION);
    expect(manifest.generatedAt).toBe("2026-11-02T00:22:36Z");
    expect(manifest.observationRange.completeYear).toBe(2025);
    expect(manifest.assets).toHaveLength(7);
    expect(Object.keys(manifest.periodDefinitions).sort()).toEqual([
      "pre_covid",
      "recent",
      "whole",
      "year_2025",
    ]);
    expect(manifest.provenance.sources).toHaveLength(2);

    const mapMetrics = manifest.assets.find(
      (asset) => asset.path === "map_metrics.json.gz",
    );
    if (mapMetrics === undefined) throw new Error("map_metrics entry missing");
    expect(mapMetrics.shape).toBe("object");
    expect(mapMetrics.bytes).toBeGreaterThan(0);
    expect(mapMetrics.sha256).toHaveLength(64);
    expect(mapMetrics.metricScopes).toContain("median_psf");
  });

  test("rejects payloads outside the 1.0.0 contract", () => {
    const assets = SYNTHETIC_MANIFEST["assets"];
    if (!Array.isArray(assets)) throw new Error("fixture has no assets array");
    const [first] = assets;
    if (!isRecord(first)) throw new Error("fixture asset is not an object");

    const rejections: unknown[] = [
      null,
      [],
      "manifest",
      { ...SYNTHETIC_MANIFEST, schemaVersion: "2.0.0" },
      { ...SYNTHETIC_MANIFEST, schemaVersion: undefined },
      { ...SYNTHETIC_MANIFEST, generation: "" },
      { ...SYNTHETIC_MANIFEST, generatedAt: 17 },
      { ...SYNTHETIC_MANIFEST, assets: undefined },
      { ...SYNTHETIC_MANIFEST, assets: [{ ...first, sha256: "not-a-digest" }] },
      { ...SYNTHETIC_MANIFEST, assets: [{ ...first, bytes: -1 }] },
      { ...SYNTHETIC_MANIFEST, assets: [{ ...first, shape: "file" }] },
      { ...SYNTHETIC_MANIFEST, assets: [{ ...first, metricScopes: [1] }] },
      {
        ...SYNTHETIC_MANIFEST,
        observationRange: { startMonth: null, endMonth: "2026-10" },
      },
      { ...SYNTHETIC_MANIFEST, periodDefinitions: { whole: { label: "x" } } },
      { ...SYNTHETIC_MANIFEST, provenance: { sources: [null] } },
    ];

    for (const candidate of rejections) {
      expect(parseReleaseManifest(candidate)).toBeNull();
    }
  });
});

describe("verifyReleaseAssets", () => {
  test("accepts matching bytes and reports a tampered asset", async () => {
    const manifest = requireManifest(SYNTHETIC_MANIFEST);
    const good = {
      "a.json.gz": new Uint8Array(0),
      "b.json.gz": new TextEncoder().encode("abc"),
    };

    expect(await verifyReleaseAssets(manifest, good)).toHaveLength(0);

    const tampered = {
      ...good,
      "b.json.gz": new TextEncoder().encode("abd"),
    };
    const problems = await verifyReleaseAssets(manifest, tampered);
    expect(problems).toHaveLength(1);
    expect(problems[0]).toContain("hash mismatch: b.json.gz");

    const resized = {
      ...good,
      "b.json.gz": new TextEncoder().encode("ab"),
    };
    // A byte change is reported once: the file hash no longer matches, which
    // already implies the size check cannot vouch for the file.
    const resizedProblems = await verifyReleaseAssets(manifest, resized);
    expect(resizedProblems).toHaveLength(1);
    expect(resizedProblems[0]).toContain("hash mismatch: b.json.gz");
  });

  test("honours the only list", async () => {
    const manifest = requireManifest(SYNTHETIC_MANIFEST);
    const tampered = {
      "a.json.gz": new Uint8Array(0),
      "b.json.gz": new TextEncoder().encode("abd"),
    };

    expect(
      await verifyReleaseAssets(manifest, tampered, ["a.json.gz"]),
    ).toHaveLength(0);
    expect(
      await verifyReleaseAssets(manifest, tampered, ["b.json.gz"]),
    ).toHaveLength(1);
    expect(await verifyReleaseAssets(manifest, tampered)).toHaveLength(1);
  });

  test("reports missing bytes and unknown asset entries", async () => {
    const manifest = requireManifest(SYNTHETIC_MANIFEST);
    const problems = await verifyReleaseAssets(
      manifest,
      { "a.json.gz": new Uint8Array(0) },
      ["a.json.gz", "b.json.gz", "c.json.gz"],
    );

    expect(problems).toHaveLength(2);
    expect(problems[0]).toContain("no bytes supplied for b.json.gz");
    expect(problems[1]).toContain("records no asset entry for c.json.gz");
  });
});

describe("loadReleaseCheck", () => {
  test("reports an absent manifest for HTTP 404", async () => {
    const { fetcher } = makeFetcher({});
    const check = await loadReleaseCheck({
      manifestUrl: MANIFEST_URL,
      assetUrls: ASSET_URLS,
      fetcher,
    });

    expect(check.status).toBe("absent");
    expect(check.manifest).toBeNull();
    expect(check.mismatches).toHaveLength(0);
  });

  test("reports unverified for malformed JSON, wrong schema and a failed fetch", async () => {
    const malformed = await loadReleaseCheck({
      manifestUrl: MANIFEST_URL,
      assetUrls: ASSET_URLS,
      fetcher: makeFetcher({
        [MANIFEST_URL]: () => new Response("{not json", { status: 200 }),
      }).fetcher,
    });
    expect(malformed.status).toBe("unverified");
    expect(malformed.mismatches[0]).toContain("not valid JSON");

    const wrongSchema = await loadReleaseCheck({
      manifestUrl: MANIFEST_URL,
      assetUrls: ASSET_URLS,
      fetcher: makeFetcher({
        [MANIFEST_URL]: () =>
          jsonResponse({ ...SYNTHETIC_MANIFEST, schemaVersion: "9.9.9" }),
      }).fetcher,
    });
    expect(wrongSchema.status).toBe("unverified");
    expect(wrongSchema.mismatches[0]).toContain("schemaVersion 9.9.9");

    const offline = await loadReleaseCheck({
      manifestUrl: MANIFEST_URL,
      assetUrls: ASSET_URLS,
      fetcher: async () => {
        throw new Error("network down");
      },
    });
    expect(offline.status).toBe("unverified");
    expect(offline.mismatches[0]).toContain("network down");
  });

  test("verifies a matching release and only fetches the requested assets", async () => {
    const { fetcher, calls } = makeFetcher({
      [MANIFEST_URL]: () => jsonResponse(SYNTHETIC_MANIFEST),
      "https://example.test/data/a.json.gz": () =>
        bytesResponse(new Uint8Array(0)),
      "https://example.test/data/b.json.gz": () =>
        bytesResponse(new TextEncoder().encode("abc")),
    });

    const check = await loadReleaseCheck({
      manifestUrl: MANIFEST_URL,
      assetUrls: ASSET_URLS,
      verifyOnly: ["a.json.gz"],
      fetcher,
    });

    expect(check.status).toBe("verified");
    expect(check.mismatches).toHaveLength(0);
    expect(check.manifest?.generation).toBe(SYNTHETIC_GENERATION);
    expect(calls).toEqual([
      MANIFEST_URL,
      "https://example.test/data/a.json.gz",
    ]);
  });

  test("reports mismatch when the manifest content was edited after publication", async () => {
    const tamperedGeneration = await loadReleaseCheck({
      manifestUrl: MANIFEST_URL,
      assetUrls: ASSET_URLS,
      fetcher: makeFetcher({
        [MANIFEST_URL]: () =>
          jsonResponse({ ...SYNTHETIC_MANIFEST, generation: "0".repeat(64) }),
        "https://example.test/data/a.json.gz": () =>
          bytesResponse(new Uint8Array(0)),
        "https://example.test/data/b.json.gz": () =>
          bytesResponse(new TextEncoder().encode("abc")),
      }).fetcher,
    });

    expect(tamperedGeneration.status).toBe("mismatch");
    expect(tamperedGeneration.mismatches).toHaveLength(1);
    expect(tamperedGeneration.mismatches[0]).toContain(
      "does not match the manifest content",
    );
  });

  test("reports mismatch when a served asset is from another generation", async () => {
    const check = await loadReleaseCheck({
      manifestUrl: MANIFEST_URL,
      assetUrls: ASSET_URLS,
      fetcher: makeFetcher({
        [MANIFEST_URL]: () => jsonResponse(SYNTHETIC_MANIFEST),
        "https://example.test/data/a.json.gz": () =>
          bytesResponse(new Uint8Array(0)),
        "https://example.test/data/b.json.gz": () =>
          bytesResponse(new TextEncoder().encode("abd")),
      }).fetcher,
    });

    expect(check.status).toBe("mismatch");
    expect(check.mismatches).toHaveLength(1);
    expect(check.mismatches[0]).toContain("hash mismatch: b.json.gz");
  });

  test("treats a missing or unfetchable asset as unverified, not mixed", async () => {
    const missingUrl = await loadReleaseCheck({
      manifestUrl: MANIFEST_URL,
      assetUrls: { "a.json.gz": "https://example.test/data/a.json.gz" },
      fetcher: makeFetcher({
        [MANIFEST_URL]: () => jsonResponse(SYNTHETIC_MANIFEST),
        "https://example.test/data/a.json.gz": () =>
          bytesResponse(new Uint8Array(0)),
      }).fetcher,
    });

    // Downloading nothing proves nothing about the generation, so the honest
    // status is "unverified" rather than "mismatch".
    expect(missingUrl.status).toBe("unverified");
    expect(missingUrl.mismatches).toHaveLength(1);
    expect(missingUrl.mismatches[0]).toContain(
      "no asset URL provided for b.json.gz",
    );

    const unfetchable = await loadReleaseCheck({
      manifestUrl: MANIFEST_URL,
      assetUrls: ASSET_URLS,
      fetcher: makeFetcher({
        [MANIFEST_URL]: () => jsonResponse(SYNTHETIC_MANIFEST),
        "https://example.test/data/a.json.gz": () =>
          bytesResponse(new Uint8Array(0)),
      }).fetcher,
    });

    expect(unfetchable.status).toBe("unverified");
    expect(unfetchable.mismatches).toHaveLength(1);
    expect(unfetchable.mismatches[0]).toContain(
      "could not fetch b.json.gz (HTTP 404)",
    );
  });
});

/**
 * Real `app/public/data/dashboard-release.json` produced by
 * `uv run python scripts/export_app_data.py --output-dir /tmp/s5/manifest-fixture`
 * on 2026-11-02. Copied verbatim; the seven payloads are not included.
 */
const REAL_MANIFEST_JSON = String.raw`{
  "assets": [
    {
      "bytes": 756,
      "metricScopes": [
        "median_price",
        "median_psf",
        "volume",
        "by_property_type",
        "by_time_period"
      ],
      "path": "dashboard_overview.json.gz",
      "sha256": "69f4499e52ca0a82f15932fa14f62f4030f31053dea7aa8f7d3cb9b2313ecdbf",
      "shape": "object"
    },
    {
      "bytes": 5781,
      "metricScopes": [
        "median_price",
        "volume",
        "by_property_type",
        "by_time_period"
      ],
      "path": "dashboard_trends.json.gz",
      "sha256": "28df3ff70f377f0d4a39f8197b35a0f9b7a599e11568a1bb6de794768b381443",
      "shape": "array"
    },
    {
      "bytes": 6130,
      "metricScopes": [
        "median_psf",
        "rental_yield",
        "volume",
        "by_property_type",
        "by_time_period"
      ],
      "path": "dashboard_segments.json.gz",
      "sha256": "7cfed2e923e174ad4fbce9ef909a41398c5533d971fcaa53062b163abe363983",
      "shape": "object"
    },
    {
      "bytes": 4742,
      "metricScopes": [
        "median_price",
        "median_psf",
        "rental_yield",
        "volume",
        "by_property_type",
        "by_time_period",
        "spatial_hotspots",
        "affordability"
      ],
      "path": "dashboard_leaderboard.json.gz",
      "sha256": "4e9b139380d1490ee4f3d34dc061b54cfd4225b980d8fbb6ce212bebb2950346",
      "shape": "array"
    },
    {
      "bytes": 11286,
      "metricScopes": [
        "median_price",
        "median_psf",
        "volume",
        "rental_yield",
        "affordability",
        "by_property_type",
        "by_time_period"
      ],
      "path": "map_metrics.json.gz",
      "sha256": "a312995fc69fa2271f284d99e4f288bb8e1684c5a2ae01dbbb152cbcf9c36e11",
      "shape": "object"
    },
    {
      "bytes": 1114,
      "metricScopes": [
        "spatial_hotspots",
        "appreciation_growth"
      ],
      "path": "hotspots.json.gz",
      "sha256": "94f06d168fc1284bd4ee4f0a90e1d0d9bc2b3dc18946652bf6e375d0af99df9a",
      "shape": "object"
    },
    {
      "bytes": 1832,
      "metricScopes": [
        "amenity"
      ],
      "path": "amenity_summary.json.gz",
      "sha256": "68388c7eaa2e9cefa9a83e7fa51c644f0a1d92cc7938e02b313580868e20b759",
      "shape": "array"
    }
  ],
  "generatedAt": "2026-11-02T00:22:36Z",
  "generation": "b2afd46d90b5368498138dcb930a0a59346bc24d152d3f86e1cfe0530b4e4ba0",
  "inclusionRules": {
    "areaSurfaceFiles": [
      "dashboard_leaderboard.json.gz",
      "dashboard_segments.json.gz",
      "map_metrics.json.gz",
      "hotspots.json.gz",
      "amenity_summary.json.gz"
    ],
    "areaSurfaces": "drops transactions in NON_RESIDENTIAL_AREAS (no residential zoning)",
    "excludedAreas": [
      "CENTRAL WATER CATCHMENT",
      "MANDAI",
      "SUNGEI KADUT"
    ],
    "excludedTransactions": 456,
    "globalAggregates": "keeps every transaction row, including non-residential areas"
  },
  "observationRange": {
    "completeYear": 2025,
    "endMonth": "2026-10",
    "startMonth": "1990-01"
  },
  "periodDefinitions": {
    "pre_covid": {
      "filter": "year <= 2021",
      "label": "through 2021 (year <= 2021)"
    },
    "recent": {
      "filter": "year >= 2022",
      "label": "2022 onward (year >= 2022)"
    },
    "whole": {
      "filter": "all",
      "label": "all history (no period filter)"
    },
    "year_2025": {
      "filter": "year == 2025",
      "label": "2025 complete year (year == 2025)"
    }
  },
  "provenance": {
    "sources": [
      {
        "bytes": 78165729,
        "columns": [
          "month",
          "town",
          "flat_type",
          "block",
          "street_name",
          "storey_range",
          "floor_area_sqm",
          "flat_model",
          "lease_commence_date",
          "price",
          "remaining_lease",
          "floor_area_sqft",
          "transaction_date",
          "property_type",
          "storey_min",
          "storey_max",
          "address",
          "property_segment",
          "is_ec",
          "project_name",
          "area_sqft",
          "Unit Price ($ PSF)",
          "sale_date",
          "type_of_sale",
          "type_of_area",
          "area_sqm",
          "Unit Price ($ PSM)",
          "nett_price",
          "property_subtype",
          "number_of_units",
          "tenure",
          "postal_district",
          "market_segment",
          "floor_level",
          "area",
          "lat",
          "lon",
          "psf",
          "nearest_schoolPRIMARY_dist",
          "nearest_schoolSECONDARY_dist",
          "nearest_schoolJUNIOR_dist",
          "dist_to_nearest_school",
          "nearest_top_primary_school_dist",
          "nearest_top_secondary_school_dist",
          "school_accessibility_score",
          "nearest_mrt_station",
          "nearest_mrt_tier",
          "nearest_mrt_is_interchange",
          "dist_to_nearest_mrt",
          "nearest_mrt_score",
          "dist_to_nearest_mall",
          "nearest_mall",
          "dist_to_nearest_hawker",
          "nearest_hawker",
          "dist_to_nearest_supermarket",
          "nearest_supermarket",
          "dist_to_nearest_park",
          "nearest_park",
          "dist_to_nearest_childcare",
          "nearest_childcare",
          "dist_to_nearest_kindergarten",
          "nearest_kindergarten",
          "dist_to_nearest_bus_stop",
          "nearest_bus_stop",
          "dist_to_nearest_chas_clinic",
          "nearest_chas_clinic",
          "dist_to_nearest_sports_facility",
          "nearest_sports_facility",
          "dist_to_nearest_community_club",
          "nearest_community_club",
          "dist_to_nearest_green_mark_building",
          "nearest_green_mark_building",
          "max_floor_lvl",
          "year_completed",
          "total_dwelling_units",
          "residential",
          "commercial",
          "market_hawker",
          "multistorey_carpark",
          "planning_area",
          "region",
          "rental_yield_pct",
          "cpi",
          "sora_rate",
          "sora_3m",
          "unemployment_rate",
          "gdp",
          "hdb_rpi",
          "ura_ppi",
          "wage_growth",
          "dwelling_units_in_town",
          "population_in_town",
          "population_per_dwelling",
          "annual_value",
          "property_tax",
          "median_monthly_income",
          "price_stratum"
        ],
        "name": "unified_dataset",
        "path": "data/pipeline/04_platinum/unified_dataset.parquet",
        "rows": 1234928,
        "sha256": "897eaa505c365959f8c07337359f38c8cba69ac1a3cc9cba09818a577fe9d284",
        "sourcePublishedAt": null
      },
      {
        "bytes": 397524,
        "columns": [
          "planning_area",
          "month",
          "median_price",
          "mean_price",
          "transaction_count",
          "avg_psf",
          "median_rental_yield",
          "avg_rental_yield",
          "median_monthly_income",
          "affordability_ratio",
          "affordability_class"
        ],
        "name": "pa_monthly_metrics",
        "path": "data/pipeline/04_platinum/metrics/pa_monthly_metrics.parquet",
        "rows": 13201,
        "sha256": "05b6cb1c052806843b7df2ad20c353f8ce5f1b02424e78381fdabeb41072b2db",
        "sourcePublishedAt": null
      }
    ]
  },
  "schemaVersion": "1.0.0"
}`;
