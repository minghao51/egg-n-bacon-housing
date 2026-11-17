/**
 * Analytics edition registry (RF07).
 *
 * RF00 froze the published research as immutable edition sources; this module is
 * the one place that names those editions, says what their evidence status is,
 * and builds their archive paths. It is pure — no Astro, React, DOM or file
 * system — so the series page, the archive route and the unit tests all read the
 * same register.
 *
 * Contract (plan §7, RF07 card):
 * - The current series entry is the latest **approved** edition, never the
 *   latest timestamp. With no approved refreshed edition, the series says so and
 *   links the archived original instead of promoting a historical finding.
 * - Editorial publication status is separate from scientific evidence status.
 * - `archive` and `personas` are reserved route segments and may not be used as
 *   series slugs.
 * - A new edition must use a new identity and new asset paths; this register
 *   never renames a frozen one.
 */

export type EditionEvidenceStatus = "approved" | "historical" | "withheld";

export type EditionEditorialStatus = "published" | "draft" | "archived";

/**
 * The three D12 sign-off roles. They must be distinct people/records: the
 * scientific reviewer may not be the publication approver, and neither the
 * source steward nor the scientific reviewer may be the edition's preparer.
 */
export type EditionSignoffRole = "source" | "scientific" | "publication";

export const EDITION_SIGNOFF_ROLES: readonly EditionSignoffRole[] = [
  "source",
  "scientific",
  "publication",
];

/**
 * One recorded attestation on one artifact.
 *
 * `artifactSha256` is the sha256 of the evidence pack the signatory read, so an
 * approval cannot drift onto a later revision. `automated` marks a recorded
 * review run (with its model identity in `name`); the repo owner accepted those
 * as the scientific signatory, provided the run is recorded verbatim and its
 * evidence path is committed.
 */
export interface EditionSignoff {
  role: EditionSignoffRole;
  /** Named person, or `<provider>/<model> (<effort>)` for a recorded review. */
  name: string;
  /** ISO `YYYY-MM-DD` the attestation was recorded. */
  date: string;
  /** sha256 of the exact evidence artifact this attestation covers. */
  artifactSha256: string;
  /** What the signatory attests, in one line. */
  statement: string;
  /** True for a recorded automated review run rather than a human signature. */
  automated: boolean;
  /** Repo-relative record of the review this signature refers to. */
  evidencePath: string;
}

export interface AnalyticsEdition {
  /** Series slug, i.e. the `/analytics/<slug>` entry this edition belongs to. */
  seriesSlug: string;
  /** Frozen edition identity, e.g. `legacy-2026-11-12`. Never reused. */
  editionId: string;
  /** Publication year for the archive path, or `null` for an undated edition. */
  publicationYear: number | null;
  /** True only for an edition that passed the three recorded sign-offs. */
  evidenceStatus: EditionEvidenceStatus;
  /** Editorial state of the frozen text, kept separate from evidence status. */
  editorialStatus: EditionEditorialStatus;
  /** Repo-relative path of the frozen source. */
  frozenSource: string;
  /** How many referenced data/figure assets the freeze pinned. */
  assetsPinned: number;
  /**
   * sha256 of the frozen edition source itself (the reviewed text), or `null`
   * when nothing pins it.
   *
   * The three sign-offs pin the *evidence* artifact; this pins the *bytes the
   * signatories published*, so a later edit to the frozen text cannot ride on an
   * older approval. It is required for an approved edition and forbidden
   * otherwise, and the archive route refuses to build when it does not match the
   * file on disk. Historical editions keep `null`: their pin is the RF00 baseline
   * manifest (`docs/analytics/editions/legacy/2026-11-12/manifest.json`).
   */
  editionSha256: string | null;
  /** Who prepared the evidence pack; `null` for a frozen historical edition. */
  preparedBy: string | null;
  /**
   * The three D12 attestations. Empty for every edition that is not `approved`:
   * a partial trail in the register would read as an approval that never
   * happened, so review notes live in the evidence pack instead.
   */
  signoffs: readonly EditionSignoff[];
  note: string;
}

/** Route segments the analytics tree reserves for non-series pages. */
export const RESERVED_ANALYTICS_SLUGS = ["archive", "personas"] as const;

/** The RF00 freeze: every published study as it was on 2026-11-12. */
export const LEGACY_EDITION_ID = "legacy-2026-11-12";

