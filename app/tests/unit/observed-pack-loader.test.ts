/**
 * Tests for the verified v2 pack loader.
 *
 * Payloads are built in-memory and gzipped with node:zlib, so the bytes hashed
 * here are the bytes decoded — the same property the loader guarantees.
 */

import { describe, expect, it } from "bun:test";
import { gzipSync, gunzipSync } from "node:zlib";
import {
  V2_MANIFEST_PATH,
  canonicalJson,
  computeV2Generation,
  loadObservedHistory,
  loadObservedPack,
  parseV2Manifest,
  sha256Hex,
  type V2ManifestIdentity,
} from "@/utils/observed-pack-loader";
import {
  MONTHLY_CELL_FIELDS,
  monthlyRole,
  type PropertyTypeId,
} from "@/utils/observed-monthly";

const BASE = "https://example.test/";

function metric(value: number | null, unit: string) {
  return { value, unit, observations: value === null ? 0 : 10 };
}

function monthlyPayload(
  propertyType: PropertyTypeId,
  cutoffMonth = "2026-10",
): Record<string, unknown> {
  const months = ["2026-09", cutoffMonth];
  return {
    schemaVersion: "2.1.0",
    methodVersion: "observed-aggregates-2",
    cutoffMonth,
    propertyType,
    disposition: "publish",
    cellFields: [...MONTHLY_CELL_FIELDS],
    geographies: { national: "SG", unassigned: [], areaCount: 0 },
    months,
    coverage: {
      firstMonth: months[0],
      lastMonth: months[months.length - 1],
      monthCount: months.length,
      rule: "covered months only",
    },
    series: [
      {
        geographyId: "SG",
        noSalesMonths: 1,
        cells: [
          [10, 500000, 10, 500.5, 10],
          [0, null, 0, null, 0],
        ],
      },
    ],
  };
}

function payloads(cutoffMonth = "2026-10") {
  const periods = {
    schemaVersion: "2.1.0",
    methodVersion: "observed-aggregates-2",
    cutoffMonth,
    periods: [
      {
        id: `month_${cutoffMonth.replace("-", "_")}`,
        kind: "month",
        startMonth: cutoffMonth,
        endMonth: cutoffMonth,
        months: [cutoffMonth],
        label: cutoffMonth,
        comparatorId: null,
      },
    ],
    propertyTypes: ["all", "hdb", "ec", "condo"],
    metrics: ["transactionCount", "medianPrice", "medianPsf"],
  };

  const summary = {
    schemaVersion: "2.1.0",
    methodVersion: "observed-aggregates-2",
    cutoffMonth,
    cutoffSource: "declared",
    monthsPresent: [cutoffMonth],
    observations: [
      {
        geographyId: "SG",
        propertyType: "all",
        periodId: `month_${cutoffMonth.replace("-", "_")}`,
        status: "available",
        disposition: "publish",
        coverage: { months: [cutoffMonth], requestedMonths: 1 },
        metrics: {
          transactionCount: metric(4719, "transactions"),
          medianPrice: metric(1280000, "SGD"),
          medianPsf: metric(1306, "SGD_per_sqft"),
        },
      },
    ],
  };

  return { periods, summary, monthly: monthlyPayload };
}

function gzipJson(value: unknown): Uint8Array {
  return new Uint8Array(gzipSync(Buffer.from(JSON.stringify(value), "utf8")));
}

