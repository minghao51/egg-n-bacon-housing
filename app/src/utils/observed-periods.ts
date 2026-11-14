/**
 * Client-safe reader for the v2 observed-period pack.
 *
 * The pack is produced by `scripts/v2_observed.py` and consists of two
 * immutable payloads plus a discovery manifest:
 *
 *   observed/<generation>/periods.json.gz   period descriptors
 *   observed/<generation>/summary.json.gz   observations per scope
 *
 * This module only parses, validates and resolves. It performs no fetch, holds
 * no React state and never falls back to a different population, window or
 * metric: an unavailable value stays `null` with the reason attached.
 *
 * Contract (see docs/plans/2026-11-12-reporting-refresh-implementation-map.md §5):
 * - Period ids are concrete (`month_2026_10`, `ttm_2026_10`). Friendly aliases
 *   resolve through the loaded pack, never the browser clock.
 * - A change is only computable when both windows are published, available and
 *   share the same property type and geography.
 * - Dispositions gate what a scope may be used for.
 */

import { ERA_DEFINITIONS } from "./observed-data";

export const V2_SCHEMA_VERSION = "2.1.0";

/**
 * Legacy `map_metrics` era ids, read from the one module that defines them.
 *
 * A pack descriptor carrying one of these ids is never offered as a period
 * option: every surface resolves a legacy id to the legacy asset, so a second
 * control with the same label would name two different windows.
 */
const LEGACY_PERIOD_IDS: ReadonlySet<string> = new Set(
  ERA_DEFINITIONS.map((era) => era.id),
);

export type PeriodKind = "month" | "rolling3" | "ytd" | "ttm" | "year";

/**
 * Shape of a concrete observed-period id: the kind, a four-digit year and, for
 * a dated kind, a real two-digit month. `year_` takes no month — a completed
 * year is one window, not a dated one.
 *
 * Every surface that accepts a period from a URL uses this union and
 * {@link isObservedPeriodId}, so a hand-edited or truncated link cannot widen
 * the vocabulary a renderer has to handle.
 */
export type ObservedPeriodId =
  | `month_${number}_${number}`
  | `rolling3_${number}_${number}`
  | `ytd_${number}_${number}`
  | `ttm_${number}_${number}`
  | `year_${number}`;

const CONCRETE_PERIOD_PATTERN =
  /^(?:(?:month|rolling3|ytd|ttm)_\d{4}_(?:0[1-9]|1[0-2])|year_\d{4})$/;

/** True for a well-formed concrete period id, published or not. */
export function isObservedPeriodId(value: string): value is ObservedPeriodId {
  return CONCRETE_PERIOD_PATTERN.test(value);
}

export const PERIOD_KINDS: readonly PeriodKind[] = [
  "month",
  "rolling3",
  "ytd",
  "ttm",
  "year",
];

export type PeriodAlias = "latest" | "ytd" | "ttm";

export type PropertyTypeId = "all" | "hdb" | "ec" | "condo";

export const PROPERTY_TYPES: readonly PropertyTypeId[] = [
  "all",
  "hdb",
  "ec",
  "condo",
];

export type ObservationStatus = "available" | "no-sales";

export type ObservationDisposition = "publish" | "limited-display" | "withhold";

export type MetricId = "transactionCount" | "medianPrice" | "medianPsf";

export interface MetricValue {
  value: number | null;
  unit: string;
  observations: number;
}

export interface PeriodDescriptor {
  id: string;
  kind: PeriodKind;
  startMonth: string;
  endMonth: string;
  months: string[];
  label: string;
  comparatorId: string | null;
}

export interface ObservationCoverage {
  months: string[];
  requestedMonths: number;
}

export interface Observation {
  geographyId: string;
  propertyType: PropertyTypeId;
  periodId: string;
  status: ObservationStatus;
  disposition: ObservationDisposition;
  coverage: ObservationCoverage;
  metrics: Record<MetricId, MetricValue>;
}

