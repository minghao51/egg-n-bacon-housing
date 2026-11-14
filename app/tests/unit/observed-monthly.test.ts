/**
 * Tests for the RF09 monthly history contract.
 *
 * The grid fixture in `tests/fixtures/v2-pack/area-monthly-hdb.json` is a
 * trimmed copy of the published `area-monthly-hdb` payload (national + three
 * planning areas, last 26 months). Synthetic payloads cover rejection paths.
 */

import { describe, expect, it } from "bun:test";
import {
  MONTHLY_CELL_FIELDS,
  MONTHLY_ROLES,
  areaSeries,
  coveredHistoryMonths,
  monthlyRole,
  parseMonthlyHistory,
  propertyTypeForRole,
  readMonth,
} from "@/utils/observed-monthly";
import { V2_SCHEMA_VERSION } from "@/utils/observed-periods";
import monthlyFixture from "../fixtures/v2-pack/area-monthly-hdb.json";

type RawPayload = Record<string, unknown>;

function cloneFixture(): RawPayload {
  return JSON.parse(JSON.stringify(monthlyFixture)) as RawPayload;
}

function parseFixture(): ReturnType<typeof parseMonthlyHistory> {
  return parseMonthlyHistory(monthlyFixture, {
    propertyType: "hdb",
    cutoffMonth: "2026-10",
  });
}

function expectRejected(payload: RawPayload, needle: string): void {
  const result = parseMonthlyHistory(payload, { propertyType: "hdb" });
  expect(result.ok).toBe(false);
  if (!result.ok) expect(result.errors.join(" ")).toContain(needle);
}

describe("roles", () => {
  it("maps every property type to one declared role", () => {
    expect(monthlyRole("hdb")).toBe("area-monthly-hdb");
    expect(monthlyRole("all")).toBe("area-monthly-all");
    for (const role of MONTHLY_ROLES) {
      expect(propertyTypeForRole(role)).not.toBeNull();
      expect(monthlyRole(propertyTypeForRole(role)!)).toBe(role);
    }
    expect(propertyTypeForRole("summary")).toBeNull();
  });
});

describe("parsing the real history payload", () => {
  it("accepts the published fixture", () => {
    const result = parseFixture();

    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.history.schemaVersion).toBe(V2_SCHEMA_VERSION);
    expect(result.history.propertyType).toBe("hdb");
    expect(result.history.cutoffMonth).toBe("2026-10");
    expect(result.history.months.at(-1)).toBe("2026-10");
    expect(result.history.coverage.monthCount).toBe(
      result.history.months.length,
    );
  });

  it("keeps the cell grid aligned to the month grid", () => {
    const result = parseFixture();
    if (!result.ok) throw new Error(result.errors.join("; "));

    for (const series of result.history.series) {
      expect(series.cells).toHaveLength(result.history.months.length);
    }
    expect(result.history.seriesById.get("SG")).toBeDefined();
    expect(result.history.seriesById.get("PUNGGOL")).toBeDefined();
  });

  it("reads a covered month without averaging or zero-filling", () => {
    const result = parseFixture();
    if (!result.ok) throw new Error(result.errors.join("; "));
    const history = result.history;
    const sg = history.seriesById.get("SG")!;
    const position = history.months.length - 1;
    const [count, price, priceObs, psf, psfObs] = sg.cells[position];
    const reading = readMonth(history, "SG", history.months[position]);

    expect(reading.status).toBe("available");
    expect(reading.transactionCount).toBe(count);
    expect(reading.medianPrice).toBe(price);
    expect(reading.priceObservations).toBe(priceObs);
    expect(reading.medianPsf).toBe(psf);
    expect(reading.psfObservations).toBe(psfObs);
  });

  it("declares which ids are areas rather than leaving it to the id string", () => {
    const result = parseFixture();
    if (!result.ok) throw new Error(result.errors.join("; "));

    expect(result.history.nationalId).toBe("SG");
    expect(result.history.unassignedIds).toEqual([]);
    expect(
      areaSeries(result.history).map((entry) => entry.geographyId),
    ).toEqual(["ANG MO KIO", "PUNGGOL", "TAMPINES"]);
  });

  it("reports an uncovered month as missing source, never as zero sales", () => {
    const result = parseFixture();
    if (!result.ok) throw new Error(result.errors.join("; "));

    const before = readMonth(result.history, "SG", "1990-01");
    const unknownArea = readMonth(result.history, "ATLANTIS", "2026-10");

    expect(before.status).toBe("missing-source");
    expect(before.transactionCount).toBeNull();
    expect(before.medianPrice).toBeNull();
    expect(unknownArea.status).toBe("missing-source");
    expect(coveredHistoryMonths(result.history, "ATLANTIS")).toEqual([]);
    expect(coveredHistoryMonths(result.history, "SG")).toEqual(
      result.history.months,
    );
  });
});