async function buildPack(options: {
  cutoffMonth?: string;
  manifestCutoff?: string;
  generationOverride?: string;
  corruptServed?: boolean;
  corruptMonthly?: boolean;
  dropRole?: "summary" | "area-monthly-hdb";
} = {}) {
  const cutoff = options.cutoffMonth ?? "2026-10";
  const { periods, summary, monthly } = payloads(cutoff);

  const periodBytes = gzipJson(periods);
  const summaryBytes = gzipJson(summary);
  const monthlyTypes: PropertyTypeId[] = ["all", "hdb", "ec", "condo"];
  const monthlyBytes = new Map(
    monthlyTypes.map((propertyType) => [
      monthlyRole(propertyType),
      gzipJson(monthly(propertyType, cutoff)),
    ]),
  );

  const roles: Record<string, string> = {
    periods: await sha256Hex(periodBytes),
    summary: await sha256Hex(summaryBytes),
  };
  for (const [role, bytes] of monthlyBytes) {
    roles[role] = await sha256Hex(bytes);
  }

  const identity: V2ManifestIdentity = {
    schemaVersion: "2.1.0",
    methodVersion: "observed-aggregates-2",
    cutoffMonth: cutoff,
    inputs: { unified_dataset: "a".repeat(64) },
    roles,
  };
  const generation = options.generationOverride ?? (await computeV2Generation(identity));

  const servedRoles = new Set(["periods", "summary", ...monthlyBytes.keys()]);
  const assets = [...servedRoles].map((role) => {
    const bytes =
      role === "periods"
        ? periodBytes
        : role === "summary"
          ? summaryBytes
          : monthlyBytes.get(role as ReturnType<typeof monthlyRole>)!;
    return {
      role,
      path: `observed/${generation}/${role}.json.gz`,
      bytes: bytes.byteLength,
      sha256: roles[role],
    };
  });

  const manifest = {
    schemaVersion: "2.1.0",
    methodVersion: "observed-aggregates-2",
    generation,
    cutoffMonth: options.manifestCutoff ?? cutoff,
    cutoffSource: "declared",
    identity,
    assets,
  };

  // Optionally corrupt the *served* bytes after the manifest has hashed them,
  // so the loader has to notice the difference.
  const servedPeriods = new Uint8Array(periodBytes);
  if (options.corruptServed) {
    servedPeriods[servedPeriods.length - 1] ^= 0xff;
  }
  const servedHdb = new Uint8Array(monthlyBytes.get("area-monthly-hdb")!);
  if (options.corruptMonthly) {
    servedHdb[servedHdb.length - 1] ^= 0xff;
  }

  // Manifest asset paths resolve beside the manifest itself (`data/`), which
  // is where `v2_observed.py --output-dir app/public/data` writes them.
  const dataBase = `${BASE}data/`;
  const files = new Map<string, ArrayBuffer>([
    [`${BASE}${V2_MANIFEST_PATH}`, new TextEncoder().encode(JSON.stringify(manifest)).buffer as ArrayBuffer],
    [`${dataBase}observed/${generation}/periods.json.gz`, servedPeriods.buffer as ArrayBuffer],
    [`${dataBase}observed/${generation}/summary.json.gz`, summaryBytes.buffer as ArrayBuffer],
  ]);
  for (const [role, bytes] of monthlyBytes) {
    const served = role === "area-monthly-hdb" ? servedHdb : bytes;
    files.set(`${dataBase}observed/${generation}/${role}.json.gz`, served.buffer as ArrayBuffer);
  }
  if (options.dropRole !== undefined) {
    files.delete(`${dataBase}observed/${generation}/${options.dropRole}.json.gz`);
  }

  const fetchBytes = async (url: string): Promise<ArrayBuffer | null> =>
    files.get(url) ?? null;

  const decode = async (bytes: ArrayBuffer): Promise<unknown> =>
    JSON.parse(gunzipSync(Buffer.from(bytes)).toString("utf8"));

  return { fetchBytes, decode, manifest, generation };
}

describe("canonical identity", () => {
  it("matches the Python generation for the same identity", async () => {
    const identity: V2ManifestIdentity = {
      schemaVersion: "2.0.0",
      methodVersion: "observed-aggregates-1",
      cutoffMonth: "2026-10",
      inputs: { unified_dataset: "a".repeat(64) },
      roles: { periods: "b".repeat(64), summary: "c".repeat(64) },
    };

    // Produced by scripts/v2_observed.py::compute_generation.
    expect(await computeV2Generation(identity)).toBe(
      "d954e2d1bbb4b196350c26bd0c4bae8bf4b0d2e13d92b05fa29d3032b2804cad",
    );
  });

  it("is insensitive to key order", () => {
    expect(canonicalJson({ b: 1, a: 2 })).toBe(canonicalJson({ a: 2, b: 1 }));
    expect(canonicalJson({ a: [1, { d: 4, c: 3 }] })).toBe('{"a":[1,{"c":3,"d":4}]}');
  });

  it("refuses non-finite numbers", () => {
    expect(() => canonicalJson({ value: Number.NaN })).toThrow();
  });
});