export interface PeriodPack {
  schemaVersion: string;
  methodVersion: string;
  cutoffMonth: string;
  cutoffSource: string;
  periods: PeriodDescriptor[];
  observations: Observation[];
  periodsById: Map<string, PeriodDescriptor>;
  observationsByKey: Map<string, Observation>;
}

export type ParseResult =
  | { ok: true; pack: PeriodPack }
  | { ok: false; errors: string[] };

const MONTH_PATTERN = /^\d{4}-(0[1-9]|1[0-2])$/;
const METRIC_IDS: readonly MetricId[] = [
  "transactionCount",
  "medianPrice",
  "medianPsf",
];

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isMonth(value: unknown): value is string {
  return typeof value === "string" && MONTH_PATTERN.test(value);
}

function isDisposition(value: unknown): value is ObservationDisposition {
  return (
    value === "publish" || value === "limited-display" || value === "withhold"
  );
}

function isPropertyType(value: unknown): value is PropertyTypeId {
  return (
    value === "all" || value === "hdb" || value === "ec" || value === "condo"
  );
}

function isPeriodKind(value: unknown): value is PeriodKind {
  return (
    value === "month" ||
    value === "rolling3" ||
    value === "ytd" ||
    value === "ttm" ||
    value === "year"
  );
}

/** Inclusive month list; `null` when the bounds are malformed or reversed. */
export function monthsBetween(
  startMonth: string,
  endMonth: string,
): string[] | null {
  if (!isMonth(startMonth) || !isMonth(endMonth)) return null;

  const toIndex = (month: string): number =>
    Number(month.slice(0, 4)) * 12 + Number(month.slice(5, 7)) - 1;

  const start = toIndex(startMonth);
  const end = toIndex(endMonth);
  if (end < start) return null;

  const months: string[] = [];
  for (let index = start; index <= end; index += 1) {
    const year = Math.floor(index / 12);
    const month = (index % 12) + 1;
    months.push(
      `${String(year).padStart(4, "0")}-${String(month).padStart(2, "0")}`,
    );
  }
  return months;
}

export function observationKey(
  geographyId: string,
  propertyType: PropertyTypeId,
  periodId: string,
): string {
  return `${geographyId}|${propertyType}|${periodId}`;
}

function parsePeriod(
  raw: unknown,
  index: number,
  errors: string[],
): PeriodDescriptor | null {
  if (!isRecord(raw)) {
    errors.push(`periods[${index}] is not an object`);
    return null;
  }

  const { id, kind, startMonth, endMonth, months, label, comparatorId } = raw;

  if (typeof id !== "string" || id.length === 0) {
    errors.push(`periods[${index}] has no id`);
    return null;
  }
  if (!isPeriodKind(kind)) {
    errors.push(`period ${id} has an unknown kind`);
    return null;
  }
  if (!isMonth(startMonth) || !isMonth(endMonth)) {
    errors.push(`period ${id} has invalid month bounds`);
    return null;
  }

  const expected = monthsBetween(startMonth, endMonth);
  if (expected === null) {
    errors.push(`period ${id} has reversed bounds`);
    return null;
  }
  if (
    !Array.isArray(months) ||
    months.length !== expected.length ||
    months.some((month, position) => month !== expected[position])
  ) {
    errors.push(`period ${id} months do not match its bounds`);
    return null;
  }

  if (
    comparatorId !== null &&
    (typeof comparatorId !== "string" || comparatorId === "")
  ) {
    errors.push(`period ${id} has an invalid comparatorId`);
    return null;
  }

  return {
    id,
    kind,
    startMonth,
    endMonth,
    months: expected,
    label: typeof label === "string" ? label : id,
    comparatorId: typeof comparatorId === "string" ? comparatorId : null,
  };
}