const LEGACY_NOTE =
  "Frozen as published on 2026-11-12. No refreshed edition has independent scientific sign-off, so this edition is historical evidence, not a current confirmed finding.";

const LEGACY_SERIES = [
  "amenity-impact",
  "causal-inference-overview",
  "data-sources",
  "facility-premiums",
  "findings",
  "lease-decay",
  "macro-sensitivity",
  "market-segments",
  "mrt-impact",
  "price-forecasts",
  "rental-yields",
  "school-quality",
  "spatial-autocorrelation",
  "spatial-hotspots",
  "temporal-evolution",
] as const;

/**
 * Refreshed editions authored from a signed evidence pack (RF08).
 *
 * They exist here as soon as their frozen text exists, because the archive route
 * refuses to emit a route for a frozen file with no identity. Their status is the
 * honest one: written, reviewed-pending. `validateEditionRegistry` refuses any
 * sign-off or `editionSha256` on a non-approved edition, so an entry can only
 * become `approved` in the same edit that records all three attestations.
 */
export const REFRESHED_EDITIONS: readonly AnalyticsEdition[] = [
  {
    seriesSlug: "data-sources",
    editionId: "data-sources-2026-11-14",
    publicationYear: 2026,
    evidenceStatus: "approved",
    editorialStatus: "published",
    frozenSource:
      "docs/analytics/editions/data-sources/2026-11-14/data-sources.md",
    assetsPinned: 0,
    preparedBy: "repo-agent/session-2026-11-14",
    editionSha256:
      "bde11c61b720c2504cdf78bde9238c5e57925e319457d52356cde0bcdeeafb81",
    signoffs: [
      {
        role: "source",
        name: "howt",
        date: "2026-11-14",
        artifactSha256:
          "65ce7a10c257d13fd4250b2e8fd1519f8c35718497379aa103effc5594bfe8ae",
        statement:
          "I attest that the measured ledger matches this checkout and accept the cutoff and dispositions it implies: 2026-10 as the last complete month, the measured per-source coverage, the stale sora_rates label and the recorded source defects.",
        automated: false,
        evidencePath: "docs/implementation/2026-11-14-rs01-source-inventory.md",
      },
      {
        role: "scientific",
        name: "openai-codex/gpt-6-luna (xhigh)",
        date: "2026-11-14",
        artifactSha256:
          "65ce7a10c257d13fd4250b2e8fd1519f8c35718497379aa103effc5594bfe8ae",
        statement:
          "I reviewed the edition text against this ledger hash: the ledger-backed numerical claims and the withdrawals were verified, and the sign-off language matches the registry gate. I do not attest to the evidence pack itself, other studies, or later edits.",
        automated: true,
        evidencePath: "docs/implementation/2026-11-14-rf08-editions-signoff.md",
      },
      {
        role: "publication",
        name: "howt",
        date: "2026-11-14",
        artifactSha256:
          "65ce7a10c257d13fd4250b2e8fd1519f8c35718497379aa103effc5594bfe8ae",
        statement:
          "I approve publication of this edition at the frozen text sha256 recorded here as its current, approved edition.",
        automated: false,
        evidencePath: "docs/implementation/2026-11-14-rf08-editions-signoff.md",
      },
    ],
    note: "RS01 inventory, measured from this checkout. Replaces the 2026-06-15 text: inferred ranges and unmeasured distance/roll-up claims are withdrawn rather than restated.",
  },
  {
    seriesSlug: "rental-yields",
    editionId: "rental-yields-2026-11-14",
    publicationYear: 2026,
    evidenceStatus: "approved",
    editorialStatus: "published",
    frozenSource:
      "docs/analytics/editions/rental-yields/2026-11-14/rental-yields.md",
    assetsPinned: 0,
    preparedBy: "repo-agent/session-2026-11-14",
    editionSha256:
      "f6b0bd9d811bb9b348b0e897b66a482add281e38f2803c61193978c97ca0ab67",
    signoffs: [
      {
        role: "source",
        name: "howt",
        date: "2026-11-14",
        artifactSha256:
          "db1345253c4c9e4d80b7e3067962199a12f120ccfdfe1b6f599a7d95459f0313",
        statement:
          "I attest that the measured ledger matches this checkout and accept the cutoff and dispositions it implies: 2026-10 as the last complete month, the measured per-source coverage, the stale sora_rates label and the recorded source defects.",
        automated: false,
        evidencePath:
          "docs/implementation/2026-11-14-rs02-rental-yield-evidence.md",
      },
      {
        role: "scientific",
        name: "openai-codex/gpt-6-luna (xhigh)",
        date: "2026-11-14",
        artifactSha256:
          "db1345253c4c9e4d80b7e3067962199a12f120ccfdfe1b6f599a7d95459f0313",
        statement:
          "I reviewed the edition text against this ledger hash: the ledger-backed numerical claims and the withdrawals were verified, and the sign-off language matches the registry gate. I do not attest to the evidence pack itself, other studies, or later edits.",
        automated: true,
        evidencePath: "docs/implementation/2026-11-14-rf08-editions-signoff.md",
      },
      {
        role: "publication",
        name: "howt",
        date: "2026-11-14",
        artifactSha256:
          "db1345253c4c9e4d80b7e3067962199a12f120ccfdfe1b6f599a7d95459f0313",
        statement:
          "I approve publication of this edition at the frozen text sha256 recorded here as its current, approved edition.",
        automated: false,
        evidencePath: "docs/implementation/2026-11-14-rf08-editions-signoff.md",
      },
    ],
    note: "RS02 gross-proxy definition, coverage and denominators. Replaces the 2026-03-31 text: per-flat-type bands, the yield-vs-appreciation claim, the league table, the affordability ratio and the downside-floor claim are withdrawn.",
  },
  {
    seriesSlug: "temporal-evolution",
    editionId: "temporal-evolution-2026-11-15",
    publicationYear: 2026,
    evidenceStatus: "approved",
    editorialStatus: "published",
    frozenSource:
      "docs/analytics/editions/temporal-evolution/2026-11-15/temporal-evolution.md",
    assetsPinned: 0,
    preparedBy: "repo-agent/session-2026-11-15",
    editionSha256:
      "d95beefc8386291ffa60c94db6c0d9a5b9f9b289e52cf9c6a74c5517d4b02b8d",
    signoffs: [
      {
        role: "source",
        name: "howt",
        date: "2026-11-15",
        artifactSha256:
          "1f0aef749b9f26b6f2f4a5f09cd472956080a413a11397c2160fd45759f71012",
        statement:
          "I attest that the measured ledger matches this checkout and accept the cutoff and dispositions it implies: 2026-10 as the last complete month, the measured HDB window coverage and composition, the condo pre-COVID window as source-missing, the single 2019-12-09 station vintage with no vintage per window, and the resulting withdrawal of the premium-evolution, clustering, trajectory and recovery-asymmetry claims.",
        automated: false,
        evidencePath:
          "docs/implementation/2026-11-15-rs03-temporal-evolution-evidence.md",
      },
      {
        role: "scientific",
        name: "openai-codex/gpt-6-luna (xhigh)",
        date: "2026-11-15",
        artifactSha256:
          "1f0aef749b9f26b6f2f4a5f09cd472956080a413a11397c2160fd45759f71012",
        statement:
          "I reviewed the edition text against this ledger hash: quantitative claims, feature lineage, cutoff bounding, absence semantics and legacy quotations were verified, and the six defects from two prior failed reviews are closed. I do not attest to source completeness beyond this checkout, causal interpretation, other editions, or later edits.",
        automated: true,
        evidencePath: "docs/implementation/2026-11-15-rs03-editions-signoff.md",
      },
      {
        role: "publication",
        name: "howt",
        date: "2026-11-15",
        artifactSha256:
          "1f0aef749b9f26b6f2f4a5f09cd472956080a413a11397c2160fd45759f71012",
        statement:
          "I approve publication of this edition at the frozen text sha256 recorded here as its current, approved edition.",
        automated: false,
        evidencePath: "docs/implementation/2026-11-15-rs03-editions-signoff.md",
      },
    ],
    note: "RS03 comparable-window re-cut: HDB window coverage, composition and like-window medians plus a descriptive per-area-year baseline (floor n = 30, aggregates bounded at the 2026-10 cutoff). Premium-evolution claims are withdrawn: the only dated MRT snapshot is a single 2019-12-09 legacy seed (no vintage per window), no dated school series exists, and the condo pre-COVID window is source-missing. Measured lineage: the shipped dist_to_nearest_mrt column reproduces exactly from the sha-pinned 188-row bronze station frame (20,000/20,000, zero deviation) and not from the seed (0/20,000).",
  },
  {
    seriesSlug: "amenity-impact",
    editionId: "amenity-impact-2026-11-16",
    publicationYear: 2026,
    evidenceStatus: "approved",
    editorialStatus: "published",
    frozenSource:
      "docs/analytics/editions/amenity-impact/2026-11-16/amenity-impact.md",
    assetsPinned: 0,
    preparedBy: "repo-agent/session-2026-11-16",
    editionSha256:
      "3a5ef72d97af0c0004491567314e180bf3238bdaaff11457707a3138657b4507",
    signoffs: [
      {
        role: "source",
        name: "howt",
        date: "2026-11-16",
        artifactSha256:
          "6232702eb8ab01e6508dee7a91418a7f272a41ae76681f35e3881a61de12e6ed",
        statement:
          "I attest that the measured ledger matches this checkout and accept the cutoff and dispositions it implies: 2026-10 as the last complete month, the measured snapshot join and its 27.46% not-established share (6.11% nearest a centre currently Under Construction), hawker completion dates as the only amenity vintage in the checkout, and the resulting withdrawal of the importance ranking, the COVID period-shift rows, the interaction/synergy claim, the 500 m localisation and every condo claim.",
        automated: false,
        evidencePath:
          "docs/implementation/2026-11-16-rs04-amenity-impact-evidence.md",
      },
      {
        role: "scientific",
        name: "openai-codex/gpt-6-luna (xhigh)",
        date: "2026-11-16",
        artifactSha256:
          "6232702eb8ab01e6508dee7a91418a7f272a41ae76681f35e3881a61de12e6ed",
        statement:
          "I reviewed the edition text against this ledger hash: model arithmetic and coefficient transforms, cutoff and exclusion accounting, snapshot mismatch, feature lineage with its targeted leave-out ablation, absence semantics, legacy quotations and byte-reproducible re-measurement were verified, and the defects from four failed rounds are closed. I do not attest to the evidence pack's method beyond these checks, to source completeness beyond this checkout, other editions, or later edits.",
        automated: true,
        evidencePath: "docs/implementation/2026-11-16-rs04-editions-signoff.md",
      },
      {
        role: "publication",
        name: "howt",
        date: "2026-11-16",
        artifactSha256:
          "6232702eb8ab01e6508dee7a91418a7f272a41ae76681f35e3881a61de12e6ed",
        statement:
          "I approve publication of this edition at the frozen text sha256 recorded here as its current, approved edition.",
        automated: false,
        evidencePath: "docs/implementation/2026-11-16-rs04-editions-signoff.md",
      },
    ],
    note: "RS04 amenity re-measurement with units and controls: one recorded OLS specification of log HDB resale price on five jointly-fitted snapshot indicators (shipped distance <= 1000 m) with floor-area/lease/storey controls and flat-type/town/year fixed effects (n = 281,020, 2015-01 -> 2026-10, R2 = 0.9157, HC1 standard errors) supports conditional associations only (hawker within 1 km +2.79%, mall +5.59%, park +0.72%, supermarket -14.42% on a 0.42% thin, geographically concentrated contrast group with no effect interpretation, MRT +10.47%; amenity count +4.10% per additional type) and no premium, ranking or temporal claim. The specification is recorded, not pre-registered: no dated prior protocol exists, so specification search cannot be ruled out — a disclosed limitation. The legacy importance ranking, COVID-period importance shifts, interaction/synergy and condo claims are withdrawn: no amenity vintage per period exists (hawker completion dates are the only presence dates in any amenity layer and the shipped features never read them; parks/supermarkets/malls/childcare/preschools/MRT carry no presence dates — update stamps only, or none), and the condo source starts 2021-01. The snapshot join is measured, not assumed: distances reproduce exactly from the bronze snapshot for 9,789/9,789 unique locations, a targeted leave-out ablation locates the six Under-Construction centres' coordinates in the shipped distances (738/738 nearest-location breaks on exclusion, 9,051 unchanged; construction start dates not in checkout), and 27.46% of transactions' nearest hawker centre is not established as completed at the transaction date (40.4% in 2015-2019).",
  },
];