describe("manifest parsing", () => {
  it("accepts a well-formed manifest", async () => {
    const { manifest } = await buildPack();
    const parsed = parseV2Manifest(manifest);

    expect(parsed.ok).toBe(true);
    if (parsed.ok) {
      expect(parsed.manifest.generation).toBe(manifest.generation);
      expect(parsed.manifest.assets.map((asset) => asset.role).sort()).toEqual([
        "area-monthly-all",
        "area-monthly-condo",
        "area-monthly-ec",
        "area-monthly-hdb",
        "periods",
        "summary",
      ]);
    }
  });

  it("rejects an unsafe asset path", async () => {
    const { manifest } = await buildPack();
    const tampered = {
      ...manifest,
      assets: [{ ...manifest.assets[0], path: "../evil.json.gz" }, manifest.assets[1]],
    };

    expect(parseV2Manifest(tampered).ok).toBe(false);
  });

  it("rejects duplicate roles and missing roles", async () => {
    const { manifest } = await buildPack();

    const duplicated = {
      ...manifest,
      assets: [manifest.assets[0], manifest.assets[0]],
    };
    expect(parseV2Manifest(duplicated).ok).toBe(false);

    const missing = { ...manifest, assets: [manifest.assets[0]] };
    expect(parseV2Manifest(missing).ok).toBe(false);
  });

  it("rejects identity roles that disagree with asset hashes", async () => {
    const { manifest } = await buildPack();
    const tampered = {
      ...manifest,
      identity: {
        ...manifest.identity,
        roles: { ...manifest.identity.roles, periods: "0".repeat(64) },
      },
    };

    const parsed = parseV2Manifest(tampered);
    expect(parsed.ok).toBe(false);
    if (!parsed.ok) expect(parsed.errors.join(" ")).toContain("does not match");
  });
});

describe("loading", () => {
  it("reports absent when no v2 manifest is published", async () => {
    const result = await loadObservedPack({
      baseUrl: BASE,
      fetchBytes: async () => null,
    });

    expect(result.state).toBe("absent");
  });

  it("returns a verified pack", async () => {
    const { fetchBytes, decode } = await buildPack();

    const result = await loadObservedPack({ baseUrl: BASE, fetchBytes, decode });

    expect(result.state).toBe("ready");
    if (result.state !== "ready") return;
    expect(result.pack.cutoffMonth).toBe("2026-10");
    expect(result.pack.observations).toHaveLength(1);
    expect(result.pack.periodsById.get("month_2026_10")?.endMonth).toBe("2026-10");
    expect(result.manifest.cutoffMonth).toBe(result.pack.cutoffMonth);
  });

  it("rejects tampered payload bytes", async () => {
    const { fetchBytes, decode } = await buildPack({ corruptServed: true });

    const result = await loadObservedPack({ baseUrl: BASE, fetchBytes, decode });

    expect(result.state).toBe("invalid");
    if (result.state === "invalid") {
      expect(result.errors.join(" ")).toContain("sha256 mismatch");
    }
  });

  it("names transport decoding when the host inflated the payload", async () => {
    // A preview server or CDN that labels a stored `.gz` file with
    // `Content-Encoding: gzip` hands the browser inflated bytes, so the pinned
    // bytes never arrive. The loader must say that rather than reporting a
    // bare size mismatch, because the fix is on the host, not in the data.
    const { fetchBytes, decode } = await buildPack();

    const inflating = async (url: string): Promise<ArrayBuffer | null> => {
      const bytes = await fetchBytes(url);
      if (bytes === null) return null;
      if (!url.endsWith(".json.gz")) return bytes;
      return gunzipSync(Buffer.from(bytes)).buffer as ArrayBuffer;
    };

    const result = await loadObservedPack({
      baseUrl: BASE,
      fetchBytes: inflating,
      decode,
    });

    expect(result.state).toBe("invalid");
    if (result.state === "invalid") {
      expect(result.errors.join(" ")).toContain("transport-decoded");
    }
  });

  it("rejects a manifest whose generation does not match its identity", async () => {
    const { fetchBytes, decode } = await buildPack({ generationOverride: "f".repeat(64) });

    const result = await loadObservedPack({ baseUrl: BASE, fetchBytes, decode });

    expect(result.state).toBe("invalid");
    if (result.state === "invalid") {
      expect(result.errors.join(" ")).toContain("generation mismatch");
    }
  });

  it("rejects a missing payload rather than degrading", async () => {
    const { fetchBytes, decode } = await buildPack({ dropRole: "summary" });

    const result = await loadObservedPack({ baseUrl: BASE, fetchBytes, decode });

    expect(result.state).toBe("invalid");
    if (result.state === "invalid") {
      expect(result.errors.join(" ")).toContain("missing asset");
    }
  });

  it("rejects a manifest cutoff that disagrees with the pack", async () => {
    const { fetchBytes, decode } = await buildPack({ manifestCutoff: "2026-09" });

    const result = await loadObservedPack({ baseUrl: BASE, fetchBytes, decode });

    expect(result.state).toBe("invalid");
    if (result.state === "invalid") {
      expect(result.errors.join(" ")).toContain("cutoff");
    }
  });

  it("propagates a manifest fetch failure as invalid, not absent", async () => {
    const result = await loadObservedPack({
      baseUrl: BASE,
      fetchBytes: async () => {
        throw new Error("network down");
      },
    });

    expect(result.state).toBe("invalid");
    if (result.state === "invalid") {
      expect(result.errors.join(" ")).toContain("network down");
    }
  });
});

