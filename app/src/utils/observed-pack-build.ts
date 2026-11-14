/**
 * Build-time reader for the v2 observed pack.
 *
 * Astro pages already read the published gzip payloads from disk, so this
 * module verifies and parses the v2 pack the same way the browser loader does
 * (same manifest parser, same generation hash, same period parser) and then
 * hands the island a small, already-labelled summary.
 *
 * Nothing here queries the network, and a missing or invalid pack never
 * produces numbers: the caller gets `absent`/`invalid` and keeps the legacy
 * view.
 */

import { createHash } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { gunzipSync } from "node:zlib";

import {
  compareWithComparator,
  findObservation,
  parsePeriodPack,
  resolvePeriodAlias,
  type MetricId,
  type Observation,
  type PeriodPack,
  type PropertyTypeId,
} from "./observed-periods";
import {
  computeV2Generation,
  parseV2Manifest,
  V2_CORE_ROLES,
  type V2Manifest,
} from "./observed-pack-loader";
import {
  monthlyRole,
  parseMonthlyHistory,
  type MonthlyHistory,
} from "./observed-monthly";

export const V2_MANIFEST_FILE = "dashboard-release-v2.json";

export type BuildPackLoad =
  | { state: "ready"; manifest: V2Manifest; pack: PeriodPack }
  | { state: "absent" }
  | { state: "invalid"; errors: string[] };

function sha256(bytes: Buffer): string {
  return createHash("sha256").update(bytes).digest("hex");
}

/**
 * Verify the pack that lives in `dataDir`.
 *
 * The manifest is checked first, then each payload's size and hash, then the
 * decoded JSON is parsed by the shared contract validator.
 */
export async function loadObservedPackFromDir(
  dataDir: string,
): Promise<BuildPackLoad> {
  const manifestPath = join(dataDir, V2_MANIFEST_FILE);
  if (!existsSync(manifestPath)) return { state: "absent" };

  let rawManifest: unknown;
  try {
    rawManifest = JSON.parse(readFileSync(manifestPath, "utf8"));
  } catch (error) {
    return { state: "invalid", errors: [`manifest is not valid JSON: ${String(error)}`] };
  }

  const parsed = parseV2Manifest(rawManifest);
  if (!parsed.ok) return { state: "invalid", errors: parsed.errors };
  const manifest = parsed.manifest;

  const recomputed = await computeV2Generation(manifest.identity);
  if (recomputed !== manifest.generation) {
    return {
      state: "invalid",
      errors: [`generation mismatch: manifest ${manifest.generation}, recomputed ${recomputed}`],
    };
  }

  const payloads: Record<string, unknown> = {};
  for (const asset of manifest.assets) {
    // Only the period/summary pair is read on every page. Monthly history is
    // verified on demand by `readMonthlyHistoryFromDir`, against this same
    // manifest generation, so a page that shows a window does not parse four
    // history payloads it will never render.
    if (!(V2_CORE_ROLES as readonly string[]).includes(asset.role)) continue;
    const filePath = join(dataDir, asset.path);
    if (!existsSync(filePath)) {
      return { state: "invalid", errors: [`missing asset ${asset.path}`] };
    }
    const bytes = readFileSync(filePath);
    if (bytes.length !== asset.bytes) {
      return {
        state: "invalid",
        errors: [`${asset.path}: expected ${asset.bytes} bytes, found ${bytes.length}`],
      };
    }
    const digest = sha256(bytes);
    if (digest !== asset.sha256) {
      return { state: "invalid", errors: [`${asset.path}: sha256 mismatch`] };
    }
    try {
      payloads[asset.role] = JSON.parse(gunzipSync(bytes).toString("utf8"));
    } catch (error) {
      return { state: "invalid", errors: [`${asset.path}: ${String(error)}`] };
    }
  }

  const packResult = parsePeriodPack(payloads.periods, payloads.summary);
  if (!packResult.ok) return { state: "invalid", errors: packResult.errors };
  if (packResult.pack.cutoffMonth !== manifest.cutoffMonth) {
    return { state: "invalid", errors: ["pack cutoff does not match the manifest"] };
  }

  return { state: "ready", manifest, pack: packResult.pack };
}

export type BuildHistoryLoad =
  | { state: "ready"; history: MonthlyHistory }
  | { state: "invalid"; errors: string[] };

/**
 * Verify and parse one property type's monthly history from disk.
 *
 * Same rules as the browser loader: the recorded size and sha256 must cover
 * the exact bytes that are decoded, and the payload must declare the requested
 * property type and the manifest's cutoff.
 */
export function readMonthlyHistoryFromDir(
  dataDir: string,
  manifest: V2Manifest,
  propertyType: Parameters<typeof monthlyRole>[0],
): BuildHistoryLoad {
  const role = monthlyRole(propertyType);
  const asset = manifest.assets.find((entry) => entry.role === role);
  if (asset === undefined) {
    return { state: "invalid", errors: [`manifest has no asset for role ${role}`] };
  }
  const filePath = join(dataDir, asset.path);
  if (!existsSync(filePath)) return { state: "invalid", errors: [`missing asset ${asset.path}`] };

  const bytes = readFileSync(filePath);
  if (bytes.length !== asset.bytes) {
    return {
      state: "invalid",
      errors: [`${asset.path}: expected ${asset.bytes} bytes, found ${bytes.length}`],
    };
  }
  if (sha256(bytes) !== asset.sha256) {
    return { state: "invalid", errors: [`${asset.path}: sha256 mismatch`] };
  }

  let payload: unknown;
  try {
    payload = JSON.parse(gunzipSync(bytes).toString("utf8"));
  } catch (error) {
    return { state: "invalid", errors: [`${asset.path}: ${String(error)}`] };
  }

  const parsed = parseMonthlyHistory(payload, {
    propertyType,
    cutoffMonth: manifest.cutoffMonth,
  });
  if (!parsed.ok) return { state: "invalid", errors: parsed.errors };
  return { state: "ready", history: parsed.history };
}

