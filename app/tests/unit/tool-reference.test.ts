/**
 * Unit tests for the S8 financing reference-price table
 * (src/components/tools/lib/tool-reference.ts).
 *
 * The table must come from joint 2025 sections only. A property-only (`hdb`) or
 * period-only (`whole`) block may never stand in for one, and an exporter empty
 * block (`0`) is omitted rather than offered as a S$0 reference price.
 */

import { describe, expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import { gunzipSync } from "node:zlib";

import {
  buildReferencePriceTable,
  DEFAULT_REFERENCE,
  defaultReferenceEntry,
  findReferenceEntry,
  referenceAreasFor,
  referenceSourceStatus,
} from "../../src/components/tools/lib/tool-reference";

const mapMetrics = JSON.parse(
  gunzipSync(
    readFileSync(
      new URL("../../public/data/map_metrics.json.gz", import.meta.url),
    ),
  ).toString("utf-8"),
);

const table = buildReferencePriceTable(mapMetrics);

describe("published reference table", () => {
  test("Tampines HDB is the documented S$710,000 from year_2025_hdb", () => {
    const entry = findReferenceEntry(table, "TAMPINES", "hdb");
    expect(entry).not.toBeNull();
    if (entry === null) return;
    expect(entry.medianPrice).toBe(710_000);
    expect(entry.section).toBe("year_2025_hdb");
    expect(entry.volume).toBe(1_921);
  });

  test("the documented default reference resolves", () => {
    const entry = defaultReferenceEntry(table);
    expect(entry).not.toBeNull();
    if (entry === null) return;
    expect(entry.areaId).toBe(DEFAULT_REFERENCE.area);
    expect(entry.property).toBe(DEFAULT_REFERENCE.property);
  });

  test("every value comes from a joint 2025 section", () => {
    expect(table.sections).toEqual([
      "year_2025_hdb",
      "year_2025_ec",
      "year_2025_condo",
    ]);
    for (const entry of table.entries) {
      expect(entry.section.startsWith("year_2025_")).toBe(true);
      expect(entry.medianPrice).toBeGreaterThan(0);
    }
  });

  test("areas are listed per property type and lookup is canonical", () => {
    expect(referenceAreasFor(table, "hdb").length).toBeGreaterThan(0);
    expect(findReferenceEntry(table, "tampines", "hdb")?.areaId).toBe(
      "TAMPINES",
    );
    expect(findReferenceEntry(table, "  ang   mo kio ", "condo")?.areaId).toBe(
      "ANG MO KIO",
    );
    expect(findReferenceEntry(table, "TAMPINES", "landed" as never)).toBeNull();
  });
});

describe("joint-section guard", () => {
  test("a property-only or period-only block never stands in", () => {
    const onlyFallbacks = {
      hdb: {
        TAMPINES: { median_price: 999_999, median_psf: 1, volume: 1 },
      },
      whole: {
        TAMPINES: { median_price: 999_999, median_psf: 1, volume: 1 },
      },
    };
    expect(buildReferencePriceTable(onlyFallbacks).entries).toEqual([]);
  });

  test("an exporter empty block is omitted, never a S$0 reference", () => {
    const synthetic = {
      year_2025_hdb: {
        TAMPINES: { median_price: 710_000, median_psf: 620, volume: 1921 },
        EMPTY_AREA: { median_price: 0, median_psf: 0, volume: 0 },
        MISSING_MEDIAN: { median_psf: 500, volume: 10 },
      },
    };
    const built = buildReferencePriceTable(synthetic);
    expect(built.entries.map((entry) => entry.areaId)).toEqual(["TAMPINES"]);
  });

  test("an unreadable payload yields an empty table", () => {
    expect(buildReferencePriceTable(null).entries).toEqual([]);
    expect(buildReferencePriceTable({}).entries).toEqual([]);
  });

  test("asset failure is distinguished from an absent 2025 section", () => {
    expect(referenceSourceStatus(null)).toBe("unavailable");
    expect(referenceSourceStatus("not-json")).toBe("unavailable");
    expect(referenceSourceStatus([])).toBe("unavailable");
    // A readable payload without the expected sections is still available;
    // its emptiness is an observation, not an asset failure.
    expect(referenceSourceStatus({})).toBe("available");
    expect(referenceSourceStatus(mapMetrics)).toBe("available");
  });
});