function parseMetric(
  raw: unknown,
  metric: MetricId,
  observationId: string,
  errors: string[],
): MetricValue | null {
  if (!isRecord(raw)) {
    errors.push(`${observationId} is missing metric ${metric}`);
    return null;
  }
  const { value, unit, observations } = raw;
  if (
    value !== null &&
    (typeof value !== "number" || !Number.isFinite(value))
  ) {
    errors.push(`${observationId} metric ${metric} has a non-numeric value`);
    return null;
  }
  if (typeof observations !== "number" || !Number.isFinite(observations)) {
    errors.push(`${observationId} metric ${metric} has no observation count`);
    return null;
  }
  return {
    value: value as number | null,
    unit: typeof unit === "string" ? unit : "",
    observations,
  };
}

function parseObservation(
  raw: unknown,
  index: number,
  periodsById: Map<string, PeriodDescriptor>,
  errors: string[],
): Observation | null {
  if (!isRecord(raw)) {
    errors.push(`observations[${index}] is not an object`);
    return null;
  }

  const {
    geographyId,
    propertyType,
    periodId,
    status,
    disposition,
    coverage,
    metrics,
  } = raw;

  if (typeof geographyId !== "string" || geographyId.length === 0) {
    errors.push(`observations[${index}] has no geographyId`);
    return null;
  }
  if (!isPropertyType(propertyType)) {
    errors.push(`observation ${geographyId} has an unknown propertyType`);
    return null;
  }
  if (typeof periodId !== "string" || !periodsById.has(periodId)) {
    errors.push(`observation ${geographyId} references an unpublished period`);
    return null;
  }
  if (status !== "available" && status !== "no-sales") {
    errors.push(`observation ${geographyId}/${periodId} has an unknown status`);
    return null;
  }
  if (!isDisposition(disposition)) {
    errors.push(
      `observation ${geographyId}/${periodId} has an unknown disposition`,
    );
    return null;
  }
  if (!isRecord(coverage) || !Array.isArray(coverage.months)) {
    errors.push(
      `observation ${geographyId}/${periodId} has no coverage months`,
    );
    return null;
  }

  const parsedMetrics = {} as Record<MetricId, MetricValue>;
  for (const metric of METRIC_IDS) {
    const parsed = parseMetric(
      isRecord(metrics) ? metrics[metric] : undefined,
      metric,
      `${geographyId}/${propertyType}/${periodId}`,
      errors,
    );
    if (parsed === null) return null;
    parsedMetrics[metric] = parsed;
  }

  const count = parsedMetrics.transactionCount.value;
  if (status === "no-sales" && count !== 0 && count !== null) {
    errors.push(
      `observation ${geographyId}/${periodId} is no-sales with a non-zero count`,
    );
    return null;
  }
  if (status === "no-sales" && parsedMetrics.medianPrice.value !== null) {
    errors.push(
      `observation ${geographyId}/${periodId} is no-sales with a price`,
    );
    return null;
  }

  return {
    geographyId,
    propertyType,
    periodId,
    status,
    disposition,
    coverage: {
      months: coverage.months.map(String),
      requestedMonths:
        typeof coverage.requestedMonths === "number"
          ? coverage.requestedMonths
          : coverage.months.length,
    },
    metrics: parsedMetrics,
  };
}

/**
 * Validate and index the two v2 payloads.
 *
 * Returns explicit errors rather than a partial pack: a caller must not render
 * numbers from a payload that failed validation.
 */
