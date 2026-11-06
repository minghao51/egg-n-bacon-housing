/**
 * Unit tests for the S8 tools evidence contract
 * (src/components/tools/lib/tool-evidence.ts + tool-assets.ts).
 *
 * Reads the **published** archive assets and the **published** release
 * manifest, so the pinned facts (band 74–79 at 75 years, 19.1%, 29,913 rows,
 * 40 spatial towns, `BISHAN` key normalization) fail loudly if the assets or
 * the contract drift. It also pins the gates: the archive assets are not in the
 * release manifest, no total-dollar MRT output exists, and no allocation or
 * recommendation copy survives.
 */

import { describe, expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import { gunzipSync } from "node:zlib";

import {
  leaseCoverageGaps,
  leaseLabelConflicts,
  LEASE_ENDPOINT_POLICY_NOTE,
  LEASE_RISK_LABEL_NOTE,
  MRT_DIRECTION_NOTE,
  MRT_WITHHELD_NOTE,
  mrtStoredTerms,
  normalizeTownKey,
  resolveTownKey,
  selectLeaseBand,
  SPATIAL_WITHHELD_NOTE,
  TOOL_ARCHIVE_LABEL,
  TOOL_ASSET_FILENAMES,
  toolArchiveStatus,
  toolAssetsVerified,
} from "../../src/components/tools/lib/tool-evidence";
import {
  readLeaseAsset,
  readMrtAsset,
  readSpatialAsset,
} from "../../src/components/tools/lib/tool-assets";
import { formatSignedPercent } from "../../src/components/tools/lib/tool-format";
import { FINANCING_NOT_OFFER_NOTE } from "../../src/components/tools/lib/tool-evidence";

function readAsset<K extends keyof typeof TOOL_ASSET_FILENAMES>(
  tool: K,
): unknown {
  const path = `../../public/data/interactive_tools/${TOOL_ASSET_FILENAMES[tool]}`;
  return JSON.parse(
    gunzipSync(readFileSync(new URL(path, import.meta.url))).toString("utf-8"),
  );
}

const leaseRead = readLeaseAsset(readAsset("lease"));
const mrtRead = readMrtAsset(readAsset("mrt"));
const spatialRead = readSpatialAsset(readAsset("spatial"));

const manifest = JSON.parse(
  readFileSync(
    new URL("../../public/data/dashboard-release.json", import.meta.url),
    "utf8",
  ),
) as { assets: Array<{ path: string }> };
const manifestPaths = manifest.assets.map((asset) => asset.path);

describe("published lease archive", () => {
  test("the asset validates and keeps its stored bands", () => {
    expect(leaseRead.ok).toBe(true);
    if (!leaseRead.ok) return;
    expect(leaseRead.asset.bands.length).toBeGreaterThan(0);
  });

  test("75 remaining years resolves to the stored 74–79 band", () => {
    if (!leaseRead.ok) throw new Error("lease asset unavailable");
    const lookup = selectLeaseBand(leaseRead.asset.bands, 75);
    expect(lookup).not.toBeNull();
    if (lookup === null) return;
    expect(lookup.band.lease_age_band).toBe("20-25");
    expect(lookup.band.min_lease_years).toBe(74);
    expect(lookup.band.max_lease_years).toBe(79);
    expect(lookup.band.discount_percent).toBe(19.1);
    expect(lookup.band.annual_decay_rate).toBe(0.25);
    expect(lookup.band.transaction_count).toBe(29_913);
    expect(lookup.sharedEndpoint).toBe(false);
  });

  test("shared endpoints are exposed, not silently resolved", () => {
    if (!leaseRead.ok) throw new Error("lease asset unavailable");
    const lookup = selectLeaseBand(leaseRead.asset.bands, 94);
    expect(lookup).not.toBeNull();
    if (lookup === null) return;
    // First-match preserves the archive's stored order…
    expect(lookup.band.lease_age_band).toBe("0-5");
    // …and the other containing band is named.
    expect(lookup.matchingBands).toHaveLength(2);
    expect(lookup.matchingBands.map((band) => band.lease_age_band)).toEqual([
      "0-5",
      "5-10",
    ]);
    expect(lookup.sharedEndpoint).toBe(true);
    expect(LEASE_ENDPOINT_POLICY_NOTE).toContain("first-match");
  });

  test("negative statistics are premiums and format with a sign", () => {
    if (!leaseRead.ok) throw new Error("lease asset unavailable");
    const negatives = leaseRead.asset.bands.filter(
      (band) => band.discount_percent < 0,
    );
    expect(negatives.length).toBeGreaterThan(0);
    expect(
      formatSignedPercent(negatives[0].discount_percent).startsWith("-"),
    ).toBe(true);
    expect(formatSignedPercent(19.1)).toBe("+19.1%");
  });

  test("the stored domain has a documented coverage gap", () => {
    if (!leaseRead.ok) throw new Error("lease asset unavailable");
    expect(leaseCoverageGaps(leaseRead.asset.bands)).toEqual([
      { from: 9, to: 39 },
    ]);
  });

  test("stored risk labels conflict with the archive's own insight prose", () => {
    if (!leaseRead.ok) throw new Error("lease asset unavailable");
    const labels = new Set(leaseRead.asset.bands.map((band) => band.risk_zone));
    expect(labels.has("cliff")).toBe(true);
    expect(labels.has("safe")).toBe(true);

    const conflicts = leaseLabelConflicts(leaseRead.asset);
    expect(conflicts.length).toBeGreaterThan(0);
    expect(conflicts.join(" ")).toContain("safe");
    expect(conflicts.join(" ")).toContain("cliff");
    expect(LEASE_RISK_LABEL_NOTE).toContain("withholds");
  });
});

describe("published MRT/CBD archive", () => {
  test("the asset validates", () => {
    expect(mrtRead.ok).toBe(true);
    if (!mrtRead.ok) return;
    expect(
      Object.keys(mrtRead.asset.property_type_multipliers).length,
    ).toBeGreaterThan(0);
  });

  test("title-case labels resolve to the stored canonical key", () => {
    if (!mrtRead.ok) throw new Error("MRT asset unavailable");
    expect(normalizeTownKey("  bishan ")).toBe("BISHAN");
    expect(resolveTownKey(mrtRead.asset.town_multipliers, "Bishan")).toBe(
      "BISHAN",
    );
    expect(
      resolveTownKey(mrtRead.asset.town_multipliers, "Nowhere"),
    ).toBeNull();
  });

  test("the stored formula is disclosed with units and the 500 m stop", () => {
    if (!mrtRead.ok) throw new Error("MRT asset unavailable");
    const terms = mrtStoredTerms(mrtRead.asset, "HDB", "Bishan", 500, 10);
    expect(terms.townKey).toBe("BISHAN");
    expect(terms.effectivePremiumPer100m).toBe(9);
    expect(terms.appliedDistanceMetres).toBe(500);
    expect(terms.formula).toBe("(500 ÷ 100) × 9 × 1000");
    expect(terms.cbdFormula).toBe("(10 km × 15000 per km)");

    const beyond = mrtStoredTerms(mrtRead.asset, "HDB", "Bishan", 900, 10);
    expect(beyond.appliedDistanceMetres).toBe(500);
    expect(MRT_DIRECTION_NOTE).toContain("500 m");
  });

  test("a missing town or type yields no term, never a fallback", () => {
    if (!mrtRead.ok) throw new Error("MRT asset unavailable");
    const missingTown = mrtStoredTerms(
      mrtRead.asset,
      "HDB",
      "Nowhere",
      500,
      10,
    );
    expect(missingTown.townKey).toBeNull();
    expect(missingTown.effectivePremiumPer100m).toBeNull();
    expect(missingTown.formula).toBeNull();
    expect(missingTown.cbdFormula).toBe("(10 km × 15000 per km)");

    const missingType = mrtStoredTerms(
      mrtRead.asset,
      "Landed",
      "Bishan",
      500,
      10,
    );
    expect(missingType.typeCoefficient).toBeNull();
    expect(missingType.formula).toBeNull();
    expect(MRT_WITHHELD_NOTE).toContain("withheld");
  });
});

describe("published spatial archive", () => {
  test("the published towns[] shape validates", () => {
    expect(spatialRead.ok).toBe(true);
    if (!spatialRead.ok) return;
    expect(spatialRead.asset.towns).toHaveLength(40);
    expect(
      spatialRead.asset.towns.every((town) =>
        ["HH", "HL", "LH", "LL"].includes(town.cluster),
      ),
    ).toBe(true);
  });

  test("a clusters[]-only payload is unavailable, not coerced", () => {
    const wrong = readSpatialAsset({ clusters: [] });
    expect(wrong.ok).toBe(false);
    if (wrong.ok) return;
    expect(wrong.reason).toContain("towns[]");
  });

  test("portfolio allocations are never surfaced", () => {
    if (!spatialRead.ok) return;
    expect(spatialRead.asset.portfolio_allocation).toEqual({});
    expect(SPATIAL_WITHHELD_NOTE).toContain("withheld");
  });
});

describe("archive release boundary", () => {
  test("none of the three research assets is in the release manifest", () => {
    for (const tool of ["lease", "mrt", "spatial"] as const) {
      expect(manifestPaths).not.toContain(TOOL_ASSET_FILENAMES[tool]);
      expect(toolArchiveStatus(manifestPaths, tool)).toBe("unverified-archive");
    }
    expect(toolAssetsVerified(manifestPaths)).toBe(false);
  });

  test("listing them would flip the gate, so promotion stays deliberate", () => {
    const promoted = [...manifestPaths, ...Object.values(TOOL_ASSET_FILENAMES)];
    expect(toolAssetsVerified(promoted)).toBe(true);
    expect(toolArchiveStatus(promoted, "mrt")).toBe(
      "share-verified-generation",
    );
  });

  test("archive copy names the missing period and sample", () => {
    expect(TOOL_ARCHIVE_LABEL).toContain("observation period");
    expect(TOOL_ARCHIVE_LABEL).toContain("sample");
  });
});

describe("no invention copy", () => {
  const copy = [
    MRT_DIRECTION_NOTE,
    MRT_WITHHELD_NOTE,
    LEASE_RISK_LABEL_NOTE,
    SPATIAL_WITHHELD_NOTE,
    FINANCING_NOT_OFFER_NOTE,
  ].join(" ");

  test("retired 7×/15× boilerplate is gone", () => {
    expect(/7x|15x|7\u00d7|15\u00d7/i.test(copy)).toBe(false);
  });

  test("the financing disclaimer is an exclusion, not an eligibility claim", () => {
    expect(FINANCING_NOT_OFFER_NOTE).toContain("Not a loan offer");
    expect(FINANCING_NOT_OFFER_NOTE).toContain("eligibility");
    expect(FINANCING_NOT_OFFER_NOTE).toContain("no CPF, MSR or TDSR");
  });
});
