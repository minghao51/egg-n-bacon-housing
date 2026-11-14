import { createHash } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
import { gunzipSync } from "node:zlib";

const root = new URL("../public/data/", import.meta.url);

/**
 * Read and parse a JSON asset with a named error.
 *
 * These files are generated, so "not valid JSON" must name the artefact that
 * broke instead of surfacing a bare SyntaxError from deep inside the validator.
 */
function readJson(url, label) {
  let text;
  try {
    text = readFileSync(url, "utf8");
  } catch (error) {
    throw new Error(`${label}: unreadable (${error?.message ?? error})`);
  }
  try {
    return JSON.parse(text);
  } catch (error) {
    throw new Error(`${label}: not valid JSON (${error?.message ?? error})`);
  }
}
const manifest = readJson(new URL("manifest.json", root), "manifest.json");

for (const asset of manifest.assets) {
  const url = new URL(asset.path, root);
  if (!existsSync(url))
    throw new Error(`Missing app data asset: ${asset.path}`);
  for (const field of [
    "logicalSource",
    "schemaVersion",
    "provenance",
    "shape",
  ]) {
    if (!(field in asset))
      throw new Error(`${asset.path}: manifest missing ${field}`);
  }
  if (asset.shape === "file") continue;
  let value;
  try {
    const bytes = readFileSync(url);
    const text = asset.path.endsWith(".gz")
      ? gunzipSync(bytes).toString("utf8")
      : bytes.toString("utf8");
    value =
      asset.shape === "jsonl"
        ? text
            .trim()
            .split("\n")
            .map((line) => JSON.parse(line))
        : JSON.parse(text);
  } catch (error) {
    throw new Error(`Invalid JSON asset ${asset.path}: ${error}`);
  }
  const shape =
    asset.shape === "geojson"
      ? value?.type === "FeatureCollection"
        ? "geojson"
        : "object"
      : asset.shape === "jsonl"
        ? "jsonl"
        : Array.isArray(value)
          ? "array"
          : value !== null && typeof value === "object"
            ? "object"
            : typeof value;
  if (shape !== asset.shape)
    throw new Error(`${asset.path}: expected ${asset.shape}, got ${shape}`);
  for (const key of asset.requiredKeys ?? []) {
    if (!(key in value))
      throw new Error(`${asset.path}: missing required key ${key}`);
  }
}

console.log(`Validated ${manifest.assets.length} app data assets`);

// ---------------------------------------------------------------------------
// Publication compatibility metadata
//
// scripts/export_app_data.py publishes dashboard-release.json after it replaces
// the seven dashboard payloads: schema version, one content-derived generation
// id, and a sha256/size record per asset. Verifying it here proves the seven
// files on disk are the ones that single exporter run produced. A tree that has
// not regenerated assets yet only warns, so the shape gate above keeps working.
// ---------------------------------------------------------------------------

const RELEASE_SCHEMA_VERSION = "1.0.0";
// dashboard-release.json must record exactly the seven assets the exporter owns.
// manifest.json does not tag them separately, so they are named explicitly.
const RELEASE_ASSETS = [
  "dashboard_overview.json.gz",
  "dashboard_trends.json.gz",
  "dashboard_segments.json.gz",
  "dashboard_leaderboard.json.gz",
  "map_metrics.json.gz",
  "hotspots.json.gz",
  "amenity_summary.json.gz",
];

function sha256(bytes) {
  return createHash("sha256").update(bytes).digest("hex");
}

// Canonical JSON matching the Python exporter: sorted keys, compact separators.
function canonicalJson(value) {
  if (Array.isArray(value))
    return `[${value.map((entry) => canonicalJson(entry)).join(",")}]`;
  if (value !== null && typeof value === "object") {
    const fields = Object.keys(value)
      .sort()
      .map((key) => `${JSON.stringify(key)}:${canonicalJson(value[key])}`);
    return `{${fields.join(",")}}`;
  }
  return JSON.stringify(value);
}