export const ANALYTICS_EDITIONS: readonly AnalyticsEdition[] = [
  ...LEGACY_SERIES.map(
    (seriesSlug): AnalyticsEdition => ({
      seriesSlug,
      editionId: LEGACY_EDITION_ID,
      publicationYear: 2026,
      evidenceStatus: "historical",
      editorialStatus: "archived",
      frozenSource: `docs/analytics/editions/legacy/2026-11-12/${seriesSlug}.md`,
      assetsPinned: 72,
      preparedBy: null,
      editionSha256: null,
      signoffs: [],
      note: LEGACY_NOTE,
    }),
  ),
  ...REFRESHED_EDITIONS,
];

const SERIES_PATTERN = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const SHA256_PATTERN = /^[0-9a-f]{64}$/;
const ISO_DATE_PATTERN = /^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$/;

/** The attestation recorded for `role`, or `null` when none exists. */
export function signoffFor(
  edition: AnalyticsEdition,
  role: EditionSignoffRole,
): EditionSignoff | null {
  return edition.signoffs.find((signoff) => signoff.role === role) ?? null;
}

function validateSignoffs(edition: AnalyticsEdition): string[] {
  const errors: string[] = [];
  const label = `edition ${edition.editionId} (${edition.seriesSlug})`;

  if (edition.evidenceStatus !== "approved") {
    if (edition.signoffs.length > 0) {
      errors.push(
        `${label}: ${edition.signoffs.length} sign-off(s) recorded on a ${edition.evidenceStatus} edition; an approval record exists only on an approved edition`,
      );
    }
    if (edition.editionSha256 !== null) {
      errors.push(
        `${label}: ${edition.evidenceStatus} edition pins an edition sha256; only an approved edition claims reviewed bytes`,
      );
    }
    return errors;
  }

  if (edition.editionSha256 === null) {
    errors.push(
      `${label}: approved edition does not pin its frozen text (editionSha256)`,
    );
  } else if (!SHA256_PATTERN.test(edition.editionSha256)) {
    errors.push(`${label}: editionSha256 is not a sha256`);
  }

  const byRole = new Map<EditionSignoffRole, EditionSignoff>();
  for (const signoff of edition.signoffs) {
    if (!(EDITION_SIGNOFF_ROLES as readonly string[]).includes(signoff.role)) {
      errors.push(`${label}: unknown sign-off role ${String(signoff.role)}`);
      continue;
    }
    if (byRole.has(signoff.role)) {
      errors.push(`${label}: duplicate ${signoff.role} sign-off`);
      continue;
    }
    byRole.set(signoff.role, signoff);
    if (signoff.name.trim() === "") {
      errors.push(`${label}: ${signoff.role} sign-off has no name`);
    }
    if (!ISO_DATE_PATTERN.test(signoff.date)) {
      errors.push(
        `${label}: ${signoff.role} sign-off date ${signoff.date} is not YYYY-MM-DD`,
      );
    }
    if (!SHA256_PATTERN.test(signoff.artifactSha256)) {
      errors.push(
        `${label}: ${signoff.role} sign-off does not pin an evidence sha256`,
      );
    }
    if (signoff.statement.trim() === "") {
      errors.push(`${label}: ${signoff.role} sign-off has no statement`);
    }
    if (signoff.evidencePath.trim() === "") {
      errors.push(`${label}: ${signoff.role} sign-off has no evidence path`);
    }
  }

  for (const role of EDITION_SIGNOFF_ROLES) {
    if (!byRole.has(role)) {
      errors.push(`${label}: approved edition is missing its ${role} sign-off`);
    }
  }

  const source = byRole.get("source");
  const scientific = byRole.get("scientific");
  const publication = byRole.get("publication");

  // D12: the scientific reviewer cannot approve publication, and nobody who
  // prepared the evidence may sign it off.
  if (scientific && publication && scientific.name === publication.name) {
    errors.push(
      `${label}: the scientific reviewer may not also approve publication`,
    );
  }
  if (edition.preparedBy !== null) {
    for (const signoff of [source, scientific, publication]) {
      if (signoff && signoff.name === edition.preparedBy) {
        errors.push(
          `${label}: ${signoff.role} sign-off is the preparer; the preparer cannot approve their own evidence`,
        );
      }
    }
  }

  const hashes = new Set(
    edition.signoffs.map((signoff) => signoff.artifactSha256),
  );
  if (hashes.size > 1) {
    errors.push(
      `${label}: the sign-offs do not all cover the same evidence artifact`,
    );
  }

  return errors;
}