describe("rejection", () => {
  it("rejects an unsupported schema version", () => {
    const payload = { ...cloneFixture(), schemaVersion: "2.0.0" };
    expectRejected(payload, "schemaVersion");
  });

  it("rejects a reordered cell field list", () => {
    const payload = cloneFixture();
    payload.cellFields = [...MONTHLY_CELL_FIELDS].reverse();
    expectRejected(payload, "cellFields");
  });

  it("rejects a cell grid that is not aligned to the month grid", () => {
    const payload = cloneFixture();
    const series = (payload.series as RawPayload[])[0];
    series.cells = (series.cells as unknown[]).slice(0, -1);
    expectRejected(payload, "cells for");
  });

  it("rejects a short cell tuple", () => {
    const payload = cloneFixture();
    const series = (payload.series as RawPayload[])[0];
    const cells = series.cells as unknown[][];
    cells[0] = [1, 2];
    expectRejected(payload, "field");
  });

  it("rejects a median without its observation count", () => {
    const payload = cloneFixture();
    const series = (payload.series as RawPayload[])[0];
    const cells = series.cells as number[][];
    cells[0] = [cells[0][0], 500000, 0, cells[0][3], cells[0][4]];
    expectRejected(payload, "price and its observation count disagree");
  });

  it("rejects more observations than transactions", () => {
    const payload = cloneFixture();
    const series = (payload.series as RawPayload[])[0];
    const cells = series.cells as number[][];
    cells[0] = [1, cells[0][1], 2, cells[0][3], cells[0][4]];
    expectRejected(payload, "invalid price observation count");
  });

  it("rejects a month grid that is not strictly ascending", () => {
    const payload = cloneFixture();
    const months = payload.months as string[];
    [months[0], months[1]] = [months[1], months[0]];
    expectRejected(payload, "is not after");
  });

  it("rejects coverage that disagrees with the grid", () => {
    const payload = cloneFixture();
    payload.coverage = { ...(payload.coverage as RawPayload), monthCount: 3 };
    expectRejected(payload, "coverage.monthCount");
  });

  it("rejects a no-sales count that does not match the cells", () => {
    const payload = cloneFixture();
    const series = (payload.series as RawPayload[])[0];
    series.noSalesMonths = 999;
    expectRejected(payload, "no-sales months");
  });

  it("rejects a payload with no national series", () => {
    const payload = cloneFixture();
    payload.series = (payload.series as RawPayload[]).filter(
      (entry) => entry.geographyId !== "SG",
    );
    expectRejected(payload, "no national series");
  });

  it("rejects a payload that declares another property type", () => {
    const payload = { ...cloneFixture(), propertyType: "condo" };
    expectRejected(payload, "expected hdb");
  });

  it("rejects a cutoff that disagrees with the manifest", () => {
    const result = parseMonthlyHistory(monthlyFixture, {
      propertyType: "hdb",
      cutoffMonth: "2026-09",
    });

    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.errors.join(" ")).toContain("cutoff");
  });

  it("rejects a payload that does not declare its geographies", () => {
    const payload = cloneFixture();
    delete payload.geographies;
    expectRejected(payload, "does not declare its geographies");
  });

  it("rejects an unassigned id with no series", () => {
    const payload = cloneFixture();
    payload.geographies = {
      national: "SG",
      unassigned: ["NONE"],
      areaCount: 2,
    };
    expectRejected(payload, "geographies.unassigned NONE has no series");
  });

  it("rejects an area count that disagrees with the declared series", () => {
    const payload = cloneFixture();
    payload.geographies = { national: "SG", unassigned: [], areaCount: 4 };
    expectRejected(payload, "geographies.areaCount");
  });

  it("rejects a duplicate series", () => {
    const payload = cloneFixture();
    const series = payload.series as RawPayload[];
    payload.series = [...series, series[0]];
    expectRejected(payload, "duplicate series");
  });
});