const releaseUrl = new URL("dashboard-release.json", root);
if (!existsSync(releaseUrl)) {
  console.warn(
    "Warning: dashboard-release.json is missing; dashboard assets have no verified single-generation identity (run scripts/export_app_data.py to publish one)",
  );
} else {
  const release = readJson(releaseUrl, "dashboard-release.json");
  if (release === null || typeof release !== "object" || Array.isArray(release))
    throw new Error("dashboard-release.json: expected a JSON object");
  if (!Array.isArray(release.assets))
    throw new Error("dashboard-release.json: expected an assets array");
  if (release.schemaVersion !== RELEASE_SCHEMA_VERSION)
    throw new Error(
      `dashboard-release.json: schemaVersion ${release.schemaVersion} != ${RELEASE_SCHEMA_VERSION}`,
    );

  const recorded = new Map();
  for (const asset of release.assets) {
    if (!asset?.path || !asset.sha256 || !Number.isInteger(asset.bytes))
      throw new Error(
        `dashboard-release.json: malformed asset entry ${JSON.stringify(asset)}`,
      );
    recorded.set(asset.path, asset);
  }
  if (recorded.size !== RELEASE_ASSETS.length)
    throw new Error(
      `dashboard-release.json: records ${recorded.size} assets, expected ${RELEASE_ASSETS.length}`,
    );

  const manifestPaths = new Set(manifest.assets.map((asset) => asset.path));
  for (const path of RELEASE_ASSETS) {
    if (!manifestPaths.has(path))
      throw new Error(
        `dashboard-release.json: ${path} is not a manifest.json asset`,
      );
    const asset = recorded.get(path);
    if (!asset)
      throw new Error(`dashboard-release.json: missing asset entry ${path}`);
    const url = new URL(path, root);
    if (!existsSync(url))
      throw new Error(`dashboard-release.json: missing asset file ${path}`);
    const bytes = readFileSync(url);
    const digest = sha256(bytes);
    if (digest !== asset.sha256)
      throw new Error(
        `dashboard-release.json: ${path} hash ${digest} != recorded ${asset.sha256} (mixed release)`,
      );
    if (bytes.length !== asset.bytes)
      throw new Error(
        `dashboard-release.json: ${path} is ${bytes.length} bytes, recorded ${asset.bytes}`,
      );
  }
  for (const path of recorded.keys()) {
    if (!RELEASE_ASSETS.includes(path))
      throw new Error(`dashboard-release.json: unexpected asset ${path}`);
  }

  const content = { ...release };
  delete content.generation;
  delete content.generatedAt;
  const generation = sha256(Buffer.from(canonicalJson(content), "utf8"));
  if (generation !== release.generation)
    throw new Error(
      `dashboard-release.json: generation ${release.generation} does not match its content (${generation})`,
    );

  console.log(
    `Verified dashboard release ${String(release.generation).slice(0, 12)} (${recorded.size} assets)`,
  );
}

// --- v2 observed pack (optional, additive) ------------------------------- //
// Present once the v2 sidecar is published. Absent means the deployment still
// serves the legacy release; that is reported, never treated as a failure.
function monthsBetween(startMonth, endMonth) {
  const index = (month) =>
    Number(month.slice(0, 4)) * 12 + Number(month.slice(5, 7)) - 1;
  if (!/^\d{4}-(0[1-9]|1[0-2])$/.test(startMonth)) return null;
  if (!/^\d{4}-(0[1-9]|1[0-2])$/.test(endMonth)) return null;
  const start = index(startMonth);
  const end = index(endMonth);
  if (end < start) return null;
  return Array.from({ length: end - start + 1 }, (_, offset) => {
    const value = start + offset;
    return `${String(Math.floor(value / 12)).padStart(4, "0")}-${String((value % 12) + 1).padStart(2, "0")}`;
  });
}

