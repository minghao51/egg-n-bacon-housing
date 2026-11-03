/**
 * Unit tests for the build-time area-fieldnote loader
 * (src/utils/area-page.ts).
 *
 * Every fixture is written by the test into a fresh temporary directory in the
 * published layout (`public/data/*.json.gz` + an optional
 * `dashboard-release.json`), so nothing here touches the repository's real
 * assets, the network or a running server.
 *
 * The fixture values are copies of the published sections, taken on 2026-11-02
 * from `app/public/data/map_metrics.json.gz` and
 * `app/public/data/dashboard_overview.json.gz` with only the approved metrics
 * (`median_price`, `median_psf`, `volume`) kept:
 * - `year_2025_hdb`: all 31 published areas (Tampines 710000/620/1921,
 *   Bedok 548000/591/1208);
 * - `year_2025_ec`: all 16 published areas (Tampines 1664000/1754/1382; Bedok
 *   has no EC transactions, so it has no entry);
 * - `whole_hdb` / `recent_hdb`: a subset (Tampines, Bedok and the
 *   all-history-only Lim Chu Kang), which is enough to exercise "published
 *   elsewhere" and "published only in a wider window" without copying 1.2M
 *   rows' worth of aggregate blocks.
 *
 * The national baselines are the matching `dashboard_overview.stats` blocks
 * (year_2025_hdb 628000/603/25084, year_2025_ec 1578000/1530/6209,
 * whole_hdb 310000/286/989535, recent_hdb 580000/559/126824).
 */