export interface MetricReading {
  metric: MetricId;
  value: number | null;
  unit: string;
  observations: number;
  absoluteChange: number | null;
  percentChange: number | null;
  /** Why a change is unavailable, when it is. */
  changeNote: string | null;
}

export interface CurrentWindow {
  periodId: string;
  label: string;
  startMonth: string;
  endMonth: string;
  comparatorId: string | null;
  comparatorLabel: string | null;
  status: Observation["status"];
  disposition: Observation["disposition"];
  publishable: boolean;
  metrics: MetricReading[];
  note: string | null;
}

export interface TypeWindows {
  latest: CurrentWindow | null;
  ytd: CurrentWindow | null;
  ttm: CurrentWindow | null;
}

export type WindowsByType = Record<PropertyTypeId, TypeWindows>;

export interface CurrentDataSummary {
  cutoffMonth: string;
  cutoffSource: string;
  generation: string;
  propertyType: PropertyTypeId;
  ytd: CurrentWindow | null;
  latestMonth: CurrentWindow | null;
}

function readWindow(pack: PeriodPack, observation: Observation): CurrentWindow {
  const period = pack.periodsById.get(observation.periodId);
  const comparison = compareWithComparator(pack, observation);

  const metrics: MetricReading[] = (
    ["transactionCount", "medianPrice", "medianPsf"] as const
  ).map((metric) => {
    const reading = observation.metrics[metric];
    const change = comparison?.changes.find((entry) => entry.metric === metric);
    const skipped = comparison?.skipped.find((entry) => entry.metric === metric);
    return {
      metric,
      value: reading.value,
      unit: reading.unit,
      observations: reading.observations,
      absoluteChange: change?.absolute ?? null,
      percentChange: change?.percent ?? null,
      changeNote:
        change !== undefined
          ? null
          : period?.comparatorId === null
            ? "no published comparator"
            : (skipped?.reason ?? "comparator not published"),
    };
  });

  return {
    periodId: observation.periodId,
    label: period?.label ?? observation.periodId,
    startMonth: period?.startMonth ?? "",
    endMonth: period?.endMonth ?? "",
    comparatorId: period?.comparatorId ?? null,
    comparatorLabel: comparison?.comparatorPeriod.label ?? null,
    status: observation.status,
    disposition: observation.disposition,
    publishable:
      observation.disposition === "publish" && observation.status === "available",
    metrics,
    note: null,
  };
}

/**
 * Compact summary for the dashboard header.
 *
 * Only the windows the page shows are extracted; the full observation set
 * stays out of the island props.
 */
export function summariseForDashboard(
  pack: PeriodPack,
  generation: string,
  propertyType: PropertyTypeId = "hdb",
): CurrentDataSummary {
  const ytdPeriod = resolvePeriodAlias(pack, "ytd");
  const latestPeriod = resolvePeriodAlias(pack, "latest");

  const ytdObservation = ytdPeriod
    ? findObservation(pack, "SG", propertyType, ytdPeriod.id)
    : null;
  const latestObservation = latestPeriod
    ? findObservation(pack, "SG", propertyType, latestPeriod.id)
    : null;

  return {
    cutoffMonth: pack.cutoffMonth,
    cutoffSource: pack.cutoffSource,
    generation,
    propertyType,
    ytd: ytdObservation ? readWindow(pack, ytdObservation) : null,
    latestMonth: latestObservation ? readWindow(pack, latestObservation) : null,
  };
}

/**
 * Every published window for every property type.
 *
 * Used where a surface lets the reader switch window and type without a
 * fetch; the payload is still the verified pack, just pre-extracted.
 */
export function summariseWindows(
  pack: PeriodPack,
  _generation: string,
): WindowsByType {
  const latestPeriod = resolvePeriodAlias(pack, "latest");
  const ytdPeriod = resolvePeriodAlias(pack, "ytd");
  const ttmPeriod = resolvePeriodAlias(pack, "ttm");

  const windowsFor = (propertyType: PropertyTypeId): TypeWindows => ({
    latest: latestPeriod
      ? (() => {
          const observation = findObservation(pack, "SG", propertyType, latestPeriod.id);
          return observation ? readWindow(pack, observation) : null;
        })()
      : null,
    ytd: ytdPeriod
      ? (() => {
          const observation = findObservation(pack, "SG", propertyType, ytdPeriod.id);
          return observation ? readWindow(pack, observation) : null;
        })()
      : null,
    ttm: ttmPeriod
      ? (() => {
          const observation = findObservation(pack, "SG", propertyType, ttmPeriod.id);
          return observation ? readWindow(pack, observation) : null;
        })()
      : null,
  });

  return {
    all: windowsFor("all"),
    hdb: windowsFor("hdb"),
    ec: windowsFor("ec"),
    condo: windowsFor("condo"),
  };
}