function checkObservedPack() {
  const manifestUrl = new URL("dashboard-release-v2.json", root);
  if (!existsSync(manifestUrl)) {
    console.log("v2 observed pack: not published (legacy release only)");
    return;
  }

  const manifest = readJson(manifestUrl, "dashboard-release-v2.json");
  if (manifest.schemaVersion !== "2.1.0")
    throw new Error(
      `dashboard-release-v2.json: unsupported schemaVersion ${manifest.schemaVersion}`,
    );

  const identity = manifest.identity;
  if (!identity || typeof identity !== "object")
    throw new Error("dashboard-release-v2.json: missing identity");
  const generation = sha256(Buffer.from(canonicalJson(identity), "utf8"));
  if (generation !== manifest.generation)
    throw new Error(
      `dashboard-release-v2.json: generation ${manifest.generation} does not match its identity (${generation})`,
    );

  const CORE_ROLES = ["periods", "summary"];
  // RF09 publishes one complete pack: the monthly history for every property
  // type lives under the same generation as the periods and summary.
  const MONTHLY_ROLES = [
    "area-monthly-all",
    "area-monthly-hdb",
    "area-monthly-ec",
    "area-monthly-condo",
  ];
  const assets = new Map();
  for (const asset of manifest.assets ?? []) {
    if (![...CORE_ROLES, ...MONTHLY_ROLES].includes(asset.role))
      throw new Error(`dashboard-release-v2.json: unknown role ${asset.role}`);
    if (assets.has(asset.role))
      throw new Error(
        `dashboard-release-v2.json: duplicate role ${asset.role}`,
      );
    if (typeof asset.path !== "string" || asset.path.includes(".."))
      throw new Error(`dashboard-release-v2.json: unsafe path ${asset.path}`);
    if (!asset.path.startsWith(`observed/${manifest.generation}/`))
      throw new Error(
        `dashboard-release-v2.json: ${asset.path} is outside its generation`,
      );
    if (identity.roles?.[asset.role] !== asset.sha256)
      throw new Error(
        `dashboard-release-v2.json: identity role ${asset.role} does not match its asset`,
      );
    assets.set(asset.role, asset);
  }
  for (const role of [...CORE_ROLES, ...MONTHLY_ROLES]) {
    if (!assets.has(role))
      throw new Error(`dashboard-release-v2.json: missing role ${role}`);
  }
  if (Object.keys(identity.roles ?? {}).length !== assets.size)
    throw new Error(
      `dashboard-release-v2.json: identity records ${Object.keys(identity.roles ?? {}).length} roles for ${assets.size} assets`,
    );

  const payloads = {};
  for (const [role, asset] of assets) {
    const url = new URL(asset.path, root);
    if (!existsSync(url))
      throw new Error(
        `dashboard-release-v2.json: missing payload ${asset.path}`,
      );
    const bytes = readFileSync(url);
    if (bytes.length !== asset.bytes)
      throw new Error(
        `${asset.path}: ${bytes.length} bytes, recorded ${asset.bytes}`,
      );
    const digest = sha256(bytes);
    if (digest !== asset.sha256)
      throw new Error(
        `${asset.path}: hash ${digest} != recorded ${asset.sha256}`,
      );
    try {
      payloads[role] = JSON.parse(gunzipSync(bytes).toString("utf8"));
    } catch (error) {
      throw new Error(`${asset.path}: invalid JSON payload: ${error}`);
    }
  }

  const periods = payloads.periods;
  if (periods.schemaVersion !== "2.1.0")
    throw new Error(
      `v2 periods: unsupported schemaVersion ${periods.schemaVersion}`,
    );
  if (periods.cutoffMonth !== manifest.cutoffMonth)
    throw new Error("v2 periods: cutoffMonth disagrees with the manifest");
  if (!Array.isArray(periods.periods) || periods.periods.length === 0)
    throw new Error("v2 periods: no periods published");

  const ids = new Set();
  for (const period of periods.periods) {
    if (ids.has(period.id))
      throw new Error(`v2 periods: duplicate id ${period.id}`);
    ids.add(period.id);
    const expected = monthsBetween(period.startMonth, period.endMonth);
    if (expected === null)
      throw new Error(`v2 periods: ${period.id} has invalid bounds`);
    if (
      !Array.isArray(period.months) ||
      period.months.length !== expected.length ||
      period.months.some((month, index) => month !== expected[index])
    )
      throw new Error(
        `v2 periods: ${period.id} months do not match its bounds`,
      );
  }
  for (const period of periods.periods) {
    if (period.comparatorId !== null && !ids.has(period.comparatorId))
      throw new Error(
        `v2 periods: ${period.id} references unpublished comparator ${period.comparatorId}`,
      );
  }

  const summary = payloads.summary;
  if (summary.cutoffMonth !== manifest.cutoffMonth)
    throw new Error("v2 summary: cutoffMonth disagrees with the manifest");
  if (!Array.isArray(summary.observations) || summary.observations.length === 0)
    throw new Error("v2 summary: no observations published");

  const dispositions = new Set(["publish", "limited-display", "withhold"]);
  for (const observation of summary.observations) {
    if (!ids.has(observation.periodId))
      throw new Error(
        `v2 summary: ${observation.geographyId} references unknown period ${observation.periodId}`,
      );
    if (!["all", "hdb", "ec", "condo"].includes(observation.propertyType))
      throw new Error(
        `v2 summary: unknown propertyType ${observation.propertyType}`,
      );
    if (!["available", "no-sales"].includes(observation.status))
      throw new Error(`v2 summary: unknown status ${observation.status}`);
    if (!dispositions.has(observation.disposition))
      throw new Error(
        `v2 summary: unknown disposition ${observation.disposition}`,
      );
    if (observation.status === "no-sales") {
      const count = observation.metrics?.transactionCount?.value;
      const price = observation.metrics?.medianPrice?.value;
      if (count !== 0)
        throw new Error(
          `v2 summary: ${observation.geographyId}/${observation.periodId} is no-sales with count ${count}`,
        );
      if (price !== null)
        throw new Error(
          `v2 summary: ${observation.geographyId}/${observation.periodId} is no-sales with a price`,
        );
    }
  }

  // --- RF09 monthly history ---------------------------------------------
  // Coverage is a contract, not a hint: a month in `months` is covered by the
  // release (zero transactions there is a verified no-sales month), while a
  // month outside it is missing source and must not be rendered as zero.
  const MONTHLY_CELL_FIELDS = [
    "transactionCount",
    "medianPrice",
    "priceObservations",
    "medianPsf",
    "psfObservations",
  ];
  const monthIndexOf = (month) =>
    Number(month.slice(0, 4)) * 12 + Number(month.slice(5, 7)) - 1;
  let monthlyCells = 0;

  for (const role of MONTHLY_ROLES) {
    const payload = payloads[role];
    const expectedType = role.replace("area-monthly-", "");
    if (payload.schemaVersion !== "2.1.0")
      throw new Error(
        `v2 ${role}: unsupported schemaVersion ${payload.schemaVersion}`,
      );
    if (payload.cutoffMonth !== manifest.cutoffMonth)
      throw new Error(`v2 ${role}: cutoffMonth disagrees with the manifest`);
    if (payload.propertyType !== expectedType)
      throw new Error(
        `v2 ${role}: declares propertyType ${payload.propertyType}`,
      );
    if (!dispositions.has(payload.disposition))
      throw new Error(`v2 ${role}: unknown disposition ${payload.disposition}`);
    if (
      !Array.isArray(payload.cellFields) ||
      payload.cellFields.length !== MONTHLY_CELL_FIELDS.length ||
      payload.cellFields.some(
        (field, index) => field !== MONTHLY_CELL_FIELDS[index],
      )
    )
      throw new Error(
        `v2 ${role}: cellFields does not match the published cell contract`,
      );

    const months = payload.months;
    if (!Array.isArray(months))
      throw new Error(`v2 ${role}: months is not an array`);
    months.forEach((month, index) => {
      if (!/^\d{4}-(0[1-9]|1[0-2])$/.test(month))
        throw new Error(`v2 ${role}: months[${index}] is not a YYYY-MM month`);
      if (index > 0 && monthIndexOf(month) <= monthIndexOf(months[index - 1]))
        throw new Error(
          `v2 ${role}: months[${index}] is not after ${months[index - 1]}`,
        );
    });
    const coverage = payload.coverage ?? {};
    if (coverage.monthCount !== months.length)
      throw new Error(
        `v2 ${role}: coverage.monthCount disagrees with the month grid`,
      );
    if ((coverage.firstMonth ?? null) !== (months[0] ?? null))
      throw new Error(
        `v2 ${role}: coverage.firstMonth disagrees with the month grid`,
      );
    if ((coverage.lastMonth ?? null) !== (months[months.length - 1] ?? null))
      throw new Error(
        `v2 ${role}: coverage.lastMonth disagrees with the month grid`,
      );

    if (!Array.isArray(payload.series) || payload.series.length === 0)
      throw new Error(`v2 ${role}: no series published`);
    const geographies = new Set();
    for (const entry of payload.series) {
      if (
        typeof entry.geographyId !== "string" ||
        entry.geographyId.length === 0
      )
        throw new Error(`v2 ${role}: series entry without a geographyId`);
      if (geographies.has(entry.geographyId))
        throw new Error(`v2 ${role}: duplicate series ${entry.geographyId}`);
      geographies.add(entry.geographyId);
      if (!Array.isArray(entry.cells) || entry.cells.length !== months.length)
        throw new Error(
          `v2 ${role}: series ${entry.geographyId} has ${entry.cells?.length} cells for ${months.length} months`,
        );
      let noSales = 0;
      for (const [position, cell] of entry.cells.entries()) {
        const label = `v2 ${role}: series ${entry.geographyId} cell ${months[position]}`;
        if (!Array.isArray(cell) || cell.length !== MONTHLY_CELL_FIELDS.length)
          throw new Error(
            `${label} is not a ${MONTHLY_CELL_FIELDS.length}-field cell`,
          );
        const [count, price, priceObs, psf, psfObs] = cell;
        for (const [name, value] of [
          ["transactionCount", count],
          ["priceObservations", priceObs],
          ["psfObservations", psfObs],
        ]) {
          if (!Number.isInteger(value) || value < 0)
            throw new Error(`${label} has an invalid ${name}`);
        }
        if (priceObs > count || psfObs > count)
          throw new Error(`${label} has more observations than transactions`);
        if ((price === null) !== (priceObs === 0))
          throw new Error(`${label} price and its observation count disagree`);
        if ((psf === null) !== (psfObs === 0))
          throw new Error(`${label} psf and its observation count disagree`);
        if (price !== null && !Number.isFinite(price))
          throw new Error(`${label} has a non-finite price`);
        if (psf !== null && !Number.isFinite(psf))
          throw new Error(`${label} has a non-finite psf`);
        if (count === 0) noSales += 1;
        monthlyCells += 1;
      }
      if (entry.noSalesMonths !== noSales)
        throw new Error(
          `v2 ${role}: series ${entry.geographyId} reports ${entry.noSalesMonths} no-sales months, ${noSales} found`,
        );
    }
    if (months.length > 0 && !geographies.has("SG"))
      throw new Error(`v2 ${role}: no national series`);

    // The payload must say which ids are areas: the unassigned bucket holds
    // real transactions that no planning area claimed, and counting it as an
    // area shifts every distribution computed from this payload.
    const declared = payload.geographies;
    if (declared === null || typeof declared !== "object")
      throw new Error(`v2 ${role}: does not declare its geographies`);
    if (
      typeof declared.national !== "string" ||
      !geographies.has(declared.national)
    )
      throw new Error(`v2 ${role}: geographies.national has no series`);
    if (!Array.isArray(declared.unassigned))
      throw new Error(`v2 ${role}: geographies.unassigned is not an array`);
    for (const id of declared.unassigned) {
      if (typeof id !== "string" || id === "" || id === declared.national)
        throw new Error(
          `v2 ${role}: geographies.unassigned has an invalid id ${id}`,
        );
      if (!geographies.has(id))
        throw new Error(
          `v2 ${role}: geographies.unassigned ${id} has no series`,
        );
    }
    const areaCount = geographies.size - 1 - declared.unassigned.length;
    if (declared.areaCount !== areaCount)
      throw new Error(
        `v2 ${role}: geographies.areaCount ${declared.areaCount} != ${areaCount} declared areas`,
      );
  }

  console.log(
    `Verified v2 observed pack ${String(manifest.generation).slice(0, 12)} (cutoff ${manifest.cutoffMonth}, ${periods.periods.length} periods, ${summary.observations.length} observations)`,
  );
  console.log(
    `Verified v2 monthly history (${MONTHLY_ROLES.length} property payloads, ${monthlyCells} month cells)`,
  );
}

checkObservedPack();