export function parsePeriodPack(
  periodsPayload: unknown,
  summaryPayload: unknown,
): ParseResult {
  const errors: string[] = [];

  if (!isRecord(periodsPayload)) {
    return { ok: false, errors: ["periods payload is not an object"] };
  }
  if (!isRecord(summaryPayload)) {
    return { ok: false, errors: ["summary payload is not an object"] };
  }
  if (periodsPayload.schemaVersion !== V2_SCHEMA_VERSION) {
    errors.push(
      `unsupported periods schemaVersion ${String(periodsPayload.schemaVersion)}`,
    );
  }
  if (summaryPayload.schemaVersion !== V2_SCHEMA_VERSION) {
    errors.push(
      `unsupported summary schemaVersion ${String(summaryPayload.schemaVersion)}`,
    );
  }
  if (periodsPayload.cutoffMonth !== summaryPayload.cutoffMonth) {
    errors.push("periods and summary disagree about the cutoff month");
  }

  const rawPeriods = periodsPayload.periods;
  if (!Array.isArray(rawPeriods) || rawPeriods.length === 0) {
    return { ok: false, errors: [...errors, "periods payload has no periods"] };
  }

  const periods: PeriodDescriptor[] = [];
  const periodsById = new Map<string, PeriodDescriptor>();
  rawPeriods.forEach((raw, index) => {
    const period = parsePeriod(raw, index, errors);
    if (period === null) return;
    if (periodsById.has(period.id)) {
      errors.push(`duplicate period id ${period.id}`);
      return;
    }
    periods.push(period);
    periodsById.set(period.id, period);
  });

  for (const period of periods) {
    if (period.comparatorId !== null && !periodsById.has(period.comparatorId)) {
      errors.push(
        `period ${period.id} references unpublished comparator ${period.comparatorId}`,
      );
    }
  }

  const rawObservations = summaryPayload.observations;
  if (!Array.isArray(rawObservations)) {
    return {
      ok: false,
      errors: [...errors, "summary payload has no observations"],
    };
  }

  const observations: Observation[] = [];
  const observationsByKey = new Map<string, Observation>();
  rawObservations.forEach((raw, index) => {
    const observation = parseObservation(raw, index, periodsById, errors);
    if (observation === null) return;
    const key = observationKey(
      observation.geographyId,
      observation.propertyType,
      observation.periodId,
    );
    if (observationsByKey.has(key)) {
      errors.push(`duplicate observation ${key}`);
      return;
    }
    observations.push(observation);
    observationsByKey.set(key, observation);
  });

  if (errors.length > 0) return { ok: false, errors };

  return {
    ok: true,
    pack: {
      schemaVersion: V2_SCHEMA_VERSION,
      methodVersion: String(summaryPayload.methodVersion ?? ""),
      cutoffMonth: String(summaryPayload.cutoffMonth),
      cutoffSource: String(summaryPayload.cutoffSource ?? "unknown"),
      periods,
      observations,
      periodsById,
      observationsByKey,
    },
  };
}

/** Structured max/min by end month; ties fall back to the longer window. */
function pickPeriod(
  pack: PeriodPack,
  predicate: (period: PeriodDescriptor) => boolean,
): PeriodDescriptor | null {
  const candidates = pack.periods.filter(predicate);
  if (candidates.length === 0) return null;
  return candidates.reduce((best, current) => {
    if (current.endMonth !== best.endMonth) {
      return current.endMonth > best.endMonth ? current : best;
    }
    return current.months.length > best.months.length ? current : best;
  });
}

/**
 * Resolve a friendly alias against the live pack.
 *
 * `latest` is the newest month, `ytd` the year-to-date window ending at the
 * cutoff, `ttm` the trailing-twelve-month window. Nothing consults the clock,
 * so a stale pack cannot look fresher than it is.
 */
export function resolvePeriodAlias(
  pack: PeriodPack,
  alias: PeriodAlias,
): PeriodDescriptor | null {
  if (alias === "latest") {
    return pickPeriod(pack, (period) => period.kind === "month");
  }
  if (alias === "ytd") {
    return pickPeriod(pack, (period) => period.kind === "ytd");
  }
  return pickPeriod(pack, (period) => period.kind === "ttm");
}

/** The default window each observed surface opens on (decision D03). */
export const DEFAULT_ALIAS_BY_SURFACE = {
  dashboard: "ytd",
  trends: "ttm",
  explorer: "ttm",
  rankings: "ttm",
} as const satisfies Record<string, PeriodAlias>;

export type ObservedSurface = keyof typeof DEFAULT_ALIAS_BY_SURFACE;

export function findObservation(
  pack: PeriodPack,
  geographyId: string,
  propertyType: PropertyTypeId,
  periodId: string,
): Observation | null {
  return (
    pack.observationsByKey.get(
      observationKey(geographyId, propertyType, periodId),
    ) ?? null
  );
}

export interface MetricChange {
  metric: MetricId;
  absolute: number;
  percent: number;
}

