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
  /**
   * Repo-relative path of the machine-readable evidence artifact (the ledger
   * JSON) the three sign-offs pin by `artifactSha256`, or `null` when nothing is
   * pinned.
   *
   * The sign-offs already carry an `evidencePath`, but that points at the human
   * review record (a markdown sign-off note), not at the ledger whose canonical
   * content hash `artifactSha256` records. This field names that ledger
   * explicitly, so the archive route can re-derive its canonical content hash at
   * build time and refuse to publish an "approved" edition whose cited evidence
   * no longer hashes to the pin. It is required for an approved edition and
   * forbidden otherwise.
   */
  evidenceArtifactPath: string | null;
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
    evidenceArtifactPath:
      "docs/implementation/artifacts/rs01-source-inventory.json",
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
    evidenceArtifactPath:
      "docs/implementation/artifacts/rs02-rental-yield-evidence.json",
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
    evidenceArtifactPath:
      "docs/implementation/artifacts/rs03-temporal-evolution-evidence.json",
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
    evidenceArtifactPath:
      "docs/implementation/artifacts/rs04-amenity-impact-evidence.json",
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
  {
    seriesSlug: "facility-premiums",
    editionId: "facility-premiums-2026-11-17",
    publicationYear: 2026,
    evidenceStatus: "approved",
    editorialStatus: "published",
    frozenSource:
      "docs/analytics/editions/facility-premiums/2026-11-17/facility-premiums.md",
    assetsPinned: 0,
    preparedBy: "repo-agent/session-2026-11-17",
    editionSha256:
      "8027e19e6d4cc8fd2402b7dd1691d1e5ab7eaf4baae547605914380fbe38f6ea",
    evidenceArtifactPath:
      "docs/implementation/artifacts/rs05-facility-premiums-evidence.json",
    signoffs: [
      {
        role: "source",
        name: "howt",
        date: "2026-11-18",
        artifactSha256:
          "8bdc5b8465907bbbe98851841b4080caa4fb246b8ed8e61503d59bcedf348970",
        statement:
          "I attest that the measured ledger matches this checkout and accept the cutoff and dispositions it implies: 2026-10 as the last complete month, the measured absence of the in-house facility layer and the withdrawal of every legacy facility claim that depends on it, the recovered project_name join with its bulk-label caveat, the between-project framing, and project-clustered uncertainty as the published measure.",
        automated: false,
        evidencePath:
          "docs/implementation/2026-11-17-rs05-facility-premiums-evidence.md",
      },
      {
        role: "scientific",
        name: "openai-codex/gpt-6-luna (xhigh)",
        date: "2026-11-18",
        artifactSha256:
          "8bdc5b8465907bbbe98851841b4080caa4fb246b8ed8e61503d59bcedf348970",
        statement:
          "I reviewed the edition text against this ledger hash: the absent facility layer and the withdrawals, the recovered join key, project-clustered standard errors with the mall/hawker non-distinguishability, the 97-column schema audit, absence semantics, legacy quotations and byte-reproducible re-measurement were verified. This attestation supersedes an earlier one because the ledger changed only in serialisation, with every measurement confirmed unchanged. I do not attest to the evidence pack's method beyond these checks, to source availability outside this checkout, other studies, or later edits.",
        automated: true,
        evidencePath: "docs/implementation/2026-11-17-rs05-editions-signoff.md",
      },
      {
        role: "publication",
        name: "howt",
        date: "2026-11-18",
        artifactSha256:
          "8bdc5b8465907bbbe98851841b4080caa4fb246b8ed8e61503d59bcedf348970",
        statement:
          "I approve publication of this edition at the frozen text sha256 recorded here as its current, approved edition.",
        automated: false,
        evidencePath: "docs/implementation/2026-11-17-rs05-editions-signoff.md",
      },
    ],
    note: "RS05 facility re-measurement: the legacy study's in-house facility layer (which development has which facility) is absent from this checkout — the four legacy-named sources measure absent (legacySourceAudit), the shipped dataset's only facility-like columns are external SportSG public-facility distances, and the only candidate join key (project_name) is fully populated (3,005 distinct projects, 0 empty) but has no counterparty layer to join to, so no facility prevalence, premium or combination is measurable and every legacy claim is withdrawn with that measured reason. What is measured: a one-way decomposition on the model sample showing 91.0638% of log condo price-psf variance lies between projects (2,413 projects, n = 234,479, 2021-01 -> 2026-10 at the 2026-10 cutoff) with the five external-access indicators 98.9-99.9% between-project — the quantified reason an unadjusted facility comparison is a comparison of projects — and one recorded descriptive OLS of log condo price-psf on five jointly-fitted distance<=1000m indicators with planning-area/year/floor-band/subtype/sale-type fixed effects and area/tenure controls (R2 = 0.7872; two standard-error batteries, HC1 and project-clustered CRVE with cluster = project_name, 2,413 clusters — the clustered battery is the published uncertainty: MRT within 1 km +7.1059% (clustered |t| = 3.82), SportSG facility -2.3628% (|t| = 2.16) and childcare -13.2448% (|t| = 2.82, on a 0.53% thin contrast with no effect interpretation) remain larger than twice their clustered SEs, while mall -1.7536% (|t| = 1.19) and hawker -0.1336% (|t| = 0.11) are NOT distinguishable from zero on this design; clustered SEs run 2.8x-16.6x the HC1 ones), labelled a between-project comparison: project identity is not conditioned on and the project-fixed-effects variant is recorded as not fitted. The specification is recorded, not pre-registered: no dated prior protocol exists, so specification search cannot be ruled out. Per-facility status is no-record (source absent) — not absent, not zero — for all nine legacy facilities and all five synergy-combination rows.",
  },
  {
    seriesSlug: "macro-sensitivity",
    editionId: "macro-sensitivity-2026-11-18",
    publicationYear: 2026,
    evidenceStatus: "approved",
    editorialStatus: "published",
    frozenSource:
      "docs/analytics/editions/macro-sensitivity/2026-11-18/macro-sensitivity.md",
    assetsPinned: 0,
    preparedBy: "repo-agent/session-2026-11-18",
    editionSha256:
      "0741e45bde949357c9bd39fdbd59e40a341c7b86597223ad9ff0484b157f002c",
    evidenceArtifactPath:
      "docs/implementation/artifacts/rs09-macro-sensitivity-evidence.json",
    signoffs: [
      {
        role: "source",
        name: "howt",
        date: "2026-11-18",
        artifactSha256:
          "ae403f11db8786e4258418d8791c6e0255fe2f4800d32e624f4014b6af629d7b",
        statement:
          "I attest that the measured ledger matches this checkout and accept the cutoff and dispositions it implies: 2026-10 as the last complete month, the measured per-series inventory including bank_rates' missing-source rows, the fallback screen and the exclusion it justifies, and the withdrawal of the legacy rate, regime and policy-timing claims.",
        automated: false,
        evidencePath:
          "docs/implementation/2026-11-18-rs09-macro-sensitivity-editions-signoff.md",
      },
      {
        role: "scientific",
        name: "openai-codex/gpt-6-luna (xhigh)",
        date: "2026-11-18",
        artifactSha256:
          "ae403f11db8786e4258418d8791c6e0255fe2f4800d32e624f4014b6af629d7b",
        statement:
          "I reviewed the edition text against this ledger hash: the ledger-backed numerical claims and the withdrawals were verified, the screen-versus-origin distinction is preserved throughout, and no edition-facing figure rests on a series the ledger designates audit-only. I do not attest to series provenance, release lag or revisions, causal or timing claims, the evidence pack, or later edits.",
        automated: true,
        evidencePath:
          "docs/implementation/2026-11-18-rs09-macro-sensitivity-editions-signoff.md",
      },
      {
        role: "publication",
        name: "howt",
        date: "2026-11-18",
        artifactSha256:
          "ae403f11db8786e4258418d8791c6e0255fe2f4800d32e624f4014b6af629d7b",
        statement:
          "I approve publication of this edition at the frozen text sha256 recorded here as its current, approved edition.",
        automated: false,
        evidencePath:
          "docs/implementation/2026-11-18-rs09-macro-sensitivity-editions-signoff.md",
      },
    ],
    note: "RS09 macro re-measurement: the legacy rate narrative rested on a 60-row SORA series screened as an annual-ramp fill pattern (between-year variance share 0.9939, year-boundary step share 0.3444, monotone year-mean path, ADF +5.16) and excluded from every edition-facing figure, with the cost of that exclusion quantified on the 60 shared months (levels r 0.9422 vs 0.5870 against HDB median psf). The source candidate bank_rates.sora_3m runs 2005-10 -> 2026-09 (465 file rows, 213 missing-source, 252 values), and unified_dataset ships both as separate columns, so sora_rate is the screened-out ramp. Two of the article's four rate bands reproduce on the source series (2021 H1 mean 0.1796; 2023 mean 3.5915) and two do not (2022 H2 2.2247 against a quoted 2.5-3.5%; 2024-2025 2.7390 against 3.0-3.5%). wage_growth is screened as annual-resolution tiling (25 of 25 years carrying one distinct value across four quarters) and no figure of it is reproduced. Six of eight series fail to reject a unit root in levels; associations are reported in levels and first differences with serial-adjusted intervals, and level coefficients are explicitly not sensitivity readings. 35 legacy claims disposed: 7 re-measured, 28 withdrawn; release lag, revisions, policy dates, regimes, segment CAGRs and rate-shock affordability recorded as not measurable or not fitted with stated evidence.",
  },
  {
    seriesSlug: "market-segments",
    editionId: "market-segments-2026-11-20",
    publicationYear: 2026,
    evidenceStatus: "approved",
    editorialStatus: "published",
    frozenSource:
      "docs/analytics/editions/market-segments/2026-11-20/market-segments.md",
    assetsPinned: 0,
    preparedBy: "repo-agent/session-2026-11-20",
    editionSha256:
      "efc8841e4420084072c926e19bbf36ed42b53603dd9661a23e00c0a6257f4167",
    evidenceArtifactPath:
      "docs/implementation/artifacts/rs10-market-segments-evidence.json",
    signoffs: [
      {
        role: "source",
        name: "howt",
        date: "2026-11-20",
        artifactSha256:
          "163273c4524bea3b45b2f53a0219ee459a7ce69812f49524218c2eda76bc9167",
        statement:
          "I attest that the RS10 measured ledger matches this checkout and accept the cutoff and the dispositions it implies: 2026-10 as the last complete month, the six stored segments' counts as the asset's own unverified figures, zero per-transaction membership for the six ids, the many-to-many area block, the two-part provenance, the CAGR window per property type with Bukit Timah refused under the article's own floor, the app matching weights unchanged, and the disposition of all 36 legacy claims. I also accept the round-15 scan-boundary regeneration, whose diff against the retained round-14 ledger is confined to the scan's declaration.",
        automated: false,
        evidencePath:
          "docs/implementation/2026-11-20-rs10-market-segments-editions-signoff.md",
      },
      {
        role: "scientific",
        name: "openai-codex/gpt-6-luna (high)",
        date: "2026-11-24",
        artifactSha256:
          "163273c4524bea3b45b2f53a0219ee459a7ce69812f49524218c2eda76bc9167",
        statement:
          "I reviewed the re-pinned evidence ledger at this hash after the 2026-11-24 remediation: every changed value is attributable to the disclosed scan-surface narrowing, a source or test file re-hashed by that remediation, or a sibling-ledger re-pin, and no coefficient, statistic, sample size, cutoff or disposition changed. I do not re-attest the edition text, other studies, or later edits.",
        automated: true,
        evidencePath: "docs/implementation/2026-11-24-ledger-repin-review.md",
      },
      {
        role: "publication",
        name: "howt",
        date: "2026-11-20",
        artifactSha256:
          "163273c4524bea3b45b2f53a0219ee459a7ce69812f49524218c2eda76bc9167",
        statement:
          "I approve publication of this edition at the frozen text sha256 recorded here as its current, approved edition.",
        automated: false,
        evidencePath:
          "docs/implementation/2026-11-20-rs10-market-segments-editions-signoff.md",
      },
    ],
    note: "RS10 measured inventory of the stored six-segment asset. Its counts close on their own shares and on nothing else (911,454 total; nearest candidate 911,797 at +343 and a different taxonomy), the six ids match zero stored values in the 97-column frame and zero identifiers in the served dashboard asset, and the only stored membership is a many-to-many planning-area block of 51 pairs. Provenance is recorded in two parts that are not interchangeable: the segment objects are hand-written literals in a plan document's generator body, while the PSF-based cluster profiles correspond 6-of-6 on names and 6-of-6 on shares (count ratios 9.502-9.5831, so no constant multiple) without any recorded link to that code, and the stored selection sweep marks K=2 and K=7 unlinked to the six-row run. The article's five-name taxonomy, its per-segment bands, its composite-score bands, its momentum rows and its strategy table are withdrawn; 36 legacy claims disposed: 1 re-measured, 4 withdrawn, 31 not reproducible.",
  },
  {
    seriesSlug: "price-forecasts",
    editionId: "price-forecasts-2026-11-20",
    publicationYear: 2026,
    evidenceStatus: "approved",
    editorialStatus: "published",
    frozenSource:
      "docs/analytics/editions/price-forecasts/2026-11-20/price-forecasts.md",
    assetsPinned: 0,
    preparedBy: "repo-agent/session-2026-11-20",
    editionSha256:
      "7cc937aecca5886cd693eb79e7e72a7879e75bc95cc0b23493703e7f127af616",
    evidenceArtifactPath:
      "docs/implementation/artifacts/rs14-price-forecasts-evidence.json",
    signoffs: [
      {
        role: "source",
        name: "howt",
        date: "2026-11-20",
        artifactSha256:
          "8d309700ff15a10501e758e27adb3d80409b745ce6d004803904f3828ff3a386",
        statement:
          "Recorded under the owner's blanket delegation of 2026-11-20 (D12), which dropped the per-study approval hop and expressly kept the scientific review: I attest that the measured ledger pins this study's checkout and accept the cutoff and the dispositions it implies. The session materialised this attestation; the owner accepted the hash without reading the ledger first, and the statement says so.",
        automated: false,
        evidencePath:
          "docs/implementation/2026-11-20-rs14-price-forecasts-editions-signoff.md",
      },
      {
        role: "scientific",
        name: "openai-codex/gpt-6-luna (high)",
        date: "2026-11-24",
        artifactSha256:
          "8d309700ff15a10501e758e27adb3d80409b745ce6d004803904f3828ff3a386",
        statement:
          "I reviewed the re-pinned evidence ledger at this hash after the 2026-11-24 remediation: every changed value is attributable to the disclosed scan-surface narrowing, a source or test file re-hashed by that remediation, or a sibling-ledger re-pin, and no coefficient, statistic, sample size, cutoff or disposition changed. I do not re-attest the edition text, other studies, or later edits.",
        automated: true,
        evidencePath: "docs/implementation/2026-11-24-ledger-repin-review.md",
      },
      {
        role: "publication",
        name: "howt",
        date: "2026-11-20",
        artifactSha256:
          "8d309700ff15a10501e758e27adb3d80409b745ce6d004803904f3828ff3a386",
        statement:
          "I approve publication of this edition at the frozen text sha256 recorded here as its current edition; recorded under the same delegation.",
        automated: false,
        evidencePath:
          "docs/implementation/2026-11-20-rs14-price-forecasts-editions-signoff.md",
      },
    ],
    note: "RS14 price-forecasts: the study turns an audit into a measurement. Legacy claims disposed: 0 re-measured, 16 withdrawn, 16 not-reproducible.",
  },
  {
    seriesSlug: "lease-decay",
    editionId: "lease-decay-2026-11-20",
    publicationYear: 2026,
    evidenceStatus: "approved",
    editorialStatus: "published",
    frozenSource:
      "docs/analytics/editions/lease-decay/2026-11-20/lease-decay.md",
    assetsPinned: 0,
    preparedBy: "repo-agent/session-2026-11-20",
    editionSha256:
      "c772a1643a1f968b07f06598c07787adc1032488a1862cded9ed723f1b368918",
    evidenceArtifactPath:
      "docs/implementation/artifacts/rs06-lease-decay-evidence.json",
    signoffs: [
      {
        role: "source",
        name: "howt",
        date: "2026-11-20",
        artifactSha256:
          "496b63b5e1a4d7fc8d2399e70d81f063203fd6777ed73f7801ac1839db78560e",
        statement:
          "Recorded under the owner's blanket delegation of 2026-11-20 (D12), which dropped the per-study approval hop and expressly kept the scientific review: I attest that the measured ledger pins this study's checkout and accept the cutoff and the dispositions it implies. The session materialised this attestation; the owner accepted the hash without reading the ledger first, and the statement says so.",
        automated: false,
        evidencePath:
          "docs/implementation/2026-11-20-rs06-lease-decay-editions-signoff.md",
      },
      {
        role: "scientific",
        name: "openai-codex/gpt-6-luna (high)",
        date: "2026-11-24",
        artifactSha256:
          "496b63b5e1a4d7fc8d2399e70d81f063203fd6777ed73f7801ac1839db78560e",
        statement:
          "I reviewed the re-pinned evidence ledger at this hash after the 2026-11-24 remediation: every changed value is attributable to the disclosed scan-surface narrowing, a source or test file re-hashed by that remediation, or a sibling-ledger re-pin, and no coefficient, statistic, sample size, cutoff or disposition changed. I do not re-attest the edition text, other studies, or later edits.",
        automated: true,
        evidencePath: "docs/implementation/2026-11-24-ledger-repin-review.md",
      },
      {
        role: "publication",
        name: "howt",
        date: "2026-11-20",
        artifactSha256:
          "496b63b5e1a4d7fc8d2399e70d81f063203fd6777ed73f7801ac1839db78560e",
        statement:
          "I approve publication of this edition at the frozen text sha256 recorded here as its current edition; recorded under the same delegation.",
        automated: false,
        evidencePath:
          "docs/implementation/2026-11-20-rs06-lease-decay-editions-signoff.md",
      },
    ],
    note: "RS06 lease-decay: the study's finding is a unit reconciliation, not a coefficient. Legacy claims disposed: 25 re-measured, 5 withdrawn, 6 not-reproducible.",
  },
  {
    seriesSlug: "mrt-impact",
    editionId: "mrt-impact-2026-11-20",
    publicationYear: 2026,
    evidenceStatus: "approved",
    editorialStatus: "published",
    frozenSource: "docs/analytics/editions/mrt-impact/2026-11-20/mrt-impact.md",
    assetsPinned: 0,
    preparedBy: "repo-agent/session-2026-11-20",
    editionSha256:
      "40a5004c51fa0670f4e4cc2c7d9cc178996632aad2446a7cf9bcc25af5a93a05",
    evidenceArtifactPath:
      "docs/implementation/artifacts/rs07-mrt-impact-evidence.json",
    signoffs: [
      {
        role: "source",
        name: "howt",
        date: "2026-11-20",
        artifactSha256:
          "bfb2c51800a65c622a402c130728efc0cebe1e84d0e36e6713223a96b9099e40",
        statement:
          "Recorded under the owner's blanket delegation of 2026-11-20 (D12), which dropped the per-study approval hop and expressly kept the scientific review: I attest that the measured ledger pins this study's checkout and accept the cutoff and the dispositions it implies. The session materialised this attestation; the owner accepted the hash without reading the ledger first, and the statement says so.",
        automated: false,
        evidencePath:
          "docs/implementation/2026-11-20-rs07-mrt-impact-editions-signoff.md",
      },
      {
        role: "scientific",
        name: "openai-codex/gpt-6-luna (high)",
        date: "2026-11-24",
        artifactSha256:
          "bfb2c51800a65c622a402c130728efc0cebe1e84d0e36e6713223a96b9099e40",
        statement:
          "I reviewed the re-pinned evidence ledger at this hash after the 2026-11-24 remediation: every changed value is attributable to the disclosed scan-surface narrowing, a source or test file re-hashed by that remediation, or a sibling-ledger re-pin, and no coefficient, statistic, sample size, cutoff or disposition changed. I do not re-attest the edition text, other studies, or later edits.",
        automated: true,
        evidencePath: "docs/implementation/2026-11-24-ledger-repin-review.md",
      },
      {
        role: "publication",
        name: "howt",
        date: "2026-11-20",
        artifactSha256:
          "bfb2c51800a65c622a402c130728efc0cebe1e84d0e36e6713223a96b9099e40",
        statement:
          "I approve publication of this edition at the frozen text sha256 recorded here as its current edition; recorded under the same delegation.",
        automated: false,
        evidencePath:
          "docs/implementation/2026-11-20-rs07-mrt-impact-editions-signoff.md",
      },
    ],
    note: "RS07 mrt-impact: the study's finding is a stated response plus a withdrawn multiple. Legacy claims disposed: 1 re-measured, 8 withdrawn, 19 not-reproducible.",
  },
  {
    seriesSlug: "school-quality",
    editionId: "school-quality-2026-11-20",
    publicationYear: 2026,
    evidenceStatus: "approved",
    editorialStatus: "published",
    frozenSource:
      "docs/analytics/editions/school-quality/2026-11-20/school-quality.md",
    assetsPinned: 0,
    preparedBy: "repo-agent/session-2026-11-20",
    editionSha256:
      "5306546ca5ba30230823c5b8cac24bf1867381fcb032f43032ca49a0e322ad9d",
    evidenceArtifactPath:
      "docs/implementation/artifacts/rs08-school-quality-evidence.json",
    signoffs: [
      {
        role: "source",
        name: "howt",
        date: "2026-11-20",
        artifactSha256:
          "1a02b6fa089d7d0f0f4767c173d4f476c38639d2123537fa231e71aa2b387e1d",
        statement:
          "Recorded under the owner's blanket delegation of 2026-11-20 (D12), which dropped the per-study approval hop and expressly kept the scientific review: I attest that the measured ledger pins this study's checkout and accept the cutoff and the dispositions it implies. The session materialised this attestation; the owner accepted the hash without reading the ledger first, and the statement says so.",
        automated: false,
        evidencePath:
          "docs/implementation/2026-11-20-rs08-school-quality-editions-signoff.md",
      },
      {
        role: "scientific",
        name: "openai-codex/gpt-6-luna (high)",
        date: "2026-11-24",
        artifactSha256:
          "1a02b6fa089d7d0f0f4767c173d4f476c38639d2123537fa231e71aa2b387e1d",
        statement:
          "I reviewed the re-pinned evidence ledger at this hash after the 2026-11-24 remediation: every changed value is attributable to the disclosed scan-surface narrowing, a source or test file re-hashed by that remediation, or a sibling-ledger re-pin, and no coefficient, statistic, sample size, cutoff or disposition changed. I do not re-attest the edition text, other studies, or later edits.",
        automated: true,
        evidencePath: "docs/implementation/2026-11-24-ledger-repin-review.md",
      },
      {
        role: "publication",
        name: "howt",
        date: "2026-11-20",
        artifactSha256:
          "1a02b6fa089d7d0f0f4767c173d4f476c38639d2123537fa231e71aa2b387e1d",
        statement:
          "I approve publication of this edition at the frozen text sha256 recorded here as its current edition; recorded under the same delegation.",
        automated: false,
        evidencePath:
          "docs/implementation/2026-11-20-rs08-school-quality-editions-signoff.md",
      },
    ],
    note: "RS08 school-quality: the study's finding is an identification audit that withdraws a causal claim. Legacy claims disposed: 3 re-measured, 4 withdrawn, 29 not-reproducible.",
  },
  {
    seriesSlug: "spatial-autocorrelation",
    editionId: "spatial-autocorrelation-2026-11-20",
    publicationYear: 2026,
    evidenceStatus: "approved",
    editorialStatus: "published",
    frozenSource:
      "docs/analytics/editions/spatial-autocorrelation/2026-11-20/spatial-autocorrelation.md",
    assetsPinned: 0,
    preparedBy: "repo-agent/session-2026-11-20",
    editionSha256:
      "d1363aafce5489f6a4e5bdb663f0f93fa29746ef972177ad8ae91483550d84ee",
    evidenceArtifactPath:
      "docs/implementation/artifacts/rs11-spatial-autocorrelation-evidence.json",
    signoffs: [
      {
        role: "source",
        name: "howt",
        date: "2026-11-20",
        artifactSha256:
          "0f2442ce74c2c6255b70ffd4b7ff94dc59b59c663af9e5de11519363e10fa4f7",
        statement:
          "Recorded under the owner's blanket delegation of 2026-11-20 (D12), which dropped the per-study approval hop and expressly kept the scientific review: I attest that the measured ledger pins this study's checkout and accept the cutoff and the dispositions it implies. The session materialised this attestation; the owner accepted the hash without reading the ledger first, and the statement says so.",
        automated: false,
        evidencePath:
          "docs/implementation/2026-11-20-rs11-spatial-autocorrelation-editions-signoff.md",
      },
      {
        role: "scientific",
        name: "openai-codex/gpt-6-luna (high)",
        date: "2026-11-24",
        artifactSha256:
          "0f2442ce74c2c6255b70ffd4b7ff94dc59b59c663af9e5de11519363e10fa4f7",
        statement:
          "I reviewed the re-pinned evidence ledger at this hash after the 2026-11-24 remediation: every changed value is attributable to the disclosed scan-surface narrowing, a source or test file re-hashed by that remediation, or a sibling-ledger re-pin, and no coefficient, statistic, sample size, cutoff or disposition changed. I do not re-attest the edition text, other studies, or later edits.",
        automated: true,
        evidencePath: "docs/implementation/2026-11-24-ledger-repin-review.md",
      },
      {
        role: "publication",
        name: "howt",
        date: "2026-11-20",
        artifactSha256:
          "0f2442ce74c2c6255b70ffd4b7ff94dc59b59c663af9e5de11519363e10fa4f7",
        statement:
          "I approve publication of this edition at the frozen text sha256 recorded here as its current edition; recorded under the same delegation.",
        automated: false,
        evidencePath:
          "docs/implementation/2026-11-20-rs11-spatial-autocorrelation-editions-signoff.md",
      },
    ],
    note: "RS11 spatial-autocorrelation: the study's finding is a re-measurement replacing a placeholder payload. Legacy claims disposed: 1 re-measured, 1 withdrawn, 26 not-reproducible.",
  },
  {
    seriesSlug: "spatial-hotspots",
    editionId: "spatial-hotspots-2026-11-20",
    publicationYear: 2026,
    evidenceStatus: "approved",
    editorialStatus: "published",
    frozenSource:
      "docs/analytics/editions/spatial-hotspots/2026-11-20/spatial-hotspots.md",
    assetsPinned: 1,
    preparedBy: "repo-agent/session-2026-11-20",
    editionSha256:
      "81236f9abc1214424e6ef7a0ad1c0bed98300c0b6291ab167958a38f6cdea072",
    evidenceArtifactPath:
      "docs/implementation/artifacts/rs12-spatial-hotspots-evidence.json",
    signoffs: [
      {
        role: "source",
        name: "howt",
        date: "2026-11-20",
        artifactSha256:
          "1872e0a2231d72b062c546b125940eff855040f35da8d8257196a9ffcb1abf74",
        statement:
          "Recorded under the owner's blanket delegation of 2026-11-20 (D12), which dropped the per-study approval hop and expressly kept the scientific review: I attest that the measured ledger pins this study's checkout and accept the cutoff and the dispositions it implies. The session materialised this attestation; the owner accepted the hash without reading the ledger first, and the statement says so.",
        automated: false,
        evidencePath:
          "docs/implementation/2026-11-20-rs12-spatial-hotspots-editions-signoff.md",
      },
      {
        role: "scientific",
        name: "openai-codex/gpt-6-luna (high)",
        date: "2026-11-24",
        artifactSha256:
          "1872e0a2231d72b062c546b125940eff855040f35da8d8257196a9ffcb1abf74",
        statement:
          "I reviewed the re-pinned evidence ledger at this hash after the 2026-11-24 remediation: every changed value is attributable to the disclosed scan-surface narrowing, a source or test file re-hashed by that remediation, or a sibling-ledger re-pin, and no coefficient, statistic, sample size, cutoff or disposition changed. I do not re-attest the edition text, other studies, or later edits.",
        automated: true,
        evidencePath: "docs/implementation/2026-11-24-ledger-repin-review.md",
      },
      {
        role: "publication",
        name: "howt",
        date: "2026-11-20",
        artifactSha256:
          "1872e0a2231d72b062c546b125940eff855040f35da8d8257196a9ffcb1abf74",
        statement:
          "I approve publication of this edition at the frozen text sha256 recorded here as its current edition; recorded under the same delegation.",
        automated: false,
        evidencePath:
          "docs/implementation/2026-11-20-rs12-spatial-hotspots-editions-signoff.md",
      },
    ],
    note: "RS12 spatial-hotspots: the study's finding is a rerun on a population the checkout can actually join. Legacy claims disposed: 15 re-measured, 10 withdrawn, 15 not-reproducible.",
  },
  {
    seriesSlug: "causal-inference-overview",
    editionId: "causal-inference-overview-2026-11-20",
    publicationYear: 2026,
    evidenceStatus: "approved",
    editorialStatus: "published",
    frozenSource:
      "docs/analytics/editions/causal-inference-overview/2026-11-20/causal-inference-overview.md",
    assetsPinned: 0,
    preparedBy: "repo-agent/session-2026-11-20",
    editionSha256:
      "73b02d4843ee5ecd1873c73054b3889380ef286ec5f4274a0662a6b8de2290cd",
    evidenceArtifactPath:
      "docs/implementation/artifacts/rs13-causal-inference-overview-evidence.json",
    signoffs: [
      {
        role: "source",
        name: "howt",
        date: "2026-11-20",
        artifactSha256:
          "d01d9d5f440a07a82f575fe3bc19c3e693ac315600097b304c39aba24130d059",
        statement:
          "Recorded under the owner's blanket delegation of 2026-11-20 (D12), which dropped the per-study approval hop and expressly kept the scientific review: I attest that the measured ledger pins this study's checkout and accept the cutoff and the dispositions it implies. The session materialised this attestation; the owner accepted the hash without reading the ledger first, and the statement says so.",
        automated: false,
        evidencePath:
          "docs/implementation/2026-11-20-rs13-causal-inference-overview-editions-signoff.md",
      },
      {
        role: "scientific",
        name: "openai-codex/gpt-6-luna (high)",
        date: "2026-11-24",
        artifactSha256:
          "d01d9d5f440a07a82f575fe3bc19c3e693ac315600097b304c39aba24130d059",
        statement:
          "I reviewed the re-pinned evidence ledger at this hash after the 2026-11-24 remediation: every changed value is attributable to the disclosed scan-surface narrowing, a source or test file re-hashed by that remediation, or a sibling-ledger re-pin, and no coefficient, statistic, sample size, cutoff or disposition changed. I do not re-attest the edition text, other studies, or later edits.",
        automated: true,
        evidencePath: "docs/implementation/2026-11-24-ledger-repin-review.md",
      },
      {
        role: "publication",
        name: "howt",
        date: "2026-11-20",
        artifactSha256:
          "d01d9d5f440a07a82f575fe3bc19c3e693ac315600097b304c39aba24130d059",
        statement:
          "I approve publication of this edition at the frozen text sha256 recorded here as its current edition; recorded under the same delegation.",
        automated: false,
        evidencePath:
          "docs/implementation/2026-11-20-rs13-causal-inference-overview-editions-signoff.md",
      },
    ],
    note: "RS13 causal-inference-overview: the study's finding is an identification audit and two withdrawals. Legacy claims disposed: 10 re-measured, 9 withdrawn, 20 not-reproducible.",
  },
  {
    seriesSlug: "findings",
    editionId: "findings-2026-11-20",
    publicationYear: 2026,
    evidenceStatus: "approved",
    editorialStatus: "published",
    frozenSource: "docs/analytics/editions/findings/2026-11-20/findings.md",
    assetsPinned: 0,
    preparedBy: "repo-agent/session-2026-11-20",
    editionSha256:
      "a2c20043c55e9497082be96c534d9fc46b614f028dd5b5830362c7fc16897073",
    evidenceArtifactPath:
      "docs/implementation/artifacts/rs15-findings-evidence.json",
    signoffs: [
      {
        role: "source",
        name: "howt",
        date: "2026-11-20",
        artifactSha256:
          "c22d2de7c3452bf8d9e0b83aa0fdfc54fd19d336615cab18086d2d099d718b3c",
        statement:
          "Recorded under the owner's blanket delegation of 2026-11-20 (D12), which dropped the per-study approval hop and expressly kept the scientific review: I attest that the measured ledger pins this checkout and accept the cutoff and the dispositions it implies, including that this page records its own series as not yet signed. The session materialised this attestation; the owner accepted the hash without reading the ledger first, and the statement says so.",
        automated: false,
        evidencePath:
          "docs/implementation/2026-11-20-rs15-findings-editions-signoff.md",
      },
      {
        role: "scientific",
        name: "openai-codex/gpt-6-luna (high)",
        date: "2026-11-24",
        artifactSha256:
          "c22d2de7c3452bf8d9e0b83aa0fdfc54fd19d336615cab18086d2d099d718b3c",
        statement:
          "I reviewed the re-pinned evidence ledger at this hash after the 2026-11-24 remediation: every changed value is attributable to the disclosed scan-surface narrowing, a source or test file re-hashed by that remediation, or a sibling-ledger re-pin, and no coefficient, statistic, sample size, cutoff or disposition changed. I do not re-attest the edition text, other studies, or later edits.",
        automated: true,
        evidencePath: "docs/implementation/2026-11-24-ledger-repin-review.md",
      },
      {
        role: "publication",
        name: "howt",
        date: "2026-11-20",
        artifactSha256:
          "c22d2de7c3452bf8d9e0b83aa0fdfc54fd19d336615cab18086d2d099d718b3c",
        statement:
          "I approve publication of this edition at the frozen text sha256 recorded here as its current edition; recorded under the same delegation.",
        automated: false,
        evidencePath:
          "docs/implementation/2026-11-20-rs15-findings-editions-signoff.md",
      },
    ],
    note: "RS15 findings register: fifteen series, fourteen signed, the fifteenth (this page) recorded as not signed and saying so; per-series edition and ledger hash comparisons recorded as measured booleans; 85 placeholder strings split 59/26 so a placeholder reads as 'not recorded for that study'; frozen findings claims disposed against the ledger.",
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
      evidenceArtifactPath: null,
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
    if (edition.evidenceArtifactPath !== null) {
      errors.push(
        `${label}: ${edition.evidenceStatus} edition names an evidence artifact; only an approved edition names reviewed evidence`,
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

  // An approved edition claims a reviewed evidence artifact; without an explicit
  // path there is nothing for the build-time content-hash check to verify, so a
  // null here would silently ship an unverifiable approval.
  if (
    edition.evidenceArtifactPath === null ||
    edition.evidenceArtifactPath.trim() === ""
  ) {
    errors.push(
      `${label}: approved edition does not name its evidence artifact (evidenceArtifactPath)`,
    );
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
        `${label}: edition prose hash — frozen source ${edition.frozenSource} is unreadable`,
      );
      continue;
    }
    if (actual !== edition.editionSha256) {
      errors.push(
        `${label}: edition prose hash — frozen source ${edition.frozenSource} is sha256 ${actual}, but the approved edition pins ${edition.editionSha256}`,
      );
    }
  }
  return errors;
}