/**
 * Validate a register before it drives routes.
 *
 * Returns every problem rather than the first, so a broken register fails the
 * build once with a complete list. Duplicate `(series, edition)` pairs, reserved
 * slugs and malformed identifiers are all rejected.
 */
export function validateEditionRegistry(
  editions: readonly AnalyticsEdition[],
): string[] {
  const errors: string[] = [];
  const seen = new Set<string>();

  for (const edition of editions) {
    if (!SERIES_PATTERN.test(edition.seriesSlug)) {
      errors.push(
        `edition ${edition.editionId}: "${edition.seriesSlug}" is not a series slug`,
      );
    }
    if (
      (RESERVED_ANALYTICS_SLUGS as readonly string[]).includes(
        edition.seriesSlug,
      )
    ) {
      errors.push(
        `edition ${edition.editionId}: "${edition.seriesSlug}" is a reserved analytics segment`,
      );
    }
    if (edition.editionId.trim() === "") {
      errors.push(`series ${edition.seriesSlug}: empty edition id`);
    }
    if (
      edition.publicationYear !== null &&
      (!Number.isInteger(edition.publicationYear) ||
        edition.publicationYear < 1900 ||
        edition.publicationYear > 2100)
    ) {
      errors.push(
        `edition ${edition.editionId}: ${edition.publicationYear} is not a publication year`,
      );
    }
    if (!Number.isInteger(edition.assetsPinned) || edition.assetsPinned < 0) {
      errors.push(
        `edition ${edition.editionId}: ${edition.assetsPinned} is not an asset count`,
      );
    }

    const key = `${edition.seriesSlug}|${edition.editionId}`;
    if (seen.has(key)) {
      errors.push(
        `duplicate edition ${edition.editionId} for series ${edition.seriesSlug}`,
      );
    }
    seen.add(key);
    errors.push(...validateSignoffs(edition));
  }

  return errors;
}