export interface PeriodComparison {
  current: Observation;
  comparator: Observation;
  comparatorPeriod: PeriodDescriptor;
  changes: MetricChange[];
  /** Metrics that could not be compared, with the reason. */
  skipped: { metric: MetricId; reason: string }[];
}

/**
 * Compare one observation with its published comparator.
 *
 * Returns `null` when the period declares no comparator (a partial window has
 * nothing valid to compare against) or when the comparator observation is
 * missing. Individual metrics that cannot be compared are listed in `skipped`
 * instead of being silently dropped.
 */
export function compareWithComparator(
  pack: PeriodPack,
  current: Observation,
): PeriodComparison | null {
  const period = pack.periodsById.get(current.periodId);
  if (!period || period.comparatorId === null) return null;

  const comparatorPeriod = pack.periodsById.get(period.comparatorId);
  if (!comparatorPeriod) return null;

  const comparator = findObservation(
    pack,
    current.geographyId,
    current.propertyType,
    comparatorPeriod.id,
  );
  if (!comparator) return null;

  const changes: MetricChange[] = [];
  const skipped: { metric: MetricId; reason: string }[] = [];

  for (const metric of METRIC_IDS) {
    if (current.status !== "available" || comparator.status !== "available") {
      skipped.push({ metric, reason: "not observed in both windows" });
      continue;
    }
    const now = current.metrics[metric].value;
    const before = comparator.metrics[metric].value;
    if (now === null || before === null) {
      skipped.push({ metric, reason: "value unavailable" });
      continue;
    }
    if (current.metrics[metric].unit !== comparator.metrics[metric].unit) {
      skipped.push({ metric, reason: "unit mismatch between windows" });
      continue;
    }
    const absolute = now - before;
    if (before === 0) {
      skipped.push({ metric, reason: "zero comparator denominator" });
      continue;
    }
    changes.push({ metric, absolute, percent: (absolute / before) * 100 });
  }

  return { current, comparator, comparatorPeriod, changes, skipped };
}

/** A scope may be presented as current evidence only when cleared to publish. */
export function isPublishable(observation: Observation): boolean {
  return (
    observation.disposition === "publish" && observation.status === "available"
  );
}

export function scopeNote(observation: Observation): string | null {
  if (observation.disposition === "withhold") {
    return "This scope is withheld pending source review.";
  }
  if (observation.disposition === "limited-display") {
    return "Coverage is limited for this scope: counts may be shown with their dates, but no growth headline or ranking.";
  }
  if (observation.status === "no-sales") {
    return "No sales were recorded in this window.";
  }
  return null;
}

/** Months the pack actually covers, derived from the observations. */
export function coveredMonths(pack: PeriodPack): string[] {
  const months = new Set<string>();
  for (const observation of pack.observations) {
    for (const month of observation.coverage.months) months.add(month);
  }
  return [...months].sort((left, right) => left.localeCompare(right));
}

/** True when the cut-off month itself has no observation (stale pack). */
export function cutoffUnobserved(pack: PeriodPack): boolean {
  return !pack.periods.some(
    (period) => period.endMonth === pack.cutoffMonth && period.kind === "month",
  );
}

/**
 * Period options a surface may offer: every published descriptor whose id is a
 * concrete period and is not shadowed by a legacy era id. A legacy id always
 * reads the legacy `map_metrics` era, so offering a pack descriptor with the
 * same id would be two different windows behind one label.
 */
export function publishedPeriodOptions(
  pack: PeriodPack,
): { value: ObservedPeriodId; label: string }[] {
  return pack.periods
    .filter(
      (period) =>
        isObservedPeriodId(period.id) && !LEGACY_PERIOD_IDS.has(period.id),
    )
    .map((period) => ({
      value: period.id as ObservedPeriodId,
      label: period.label,
    }));
}

/** Label for one published period id, or `null` when it is not published. */
export function packPeriodLabel(
  pack: PeriodPack,
  periodId: string,
): string | null {
  return pack.periodsById.get(periodId)?.label ?? null;
}
