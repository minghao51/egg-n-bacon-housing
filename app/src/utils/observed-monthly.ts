/**
 * RF09 monthly history contract: `(canonical area, property type, month)`.
 *
 * One payload is published per property type (`area-monthly-<property>.json.gz`)
 * beside `periods` and `summary` under the same pack generation. Cells are
 * positional arrays aligned to the payload's `months` grid so the assets stay
 * small enough to lazy-load per property; `cellFields` declares the order, and
 * the parser rejects a payload whose field list does not match this module.
 *
 * Coverage is a hard rule, not a hint:
 * - a month in `months` is covered by the release, and a covered month with
 *   zero transactions is a verified `no-sales` month;
 * - a month absent from `months` is missing source and must never be rendered
 *   as zero sales.
 *
 * Pure and client-safe: no fetch, no DOM, no React, no `node:*`.
 */

import {
  V2_SCHEMA_VERSION,
  type ObservationDisposition,
  type PropertyTypeId,
} from "./observed-periods";

export type { ObservationDisposition, PropertyTypeId };

export const MONTHLY_CELL_FIELDS = [
  "transactionCount",
  "medianPrice",
  "priceObservations",
  "medianPsf",
  "psfObservations",
] as const;

export type MonthlyCellField = (typeof MONTHLY_CELL_FIELDS)[number];

export type MonthlyCell = [
  transactionCount: number,
  medianPrice: number | null,
  priceObservations: number,
  medianPsf: number | null,
  psfObservations: number,
];

export const MONTHLY_ROLES = [
  "area-monthly-all",
  "area-monthly-hdb",
  "area-monthly-ec",
  "area-monthly-condo",
] as const;

export type MonthlyRole = (typeof MONTHLY_ROLES)[number];

const PROPERTY_TYPE_BY_ROLE: Record<MonthlyRole, PropertyTypeId> = {
  "area-monthly-all": "all",
  "area-monthly-hdb": "hdb",
  "area-monthly-ec": "ec",
  "area-monthly-condo": "condo",
};

/** Manifest role for a property type's monthly history payload. */
export function monthlyRole(propertyType: PropertyTypeId): MonthlyRole {
  switch (propertyType) {
    case "all":
      return "area-monthly-all";
    case "hdb":
      return "area-monthly-hdb";
    case "ec":
      return "area-monthly-ec";
    case "condo":
      return "area-monthly-condo";
    default:
      throw new Error(`unknown property type ${String(propertyType)}`);
  }
}

/** Property type a monthly role describes; `null` for a non-monthly role. */
export function propertyTypeForRole(role: string): PropertyTypeId | null {
  return (MONTHLY_ROLES as readonly string[]).includes(role)
    ? PROPERTY_TYPE_BY_ROLE[role as MonthlyRole]
    : null;
}

export interface MonthlyCoverage {
  /** First covered month, or `null` when the type was never observed. */
  firstMonth: string | null;
  /** Last covered month, or `null` when the type was never observed. */
  lastMonth: string | null;
  monthCount: number;
  /** Reader-facing statement of the coverage rule above. */
  rule: string;
}

export interface MonthlySeries {
  geographyId: string;
  /** Covered months inside the grid with zero included transactions. */
  noSalesMonths: number;
  /** One cell per entry of `MonthlyHistory.months`, in the same order. */
  cells: MonthlyCell[];
}

export interface MonthlyHistory {
  schemaVersion: string;
  methodVersion: string;
  cutoffMonth: string;
  propertyType: PropertyTypeId;
  disposition: ObservationDisposition;
  /** National scope id (`SG`); always one of the published series. */
  nationalId: string;
  /**
   * Transactions the pipeline could not assign to a planning area. They are
   * real rows and stay in the national scope, but they are **not** areas: an
   * area list, distribution or map must exclude them.
   */
  unassignedIds: string[];
  months: string[];
  coverage: MonthlyCoverage;
  series: MonthlySeries[];
  seriesById: Map<string, MonthlySeries>;
}

export type MonthlyParse =
  | { ok: true; history: MonthlyHistory }
  | { ok: false; errors: string[] };