/**
 * Verify that every approved edition still pins the evidence artifact it cites.
 *
 * The prose pin above answers "are these the bytes the signatories published?".
 * This pin answers the other half of the claim: "is this the evidence pack the
 * signatories read?". It re-derives the canonical content hash of the cited
 * ledger and compares it to the sha256 all three sign-offs recorded. It is the
 * gap REL-2 closed: before this, a sign-off could cite an artifact whose bytes
 * had changed and the build still published `approved`.
 *
 * `sha256OfCanonicalJson` is injected for the same reason as `sha256OfFile`: the
 * registry stays pure, and only the archive route (build time) supplies a real
 * `node:crypto` + `node:fs` reader. This never runs in the browser bundle.
 */
export function verifyEditionEvidenceArtifacts(
  editions: readonly AnalyticsEdition[],
  sha256OfCanonicalJson: (repoRelativePath: string) => string | null,
): string[] {
  const errors: string[] = [];
  for (const edition of editions) {
    if (edition.evidenceStatus !== "approved") {
      continue;
    }
    const label = `edition ${edition.editionId} (${edition.seriesSlug})`;
    if (edition.evidenceArtifactPath === null) {
      errors.push(
        `${label}: evidence artifact hash — the approved edition names no evidence artifact (evidenceArtifactPath)`,
      );
      continue;
    }
    const pinned = new Set(
      edition.signoffs.map((signoff) => signoff.artifactSha256),
    );
    if (pinned.size !== 1) {
      // validateSignoffs already rejects this; the guard keeps the hash below
      // unambiguous even if a caller verifies an unvalidated record.
      errors.push(
        `${label}: evidence artifact hash — the sign-offs do not all cover the same evidence artifact`,
      );
      continue;
    }
    const expected = edition.signoffs[0]!.artifactSha256;
    const actual = sha256OfCanonicalJson(edition.evidenceArtifactPath);
    if (actual === null) {
      errors.push(
        `${label}: evidence artifact hash — evidence artifact ${edition.evidenceArtifactPath} is missing or unreadable`,
      );
      continue;
    }
    if (actual !== expected) {
      errors.push(
        `${label}: evidence artifact hash — evidence artifact ${edition.evidenceArtifactPath} canonicalises to sha256 ${actual}, but the sign-offs pin ${expected}`,
      );
    }
  }
  return errors;
}