describe("monthly history", () => {
  it("verifies one property payload against the manifest generation", async () => {
    const { fetchBytes, decode, manifest } = await buildPack();
    const parsed = parseV2Manifest(manifest);
    if (!parsed.ok) throw new Error(parsed.errors.join("; "));

    const result = await loadObservedHistory(parsed.manifest, "hdb", {
      baseUrl: BASE,
      fetchBytes,
      decode,
    });

    expect(result.state).toBe("ready");
    if (result.state === "ready") {
      expect(result.history.propertyType).toBe("hdb");
      expect(result.history.months).toEqual(["2026-09", "2026-10"]);
      expect(result.history.seriesById.get("SG")?.cells).toHaveLength(2);
    }
  });

  it("does not download the other property payloads on the eager path", async () => {
    const { fetchBytes, decode } = await buildPack();
    const requested: string[] = [];

    const result = await loadObservedPack({
      baseUrl: BASE,
      fetchBytes: async (url) => {
        requested.push(url);
        return fetchBytes(url);
      },
      decode,
    });

    expect(result.state).toBe("ready");
    expect(requested.some((url) => url.includes("area-monthly"))).toBe(false);
  });

  it("rejects a monthly payload whose bytes were altered", async () => {
    const { fetchBytes, decode, manifest } = await buildPack({ corruptMonthly: true });
    const parsed = parseV2Manifest(manifest);
    if (!parsed.ok) throw new Error(parsed.errors.join("; "));

    const result = await loadObservedHistory(parsed.manifest, "hdb", {
      baseUrl: BASE,
      fetchBytes,
      decode,
    });

    expect(result.state).toBe("invalid");
    if (result.state === "invalid") {
      expect(result.errors.join(" ")).toContain("sha256 mismatch");
    }
  });

  it("reports a missing monthly payload instead of an empty history", async () => {
    const { fetchBytes, decode } = await buildPack({ dropRole: "area-monthly-hdb" });
    const eager = await loadObservedPack({ baseUrl: BASE, fetchBytes, decode });
    // The manifest itself is complete, so the pack loads; the missing history
    // is reported when it is asked for, never rendered as a shorter series.
    expect(eager.state).toBe("ready");
    if (eager.state !== "ready") return;

    const result = await loadObservedHistory(eager.manifest, "hdb", {
      baseUrl: BASE,
      fetchBytes,
      decode,
    });

    expect(result.state).toBe("invalid");
    if (result.state === "invalid") {
      expect(result.errors.join(" ")).toContain("missing asset");
    }
  });
});