export interface MonthlyParseOptions {
  /** When given, the payload must declare this property type. */
  propertyType?: PropertyTypeId;
  /** When given, the payload must declare this cutoff. */
  cutoffMonth?: string;
}

export type MonthlyStatus = "available" | "no-sales" | "missing-source";

export interface MonthlyReading {
  month: string;
  status: MonthlyStatus;
  transactionCount: number | null;
  medianPrice: number | null;
  priceObservations: number;
  medianPsf: number | null;
  psfObservations: number;
}

const MONTH_PATTERN = /^\d{4}-(0[1-9]|1[0-2])$/;
const NATIONAL_ID = "SG";
function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isMonth(value: unknown): value is string {
  return typeof value === "string" && MONTH_PATTERN.test(value);
}

function isPropertyType(value: unknown): value is PropertyTypeId {
  return (
    value === "all" || value === "hdb" || value === "ec" || value === "condo"
  );
}

function isDisposition(value: unknown): value is ObservationDisposition {
  return (
    value === "publish" || value === "limited-display" || value === "withhold"
  );
}

function monthIndex(month: string): number {
  return Number(month.slice(0, 4)) * 12 + Number(month.slice(5, 7)) - 1;
}

function isCount(value: unknown): value is number {
  return typeof value === "number" && Number.isInteger(value) && value >= 0;
}

function isOptionalMedian(value: unknown): value is number | null {
  return (
    value === null || (typeof value === "number" && Number.isFinite(value))
  );
}

function parseCell(
  raw: unknown,
  label: string,
  errors: string[],
): MonthlyCell | null {
  if (!Array.isArray(raw)) {
    errors.push(`${label} is not an array`);
    return null;
  }
  if (raw.length !== MONTHLY_CELL_FIELDS.length) {
    errors.push(
      `${label} has ${raw.length} fields, expected ${MONTHLY_CELL_FIELDS.length}`,
    );
    return null;
  }
  const [count, price, priceObs, psf, psfObs] = raw;
  if (!isCount(count)) {
    errors.push(`${label} has no transaction count`);
    return null;
  }
  if (!isCount(priceObs) || priceObs > count) {
    errors.push(`${label} has an invalid price observation count`);
    return null;
  }
  if (!isCount(psfObs) || psfObs > count) {
    errors.push(`${label} has an invalid psf observation count`);
    return null;
  }
  if (!isOptionalMedian(price) || (price === null) !== (priceObs === 0)) {
    errors.push(`${label} price and its observation count disagree`);
    return null;
  }
  if (!isOptionalMedian(psf) || (psf === null) !== (psfObs === 0)) {
    errors.push(`${label} psf and its observation count disagree`);
    return null;
  }
  return [count, price, priceObs, psf, psfObs];
}

function parseMonths(raw: unknown, errors: string[]): string[] {
  if (!Array.isArray(raw)) {
    errors.push("months is not an array");
    return [];
  }
  const months: string[] = [];
  for (const [index, month] of raw.entries()) {
    if (!isMonth(month)) {
      errors.push(`months[${index}] is not a YYYY-MM month`);
      return [];
    }
    if (index > 0 && monthIndex(month) <= monthIndex(months[index - 1])) {
      errors.push(`months[${index}] is not after ${months[index - 1]}`);
      return [];
    }
    months.push(month);
  }
  return months;
}

function parseCoverage(
  raw: unknown,
  months: string[],
  errors: string[],
): MonthlyCoverage | null {
  if (!isRecord(raw)) {
    errors.push("coverage is not an object");
    return null;
  }
  const firstMonth = months[0] ?? null;
  const lastMonth = months.at(-1) ?? null;
  if (raw.monthCount !== months.length) {
    errors.push("coverage.monthCount disagrees with the month grid");
    return null;
  }
  if (raw.firstMonth !== firstMonth || raw.lastMonth !== lastMonth) {
    errors.push("coverage bounds disagree with the month grid");
    return null;
  }
  return {
    firstMonth,
    lastMonth,
    monthCount: months.length,
    rule: typeof raw.rule === "string" ? raw.rule : "",
  };
}