/**
 * Canonical JSON text of a document, byte-identical to the form the evidence
 * producers write: `json.dumps(payload, sort_keys=True, indent=2,
 * ensure_ascii=False)` followed by one trailing newline.
 *
 * Wiring a ledger to its sign-off hash means reproducing *that* encoder in the
 * build, not hashing whatever formatting happens to be on disk: a formatter run
 * may move a ledger's raw bytes without touching a byte of its content (see the
 * `data-sources` serialisation drift the RS15 producer pins). This function is
 * pure — it takes the file's text and returns canonical text, so the caller can
 * hash it with `node:crypto` at build time and it never reaches the browser.
 *
 * Objects are re-sorted by decoded key; array order is preserved. Strings are
 * re-encoded the way `ensure_ascii=False` writes them (`JSON.stringify` matches
 * Python for every escape these producers emit). Number tokens are kept verbatim
 * because a JS round-trip through `Number` would turn Python's `0.0` into `0` and
 * change the hash.
 *
 * Throws on malformed input; the caller treats that as an unreadable artifact.
 */
export function canonicalJsonText(source: string): string {
  type Node =
    | { kind: "token"; text: string }
    | { kind: "array"; items: Node[] }
    | { kind: "object"; entries: Array<{ key: string; value: Node }> };

  let index = 0;
  const length = source.length;

  const skipWhitespace = (): void => {
    while (index < length) {
      const ch = source[index];
      if (ch === " " || ch === "\t" || ch === "\n" || ch === "\r") {
        index += 1;
      } else {
        return;
      }
    }
  };

  const readString = (): { raw: string; decoded: string } => {
    const start = index;
    index += 1;
    while (index < length) {
      const ch = source[index];
      if (ch === "\\") {
        index += 2;
        continue;
      }
      if (ch === '"') {
        index += 1;
        const raw = source.slice(start, index);
        return { raw, decoded: JSON.parse(raw) as string };
      }
      index += 1;
    }
    throw new Error("canonicalJsonText: unterminated string");
  };

  const readNumber = (): string => {
    const start = index;
    while (index < length && /[-+0-9.eE]/.test(source[index]!)) {
      index += 1;
    }
    if (index === start) {
      throw new Error("canonicalJsonText: expected a value");
    }
    return source.slice(start, index);
  };

  const readValue = (): Node => {
    skipWhitespace();
    const ch = source[index];
    if (ch === "{") return readObject();
    if (ch === "[") return readArray();
    if (ch === '"')
      return { kind: "token", text: JSON.stringify(readString().decoded) };
    if (source.startsWith("true", index)) {
      index += 4;
      return { kind: "token", text: "true" };
    }
    if (source.startsWith("false", index)) {
      index += 5;
      return { kind: "token", text: "false" };
    }
    if (source.startsWith("null", index)) {
      index += 4;
      return { kind: "token", text: "null" };
    }
    return { kind: "token", text: readNumber() };
  };

  const readArray = (): Node => {
    index += 1;
    skipWhitespace();
    const items: Node[] = [];
    if (source[index] === "]") {
      index += 1;
      return { kind: "array", items };
    }
    for (;;) {
      items.push(readValue());
      skipWhitespace();
      if (source[index] === ",") {
        index += 1;
        continue;
      }
      if (source[index] === "]") {
        index += 1;
        return { kind: "array", items };
      }
      throw new Error("canonicalJsonText: expected , or ] in array");
    }
  };

  const readObject = (): Node => {
    index += 1;
    skipWhitespace();
    const entries: Array<{ key: string; value: Node }> = [];
    if (source[index] === "}") {
      index += 1;
      return { kind: "object", entries };
    }
    for (;;) {
      skipWhitespace();
      const key = readString().decoded;
      skipWhitespace();
      if (source[index] !== ":") {
        throw new Error("canonicalJsonText: expected : after object key");
      }
      index += 1;
      entries.push({ key, value: readValue() });
      skipWhitespace();
      if (source[index] === ",") {
        index += 1;
        continue;
      }
      if (source[index] === "}") {
        index += 1;
        entries.sort((left, right) =>
          left.key < right.key ? -1 : left.key > right.key ? 1 : 0,
        );
        return { kind: "object", entries };
      }
      throw new Error("canonicalJsonText: expected , or } in object");
    }
  };

  const emit = (node: Node, depth: number): string => {
    const pad = "  ".repeat(depth);
    if (node.kind === "token") return node.text;
    if (node.kind === "array") {
      if (node.items.length === 0) return "[]";
      const inner = node.items
        .map((item) => `${`  `.repeat(depth + 1)}${emit(item, depth + 1)}`)
        .join(",\n");
      return `[\n${inner}\n${pad}]`;
    }
    if (node.entries.length === 0) return "{}";
    const inner = node.entries
      .map(
        (entry) =>
          `${`  `.repeat(depth + 1)}${JSON.stringify(entry.key)}: ${emit(entry.value, depth + 1)}`,
      )
      .join(",\n");
    return `{\n${inner}\n${pad}}`;
  };

  const canonical = emit(readValue(), 0);
  return `${canonical}\n`;
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