/**
 * Verify that every approved edition still pins the frozen text it was reviewed as.
 *
 * The registry is pure, so the hasher is injected: the archive route passes a
 * `node:crypto` reader (build time), and the unit tests pass a stub or a real
 * file reader. Returning errors rather than throwing keeps the caller free to
 * collect them with the registry errors in one message.
 */
export function verifyEditionArtifacts(
  editions: readonly AnalyticsEdition[],
  sha256OfFile: (repoRelativePath: string) => string | null,
): string[] {
  const errors: string[] = [];
  for (const edition of editions) {
    if (
      edition.evidenceStatus !== "approved" ||
      edition.editionSha256 === null
    ) {
      continue;
    }
    const label = `edition ${edition.editionId} (${edition.seriesSlug})`;
    const actual = sha256OfFile(edition.frozenSource);
    if (actual === null) {
      errors.push(
        `${label}: frozen source ${edition.frozenSource} is unreadable`,
      );
      continue;
    }
    if (actual !== edition.editionSha256) {
      errors.push(
        `${label}: frozen source ${edition.frozenSource} is sha256 ${actual}, but the approved edition pins ${edition.editionSha256}`,
      );
    }
  }
  return errors;
}

/** Every edition of one series, newest publication year first. */ export function editionsForSeries(
  seriesSlug: string,
  editions: readonly AnalyticsEdition[] = ANALYTICS_EDITIONS,
): AnalyticsEdition[] {
  return editions
    .filter((edition) => edition.seriesSlug === seriesSlug)
    .sort((a, b) => {
      const left = a.publicationYear ?? 0;
      const right = b.publicationYear ?? 0;
      if (left !== right) return right - left;
      return a.editionId.localeCompare(b.editionId);
    });
}

/**
 * The edition a series entry may render as current: the newest **approved** one,
 * or `null` when nothing has that evidence status.
 */
export function approvedEditionFor(
  seriesSlug: string,
  editions: readonly AnalyticsEdition[] = ANALYTICS_EDITIONS,
): AnalyticsEdition | null {
  return (
    editionsForSeries(seriesSlug, editions).find(
      (edition) => edition.evidenceStatus === "approved",
    ) ?? null
  );
}

/** The archive path segment for a publication year, or `undated`. */
export function archiveYearSegment(
  edition: Pick<AnalyticsEdition, "publicationYear">,
): string {
  return edition.publicationYear === null
    ? "undated"
    : String(edition.publicationYear);
}

/** Repo-relative archive path, e.g. `/analytics/archive/2026/legacy-2026-11-12/mrt-impact`. */
export function archivePath(edition: AnalyticsEdition): string {
  return `/analytics/archive/${archiveYearSegment(edition)}/${edition.editionId}/${edition.seriesSlug}`;
}