/** Series ids that are planning areas: everything except national + unassigned. */
function areaSeriesIds(
  seriesById: Map<string, MonthlySeries>,
  nationalId: string,
  unassignedIds: readonly string[],
): string[] {
  const excluded = new Set([nationalId, ...unassignedIds]);
  return [...seriesById.keys()].filter((id) => !excluded.has(id));
}

/**
 * Area-only series, in payload order.
 *
 * Prefer this over `history.series` whenever an area list, distribution, rank
 * or map is built: the national scope and the unassigned bucket are real data
 * but are not planning areas.
 */
export function areaSeries(history: MonthlyHistory): MonthlySeries[] {
  const excluded = new Set([history.nationalId, ...history.unassignedIds]);
  return history.series.filter((entry) => !excluded.has(entry.geographyId));
}

/**
 * Validate one monthly history payload.
 *
 * Anything the exporter cannot produce is rejected rather than repaired: a
 * grid/cell length mismatch, a reordered `cellFields` list, a median without
 * its observation count, or a month grid that is not strictly ascending.
 */
export function parseMonthlyHistory(
  raw: unknown,
  options: MonthlyParseOptions = {},
): MonthlyParse {
  const errors: string[] = [];

  if (!isRecord(raw))
    return { ok: false, errors: ["monthly payload is not an object"] };
  if (raw.schemaVersion !== V2_SCHEMA_VERSION) {
    errors.push(
      `unsupported monthly schemaVersion ${String(raw.schemaVersion)}`,
    );
  }
  if (!isMonth(raw.cutoffMonth)) {
    errors.push("monthly payload has no cutoffMonth");
  }
  if (
    options.cutoffMonth !== undefined &&
    raw.cutoffMonth !== options.cutoffMonth
  ) {
    errors.push("monthly cutoff disagrees with the manifest");
  }
  if (!isPropertyType(raw.propertyType)) {
    errors.push(`unknown propertyType ${String(raw.propertyType)}`);
  }
  if (
    options.propertyType !== undefined &&
    raw.propertyType !== options.propertyType
  ) {
    errors.push(
      `monthly payload declares ${String(raw.propertyType)}, expected ${options.propertyType}`,
    );
  }
  if (!isDisposition(raw.disposition)) {
    errors.push(`unknown disposition ${String(raw.disposition)}`);
  }
  if (
    !Array.isArray(raw.cellFields) ||
    raw.cellFields.length !== MONTHLY_CELL_FIELDS.length ||
    raw.cellFields.some((field, index) => field !== MONTHLY_CELL_FIELDS[index])
  ) {
    errors.push("cellFields does not match the published cell contract");
  }

  const months = parseMonths(raw.months, errors);
  const coverage = parseCoverage(raw.coverage, months, errors);

  const rawSeries = raw.series;
  if (!Array.isArray(rawSeries)) {
    return { ok: false, errors: [...errors, "monthly payload has no series"] };
  }

  const series: MonthlySeries[] = [];
  const seriesById = new Map<string, MonthlySeries>();
  rawSeries.forEach((entry, index) => {
    if (!isRecord(entry)) {
      errors.push(`series[${index}] is not an object`);
      return;
    }
    const geographyId = entry.geographyId;
    if (typeof geographyId !== "string" || geographyId.length === 0) {
      errors.push(`series[${index}] has no geographyId`);
      return;
    }
    if (seriesById.has(geographyId)) {
      errors.push(`duplicate series ${geographyId}`);
      return;
    }
    const rawCells = entry.cells;
    if (!Array.isArray(rawCells)) {
      errors.push(`series ${geographyId} has no cells`);
      return;
    }
    if (rawCells.length !== months.length) {
      errors.push(
        `series ${geographyId} has ${rawCells.length} cells for ${months.length} months`,
      );
      return;
    }
    const cells: MonthlyCell[] = [];
    for (const [position, rawCell] of rawCells.entries()) {
      const cell = parseCell(
        rawCell,
        `series ${geographyId} cell ${months[position] ?? position}`,
        errors,
      );
      if (cell === null) return;
      cells.push(cell);
    }
    const noSales = cells.filter((cell) => cell[0] === 0).length;
    if (entry.noSalesMonths !== noSales) {
      errors.push(
        `series ${geographyId} reports ${String(entry.noSalesMonths)} no-sales months, ${noSales} found`,
      );
      return;
    }
    const parsedSeries: MonthlySeries = {
      geographyId,
      noSalesMonths: noSales,
      cells,
    };
    series.push(parsedSeries);
    seriesById.set(geographyId, parsedSeries);
  });

  if (months.length > 0 && !seriesById.has(NATIONAL_ID)) {
    errors.push("monthly payload has no national series");
  }

  // The payload must say which ids are areas. Without this a reader counts the
  // unassigned bucket (real rows that no planning area claimed) as a planning
  // area and shifts every distribution it computes.
  const rawGeographies = raw.geographies;
  let nationalId = NATIONAL_ID;
  const unassignedIds: string[] = [];
  if (!isRecord(rawGeographies)) {
    errors.push("monthly payload does not declare its geographies");
  } else {
    if (
      typeof rawGeographies.national !== "string" ||
      rawGeographies.national === ""
    ) {
      errors.push("geographies.national is not an id");
    } else {
      nationalId = rawGeographies.national;
      if (months.length > 0 && !seriesById.has(nationalId)) {
        errors.push(`geographies.national ${nationalId} has no series`);
      }
    }
    if (!Array.isArray(rawGeographies.unassigned)) {
      errors.push("geographies.unassigned is not an array");
    } else {
      for (const id of rawGeographies.unassigned) {
        if (typeof id !== "string" || id === "" || id === nationalId) {
          errors.push(`geographies.unassigned has an invalid id ${String(id)}`);
          continue;
        }
        if (months.length > 0 && !seriesById.has(id)) {
          errors.push(`geographies.unassigned ${id} has no series`);
          continue;
        }
        unassignedIds.push(id);
      }
    }
    if (
      typeof rawGeographies.areaCount !== "number" ||
      !Number.isInteger(rawGeographies.areaCount) ||
      rawGeographies.areaCount < 0
    ) {
      errors.push("geographies.areaCount is not a count");
    } else {
      const areas = areaSeriesIds(seriesById, nationalId, unassignedIds);
      if (rawGeographies.areaCount !== areas.length) {
        errors.push("geographies.areaCount disagrees with the declared series");
      }
    }
  }

  if (errors.length > 0 || coverage === null) return { ok: false, errors };

  return {
    ok: true,
    history: {
      schemaVersion: V2_SCHEMA_VERSION,
      methodVersion: String(raw.methodVersion ?? ""),
      cutoffMonth: String(raw.cutoffMonth),
      propertyType: raw.propertyType as PropertyTypeId,
      disposition: raw.disposition as ObservationDisposition,
      nationalId,
      unassignedIds,
      months,
      coverage,
      series,
      seriesById,
    },
  };
}

/**
 * Read one month for one geography.
 *
 * Returns `missing-source` — never zero — for a month outside the published
 * grid or a geography the release does not carry.
 */
export function readMonth(
  history: MonthlyHistory,
  geographyId: string,
  month: string,
): MonthlyReading {
  const position = history.months.indexOf(month);
  const entry = history.seriesById.get(geographyId);
  if (position === -1 || entry === undefined) {
    return {
      month,
      status: "missing-source",
      transactionCount: null,
      medianPrice: null,
      priceObservations: 0,
      medianPsf: null,
      psfObservations: 0,
    };
  }
  const [count, price, priceObs, psf, psfObs] = entry.cells[position];
  return {
    month,
    status: count === 0 ? "no-sales" : "available",
    transactionCount: count,
    medianPrice: price,
    priceObservations: priceObs,
    medianPsf: psf,
    psfObservations: psfObs,
  };
}

/** Covered month grid of one geography, in ascending order. */
export function coveredHistoryMonths(
  history: MonthlyHistory,
  geographyId: string,
): string[] {
  return history.seriesById.has(geographyId) ? history.months : [];
}