import { afterEach, describe, expect, test } from "bun:test";
import { createHash } from "node:crypto";
import {
  mkdtempSync,
  mkdirSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { gunzipSync, gzipSync } from "node:zlib";

import {
  AREA_PAGE_COMBINATIONS,
  areaHref,
  loadAreaPages,
  verifyBaselineAtBuild,
  type AreaPageData,
} from "../../src/utils/area-page";
import { sectionKey } from "../../src/utils/observed-data";
import { AREA_RETURN_PARAMETERS } from "../../src/utils/area-links";

/** The published `map_metrics.year_2025_hdb` section, approved metrics only. */
const YEAR_2025_HDB = {
  "ANG MO KIO": { median_price: 499000, median_psf: 583, volume: 971 },
  BEDOK: { median_price: 548000, median_psf: 591, volume: 1208 },
  BISHAN: { median_price: 849000, median_psf: 756, volume: 376 },
  "BUKIT BATOK": { median_price: 600000, median_psf: 599, volume: 1304 },
  "BUKIT MERAH": { median_price: 785000, median_psf: 810, volume: 933 },
  "BUKIT PANJANG": { median_price: 610000, median_psf: 580, volume: 798 },
  "BUKIT TIMAH": { median_price: 945500, median_psf: 821, volume: 60 },
  CHANGI: { median_price: 360000, median_psf: 502, volume: 8 },
  "CHOA CHU KANG": { median_price: 592888, median_psf: 513, volume: 1027 },
  CLEMENTI: { median_price: 590000, median_psf: 621, volume: 551 },
  "DOWNTOWN CORE": { median_price: 812500, median_psf: 920, volume: 6 },
  GEYLANG: { median_price: 570000, median_psf: 621, volume: 638 },
  HOUGANG: { median_price: 615000, median_psf: 611, volume: 1311 },
  "JURONG EAST": { median_price: 524000, median_psf: 545, volume: 482 },
  "JURONG WEST": { median_price: 568000, median_psf: 521, volume: 1591 },
  KALLANG: { median_price: 761500, median_psf: 742, volume: 588 },
  "MARINE PARADE": { median_price: 539750, median_psf: 685, volume: 162 },
  NOVENA: { median_price: 630000, median_psf: 652, volume: 201 },
  OUTRAM: { median_price: 808000, median_psf: 927, volume: 105 },
  "PASIR RIS": { median_price: 715000, median_psf: 555, volume: 626 },
  PUNGGOL: { median_price: 672000, median_psf: 686, volume: 1538 },
  QUEENSTOWN: { median_price: 816888, median_psf: 920, volume: 599 },
  ROCHOR: { median_price: 572500, median_psf: 705, volume: 62 },
  SEMBAWANG: { median_price: 620000, median_psf: 631, volume: 1191 },
  SENGKANG: { median_price: 660888, median_psf: 641, volume: 1905 },
  SERANGOON: { median_price: 669444, median_psf: 657, volume: 404 },
  TAMPINES: { median_price: 710000, median_psf: 620, volume: 1921 },
  TANGLIN: { median_price: 810000, median_psf: 694, volume: 2 },
  "TOA PAYOH": { median_price: 785000, median_psf: 727, volume: 1063 },
  WOODLANDS: { median_price: 590000, median_psf: 531, volume: 1748 },
  YISHUN: { median_price: 547000, median_psf: 577, volume: 1703 },
};

/** The published `map_metrics.year_2025_ec` section. BEDOK is absent. */
const YEAR_2025_EC = {
  "ANG MO KIO": { median_price: 1900000, median_psf: 1348, volume: 14 },
  BISHAN: { median_price: 2390044, median_psf: 1689, volume: 24 },
  "BUKIT BATOK": { median_price: 1666000, median_psf: 1502, volume: 164 },
  "BUKIT PANJANG": { median_price: 1300000, median_psf: 1245, volume: 102 },
  "CHOA CHU KANG": { median_price: 1450000, median_psf: 1465, volume: 407 },
  HOUGANG: { median_price: 1745000, median_psf: 1766, volume: 321 },
  "JURONG EAST": { median_price: 1389000, median_psf: 1184, volume: 20 },
  "JURONG WEST": { median_price: 1435000, median_psf: 1310, volume: 195 },
  "PASIR RIS": { median_price: 1385000, median_psf: 1249, volume: 211 },
  PUNGGOL: { median_price: 1660000, median_psf: 1484, volume: 433 },
  SEMBAWANG: { median_price: 1471888, median_psf: 1410, volume: 369 },
  SENGKANG: { median_price: 1570000, median_psf: 1501, volume: 762 },
  TAMPINES: { median_price: 1664000, median_psf: 1754, volume: 1382 },
  TENGAH: { median_price: 1659000, median_psf: 1739, volume: 1054 },
  WOODLANDS: { median_price: 1280000, median_psf: 1201, volume: 401 },
  YISHUN: { median_price: 1348888, median_psf: 1303, volume: 350 },
};

const WHOLE_HDB = {
  TAMPINES: { median_price: 330000, median_psf: 276, volume: 84816 },
  BEDOK: { median_price: 255000, median_psf: 260, volume: 69497 },
  // All-history only: this area has no 2025 HDB block, so its fieldnote must
  // exist and say so rather than showing a zero.
  "LIM CHU KANG": { median_price: 66000, median_psf: 99, volume: 33 },
};

const RECENT_HDB = {
  TAMPINES: { median_price: 639000, median_psf: 572, volume: 9021 },
  BEDOK: { median_price: 500000, median_psf: 545, volume: 6363 },
};

const MAP_METRICS = {
  year_2025_hdb: YEAR_2025_HDB,
  year_2025_ec: YEAR_2025_EC,
  whole_hdb: WHOLE_HDB,
  recent_hdb: RECENT_HDB,
  // Property-only and period-only blocks the loader must never read.
  hdb: { TAMPINES: { median_price: 1, median_psf: 1, volume: 1 } },
  year_2025: { TAMPINES: { median_price: 2, median_psf: 2, volume: 2 } },
};

const OVERVIEW = {
  metadata: { date_range: { start: "1990-01-01", end: "2026-10-31" } },
  stats: {
    year_2025_hdb: {
      count: 25084,
      median_price: 628000,
      median_psf: 603,
      volume: 25084,
    },
    year_2025_ec: {
      count: 6209,
      median_price: 1578000,
      median_psf: 1530,
      volume: 6209,
    },
    whole_hdb: {
      count: 989535,
      median_price: 310000,
      median_psf: 286,
      volume: 989535,
    },
    recent_hdb: {
      count: 126824,
      median_price: 580000,
      median_psf: 559,
      volume: 126824,
    },
    hdb: { median_price: 111111, median_psf: 111, volume: 1 },
  },
};

const tempRoots: string[] = [];

afterEach(() => {
  for (const root of tempRoots.splice(0)) {
    rmSync(root, { recursive: true, force: true });
  }
});

/**
 * Write a fixture tree in the published layout and return its root.
 *
 * `omitNational` drops one `dashboard_overview.stats` block so the "no national
 * value for this combination" path is exercised without inventing a number.
 */
function writeFixture(
  options: { manifest?: boolean; omitNational?: string } = {},
): string {
  const root = mkdtempSync(join(tmpdir(), "area-page-"));
  tempRoots.push(root);
  const dataDir = join(root, "public", "data");
  mkdirSync(dataDir, { recursive: true });

  const overview = structuredClone(OVERVIEW) as {
    stats: Record<string, unknown>;
  };
  if (options.omitNational !== undefined) {
    delete overview.stats[options.omitNational];
  }

  // The release contract covers the seven exporter-owned assets, so the
  // fixture publishes all of them: a manifest that omits one is not a valid
  // generation and must not be reported as compatible.
  const assets: Record<string, unknown> = {
    "map_metrics.json.gz": MAP_METRICS,
    "dashboard_overview.json.gz": overview,
    "dashboard_trends.json.gz": [{ month: "2025-01", value: 1 }],
    "dashboard_segments.json.gz": { segments: [] },
    "dashboard_leaderboard.json.gz": [],
    "hotspots.json.gz": {},
    "amenity_summary.json.gz": [],
  };
  for (const [name, payload] of Object.entries(assets)) {
    writeFileSync(
      join(dataDir, name),
      gzipSync(Buffer.from(JSON.stringify(payload), "utf8")),
    );
  }

  if (options.manifest === true) {
    writeFileSync(
      join(dataDir, "dashboard-release.json"),
      JSON.stringify(buildManifest(dataDir)),
    );
  }
  return root;
}

function sha256(bytes: Uint8Array): string {
  return createHash("sha256").update(bytes).digest("hex");
}

/**
 * Build a contract-shaped release manifest from the fixture's own bytes, using
 * the exporter's canonical JSON (sorted keys, compact separators, no
 * `generation`/`generatedAt`).
 */
function buildManifest(dataDir: string): Record<string, unknown> {
  const paths = [
    "dashboard_overview.json.gz",
    "dashboard_trends.json.gz",
    "dashboard_segments.json.gz",
    "dashboard_leaderboard.json.gz",
    "map_metrics.json.gz",
    "hotspots.json.gz",
    "amenity_summary.json.gz",
  ];
  const assets = paths.map((path) => {
    const bytes = readFileSync(join(dataDir, path));
    const content = gunzipSync(bytes);
    return {
      path,
      sha256: sha256(bytes),
      contentSha256: sha256(content),
      bytes: bytes.length,
      shape: "object",
      metricScopes: ["median_price", "median_psf", "volume"],
    };
  });

  const body = {
    schemaVersion: "1.0.0",
    generatedAt: "2026-11-02T00:00:00Z",
    observationRange: {
      startMonth: "1990-01",
      endMonth: "2026-10",
      completeYear: 2025,
    },
    periodDefinitions: {
      year_2025: { label: "2025 complete year", filter: "year == 2025" },
    },
    inclusionRules: { excludedTransactions: 2 },
    provenance: { sources: [] },
    assets,
  };
  return { ...body, generation: generationOf(body) };
}

/** Canonical JSON + SHA-256, byte-identical to the Python exporter. */
function generationOf(body: Record<string, unknown>): string {
  const content: Record<string, unknown> = { ...body };
  delete content.generation;
  delete content.generatedAt;
  return sha256(Buffer.from(canonicalJson(content), "utf8"));
}

function canonicalJson(value: unknown): string {
  if (Array.isArray(value)) {
    return `[${value.map((entry) => canonicalJson(entry)).join(",")}]`;
  }
  if (typeof value === "object" && value !== null) {
    const record = value as Record<string, unknown>;
    return `{${Object.keys(record)
      .sort()
      .map((key) => `${JSON.stringify(key)}:${canonicalJson(record[key])}`)
      .join(",")}}`;
  }
  return JSON.stringify(value);
}

function metricOf(
  observations: { metric: string; value: number | null }[] | null,
  metric: string,
): number | null {
  if (observations === null) throw new Error("no observations");
  const found = observations.find((entry) => entry.metric === metric);
  if (found === undefined) throw new Error(`missing metric ${metric}`);
  return found.value;
}

function page(pages: AreaPageData[], areaId: string): AreaPageData {
  const found = pages.find((entry) => entry.areaId === areaId);
  if (found === undefined) throw new Error(`missing page for ${areaId}`);
  return found;
}

function section(
  entry: AreaPageData,
  era: string,
  property: string,
): AreaPageData["sections"][number] {
  const found = entry.sections.find(
    (candidate) => candidate.era === era && candidate.property === property,
  );
  if (found === undefined) throw new Error(`missing ${era}_${property}`);
  return found;
}

describe("area page sections", () => {
  test("covers the full joint-section matrix in reading order", () => {
    expect(AREA_PAGE_COMBINATIONS).toHaveLength(16);
    expect(AREA_PAGE_COMBINATIONS.slice(0, 4).map((entry) => entry.label)).toEqual([
      "2025 complete year · HDB",
      "2025 complete year · EC",
      "2025 complete year · Condominium",
      "2025 complete year · All property types",
    ]);
    expect(
      AREA_PAGE_COMBINATIONS.map((entry) =>
        sectionKey(entry.era, entry.property),
      ).join(","),
    ).toBe(
      [
        "year_2025_hdb",
        "year_2025_ec",
        "year_2025_condo",
        "year_2025",
        "whole_hdb",
        "whole_ec",
        "whole_condo",
        "whole",
        "recent_hdb",
        "recent_ec",
        "recent_condo",
        "recent",
        "pre_covid_hdb",
        "pre_covid_ec",
        "pre_covid_condo",
        "pre_covid",
      ].join(","),
    );
  });

  test("loads one page per area, 31 of which publish a 2025 HDB block", async () => {
    const pages = await loadAreaPages(writeFixture());

    // The union of the four combinations: the 31 areas of the published 2025
    // HDB section, plus the all-history-only Lim Chu Kang and the
    // 2025-EC-only Tengah. The two extras exist so the "published elsewhere"
    // and "not published here" states have a real page.
    expect(pages).toHaveLength(33);
    const withYear2025Hdb = pages.filter(
      (entry) => section(entry, "year_2025", "hdb").area !== null,
    );
    expect(withYear2025Hdb).toHaveLength(31);

    // Deterministic, canonical ids and slugs.
    expect(pages.map((entry) => entry.areaId)).toEqual(
      [...pages.map((entry) => entry.areaId)].sort(),
    );
    expect(page(pages, "ANG MO KIO").slug).toBe("ang-mo-kio");
    expect(page(pages, "ANG MO KIO").areaName).toBe("Ang Mo Kio");
  });

  test("reads Tampines 2025 HDB and the national baseline from one joint section", async () => {
    const pages = await loadAreaPages(writeFixture());
    const tampines = page(pages, "TAMPINES");
    const primary = section(tampines, "year_2025", "hdb");

    expect(primary.section).toBe("year_2025_hdb");
    expect(primary.area?.section).toBe("year_2025_hdb");
    expect(metricOf(primary.area?.metrics ?? null, "median_price")).toBe(710000);
    expect(metricOf(primary.area?.metrics ?? null, "median_psf")).toBe(620);
    expect(metricOf(primary.area?.metrics ?? null, "volume")).toBe(1921);

    expect(metricOf(primary.national, "median_price")).toBe(628000);
    expect(metricOf(primary.national, "median_psf")).toBe(603);
    expect(metricOf(primary.national, "volume")).toBe(25084);
  });

  test("never substitutes the property-only or period-only blocks", async () => {
    const pages = await loadAreaPages(writeFixture());
    const limChuKang = page(pages, "LIM CHU KANG");
    const primary = section(limChuKang, "year_2025", "hdb");

    // The fixture's `hdb` / `year_2025` blocks carry Tampines values; they are
    // never read for a joint section.
    expect(primary.area).toBeNull();
    expect(section(page(pages, "TAMPINES"), "year_2025", "hdb").area).not.toBeNull();
    expect(metricOf(section(page(pages, "TAMPINES"), "year_2025", "hdb").area?.metrics ?? null, "median_price")).toBe(710000);
  });

  test("an area without EC transactions has a null EC record, not a zero", async () => {
    const pages = await loadAreaPages(writeFixture());
    const bedok = page(pages, "BEDOK");

    const ec = section(bedok, "year_2025", "ec");
    expect(ec.section).toBe("year_2025_ec");
    expect(ec.area).toBeNull();
    // The same area does publish 2025 HDB, so the page can still show a price.
    expect(metricOf(section(bedok, "year_2025", "hdb").area?.metrics ?? null, "volume")).toBe(1208);
    // ... and the EC baseline is still available for that combination.
    expect(metricOf(ec.national, "median_price")).toBe(1578000);

    // Tengah is the mirror case: 2025 EC published, 2025 HDB absent.
    const tengah = page(pages, "TENGAH");
    expect(
      metricOf(section(tengah, "year_2025", "ec").area?.metrics ?? null, "median_price"),
    ).toBe(1659000);
    expect(section(tengah, "year_2025", "hdb").area).toBeNull();
  });

  test("a combination with no national block keeps national null", async () => {
    const pages = await loadAreaPages(writeFixture({ omitNational: "recent_hdb" }));
    const tampines = page(pages, "TAMPINES");

    const recent = section(tampines, "recent", "hdb");
    expect(recent.area).not.toBeNull();
    expect(recent.national).toBeNull();
    // Every other combination keeps its own baseline, and no baseline is ever
    // borrowed from a different section.
    for (const candidate of tampines.sections) {
      if (candidate.national === null) continue;
      expect(candidate.national.every((metric) => metric.source.section === candidate.section)).toBe(true);
      expect(candidate.national.every((metric) => metric.source.asset === "dashboard_overview")).toBe(true);
    }
  });
});

describe("baseline verdict at build time", () => {
  test("no manifest is absent, never compatible", async () => {
    const verdict = await verifyBaselineAtBuild(writeFixture());

    expect(verdict).toEqual({
      compatible: false,
      status: "absent",
      generation: null,
      reason: null,
    });
  });

  test("a matching manifest is compatible and carries the generation", async () => {
    const root = writeFixture({ manifest: true });
    const verdict = await verifyBaselineAtBuild(root);

    expect(verdict.compatible).toBe(true);
    expect(verdict.status).toBe("verified");
    expect(/^[0-9a-f]{64}$/.test(verdict.generation ?? "")).toBe(true);
    expect(verdict.reason).toBeNull();
  });

  test("a one-byte tamper is a mismatch, not an unverified guess", async () => {
    const root = writeFixture({ manifest: true });
    const assetPath = join(root, "public", "data", "map_metrics.json.gz");
    const bytes = readFileSync(assetPath);
    bytes[bytes.length - 1] = bytes[bytes.length - 1] ^ 0xff;
    writeFileSync(assetPath, bytes);

    const verdict = await verifyBaselineAtBuild(root);

    expect(verdict.compatible).toBe(false);
    expect(verdict.status).toBe("mismatch");
    expect(verdict.reason).toBe(
      "map_metrics.json.gz: sha256 does not match the recorded digest",
    );
  });

  test("a manifest whose generation disagrees with its content is a mismatch", async () => {
    const root = writeFixture({ manifest: true });
    const manifestPath = join(root, "public", "data", "dashboard-release.json");
    const manifest = JSON.parse(readFileSync(manifestPath, "utf8")) as Record<
      string,
      unknown
    >;
    manifest["inclusionRules"] = { excludedTransactions: 3 };
    writeFileSync(manifestPath, JSON.stringify(manifest));

    const verdict = await verifyBaselineAtBuild(root);

    expect(verdict.compatible).toBe(false);
    expect(verdict.status).toBe("mismatch");
    expect(verdict.reason).toContain("does not match the manifest content");
  });

  test("an unparseable manifest is unverified", async () => {
    const root = writeFixture({ manifest: true });
    writeFileSync(
      join(root, "public", "data", "dashboard-release.json"),
      "{ not json",
    );

    const verdict = await verifyBaselineAtBuild(root);

    expect(verdict.compatible).toBe(false);
    expect(verdict.status).toBe("unverified");
    expect(verdict.generation).toBeNull();
  });

  test("the page data carries the verdict it was built under", async () => {
    const pages = await loadAreaPages(writeFixture({ manifest: true }));

    expect(pages.every((entry) => entry.baselineCompatible)).toBe(true);
    expect(pages.every((entry) => entry.baselineStatus === "verified")).toBe(true);
    expect(new Set(pages.map((entry) => entry.generation)).size).toBe(1);
  });
});

describe("areaHref", () => {
  test("builds the fieldnote path with the explorer return marker", () => {
    expect(areaHref("tampines")).toBe("/areas/tampines?from=explore");
  });

  test("carries the validated property and period", () => {
    expect(areaHref("tampines", { property: "hdb", period: "year_2025" })).toBe(
      "/areas/tampines?from=explore&property=hdb&period=year_2025",
    );
    expect(areaHref("lim-chu-kang", { period: "whole" })).toBe(
      "/areas/lim-chu-kang?from=explore&period=whole",
    );
  });

  test("never echoes a value outside the explorer vocabulary", () => {
    expect(
      areaHref("tampines", {
        property: "https://example.com/",
        period: "<script>",
      }),
    ).toBe("/areas/tampines?from=explore");
  });
});


describe("return-link contract", () => {
  test("the area page inline allow-list matches the exported constant", () => {
    const page = readFileSync(
      join(process.cwd(), "src", "pages", "areas", "[slug].astro"),
      "utf8",
    );
    const block = page.slice(page.indexOf("const allowed = ["));
    const list = block
      .slice(0, block.indexOf("];"))
      .split("\n")
      .slice(1)
      .map((line) => line.trim().replace(/[",]/g, ""))
      .filter((line) => line.length > 0);
    expect(list).toEqual([...AREA_RETURN_PARAMETERS]);
  });
});
