#!/usr/bin/env python3
"""Measure RS15's findings evidence: a register of the fifteen RF08 series.

RS15 is the summary page, and its register gate is unusually direct:

    "Refresh last. Every quantitative sentence links to a reviewed edition and
    exact population/window/unit. Omit or explicitly flag blocked dependencies;
    never summarize unresolved models as settled conclusions."

A summary page cannot be measured the way a study's own subject can: its subject
IS the other studies. So this tool measures the register itself instead of the
market, and it measures it from the two places the register actually exists:

1. **The app registry** (`app/src/components/studies/lib/edition-registry.ts`) —
   read as text and parsed deterministically, never imported: every series slug,
   every edition id, every evidence/editorial status, every `editionSha256` pin,
   and every attestation's role, name and `artifactSha256`.
2. **The edition files and their ledgers on disk** — each frozen text's actual
   sha256 and byte count, each ledger's actual sha256 and byte count, both
   compared against the pins the register records.

Three questions are answered per series, and each is a boolean field rather than a
sentence: does the text on disk hash to its `editionSha256`; does the ledger on
disk hash to the `artifactSha256` its three attestations share; and what does that
ledger say it did with its own legacy claims. A mismatch fails the build. One
class is disclosed rather than failed, because it is real, dated and provable: the
RS01 ledger's raw bytes were reformatted by a formatter run after signature, so its
raw sha256 no longer equals the pin while its canonical re-serialisation still
does — recorded as `serialisationDrift` under `KNOWN_SERIALISATION_DRIFT`, with
both hashes measured, and re-pinned so a future move fails.

It also records what the register asks for and this checkout cannot supply
(`notMeasurable`), the dependency graph and why nothing it cites is blocked
(`dependencies`), and the disposition of every quantitative sentence of the frozen
findings text (`legacyClaims`), each one traced to the claim the dependent
edition's own ledger records for the same figure (`crossLedgerCheck`).

**The ledger is invariant under its own signature.** RS15 signs by editing the
registry, so nothing this page measures may move when that happens:

- The registry is **not pinned**. It is read as text at measurement time and its
  path and series list are recorded, but its bytes are not an input, because every
  signature in the programme edits it — including this page's own
  (`registryReadRule`). What is pinned is what the register actually uses: each
  edition file's sha256 and byte count, and each sibling ledger's sha256 and byte
  count.
- The `findings` row is recorded as `self: true` with facts that do not change
  when RS15 signs — the frozen legacy edition the register falls back to and that
  text's measured bytes — and with no signing state at all, because `signed: true`
  and `signed: false` both flip the moment the page is signed (`selfNote`).
- `dependencies` and `notMeasurable` exclude the self row by rule rather than by
  status, so no blocked-dependency row and no unsigned count hangs on this page's
  own state. Every other series' status stays an input: those are genuinely
  independent of this page.
- `sentinelScan` reads the sibling ledgers, and its sibling set is the register's
  own series list minus the self row — series membership, not signing status, so
  the page's own signature cannot add or remove a ledger from the scan
  (`sentinelScan.siblingSet`).

The test of all four rules is mechanical: copy the registry, edit only the
`findings` entry's status and attestations, and `--check` must still pass. It
does.

It never runs the pipeline, never rebuilds an edition, never writes outside
`--output`, and never touches the registry, the app or `data/pipeline/**`.

Usage:

    uv run python scripts/tools/findings_evidence.py \\
        --output docs/implementation/artifacts/rs15-findings-evidence.json

    uv run python scripts/tools/findings_evidence.py --check   # no drift
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow.parquet as pq

REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY = REPO_ROOT / "app" / "src" / "components" / "studies" / "lib" / "edition-registry.ts"
ARTIFACTS = REPO_ROOT / "docs" / "implementation" / "artifacts"
UNIFIED = REPO_ROOT / "data" / "pipeline" / "04_platinum" / "unified_dataset.parquet"
LEGACY_FINDINGS = (
    REPO_ROOT / "docs" / "analytics" / "editions" / "legacy" / "2026-11-12" / "findings.md"
)
PERSONA_CONTENT = REPO_ROOT / "app" / "src" / "data" / "persona-content.json"
PACK_PATH = "docs/implementation/2026-11-20-rs15-findings-evidence.md"
EDITION_PATH = "docs/analytics/editions/findings/2026-11-20/findings.md"
DEFAULT_OUTPUT = ARTIFACTS / "rs15-findings-evidence.json"

FRAME_PATH = "data/pipeline/04_platinum/unified_dataset.parquet"
SCHEMA_VERSION = "1.0.0"

# RS15 IS one of the fifteen series, so its own row cannot be measured like a
# sibling's: every fact that would describe the page's own signing state flips at
# the moment the page is signed, and a ledger that changes when it is approved is
# not a ledger. The self row therefore records only facts that are invariant under
# this page's own signature, and the summary/dependency/scan machinery excludes it
# by identity rather than by status.
SELF_SERIES = "findings"
SELF_STATE = "self-not-an-input"
SELF_NOTE = (
    "this row is the page under production. Its own signing state is deliberately "
    "not an input: `signed: true` and `signed: false` would both change at the "
    "moment this page is signed, and a hash-pinned artefact that does not "
    "re-measure is not an artefact. What is recorded instead is invariant under "
    "this page's own signature: the frozen legacy edition the register falls back "
    "to for this series, and that text's measured sha256 and byte count. The "
    "page's own ledger is not read either, for the same reason."
)
REGISTRY_READ_RULE = (
    "the register is derived from the app registry at measurement time, and the "
    "registry is deliberately NOT pinned: every signature in the programme edits "
    "it - this page's own included - so a pin here would make this ledger fail its "
    "own approval. What is pinned is what the register uses: each edition file's "
    "sha256 and byte count and each sibling ledger's sha256 and byte count. A "
    "changed registry that moves a series list, an edition pin or an attestation "
    "still fails the build through those measured inputs and through the pin "
    "checks in seriesRegister."
)

GATE = (
    "Refresh last. Every quantitative sentence links to a reviewed edition and "
    "exact population/window/unit. Omit or explicitly flag blocked dependencies; "
    "never summarize unresolved models as settled conclusions."
)

DEFINITION = (
    "A measured register of the fifteen RF08 series, not a re-measurement of any "
    "of them. Each series row is read twice: from the app registry (edition id, "
    "evidence status, editorial status, the text pin, and the three attestation "
    "roles with the artifact pin they share) and from the files on disk (the "
    "frozen text's actual sha256 and byte count, the ledger's actual sha256 and "
    "byte count). Two booleans per row are the whole test: does the measured text "
    "hash equal the pin the register records, and does the measured ledger hash "
    "equal the pin the three attestations share. A false in either fails this "
    "build. The claim disposition split is read from each edition's own ledger, "
    "never restated from its prose, and the two ledgers that carry no "
    "`legacyClaims` block are recorded as that state rather than as zero claims. "
    "What this ledger does NOT do: it re-measures no study's subject, so no "
    "figure from another edition appears here as a finding; it records which "
    "edition owns each legacy sentence and what that edition's ledger says it did "
    "with it. A summary page that restated a sibling's number would be a copy of "
    "an unverified measurement, and two of the programme's blocking defects were "
    "exactly prose outrunning a ledger."
)

# The statuses this page uses for the frozen findings text. Each one is a claim
# about WHICH edition owns the sentence and WHAT that edition's ledger records,
# never about the figure itself; `crossLedgerCheck` re-reads the dependent ledger
# and fails the build when the recorded disposition does not match.
CLAIM_STATUSES = {
    "referred-re-measured": (
        "the dependent edition's ledger records a re-measurement of this claim's "
        "figure; this page does not restate it"
    ),
    "referred-withdrawn": (
        "the dependent edition's ledger records a withdrawal of this claim's "
        "figure; this page repeats neither the figure nor the withdrawal's reasoning"
    ),
    "referred-not-reproducible": (
        "the dependent edition's ledger records this claim's figure as not "
        "reproducible from the checkout; this page does not restate it"
    ),
    "not-measurable-cross-study": (
        "no single edition can dispose this sentence: it needs a joint model over "
        "several series whose populations, windows and units differ"
    ),
}

# A ledger's raw bytes may legitimately differ from its attestation pin ONLY when
# the parsed content is identical and the pin is reproduced by canonical
# re-serialisation. Every such case is named here with the raw hash measured at
# declaration time, so a later move of either hash fails the build instead of
# sliding through. `git show 7862b5d -- <path>` is a whitespace-only reformat of
# the signed bytes; that commit also added the prettier exclusion that keeps the
# artifacts tree out of the formatter's reach afterwards.
KNOWN_SERIALISATION_DRIFT: dict[str, dict[str, str]] = {
    "data-sources": {
        "path": "docs/implementation/artifacts/rs01-source-inventory.json",
        "observedRawSha256": "21d74a7f233d972792b7027b3fba8573852215b54e463b072d137dc8a729a81f",  # pragma: allowlist secret
        "cause": (
            "post-signature formatter run: arrays collapse onto single lines, the "
            "parsed JSON is identical, and canonical re-serialisation reproduces "
            "the pinned sha256 exactly"
        ),
    }
}

# The fifteen series, as the register's own frozen list orders them. Measured from
# the registry at build time; a changed list changes every count in this ledger.
LEGACY_EDITION_TEMPLATE_MARKERS = (
    "LEGACY_SERIES.map",
    'evidenceStatus: "historical"',
    'editorialStatus: "archived"',
)

# Per-series descriptors: the population/unit a series' edition states, quoted
# VERBATIM from one field of that edition's ledger. The quote is verified as a
# substring of the resolved field, so a paraphrase fails the build; a series whose
# ledger carries no such prose is recorded as that state, not given one here.
DESCRIPTORS: tuple[dict[str, Any], ...] = (
    {
        "series": "data-sources",
        "entries": (
            {
                "field": "population",
                "sourceKey": "definition",
                "quote": "One row per acquisition file",
            },
        ),
    },
    {
        "series": "rental-yields",
        "entries": (
            {
                "field": "population",
                "sourceKey": "definition",
                "quote": "two independent transaction populations",
            },
            {
                "field": "unit",
                "sourceKey": "definition",
                "quote": "median_rent x 12 / median_sale_price x 100",
            },
        ),
    },
    {
        "series": "temporal-evolution",
        "entries": (
            {
                "field": "population",
                "sourceKey": "definition",
                "quote": "transaction counts, sample composition",
            },
            {
                "field": "unit",
                "sourceKey": "definition",
                "quote": "nominal and CPI-deflated median prices per (property type, window)",
            },
        ),
    },
    {
        "series": "amenity-impact",
        "entries": (
            {
                "field": "population",
                "sourceKey": "definition",
                "quote": "log(HDB resale price in SGD)",
            },
            {
                "field": "unit",
                "sourceKey": "definition",
                "quote": "shipped distance <= 1000 m",
            },
        ),
    },
    {
        "series": "facility-premiums",
        "entries": (
            {
                "field": "population",
                "sourceKey": "definition",
                "quote": "log condo price-psf",
            },
            {
                "field": "unit",
                "sourceKey": "definition",
                "quote": "project-clustered standard errors",
            },
        ),
    },
    {
        "series": "lease-decay",
        "entries": (
            {
                "field": "population",
                "sourceKey": "definition",
                "quote": "exact on every HDB row",
            },
            {
                "field": "unit",
                "sourceKey": "definition",
                "quote": "psf, $ per square foot",
            },
        ),
    },
    {
        "series": "mrt-impact",
        "entries": (),
        "missingReason": (
            "this ledger records no `definition` or `scope` prose; its population "
            "and window are carried by `studyWindow` (per property type, window "
            "start/end and window rows) and its unit by `responses"
            ".responseDefinition`, both cited here rather than paraphrased"
        ),
    },
    {
        "series": "school-quality",
        "entries": (
            {
                "field": "population",
                "sourceKey": "definition",
                "quote": "descriptive OLS association of ln(psf)",
            },
            {
                "field": "unit",
                "sourceKey": "definition",
                "quote": "the shipped school-distance columns",
            },
        ),
    },
    {
        "series": "macro-sensitivity",
        "entries": (
            {
                "field": "population",
                "sourceKey": "definition",
                "quote": "macro-housing association",
            },
            {
                "field": "unit",
                "sourceKey": "definition",
                "quote": "in levels and in first differences",
            },
        ),
    },
    {
        "series": "market-segments",
        "entries": (
            {
                "field": "population",
                "sourceKey": "definition",
                "quote": "the stored research segment asset",
            },
            {
                "field": "unit",
                "sourceKey": "definition",
                "quote": "its six segments, their stored metrics",
            },
        ),
    },
    {
        "series": "spatial-autocorrelation",
        "entries": (
            {
                "field": "population",
                "sourceKey": "definition",
                "quote": "The unit that carries reproducible memberships is the planning area",
            },
            {
                "field": "unit",
                "sourceKey": "definition",
                "quote": "median-psf ratio of the trailing 12 completed months",
            },
        ),
    },
    {
        "series": "spatial-hotspots",
        "entries": (
            {
                "field": "population",
                "sourceKey": "definition",
                "quote": "median monthly_rent per cell",
            },
            {
                "field": "unit",
                "sourceKey": "gate",
                "quote": "Retain January 2024-January 2025 as its own historical window",
            },
        ),
    },
    {
        "series": "causal-inference-overview",
        "entries": (
            {
                "field": "population",
                "sourceKey": "definition",
                "quote": "the frame the two cohorts would be drawn from",
            },
            {
                "field": "unit",
                "sourceKey": "scope",
                "quote": "cohort-size screens inside the measured cutoff",
            },
        ),
    },
    {
        "series": "price-forecasts",
        "entries": (
            {
                "field": "population",
                "sourceKey": "definition",
                "quote": "realised area median prices",
            },
            {
                "field": "unit",
                "sourceKey": "definition",
                "quote": "MAE, RMSE, bias, MAPE on implied levels",
            },
        ),
    },
    {
        "series": "findings",
        "entries": (),
        "missingReason": (
            "this row is the page under production, so it records no descriptor of "
            "its own: the population and unit it reports are the sibling editions' "
            "and are quoted on their own rows. Its only other registered edition is "
            "the frozen 2026-11-12 text, whose population and unit are its own "
            "unverified prose"
        ),
    },
)

# The frozen findings text's quantitative sentences. Each is quoted verbatim and
# traced to the dependent edition's OWN claim id, so the disposition is read from
# that ledger instead of asserted here.
LEGACY_CLAIMS: tuple[dict[str, Any], ...] = (
    {
        "id": "C01",
        "phrase": "**Data Coverage**: 911,797 transactions (2017-2026)",
        "status": "not-measurable-cross-study",
        "ledgerKey": "notMeasurable.legacyCorpusAggregates",
        "note": (
            "the sentence's population is a retired corpus vintage: no data vintage "
            "in this checkout reproduces 911,797 rows, and the shipped frame's own "
            "row count over its own month span is a different population, recorded "
            "at inputs."
        ),
    },
    {
        "id": "C02",
        "phrase": (
            "CBD distance explains **22.6%** of price variation on its own, while "
            "adding MRT access increases explanatory power by only **0.78 "
            "percentage points**."
        ),
        "status": "referred-not-reproducible",
        "dependentSeries": "mrt-impact",
        "dependentClaimId": "hierarchical-r2",
        "ledgerKey": "seriesRegister.rows.mrt-impact.claimDispositions",
        "note": (
            "the dependent edition's ledger records the hierarchical R-squared "
            "literals as not reproducible from the checkout; the figure is not "
            "restated on this page."
        ),
    },
    {
        "id": "C03",
        "phrase": "Condo prices are roughly **15x** more MRT-sensitive than HDB prices.",
        "status": "referred-withdrawn",
        "dependentSeries": "mrt-impact",
        "dependentClaimId": "condo-15x-table",
        "ledgerKey": "seriesRegister.rows.mrt-impact.claimDispositions",
        "note": (
            "withdrawn by the dependent edition as a raw-coefficient multiple; this "
            "page does not repeat the multiple as a finding or as a comparison."
        ),
    },
    {
        "id": "C04",
        "phrase": "| 70-80 years | -21.9%              | 47,044       |",
        "status": "referred-re-measured",
        "dependentSeries": "lease-decay",
        "dependentClaimId": "C4",
        "ledgerKey": "seriesRegister.rows.lease-decay.claimDispositions",
        "note": (
            "the dependent edition's ledger records a re-measurement of this band on "
            "its own stated response and window; the measured value lives there."
        ),
    },
    {
        "id": "C05",
        "phrase": "| HDB               | 79.8% | 99.4%                | Useful for timing and trend direction |",
        "status": "referred-withdrawn",
        "dependentSeries": "price-forecasts",
        "dependentClaimId": "C23",
        "ledgerKey": "seriesRegister.rows.price-forecasts.claimDispositions",
        "note": (
            "withdrawn by the dependent edition: the per-segment figures appear only "
            "in the article's own copies and no artefact carries them."
        ),
    },
    {
        "id": "C06",
        "phrase": "about **-$137,743** relative effect vs OCR",
        "status": "referred-withdrawn",
        "dependentSeries": "causal-inference-overview",
        "dependentClaimId": "C03",
        "ledgerKey": "seriesRegister.rows.causal-inference-overview.claimDispositions",
        "note": (
            "withdrawn by the dependent edition as unreconstructable identification "
            "under the recorded programme disposition."
        ),
    },
    {
        "id": "C07",
        "phrase": "**hawker centre proximity** (27.4% feature importance vs 5.5% for MRT)",
        "status": "referred-withdrawn",
        "dependentSeries": "mrt-impact",
        "dependentClaimId": "importance-table-core",
        "ledgerKey": "seriesRegister.rows.mrt-impact.claimDispositions",
        "note": (
            "the importance ranking is withdrawn by the dependent edition: it is an "
            "output of a model family no machine-readable artefact in this checkout "
            "carries."
        ),
    },
    {
        "id": "C08",
        "phrase": "Clustering reveals five behavioral segments",
        "status": "referred-withdrawn",
        "dependentSeries": "market-segments",
        "dependentClaimId": "C1",
        "ledgerKey": "seriesRegister.rows.market-segments.claimDispositions",
        "note": (
            "withdrawn by the dependent edition: the stored asset holds six segments "
            "and the five names do not appear in it."
        ),
    },
    {
        "id": "C09",
        "phrase": (
            "SORA changes have an immediate correlation with housing affordability "
            "and a 1-quarter lag with price trends."
        ),
        "status": "referred-withdrawn",
        "dependentSeries": "macro-sensitivity",
        "dependentClaimId": "C35",
        "ledgerKey": "seriesRegister.rows.macro-sensitivity.claimDispositions",
        "note": (
            "the lag clause is withdrawn by the dependent edition: no cross-"
            "correlation or lag-order implementation exists on the shipping surface, "
            "so the ordering is unmeasured."
        ),
    },
    {
        "id": "C10",
        "phrase": "Real (inflation-adjusted) returns are approximately 2% above CPI across all segments",
        "status": "referred-withdrawn",
        "dependentSeries": "macro-sensitivity",
        "dependentClaimId": "C8",
        "ledgerKey": "seriesRegister.rows.macro-sensitivity.claimDispositions",
        "note": (
            "withdrawn by the dependent edition: no segment price index exists, so "
            "the cross-segment spread is not reproducible and only the HDB rows are "
            "measurable."
        ),
    },
    {
        "id": "C11",
        "phrase": "| Spatial clustering                | Moran's I / z-score               | 0.766 / 9.91     | High — p < 0.001                         |",
        "status": "referred-not-reproducible",
        "dependentSeries": "spatial-autocorrelation",
        "dependentClaimId": "C01",
        "ledgerKey": "seriesRegister.rows.spatial-autocorrelation.claimDispositions",
        "note": (
            "the dependent edition's ledger records the statistic's variable as "
            "unstated and its named input as absent, so the figure is not "
            "reproducible; its own protocol's estimate is a different quantity."
        ),
    },
    {
        "id": "C12",
        "phrase": "| Rental hotspot selectivity        | 99% confidence cells              | 12 of 847        | High — Gi\\* statistic                    |",
        "status": "referred-re-measured",
        "dependentSeries": "spatial-hotspots",
        "dependentClaimId": "C09",
        "ledgerKey": "seriesRegister.rows.spatial-hotspots.claimDispositions",
        "note": (
            "the dependent edition's ledger re-measures the cell population inside "
            "the gate-pinned window and records its own cell counts; the stated "
            "counts are not restated here."
        ),
    },
    {
        "id": "C13",
        "phrase": "| Pure lease effect                 | Per extra year (after controls)   | +$54.75 PSF      | Moderate — hedonic regression            |",
        "status": "referred-withdrawn",
        "dependentSeries": "lease-decay",
        "dependentClaimId": "C9",
        "ledgerKey": "seriesRegister.rows.lease-decay.claimDispositions",
        "note": (
            "withdrawn by the dependent edition under its own gate: a coefficient is "
            "not converted without confirming its original response and unit."
        ),
    },
    {
        "id": "C14",
        "phrase": "| School quality OLS                | Coefficient                       | +$9.66 PSF       | High — predictive                        |",
        "status": "referred-not-reproducible",
        "dependentSeries": "school-quality",
        "dependentClaimId": "C4",
        "ledgerKey": "seriesRegister.rows.school-quality.claimDispositions",
        "note": (
            "the dependent edition's ledger records the coefficient as not "
            "reproducible: the feature it names exists in no shipped schema and no "
            "coefficient table is stored."
        ),
    },
    {
        "id": "C15",
        "phrase": (
            "Across all thirteen analysis domains, the most decision-useful findings "
            "share a common pattern: segment-level specificity matters far more than "
            "model sophistication."
        ),
        "status": "not-measurable-cross-study",
        "ledgerKey": "notMeasurable.jointModelAcrossStudies",
        "note": (
            "a ranking across series needs a joint model on a common outcome; the "
            "editions measure different populations, windows and units, so the "
            "sentence is omitted rather than reworded into a conclusion."
        ),
    },
)

# Absence scans are bounded and their exclusions disclosed. A scan that read every
# file in the checkout would be unpinnable (RS10's and RS14's both drifted on
# sibling programme outputs), so the programme's own output surfaces are excluded
# and the exclusion list is a ledger field. `docs/plans/` is part of that surface:
# the planning/spec documents are prose ABOUT the series (including the D12
# decision register this scan already excluded by path), so recording a plan or
# an audit pack must not move a pinned count. `docs/guides/` is the operational
# surface and is excluded for the same reason: a runbook or setup guide that
# names a series is not an implementation of its method, and these scans
# establish absence FROM CODE. Pinning operator documentation made a signed
# ledger re-drift on any documentation edit while no measurement moved.
SCAN_ROOTS = ("docs", "scripts", "src", "app/src", "prompts", "assets")
SCAN_SUFFIXES = (".md", ".py", ".ts", ".tsx", ".json")
EXCLUDED_SCAN_PREFIXES = (
    "docs/implementation/",
    "docs/plans/",
    "docs/guides/",
    "prompts/",
    "scripts/tools/",
    "app/src/components/studies/",
    "app/tests/",
)
EDITION_PREFIX = "docs/analytics/editions/"
RETAINED_EDITION_PREFIX = "docs/analytics/editions/legacy/"
EXCLUDED_SCAN_PATHS = (
    "docs/plans/2026-11-12-reporting-refresh-decisions.md",
    ".secrets.baseline",
)
EXCLUDED_DIR_COMPONENTS = (
    ".astro",
    ".astro-cache",
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "htmlcov",
    "node_modules",
)
JOINT_MODEL_TOKENS = (
    "joint model",
    "joint-model",
    "pooled model",
    "pooled estimate",
    "meta-analysis",
    "meta analysis",
    "cross-study",
    "cross study",
    "multi-study model",
)
JOINT_MODEL_FILENAME_TOKENS = ("joint_model", "pooled_model", "meta_analysis", "cross_study")
MAX_MATCHES = 40

# The sentinel-string state, declared so a field carrying a placeholder can never
# be read as a measurement. Measured, not assumed: `sentinelScan` reports whether
# any field this ledger reads carries one of these values.
SENTINEL_STRINGS = (
    "n/a",
    "na",
    "nan",
    "none",
    "null",
    "nil",
    "unknown",
    "notrecorded",
    "not-recorded",
    "not recorded",
    "tbd",
    "todo",
    "-",
    "",
)

# The ledger-wide sentinel split, declared rather than inferred, and checked against
# the scan instead of asserted. rs01's source inventory records one acquisition
# status per acquisition file, so a placeholder in `sources[].acquisition.status`
# is ONE ledger's own vocabulary for an unrecorded source, repeated once per
# source. Everything else is enumerated in full under
# `ledgerWide.split.otherFields`, so this boundary is checkable by a reader: a
# placeholder anywhere else joins the enumerated class automatically. The earlier
# version of this scan capped its match list at twelve rs01 entries and left the
# prose to generalise from them, which produced exactly the sentence this
# declaration exists to prevent.
SENTINEL_REGISTER_FIELD = {
    "ledgerSuffix": "rs01-source-inventory.json",
    "fieldPath": "sources[].acquisition.status",
}
SENTINEL_MATCH_CAP = 12
INDEX_SUFFIX = re.compile(r"\[\d+\]")

MISSINGNESS_STATES = {
    "recorded-value": "the field is present and carries a value this ledger cites",
    "recorded-null": "the field is present and explicitly null (a registry pin, for example)",
    "recorded-empty-list": "the field is present and empty (an attestation list on a non-signed edition)",
    "absent-block": (
        "the block the field would live in is not present in the ledger at all; "
        "this is not a zero and not a null"
    ),
    "absent-key": "the block is present but does not carry the key",
    "sentinel-string": (
        "the field carries a declared placeholder string instead of a measurement; "
        "verified by `sentinelScan`, never inferred"
    ),
    SELF_STATE: (
        "the field describes this page's own series, whose signing state is "
        "deliberately not an input because it changes the moment the page is "
        "signed; the row records only facts invariant under that signature"
    ),
}


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_bytes(payload: object) -> bytes:
    return json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"


def canonical_content_sha256(path: Path) -> str:
    """sha256 of the canonical re-serialisation of a JSON file's parsed content.

    A formatter can move a ledger's raw bytes without touching a byte of its
    content. That distinction is the difference between a stale signature and a
    reformatted file, so both hashes are measured for every ledger.
    """
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SystemExit(f"Unreadable ledger {_relative(path)}: {error}") from error
    return hashlib.sha256(canonical_bytes(payload)).hexdigest()


def _relative(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def _r(value: Any, digits: int) -> float | None:
    if value is None:
        return None
    number = float(value)
    if number != number:  # NaN
        return None
    return round(number, digits)


def _text_of(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise SystemExit(f"Unreadable file {_relative(path)}: {error}") from error


def _load_json(path: Path) -> Any:
    """A JSON file parsed with the file named on failure, never a bare SyntaxError."""
    try:
        return json.loads(_text_of(path))
    except json.JSONDecodeError as error:
        raise SystemExit(f"Unparseable JSON in {_relative(path)}: {error}") from error


def _match1(pattern: str, text: str, label: str) -> str:
    """The first capture of `pattern`, or a loud failure naming what went missing."""
    match = re.search(pattern, text)
    if match is None:
        raise SystemExit(f"registry entry lost its {label}: {text[:120]!r}")
    return match.group(1)


def _block(text: str, start_marker: str, end_marker: str, label: str) -> str:
    start = text.find(start_marker)
    if start < 0:
        raise SystemExit(f"registry no longer carries the {label} block ({start_marker!r})")
    end = text.find(end_marker, start)
    if end < 0:
        raise SystemExit(f"registry {label} block has no closing marker ({end_marker!r})")
    return text[start:end]


# --------------------------------------------------------------------------- #
# 1. The register, read from the app registry
# --------------------------------------------------------------------------- #


def parse_registry() -> dict[str, Any]:
    """Parse the edition register as text; never import or execute it.

    The registry is the authority for edition identity and for the pins, so it is
    read as bytes and parsed with explicit patterns. Every list this parser
    produces is length-checked against the others in the same entry: a registry
    edit that adds a field this parser does not understand fails here rather than
    silently dropping an attestation.
    """
    text = _text_of(REGISTRY)
    legacy_slugs = re.findall(
        r'"([a-z0-9]+(?:-[a-z0-9]+)*)"',
        _block(text, "const LEGACY_SERIES = [", "] as const;", "LEGACY_SERIES"),
    )
    if not legacy_slugs:
        raise SystemExit("registry LEGACY_SERIES block parsed to zero slugs")

    template = _block(
        text, "export const ANALYTICS_EDITIONS", "const SERIES_PATTERN", "ANALYTICS_EDITIONS"
    )
    for marker in LEGACY_EDITION_TEMPLATE_MARKERS:
        if marker not in template:
            raise SystemExit(f"registry legacy-edition template no longer carries {marker!r}")
    legacy_evidence = re.search(r'evidenceStatus: "([a-z]+)"', template)
    legacy_editorial = re.search(r'editorialStatus: "([a-z]+)"', template)
    if legacy_evidence is None or legacy_editorial is None:
        raise SystemExit("registry legacy-edition template lost its status literals")

    refreshed = _block(
        text,
        "export const REFRESHED_EDITIONS",
        "export const ANALYTICS_EDITIONS",
        "REFRESHED_EDITIONS",
    )
    entries: list[dict[str, Any]] = []
    for chunk in re.split(r"\n  \{\n", refreshed)[1:]:
        if 'seriesSlug: "' not in chunk:
            continue
        entry = _parse_entry(chunk)
        entries.append(entry)

    slugs = [entry["seriesSlug"] for entry in entries]
    duplicates = sorted({slug for slug in slugs if slugs.count(slug) > 1})
    if duplicates:
        raise SystemExit(f"registry registers more than one refreshed edition for {duplicates}")
    unknown = sorted(set(slugs) - set(legacy_slugs))
    if unknown:
        raise SystemExit(f"registry registers a refreshed edition outside LEGACY_SERIES: {unknown}")

    return {
        "path": _relative(REGISTRY),
        "sha256": sha256_of(REGISTRY),
        "bytes": int(REGISTRY.stat().st_size),
        "seriesFromLegacyList": legacy_slugs,
        "seriesCount": len(legacy_slugs),
        "refreshedEditions": entries,
        "refreshedCount": len(entries),
        "legacyEdition": {
            "editionIdConstant": _match1(
                r"LEGACY_EDITION_ID\s*=\s*\"([^\"]+)\"", text, "LEGACY_EDITION_ID constant"
            ),
            "evidenceStatus": legacy_evidence.group(1),
            "editorialStatus": legacy_editorial.group(1),
            "editionSha256": None,
            "signoffCount": 0,
        },
    }


def _parse_entry(chunk: str) -> dict[str, Any]:
    def one(pattern: str, label: str) -> str:
        return _match1(pattern, chunk, label)

    pin_match = re.search(r'editionSha256:\s*(null|"([0-9a-f]{64})")', chunk)
    if pin_match is None:
        raise SystemExit(f"registry entry lost its editionSha256 pin: {chunk[:120]!r}")
    prepared_match = re.search(r'preparedBy:\s*(null|"([^"]+)")', chunk)

    signoffs: list[dict[str, Any]] = []
    position = chunk.find("signoffs: [")
    if position < 0:
        raise SystemExit("registry entry lost its signoffs list")
    for block in re.split(r"\n      \{\n", chunk[position:])[1:]:
        if 'role: "' not in block:
            continue
        signoffs.append(
            {
                "role": _match1(r'role: "([a-z]+)"', block, "sign-off role"),
                "name": _match1(r'name: "([^"]*)"', block, "sign-off name"),
                "date": _match1(r'date: "([0-9-]+)"', block, "sign-off date"),
                "artifactSha256": _match1(
                    r'artifactSha256:\s*\n?\s*"([0-9a-f]{64})"', block, "artifact pin"
                ),
                "automated": _match1(r"automated: (true|false)", block, "automated flag") == "true",
                "evidencePath": _match1(r'evidencePath:\s*\n?\s*"([^"]+)"', block, "evidence path"),
            }
        )

    return {
        "seriesSlug": one(r'seriesSlug: "([^"]+)"', "series slug"),
        "editionId": one(r'editionId: "([^"]+)"', "edition id"),
        "publicationYear": int(one(r"publicationYear: (\d+)", "publication year")),
        "evidenceStatus": one(r'evidenceStatus: "([a-z]+)"', "evidence status"),
        "editorialStatus": one(r'editorialStatus: "([a-z]+)"', "editorial status"),
        "frozenSource": one(r'frozenSource:\s*"([^"]+)"', "frozen source"),
        "assetsPinned": int(one(r"assetsPinned: (\d+)", "assets pinned")),
        "preparedBy": prepared_match.group(2)
        if prepared_match and prepared_match.group(2)
        else None,
        "editionSha256": pin_match.group(2) if pin_match.group(2) else None,
        "signoffs": signoffs,
    }


# --------------------------------------------------------------------------- #
# 2. The files on disk, measured against those pins
# --------------------------------------------------------------------------- #


def resolve_ledger(pin: str, series: str) -> tuple[Path, str]:
    """The ledger file whose bytes, or whose content, hash to `pin`.

    Resolution is by hash, not by filename: RS01 and RS02 do not follow the
    `rs<NN>-<series>-evidence.json` convention, and a filename convention that has
    to be special-cased is not a measurement.
    """
    candidates = sorted(path for path in ARTIFACTS.glob("rs*.json") if path.is_file())
    exact = [path for path in candidates if sha256_of(path) == pin]
    if len(exact) == 1:
        return exact[0], "raw-bytes"
    if len(exact) > 1:
        raise SystemExit(f"{series}: more than one ledger hashes to the attestation pin: {exact}")
    by_content = [path for path in candidates if canonical_content_sha256(path) == pin]
    if len(by_content) == 1:
        return by_content[0], "canonical-content"
    raise SystemExit(
        f"{series}: no ledger in {_relative(ARTIFACTS)} hashes to the attestation pin {pin} "
        f"(checked {len(candidates)} files, raw and canonical); the signature is stale and "
        "this register cannot be built on it"
    )


def claim_dispositions(ledger: dict[str, Any]) -> dict[str, Any]:
    """What the edition's own ledger says it did with its own legacy claims.

    Four ledgers (RS03-RS05) recorded the disposition under `disposition` with a
    different vocabulary; two (RS01, RS02) recorded no `legacyClaims` block at all.
    The vocabularies are recorded per ledger and never merged into one total, and
    an absent block is a state rather than a zero.
    """
    if "legacyClaims" not in ledger:
        return {
            "state": "absent-block",
            "itemCount": None,
            "statusKey": None,
            "byValue": None,
            "meaning": (
                "this ledger carries no legacyClaims block, so it records no claim "
                "dispositions at all; that is not zero disposed claims"
            ),
        }
    claims = ledger.get("legacyClaims")
    if not isinstance(claims, list):
        return {"state": "unexpected-shape", "itemCount": None, "statusKey": None, "byValue": None}
    status_key = None
    for candidate in ("status", "disposition"):
        if any(isinstance(item, dict) and candidate in item for item in claims):
            status_key = candidate
            break
    if status_key is None:
        return {
            "state": "no-status-key",
            "itemCount": len(claims),
            "statusKey": None,
            "byValue": None,
            "meaning": "items are present but carry neither a `status` nor a `disposition` field",
        }
    counts = Counter(str(item[status_key]) for item in claims if isinstance(item, dict))
    return {
        "state": "measured",
        "itemCount": len(claims),
        "statusKey": status_key,
        "byValue": {key: int(counts[key]) for key in sorted(counts)},
        "meaning": (
            "counts are of this ledger's own claim items under its own status "
            "vocabulary; vocabularies differ across ledgers and are never summed"
        ),
    }


def _input_records(node: Any) -> list[dict[str, Any]]:
    """Every {path, sha256}-shaped input record anywhere in an `inputs` block."""
    found: list[dict[str, Any]] = []
    if isinstance(node, dict):
        path = node.get("path")
        digest = node.get("sha256")
        if isinstance(path, str) and isinstance(digest, str):
            found.append({"path": path, "sha256": digest})
        for key, value in node.items():
            if (
                isinstance(key, str)
                and isinstance(value, dict)
                and isinstance(value.get("sha256"), str)
            ):
                if "/" in key or "." in Path(key).suffix:
                    found.append({"path": key, "sha256": str(value["sha256"])})
            found.extend(_input_records(value))
    elif isinstance(node, list):
        for item in node:
            found.extend(_input_records(item))
    return found


def frame_dependency(ledger: dict[str, Any], frame_sha: str) -> dict[str, Any]:
    """Does this ledger record the shipped frame it measured, and at which hash?"""
    if "inputs" not in ledger:
        return {
            "state": "absent-block",
            "recordedSha256": None,
            "matchesCurrentFrame": None,
            "meaning": "this ledger carries no `inputs` block; it records no input pins",
        }
    records = _input_records(ledger.get("inputs"))
    matches = [record for record in records if record["path"] == FRAME_PATH]
    if not matches:
        return {
            "state": "not-recorded-in-ledger",
            "recordedSha256": None,
            "matchesCurrentFrame": None,
            "inputRecordCount": len(records),
            "meaning": (
                "the ledger records inputs but not this frame; its measurements may "
                "rest on other sources, and this ledger does not assume the frame"
            ),
        }
    recorded = matches[0]["sha256"]
    return {
        "state": "recorded",
        "recordedSha256": recorded,
        "matchesCurrentFrame": recorded == frame_sha,
        "inputRecordCount": len(records),
        "meaning": "the ledger recorded the frame hash it measured",
    }


def _resolve_key(ledger: dict[str, Any], key: str) -> tuple[bool, Any]:
    if key not in ledger:
        return False, None
    value = ledger[key]
    if not isinstance(value, str):
        return True, None
    return True, value


def descriptors_for(series: str, ledger: dict[str, Any] | None) -> dict[str, Any]:
    """The population/unit quotes a series' edition records, verbatim-checked."""
    spec = next((item for item in DESCRIPTORS if item["series"] == series), None)
    if spec is None:
        raise SystemExit(f"no descriptor spec for series {series!r}")
    if ledger is None:
        return {
            "state": "no-ledger",
            "entries": [],
            "missingReason": spec.get("missingReason"),
        }
    entries: list[dict[str, Any]] = []
    missing: list[dict[str, str]] = []
    for entry in spec.get("entries", ()):
        present, value = _resolve_key(ledger, str(entry["sourceKey"]))
        if not present or value is None:
            missing.append(
                {
                    "field": str(entry["field"]),
                    "sourceKey": str(entry["sourceKey"]),
                    "reason": "the cited field is absent from this ledger",
                }
            )
            continue
        if str(entry["quote"]) not in value:
            raise SystemExit(
                f"{series}: descriptor quote for {entry['field']} is not a verbatim "
                f"substring of {entry['sourceKey']}: {entry['quote']!r}"
            )
        entries.append(
            {
                "field": str(entry["field"]),
                "sourceKey": str(entry["sourceKey"]),
                "quote": str(entry["quote"]),
                "verbatimInSource": True,
            }
        )
    return {
        "state": "measured" if entries else "absent-value",
        "entries": entries,
        "missing": missing,
        "missingReason": spec.get("missingReason"),
    }


def _self_row(series: str, registry: dict[str, Any], inputs: dict[str, Any]) -> dict[str, Any]:
    """One register row for the page's own series, recording only invariant facts.

    The page cannot describe itself: `signed`, `attestation`, `editionFile` against
    the new pin, the claim split, the frame record — every one of those changes when
    RS15 signs, so recording them would put the ledger out of reach of its own
    approval. The frozen legacy edition is the one registered fact that survives,
    and it is measured here like any other text.
    """
    legacy = registry["legacyEdition"]
    legacy_source = f"docs/analytics/editions/legacy/2026-11-12/{series}.md"
    legacy_path = REPO_ROOT / legacy_source
    if not legacy_path.is_file():
        raise SystemExit(f"{series}: legacy frozen source is not on disk: {legacy_source}")
    legacy_sha = sha256_of(legacy_path)
    legacy_bytes = int(legacy_path.stat().st_size)
    inputs[legacy_source] = {"sha256": legacy_sha, "bytes": legacy_bytes}
    not_an_input = (
        "not recorded for this row: it is the page under production, and this fact "
        "would change at the moment the page is signed"
    )
    return {
        "id": series,
        "series": series,
        "self": True,
        "selfNote": SELF_NOTE,
        "currentEdition": {
            "editionId": legacy["editionIdConstant"],
            "publicationYear": None,
            "evidenceStatus": legacy["evidenceStatus"],
            "editorialStatus": legacy["editorialStatus"],
            "frozenSource": legacy_source,
            "assetsPinned": None,
            "preparedBy": None,
            "editionSha256": None,
            "state": SELF_STATE,
            "meaning": (
                "the register's own fallback for this series: the frozen legacy "
                "edition, which stays registered whatever this page's signing state "
                "is"
            ),
        },
        "legacyEdition": {
            "editionId": legacy["editionIdConstant"],
            "evidenceStatus": legacy["evidenceStatus"],
            "editorialStatus": legacy["editorialStatus"],
            "frozenSource": legacy_source,
            "editionSha256": None,
        },
        "signed": None,
        "signedState": {
            "state": SELF_STATE,
            "value": None,
            "meaning": (
                "deliberately null rather than true or false: either literal would "
                "flip when this page is signed, and the point of the row is that it "
                "does not move"
            ),
        },
        "attestation": {
            "state": SELF_STATE,
            "roleCount": None,
            "roles": [],
            "rolesComplete": None,
            "distinctNames": None,
            "sharedArtifactSha256": None,
            "artifactShaUnique": None,
            "preparerIsNotASignatory": None,
            "automatedRoles": [],
            "meaning": not_an_input,
        },
        "editionFile": {
            "path": legacy_source,
            "sha256": legacy_sha,
            "bytes": legacy_bytes,
            "pin": None,
            "matchesPin": None,
            "matchesPinState": SELF_STATE,
            "meaning": (
                "this is the frozen legacy text the series falls back to, measured "
                "on disk; the row records no pin for the page's own edition because "
                "the text on disk changes when its provenance is refreshed"
            ),
        },
        "ledger": {
            "state": SELF_STATE,
            "path": None,
            "rawSha256": None,
            "bytes": None,
            "rawMatchesPin": None,
            "contentSha256": None,
            "contentMatchesPin": None,
            "pin": None,
            "resolution": None,
            "serialisationDrift": None,
            "meaning": (
                "this page's own ledger is not read: its hash is an output of this "
                "measurement, so treating it as an input would be circular"
            ),
        },
        "claimDispositions": {
            "state": SELF_STATE,
            "itemCount": None,
            "statusKey": None,
            "byValue": None,
            "meaning": not_an_input,
        },
        "ledgerCutoff": {"state": SELF_STATE, "lastCompleteMonth": None},
        "descriptors": {
            "state": SELF_STATE,
            "entries": [],
            "missing": [],
            "missingReason": descriptors_for(series, None)["missingReason"],
        },
        "frameDependency": {
            "state": SELF_STATE,
            "recordedSha256": None,
            "matchesCurrentFrame": None,
            "meaning": not_an_input,
        },
    }


def measure_row(
    series: str,
    registry: dict[str, Any],
    frame_sha: str,
    inputs: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """One register row, measured twice (registry and disk) and reconciled."""
    if series == SELF_SERIES:
        row = _self_row(series, registry, inputs)
        return row, {
            "series": series,
            "self": True,
            "signed": None,
            "textMatchesPin": None,
            "ledgerRawMatchesPin": None,
            "ledgerContentMatchesPin": None,
            "serialisationDrift": False,
        }
    refreshed = next(
        (entry for entry in registry["refreshedEditions"] if entry["seriesSlug"] == series), None
    )
    legacy = registry["legacyEdition"]
    legacy_source = f"docs/analytics/editions/legacy/2026-11-12/{series}.md"
    legacy_path = REPO_ROOT / legacy_source

    current = refreshed or {
        "seriesSlug": series,
        "editionId": legacy["editionIdConstant"],
        "publicationYear": None,
        "evidenceStatus": legacy["evidenceStatus"],
        "editorialStatus": legacy["editorialStatus"],
        "frozenSource": legacy_source,
        "assetsPinned": None,
        "preparedBy": None,
        "editionSha256": None,
        "signoffs": [],
    }

    edition_path = REPO_ROOT / str(current["frozenSource"])
    if not edition_path.is_file():
        raise SystemExit(
            f"{series}: registered frozen source is not on disk: {current['frozenSource']}"
        )
    edition_sha = sha256_of(edition_path)
    edition_bytes = int(edition_path.stat().st_size)
    inputs[_relative(edition_path)] = {"sha256": edition_sha, "bytes": edition_bytes}
    inputs[legacy_source] = {
        "sha256": sha256_of(legacy_path),
        "bytes": int(legacy_path.stat().st_size),
    }

    pin = current["editionSha256"]
    matches_pin = None if pin is None else edition_sha == pin
    if matches_pin is False:
        raise SystemExit(
            f"{series}: frozen text {current['frozenSource']} is sha256 {edition_sha} but the "
            f"register pins {pin}; the signature no longer covers the file on disk"
        )

    signoffs = list(current["signoffs"])
    roles = [signoff["role"] for signoff in signoffs]
    artifacts = sorted({signoff["artifactSha256"] for signoff in signoffs})
    attestation: dict[str, Any] = {
        "roleCount": len(signoffs),
        "roles": roles,
        "rolesComplete": roles == ["source", "scientific", "publication"],
        "distinctNames": len({signoff["name"] for signoff in signoffs}) == len(signoffs),
        "sharedArtifactSha256": artifacts[0] if len(artifacts) == 1 else None,
        "artifactShaUnique": len(artifacts) == 1,
        "preparerIsNotASignatory": all(
            signoff["name"] != current["preparedBy"] for signoff in signoffs
        ),
        "automatedRoles": [signoff["role"] for signoff in signoffs if signoff["automated"]],
    }
    if current["evidenceStatus"] == "approved":
        if not attestation["rolesComplete"]:
            raise SystemExit(
                f"{series}: an approved edition must carry exactly source/scientific/"
                f"publication, found {roles}"
            )
        if not attestation["artifactShaUnique"]:
            raise SystemExit(f"{series}: the three attestations do not share one artifact pin")
        if not attestation["preparerIsNotASignatory"]:
            raise SystemExit(f"{series}: a signatory is also the edition's preparer")

    ledger: dict[str, Any]
    claim_split: dict[str, Any]
    cutoff_state: dict[str, Any]
    descriptors: dict[str, Any]
    frame_state: dict[str, Any]
    # The ledger is pinned by the artifact sha256 its attestations share, NOT by
    # `editionSha256` (which pins the frozen text). Conflating the two is the
    # defect this register exists to catch.
    ledger_pin = attestation["sharedArtifactSha256"]
    if ledger_pin is None:
        ledger = {
            "state": "no-attestation-pin",
            "path": None,
            "rawSha256": None,
            "bytes": None,
            "rawMatchesPin": None,
            "contentSha256": None,
            "contentMatchesPin": None,
            "resolution": None,
            "serialisationDrift": None,
            "meaning": (
                "this series carries no signed edition in this checkout, so there is "
                "no attestation pin to measure a ledger against"
            ),
        }
        claim_split = {"state": "no-signed-edition", "itemCount": None, "statusKey": None}
        cutoff_state = {"state": "no-signed-edition", "lastCompleteMonth": None}
        descriptors = descriptors_for(series, None)
        frame_state = {"state": "no-signed-edition", "recordedSha256": None}
    else:
        ledger_path, resolution = resolve_ledger(str(ledger_pin), series)
        raw_sha = sha256_of(ledger_path)
        content_sha = canonical_content_sha256(ledger_path)
        try:
            ledger_json = json.loads(_text_of(ledger_path))
        except json.JSONDecodeError as error:
            raise SystemExit(f"{series}: ledger is not valid JSON: {error}") from error
        inputs[_relative(ledger_path)] = {
            "sha256": raw_sha,
            "bytes": int(ledger_path.stat().st_size),
        }
        drift = raw_sha != ledger_pin
        if drift and content_sha != ledger_pin:
            raise SystemExit(
                f"{series}: ledger {_relative(ledger_path)} is sha256 {raw_sha} on disk and "
                f"{content_sha} canonicalised, but the attestations pin {ledger_pin}; the "
                "content changed after signature"
            )
        declared = KNOWN_SERIALISATION_DRIFT.get(series)
        if drift:
            if declared is None:
                raise SystemExit(
                    f"{series}: ledger bytes moved from their pin by serialisation only; "
                    "declare it in KNOWN_SERIALISATION_DRIFT with the observed raw sha256 "
                    "rather than recording a quiet mismatch"
                )
            if declared["observedRawSha256"] != raw_sha or declared["path"] != _relative(
                ledger_path
            ):
                raise SystemExit(
                    f"{series}: declared serialisation drift no longer matches this checkout "
                    f"(expected {declared['observedRawSha256']} at {declared['path']}, measured "
                    f"{raw_sha} at {_relative(ledger_path)})"
                )
        ledger = {
            "state": "measured",
            "path": _relative(ledger_path),
            "rawSha256": raw_sha,
            "bytes": int(ledger_path.stat().st_size),
            "rawMatchesPin": not drift,
            "contentSha256": content_sha,
            "contentMatchesPin": content_sha == ledger_pin,
            "pin": ledger_pin,
            "resolution": resolution,
            "serialisationDrift": (
                {
                    "declared": True,
                    "observedRawSha256": raw_sha,
                    "pinnedSha256": ledger_pin,
                    "contentSha256": content_sha,
                    "cause": declared["cause"] if declared else None,
                    "meaning": (
                        "the file's bytes differ from the pinned bytes; its parsed content "
                        "is identical and canonical re-serialisation reproduces the pin, so "
                        "the attestation still covers this content and not these bytes"
                    ),
                }
                if drift
                else None
            ),
        }
        claim_split = claim_dispositions(ledger_json)
        cutoff_block = ledger_json.get("cutoff")
        if not isinstance(cutoff_block, dict):
            cutoff_state = {"state": "absent-block", "lastCompleteMonth": None}
        elif "lastCompleteMonth" not in cutoff_block:
            cutoff_state = {"state": "absent-key", "lastCompleteMonth": None}
        else:
            cutoff_state = {
                "state": "recorded-value",
                "lastCompleteMonth": cutoff_block["lastCompleteMonth"],
            }
        descriptors = descriptors_for(series, ledger_json)
        frame_state = frame_dependency(ledger_json, frame_sha)

    row = {
        "id": series,
        "series": series,
        "self": False,
        "editionsRegistered": 2 if refreshed is not None else 1,
        "currentEdition": {
            "editionId": current["editionId"],
            "publicationYear": current["publicationYear"],
            "evidenceStatus": current["evidenceStatus"],
            "editorialStatus": current["editorialStatus"],
            "frozenSource": current["frozenSource"],
            "assetsPinned": current["assetsPinned"],
            "preparedBy": current["preparedBy"],
            "editionSha256": pin,
        },
        "legacyEdition": {
            "editionId": legacy["editionIdConstant"],
            "evidenceStatus": legacy["evidenceStatus"],
            "editorialStatus": legacy["editorialStatus"],
            "frozenSource": legacy_source,
            "editionSha256": None,
        },
        "signed": current["evidenceStatus"] == "approved",
        "attestation": attestation,
        "editionFile": {
            "path": str(current["frozenSource"]),
            "sha256": edition_sha,
            "bytes": edition_bytes,
            "pin": pin,
            "matchesPin": matches_pin,
            "matchesPinState": (
                "no-pin" if pin is None else ("matches" if matches_pin else "differs")
            ),
        },
        "ledger": ledger,
        "claimDispositions": claim_split,
        "ledgerCutoff": cutoff_state,
        "descriptors": descriptors,
        "frameDependency": frame_state,
    }
    return row, {
        "series": series,
        "self": False,
        "signed": row["signed"],
        "textMatchesPin": matches_pin,
        "ledgerRawMatchesPin": ledger["rawMatchesPin"],
        "ledgerContentMatchesPin": ledger["contentMatchesPin"],
        "serialisationDrift": bool(ledger["serialisationDrift"]),
    }


def _cutoff_values(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """The last-complete-month values the signed ledgers record, with their counts."""
    counter: Counter[str] = Counter()
    for row in rows:
        state = row["ledgerCutoff"]
        if state.get("state") == "recorded-value":
            counter[str(state["lastCompleteMonth"])] = counter[str(state["lastCompleteMonth"])] + 1
    return {
        "recordedValueCount": int(sum(counter.values())),
        "byValue": {value: int(counter[value]) for value in sorted(counter)},
        "meaning": (
            "each edition's own ledger window end, counted as recorded; this ledger "
            "does not re-derive a sibling's window and does not assume they agree"
        ),
    }


def _claim_values(rows: list[dict[str, Any]], status_key: str) -> dict[str, Any]:
    """Claim-item counts for one status vocabulary, across the ledgers that use it."""
    counter: Counter[str] = Counter()
    ledgers: list[str] = []
    for row in rows:
        split = row["claimDispositions"]
        if split.get("state") != "measured" or split.get("statusKey") != status_key:
            continue
        ledgers.append(row["id"])
        for value, count in (split.get("byValue") or {}).items():
            counter[value] = counter[value] + int(count)
    return {
        "ledgers": sorted(ledgers),
        "ledgerCount": len(ledgers),
        "itemCount": int(sum(counter.values())),
        "byValue": {value: int(counter[value]) for value in sorted(counter)},
    }


def _absent_claim_ledgers(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Ledgers that carry no legacyClaims block at all — a state, not a zero."""
    ids = sorted(
        row["id"] for row in rows if row["claimDispositions"].get("state") == "absent-block"
    )
    return {"ledgers": ids, "ledgerCount": len(ids), "itemCount": None}


def register(registry: dict[str, Any], frame_sha: str, inputs: dict[str, Any]) -> dict[str, Any]:
    measured = [
        measure_row(series, registry, frame_sha, inputs)
        for series in registry["seriesFromLegacyList"]
    ]
    rows = [row for row, _pin in measured]
    pins = [pin for _row, pin in measured]
    siblings = [row for row in rows if not row["self"]]
    self_rows = [row["id"] for row in rows if row["self"]]

    # `signed` is null on the self row by design, so it is counted by literal
    # equality: neither a True nor a False total may depend on this page's own
    # signing state.
    signed = [row["id"] for row in siblings if row["signed"] is True]
    unsigned = [row["id"] for row in siblings if row["signed"] is False]
    text_checks = [pin for pin in pins if pin["textMatchesPin"] is not None]
    ledger_checks = [pin for pin in pins if pin["ledgerContentMatchesPin"] is not None]
    split_states = Counter(row["claimDispositions"]["state"] for row in siblings)
    cutoff_states = Counter(row["ledgerCutoff"]["state"] for row in siblings)
    frame_states = Counter(row["frameDependency"]["state"] for row in siblings)
    vocabularies = {
        row["id"]: row["claimDispositions"].get("statusKey") for row in siblings if row["signed"]
    }
    return {
        "registry": {
            "path": registry["path"],
            "seriesFromLegacyListCount": registry["seriesCount"],
            "seriesFromLegacyList": registry["seriesFromLegacyList"],
            "pinned": False,
            "meaning": (
                "the register is derived from this registry file at measurement "
                "time and the file itself is deliberately not pinned; the rule is "
                "stated once at registryReadRule"
            ),
        },
        "meaning": (
            "one row per series, read from the app registry and from the files on "
            "disk; `signed` is the registry's own evidenceStatus, and the two "
            "booleans on each row are measurements of the bytes this checkout "
            "holds. The `findings` row is the page under production and carries "
            "`self: true` with no signing state at all: it is the one row that "
            "must not move when this page is signed"
        ),
        "rows": rows,
        "summary": {
            "seriesCount": len(rows),
            "signedCount": len(signed),
            "unsignedSeries": unsigned,
            "unsignedCount": len(unsigned),
            "selfSeries": self_rows,
            "selfCount": len(self_rows),
            "selfSeriesMeaning": (
                "rows describing this page itself; they are excluded from the "
                "signed/unsigned totals, from every state counter below and from the "
                "sibling scan, because their state changes when this page is signed "
                "and an approval must not move the ledger it approves"
            ),
            "textPinChecks": {
                "checked": len(text_checks),
                "matched": sum(1 for pin in text_checks if pin["textMatchesPin"]),
                "differed": sum(1 for pin in text_checks if not pin["textMatchesPin"]),
                "notCheckedNoPin": len(pins) - len(text_checks),
            },
            "ledgerPinChecks": {
                "checked": len(ledger_checks),
                "rawMatched": sum(1 for pin in ledger_checks if pin["ledgerRawMatchesPin"]),
                "rawDiffered": sum(1 for pin in ledger_checks if not pin["ledgerRawMatchesPin"]),
                "contentMatched": sum(1 for pin in ledger_checks if pin["ledgerContentMatchesPin"]),
                "contentDiffered": sum(
                    1 for pin in ledger_checks if not pin["ledgerContentMatchesPin"]
                ),
                "serialisationDriftSeries": [
                    pin["series"] for pin in ledger_checks if pin["serialisationDrift"]
                ],
                "notCheckedNoPin": len(pins) - len(ledger_checks),
            },
            "claimSplitStates": {
                "measured": int(split_states.get("measured", 0)),
                "absentBlock": int(split_states.get("absent-block", 0)),
                "noSignedEdition": int(split_states.get("no-signed-edition", 0)),
                "otherStates": sorted(
                    state
                    for state in split_states
                    if state not in {"measured", "absent-block", "no-signed-edition"}
                ),
                "selfRowsExcluded": len(self_rows),
            },
            "claimStatusVocabulary": {
                "status": sorted(series for series, key in vocabularies.items() if key == "status"),
                "disposition": sorted(
                    series for series, key in vocabularies.items() if key == "disposition"
                ),
                "note": (
                    "the ledgers use two vocabularies under two keys and one counts "
                    "neither; they are recorded per ledger and never summed"
                ),
            },
            "claimStatusValues": {
                "byStatusKey": {
                    "status": _claim_values(siblings, "status"),
                    "disposition": _claim_values(siblings, "disposition"),
                    "noStatusKey": _absent_claim_ledgers(siblings),
                },
                "meaning": (
                    "counts of claim items per vocabulary: the totals under `status` "
                    "and under `disposition` describe different ledgers with "
                    "different vocabularies, so they are reported apart and never "
                    "added together"
                ),
            },
            "ledgerCutoffStates": {
                state: int(cutoff_states[state]) for state in sorted(cutoff_states)
            },
            "ledgerCutoffValues": _cutoff_values(siblings),
            "frameDependencyStates": {
                state: int(frame_states[state]) for state in sorted(frame_states)
            },
            "attestationRoleStates": {
                "complete": sum(1 for row in siblings if row["attestation"]["rolesComplete"]),
                "absent": sum(1 for row in siblings if row["attestation"]["roleCount"] == 0),
                "partial": sum(
                    1
                    for row in siblings
                    if row["attestation"]["roleCount"] is not None
                    and 0 < row["attestation"]["roleCount"]
                    and not row["attestation"]["rolesComplete"]
                ),
                "selfRowsExcluded": len(self_rows),
            },
        },
    }


# --------------------------------------------------------------------------- #
# 3. Cutoff, dependencies, what cannot be measured, bounded scans
# --------------------------------------------------------------------------- #


def cutoff(frame: pd.DataFrame) -> dict[str, Any]:
    """The last complete month, measured — the terminal month is partial."""
    months = frame["month"].astype(str)
    condo = pd.DataFrame(frame.loc[frame["property_type"] == "condo"]).reset_index(drop=True)
    counts = {str(key): int(value) for key, value in condo.groupby("month").size().items()}
    ordered = sorted(counts)
    terminal_month = ordered[-1]
    last_complete_month = ordered[-2]
    trailing_months = ordered[-13:-1]
    trailing = [counts[month] for month in trailing_months]
    trailing_median = float(pd.Series(trailing).median()) if trailing else 0.0

    all_counts = {str(key): int(value) for key, value in frame.groupby("month").size().items()}
    all_ordered = sorted(all_counts)
    all_trailing = [all_counts[month] for month in all_ordered[-13:-1]]
    all_median = float(pd.Series(all_trailing).median()) if all_trailing else 0.0

    return {
        "basis": (
            "last complete month = the month before the terminal month, whose "
            "transaction count is a measured fraction of the trailing-12-month "
            "median, not an assumed calendar fact (the same rule RS03-RS14 shipped, "
            "computed on the private rows so the bound is identical across studies)"
        ),
        "lastCompleteMonth": last_complete_month,
        "terminalMonth": terminal_month,
        "terminalMonthTransactions": counts[terminal_month],
        "trailing12MedianTransactions": _r(trailing_median, 1),
        "terminalMonthShareOfTrailingMedian": _r(
            counts[terminal_month] / trailing_median if trailing_median else None, 4
        ),
        "lastCompleteMonthTransactions": counts[last_complete_month],
        "allPropertyTypesTerminalMonth": all_ordered[-1],
        "allPropertyTypesTerminalMonthTransactions": all_counts[all_ordered[-1]],
        "allPropertyTypesTrailing12MedianTransactions": _r(all_median, 1),
        "frameFirstMonth": str(months.min()),
        "frameLastMonth": str(months.max()),
        "meaning": (
            "every frame aggregation in this ledger stops at lastCompleteMonth; no "
            "sibling edition's own window is re-derived here, and each series row "
            "cites the window its ledger records"
        ),
    }


def dependencies(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """What the summary page depends on, and why nothing it cites is blocked.

    The rule is mechanical, not editorial: a dependency is blocked when its
    edition is not signed, or when its text hash differs from its pin, or when its
    ledger's canonical content differs from the attestation pin. `blocked` is the
    measured result of applying that rule, not an assertion about it.
    """
    depends_on: list[dict[str, Any]] = []
    for row in rows:
        if row["self"]:
            state = SELF_STATE
        else:
            state = "signed"
            if not row["signed"]:
                state = "unsigned"
            elif row["ledger"]["serialisationDrift"]:
                state = "signed-with-disclosed-serialisation-drift"
        depends_on.append(
            {
                "series": row["id"],
                "self": row["self"],
                "editionId": row["currentEdition"]["editionId"],
                "evidenceStatus": row["currentEdition"]["evidenceStatus"],
                "signed": row["signed"],
                "textMatchesPin": row["editionFile"]["matchesPin"],
                "ledgerRawMatchesPin": row["ledger"]["rawMatchesPin"],
                "ledgerContentMatchesPin": row["ledger"]["contentMatchesPin"],
                "state": state,
            }
        )

    # The block is computed over sibling rows only. The page's own row is not a
    # dependency of the page - it IS the page - and it carries no signing state to
    # block on: an approval that could add itself to `blocked` would be a ledger
    # that fails its own signature.
    blocked = [
        dependency["series"]
        for dependency in depends_on
        if not dependency["self"]
        and (
            dependency["signed"] is not True
            or dependency["textMatchesPin"] is False
            or dependency["ledgerContentMatchesPin"] is False
        )
    ]

    per_series: list[dict[str, Any]] = []
    for row in rows:
        shared = [
            {
                "kind": "shared-frame",
                "id": FRAME_PATH,
                "state": row["frameDependency"]["state"],
                "recordedSha256": row["frameDependency"].get("recordedSha256"),
                "matchesCurrentFrame": row["frameDependency"].get("matchesCurrentFrame"),
                "signed": None,
            }
        ]
        per_series.append(
            {
                "id": row["id"],
                "dependsOn": shared,
                "meaning": (
                    "the shared frame is the only input every series row exposes here; "
                    "each ledger's full input list is its own record, cited at "
                    "seriesRegister.rows.<series>.frameDependency"
                ),
            }
        )

    return {
        "meaning": (
            "the summary page depends on the fifteen register rows; each row depends "
            "on its own edition text, its own ledger, and (where the ledger records "
            "it) the shared frame"
        ),
        "blockedRule": (
            "blocked iff the dependency is a sibling series and (its evidenceStatus "
            "is not the registry's signed value, or its measured text sha256 differs "
            "from editionSha256, or its ledger's canonical content sha256 differs "
            "from the attestation pin). The page's own row is excluded by identity, "
            "not by status: it carries no signing state, so its approval cannot add "
            "or remove anything here"
        ),
        "pages": [{"id": "findings", "dependsOn": depends_on}],
        "perSeries": per_series,
        "blocked": blocked,
        "blockedCheck": {
            "rowsEvaluated": len(depends_on),
            "siblingRowsEvaluated": sum(1 for dependency in depends_on if not dependency["self"]),
            "signedRows": sum(1 for dependency in depends_on if dependency["signed"] is True),
            "rowsWithTextPinMismatch": sum(
                1 for dependency in depends_on if dependency["textMatchesPin"] is False
            ),
            "rowsWithLedgerContentMismatch": sum(
                1 for dependency in depends_on if dependency["ledgerContentMatchesPin"] is False
            ),
            "rowsWithDisclosedSerialisationDrift": sum(
                1
                for dependency in depends_on
                if dependency["state"] == "signed-with-disclosed-serialisation-drift"
            ),
            "rowsExcludedFromBlockedBecauseContentMatches": [
                dependency["series"]
                for dependency in depends_on
                if dependency["ledgerRawMatchesPin"] is False
                and dependency["ledgerContentMatchesPin"] is True
            ],
            "rowsExcludedFromBlockedBecauseSelf": [
                dependency["series"] for dependency in depends_on if dependency["self"]
            ],
            "selfRule": (
                "the self row is excluded because it is the page itself and carries "
                "no signing state; recording it as an excluded unsigned dependency "
                "would be a status that flips at approval"
            ),
            "meaning": (
                "the `rowsExcludedFromBlockedBecauseContentMatches` row is not a "
                "waived failure: its attestation covers content that this checkout "
                "still reproduces byte-for-byte under canonical serialisation, and "
                "that is the measured reason it is not in `blocked`. An empty "
                "`blocked` is the result of applying the rule above to these counts, "
                "not an assertion that nothing is blocked"
            ),
        },
    }


def not_measurable(
    rows: list[dict[str, Any]], measured_cutoff: dict[str, Any], scans: dict[str, Any]
) -> list[dict[str, Any]]:
    # Siblings only: the page's own row carries no signing state, so including it
    # would make `signedEditions` move when this page is signed.
    signed = [row for row in rows if row["signed"] is True]
    windows = sorted(
        {
            str(row["ledgerCutoff"]["lastCompleteMonth"])
            for row in signed
            if row["ledgerCutoff"]["state"] == "recorded-value"
        }
    )
    units = sorted(
        {
            entry["quote"]
            for row in signed
            for entry in row["descriptors"]["entries"]
            if entry["field"] == "unit"
        }
    )
    return [
        {
            "id": "jointModelAcrossStudies",
            "asks": (
                "a statement that ranks one series' finding above another, or that "
                "pools several series into one estimate"
            ),
            "state": "not-measurable",
            "reason": (
                "a ranking or a pooled estimate needs a joint model on one outcome; "
                "these editions measure different populations, windows and units, so "
                "their coefficients are not commensurable and this checkout holds no "
                "joint artefact"
            ),
            "measuredBound": {
                "signedEditions": len(signed),
                "signedEditionsMeaning": (
                    "sibling editions the registry records as signed; the page's own "
                    "row is excluded because its state is not an input"
                ),
                "distinctLedgerCutoffMonths": windows,
                "distinctDeclaredUnits": len(units),
                "units": units,
                "scan": "absenceScans.jointModel",
            },
        },
        {
            "id": "legacyCorpusAggregates",
            "asks": (
                "the frozen text's own corpus totals - 911,797 transactions over "
                "2017-2026, and the lease-band transaction total its appendix states"
            ),
            "state": "not-measurable",
            "reason": (
                "no data vintage in this checkout carries that corpus: the shipped "
                "frame's row count and month span are a different population "
                "measured at inputs and cutoff, and no ledger reconstructs the "
                "retired extract"
            ),
            "measuredBound": {
                "frameRows": "inputs.data/pipeline/04_platinum/unified_dataset.parquet.rows",
                "frameFirstMonth": measured_cutoff["frameFirstMonth"],
                "frameLastMonth": measured_cutoff["frameLastMonth"],
                "lastCompleteMonth": measured_cutoff["lastCompleteMonth"],
            },
        },
        {
            "id": "mrtImpactScopeProse",
            "asks": "a population/unit sentence the mrt-impact edition records in prose",
            "state": "absent-key",
            "reason": (
                "that ledger carries neither `scope` nor `definition`; its window is "
                "recorded at `studyWindow` and its unit at `responses"
                ".responseDefinition`, which this ledger cites instead of writing a "
                "sentence the source does not contain"
            ),
            "measuredBound": {"series": "mrt-impact", "scan": "seriesRegister.rows.mrt-impact"},
        },
        {
            "id": "dataSourcesLedgerRawBytes",
            "asks": "a ledger whose bytes on disk equal the hash its attestations pin",
            "state": "sentinel-string-free-mismatch",
            "reason": (
                "the RS01 ledger's raw bytes were reformatted after signature; its "
                "canonical re-serialisation still hashes to the pin. The mismatch is "
                "recorded with both hashes rather than waived, and no other row has "
                "one"
            ),
            "measuredBound": {
                "series": "data-sources",
                "row": "seriesRegister.rows.data-sources.ledger",
                "declared": "KNOWN_SERIALISATION_DRIFT",
            },
        },
        {
            "id": "personaContentPromises",
            "asks": (
                "the persona promises the app carries, which the register's row notes "
                "as still unsupported"
            ),
            "state": "not-measurable",
            "reason": (
                "the persona file's key concerns carry no quantitative token at all "
                "under the declared pattern, so there is no figure for an edition to "
                "link to; what it does carry is a recommended-reading list, recorded "
                "here with each slug's register status"
            ),
            "measuredBound": scans["personaContent"],
        },
    ]


def _scan_files() -> tuple[list[Path], dict[str, Any]]:
    paths: list[Path] = []
    excluded = {
        "prefixes": list(EXCLUDED_SCAN_PREFIXES),
        "editionPrefixExceptRetained": [EDITION_PREFIX, RETAINED_EDITION_PREFIX],
        "paths": list(EXCLUDED_SCAN_PATHS),
        "directoryComponents": list(EXCLUDED_DIR_COMPONENTS),
    }
    for root in SCAN_ROOTS:
        base = REPO_ROOT / root
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file() or path.suffix not in SCAN_SUFFIXES:
                continue
            parts = set(path.relative_to(REPO_ROOT).parts)
            if parts & set(EXCLUDED_DIR_COMPONENTS):
                continue
            relative = _relative(path)
            if any(relative.startswith(prefix) for prefix in EXCLUDED_SCAN_PREFIXES):
                continue
            if relative.startswith(EDITION_PREFIX) and not relative.startswith(
                RETAINED_EDITION_PREFIX
            ):
                continue
            if relative in EXCLUDED_SCAN_PATHS:
                continue
            paths.append(path)
    return sorted(paths), excluded


def absence_scans() -> dict[str, Any]:
    """Bounded scans for the artefacts a joint-model claim would need."""
    paths, excluded = _scan_files()
    matches: list[dict[str, Any]] = []
    for path in paths:
        for number, line in enumerate(_text_of(path).splitlines(), start=1):
            lowered = line.lower()
            if any(token in lowered for token in JOINT_MODEL_TOKENS):
                matches.append(
                    {"path": _relative(path), "line": number, "quote": line.strip()[:160]}
                )
    filename_matches = [
        _relative(path)
        for path in paths
        if any(token in path.name.lower() for token in JOINT_MODEL_FILENAME_TOKENS)
    ]
    return {
        "jointModel": {
            "question": (
                "does this checkout hold a joint or pooled model over the series "
                "that could carry a cross-study ranking?"
            ),
            "roots": list(SCAN_ROOTS),
            "suffixes": list(SCAN_SUFFIXES),
            "exclusions": excluded,
            "filesScanned": len(paths),
            "tokens": list(JOINT_MODEL_TOKENS),
            "filenameTokens": list(JOINT_MODEL_FILENAME_TOKENS),
            "matchCount": len(matches),
            "matches": matches[:MAX_MATCHES],
            "matchesTruncated": len(matches) > MAX_MATCHES,
            "filenameMatchCount": len(filename_matches),
            "filenameMatches": filename_matches[:MAX_MATCHES],
            "meaning": (
                "a bounded scan, not proof of universal absence: it reads the listed "
                "roots and suffixes, excludes the programme's own output surfaces as "
                "disclosed, and records every match it found. The planning/spec "
                "surface docs/plans/ is one of the excluded prefixes: the two "
                "matches this scan used to record were plan prose proposing a "
                "pooled model ('Run pooled model with interaction terms'), which "
                "is a plan, not a model in the checkout — excluding that surface "
                "is why matchCount is now zero, and it changes no disposition. "
                "The operational surface docs/guides/ (runbooks and setup/CI "
                "documentation about the programme) is excluded as a second "
                "disclosed prefix for the same reason: a guide that names a "
                "series is not an implementation of its method, because this "
                "scan establishes absence FROM CODE rather than absence from "
                "documentation. A "
                "screen is not a "
                "finding about origin, and an unlinked artefact adjudicates nothing"
            ),
        },
        "personaContent": _persona_scan(),
    }


def _persona_scan() -> dict[str, Any]:
    path = PERSONA_CONTENT
    payload = _load_json(path)
    numeric = re.compile(r"\d+(?:\.\d+)?\s*(?:%|x|×|percent)")
    tokens: list[str] = []
    recommended: list[dict[str, Any]] = []
    for persona in sorted(payload):
        block = payload[persona]
        tokens.extend(numeric.findall(json.dumps(block, ensure_ascii=False)))
        for doc in block.get("recommendedDocs", []):
            recommended.append(
                {"persona": persona, "slug": doc.get("slug"), "title": doc.get("title")}
            )
    return {
        "path": _relative(path),
        "sha256": sha256_of(path),
        "bytes": int(path.stat().st_size),
        "personas": sorted(payload),
        "quantitativePattern": r"\d+(?:\.\d+)?\s*(?:%|x|×|percent)",
        "quantitativeTokenCount": len(tokens),
        "quantitativeTokens": tokens[:MAX_MATCHES],
        "recommendedSlugs": recommended,
        "meaning": (
            "the persona file's concerns carry no quantitative token under the "
            "declared pattern; its recommended-reading slugs are resolved against "
            "the register at notMeasurable.personaContentPromises"
        ),
    }


def _sentinel_value_tally(rows: list[dict[str, Any]]) -> dict[str, int]:
    counted = Counter(str(row["value"]) for row in rows)
    return {value: counted[value] for value in sorted(counted)}


def _sentinel_ledger_tally(rows: list[dict[str, Any]]) -> dict[str, int]:
    counted = Counter(str(row["ledger"]) for row in rows)
    return {ledger: counted[ledger] for ledger in sorted(counted)}


def _sentinel_path_tally(rows: list[dict[str, Any]]) -> dict[str, int]:
    counted = Counter(str(row["fieldPath"]) for row in rows)
    return {path: counted[path] for path in sorted(counted)}


def _sentinel_sample(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"location": row["location"], "value": row["value"]} for row in rows]


def _sentinel_breakdown(
    wide: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    """The complete ledger-wide breakdown, by ledger and by field path."""
    by_ledger: dict[str, dict[str, Any]] = {}
    by_field_path: dict[str, dict[str, Any]] = {}
    for ledger, count in _sentinel_ledger_tally(wide).items():
        rows = [row for row in wide if row["ledger"] == ledger]
        by_ledger[ledger] = {
            "matchCount": count,
            "distinctValues": _sentinel_value_tally(rows),
            "fieldPathCount": len(_sentinel_path_tally(rows)),
            "fieldPaths": sorted(_sentinel_path_tally(rows)),
        }
    for field_path, count in _sentinel_path_tally(wide).items():
        rows = [row for row in wide if row["fieldPath"] == field_path]
        by_field_path[field_path] = {
            "matchCount": count,
            "values": _sentinel_value_tally(rows),
            "ledgers": sorted(_sentinel_ledger_tally(rows)),
        }
    return by_ledger, by_field_path


def sentinel_scan(paths: list[Path], sibling_set: dict[str, Any]) -> dict[str, Any]:
    """Do any of the fields this ledger reads carry a declared placeholder string?

    Two scopes, deliberately. `citedFields` is the bounded question: the fields
    this register actually reads are compared on their WHOLE value, so a
    placeholder in a field that feeds a row would be visible. `ledgerWide` is the
    disclosure: the same comparison over every string field of every sibling
    ledger.

    The sibling set is the register's own series list minus the self row — series
    membership, never signing status. A set filtered by "is signed" would gain this
    page's own ledger the moment the page is signed, which is exactly the drift this
    ledger exists to refuse. `sibling_set` states that rule and its members as
    fields, so a reader can check the set instead of inferring it.

    `ledgerWide` states its own shape instead of leaving a reader to generalise
    from a capped list. `matches` stays a short sample, and `matchesTruncated`
    says so; `matchCount`, `distinctValues`, `byLedger`, `byFieldPath` and
    `split` are complete over every match. `split` is the load-bearing part: it
    separates the one repeated register field (rs01's per-source acquisition
    status, declared in `SENTINEL_REGISTER_FIELD`) from every other placeholder,
    and enumerates the second class in full, by field path and by ledger. Neither
    scope is inferred from the other.
    """
    declared = {value.lower() for value in SENTINEL_STRINGS}
    cited: list[dict[str, Any]] = []
    cited_checked = 0
    wide: list[dict[str, Any]] = []
    wide_checked = 0

    def inspect(value: Any, location: str, into: list[dict[str, Any]]) -> None:
        if isinstance(value, str) and value.strip().lower() in declared:
            into.append({"location": location, "value": value})

    def walk(node: Any, location: str, ledger: str, field_path: str) -> None:
        nonlocal wide_checked
        if isinstance(node, dict):
            for key in sorted(node):
                walk(
                    node[key],
                    f"{location}.{key}",
                    ledger,
                    f"{field_path}.{key}" if field_path else key,
                )
        elif isinstance(node, list):
            for index, item in enumerate(node):
                walk(item, f"{location}[{index}]", ledger, f"{field_path}[{index}]")
        elif isinstance(node, str):
            wide_checked += 1
            if node.strip().lower() in declared:
                wide.append(
                    {
                        "ledger": ledger,
                        "fieldPath": INDEX_SUFFIX.sub("[]", field_path),
                        "value": node,
                        "location": location,
                    }
                )

    for path in paths:
        ledger = _load_json(path)
        walk(ledger, _relative(path), _relative(path), "")
        cited_fields: list[tuple[str, Any]] = [
            ("scope", ledger.get("scope")),
            ("definition", ledger.get("definition")),
            ("gate", ledger.get("gate")),
        ]
        cutoff_block = ledger.get("cutoff")
        if isinstance(cutoff_block, dict):
            cited_fields.append(("cutoff.lastCompleteMonth", cutoff_block.get("lastCompleteMonth")))
        claims = ledger.get("legacyClaims")
        if isinstance(claims, list):
            for index, item in enumerate(claims):
                if not isinstance(item, dict):
                    continue
                for key in ("id", "status", "disposition"):
                    cited_fields.append((f"legacyClaims[{index}].{key}", item.get(key)))
        for key, value in cited_fields:
            if isinstance(value, str):
                cited_checked += 1
                inspect(value, f"{_relative(path)}.{key}", cited)

    register_ledger = SENTINEL_REGISTER_FIELD["ledgerSuffix"]
    register_path = SENTINEL_REGISTER_FIELD["fieldPath"]
    register_matches = [
        match
        for match in wide
        if str(match["ledger"]).endswith(register_ledger) and match["fieldPath"] == register_path
    ]
    other_matches = [match for match in wide if match not in register_matches]
    status_field_rows = [row for row in other_matches if str(row["fieldPath"]).endswith(".status")]
    other_value_rows = [row for row in other_matches if row not in status_field_rows]
    by_ledger, by_field_path = _sentinel_breakdown(wide)

    return {
        "siblingSet": sibling_set,
        "declared": list(SENTINEL_STRINGS),
        "citedFields": {
            "fieldsCompared": [
                "scope",
                "definition",
                "gate",
                "cutoff.lastCompleteMonth",
                "legacyClaims[].id",
                "legacyClaims[].status",
                "legacyClaims[].disposition",
            ],
            "valuesCompared": cited_checked,
            "matchCount": len(cited),
            "matches": cited[:MAX_MATCHES],
        },
        "ledgerWide": {
            "stringValuesCompared": wide_checked,
            "matchCount": len(wide),
            "distinctValues": _sentinel_value_tally(wide),
            "distinctLedgerCount": len(by_ledger),
            "distinctFieldPathCount": len(by_field_path),
            "byLedger": by_ledger,
            "byFieldPath": by_field_path,
            "split": {
                "meaning": (
                    "the placement rule is declared in `registerField.declared` and "
                    "everything the rule does not capture is enumerated in full under "
                    "`otherFields`, so the split is checkable against `byFieldPath` "
                    "rather than taken on trust"
                ),
                "registerField": {
                    "declared": dict(SENTINEL_REGISTER_FIELD),
                    "matchCount": len(register_matches),
                    "ledgers": sorted(_sentinel_ledger_tally(register_matches)),
                    "fieldPaths": sorted(_sentinel_path_tally(register_matches)),
                    "values": _sentinel_value_tally(register_matches),
                    "meaning": (
                        "one ledger's own vocabulary for an acquisition source it did "
                        "not record, repeated once per source in a single field path; "
                        "this register reads no part of it as a measurement"
                    ),
                },
                "otherFields": {
                    "matchCount": len(other_matches),
                    "ledgers": _sentinel_ledger_tally(other_matches),
                    "fieldPaths": _sentinel_path_tally(other_matches),
                    "byPathShape": {
                        "statusField": {
                            "matchCount": len(status_field_rows),
                            "fieldPaths": _sentinel_path_tally(status_field_rows),
                            "values": _sentinel_value_tally(status_field_rows),
                            "meaning": (
                                "a study's own status field carrying the shared placeholder "
                                "vocabulary: the value means the item was not recorded FOR "
                                "THAT STUDY, not that it is absent everywhere"
                            ),
                        },
                        "otherValue": {
                            "matchCount": len(other_value_rows),
                            "matches": _sentinel_sample(other_value_rows),
                            "values": _sentinel_value_tally(other_value_rows),
                            "meaning": (
                                "the placeholder string is an ordinary value in a field that "
                                "is not a status: a `-` floor-level bucket, a "
                                "`correctionApplied` of none, and a quoted missing-name "
                                "literal, each read as the value it is"
                            ),
                        },
                    },
                    "matches": _sentinel_sample(other_matches),
                    "meaning": (
                        "complete: every ledger-wide match outside the declared register "
                        "field appears here, with its ledger and field path"
                    ),
                },
            },
            "matches": _sentinel_sample(wide[:SENTINEL_MATCH_CAP]),
            "matchesCappedAt": SENTINEL_MATCH_CAP,
            "matchesTruncated": len(wide) > SENTINEL_MATCH_CAP,
            "meaning": (
                "`matches` is a capped sample of the first "
                f"{SENTINEL_MATCH_CAP} matches, and `matchesTruncated` says whether "
                "it was cut; `matchCount`, `distinctValues`, `byLedger`, "
                "`byFieldPath` and `split` are complete over every match, so a "
                "sentence about the split must cite those and never this list"
            ),
        },
        "meaning": (
            "the sentinel-string state is measured on whole values, not by "
            "substring, and the two scopes are reported apart: a placeholder in a "
            "field this register cites would appear under citedFields, and the "
            "ledger-wide scan is a disclosure of the same test elsewhere, split by "
            "ledger and by field path. The scan's sibling set is the register's "
            "series list minus the page's own series, so adding a signature "
            "elsewhere can only change it by changing the register, and signing "
            "this page cannot change it at all"
        ),
    }


# --------------------------------------------------------------------------- #
# 4. The frozen findings text
# --------------------------------------------------------------------------- #


def legacy_claims() -> list[dict[str, Any]]:
    return [dict(claim) for claim in LEGACY_CLAIMS]


def legacy_quote_check(claims: list[dict[str, Any]]) -> dict[str, Any]:
    """Every quoted phrase must appear verbatim in the frozen findings text."""
    text = _text_of(LEGACY_FINDINGS)
    quotes = [
        {
            "id": claim["id"],
            "phrase": claim["phrase"],
            "occurrences": int(text.count(claim["phrase"])),
        }
        for claim in claims
    ]
    missing = [quote for quote in quotes if quote["occurrences"] == 0]
    if missing:
        raise SystemExit(
            "legacy phrases not found verbatim in the frozen findings text: "
            + ", ".join(quote["id"] for quote in missing)
        )
    return {
        "legacyFile": _relative(LEGACY_FINDINGS),
        "legacyFileSha256": sha256_of(LEGACY_FINDINGS),
        "claimsChecked": len(claims),
        "quotes": quotes,
        "allQuotesFound": True,
        "method": (
            "each phrase is required to appear verbatim in the frozen text; a "
            "paraphrase inside quotation marks is a defect, and an ellipsis is "
            "permitted only for a genuine omission"
        ),
    }


def _resolve_ledger_path(payload: dict[str, Any], dotted: str) -> bool:
    """Does a claim's `ledgerKey` resolve inside the ledger that quotes it?"""
    node: Any = payload
    for part in dotted.split("."):
        if isinstance(node, dict):
            if part not in node:
                return False
            node = node[part]
        elif isinstance(node, list):
            match = next(
                (item for item in node if isinstance(item, dict) and item.get("id") == part), None
            )
            if match is None:
                return False
            node = match
        else:
            return False
    return True


def check_claim_keys(payload: dict[str, Any], claims: list[dict[str, Any]]) -> dict[str, Any]:
    """Every claim's key must resolve, or the build fails."""
    unresolved = [
        {"id": claim["id"], "ledgerKey": claim["ledgerKey"]}
        for claim in claims
        if not _resolve_ledger_path(payload, claim["ledgerKey"])
    ]
    if unresolved:
        raise SystemExit(
            "unresolved legacyClaims ledgerKey(s): "
            + ", ".join(f"{item['id']} -> {item['ledgerKey']}" for item in unresolved)
        )
    return {
        "claimsChecked": len(claims),
        "unresolved": [],
        "method": (
            "each claim's ledgerKey is resolved against this ledger at build time by "
            "walking dict keys and list items by their `id`; an unresolved key fails "
            "the build rather than shipping"
        ),
    }


def cross_ledger_check(claims: list[dict[str, Any]], rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Every `referred-*` disposition must match the dependent edition's own record.

    A disposition that says another edition withdrew a figure is only evidence if
    that edition's ledger says so. This reads the dependent ledger's `legacyClaims`
    item by id and compares its status against the one this page recorded; a
    mismatch fails the build.
    """
    expected = {
        "re-measured": "referred-re-measured",
        "withdrawn": "referred-withdrawn",
        "not-reproducible": "referred-not-reproducible",
    }
    by_series = {row["id"]: row for row in rows}
    checks: list[dict[str, Any]] = []
    problems: list[str] = []
    for claim in claims:
        series = claim.get("dependentSeries")
        if series is None:
            continue
        dependent_id = claim.get("dependentClaimId")
        row = by_series.get(str(series))
        if row is None or row["ledger"]["path"] is None:
            problems.append(f"{claim['id']}: dependent series {series} carries no ledger")
            continue
        ledger = _load_json(REPO_ROOT / str(row["ledger"]["path"]))
        items = ledger.get("legacyClaims")
        if not isinstance(items, list):
            problems.append(f"{claim['id']}: {series} ledger carries no legacyClaims list")
            continue
        item = next(
            (
                entry
                for entry in items
                if isinstance(entry, dict) and entry.get("id") == dependent_id
            ),
            None,
        )
        if item is None:
            problems.append(f"{claim['id']}: {series} ledger has no claim id {dependent_id}")
            continue
        status_key = (
            "status" if "status" in item else ("disposition" if "disposition" in item else None)
        )
        if status_key is None:
            problems.append(f"{claim['id']}: {series} claim {dependent_id} carries no status")
            continue
        dependent_status = str(item[status_key])
        mapped = expected.get(dependent_status)
        checks.append(
            {
                "id": claim["id"],
                "dependentSeries": series,
                "dependentClaimId": dependent_id,
                "dependentStatusKey": status_key,
                "dependentStatus": dependent_status,
                "pageStatus": claim["status"],
                "matches": mapped == claim["status"],
            }
        )
        if mapped != claim["status"]:
            problems.append(
                f"{claim['id']}: {series}/{dependent_id} records {dependent_status!r}, which "
                f"maps to {mapped!r}, not the page's {claim['status']!r}"
            )
    if problems:
        raise SystemExit("cross-ledger disposition mismatch: " + "; ".join(problems))
    return {
        "checked": len(checks),
        "mismatched": 0,
        "checks": checks,
        "method": (
            "for every claim that names a dependent edition, that edition's own "
            "ledger is re-read at the named claim id and its recorded status is "
            "mapped to this page's status; a mismatch fails the build"
        ),
    }


# --------------------------------------------------------------------------- #
# 5. Assemble, verify, print
# --------------------------------------------------------------------------- #


def build() -> dict[str, Any]:
    frame = pd.read_parquet(UNIFIED, columns=["month", "property_type"])
    measured_cutoff = cutoff(frame)
    frame_sha = sha256_of(UNIFIED)
    registry = parse_registry()

    inputs: dict[str, Any] = {}
    inputs[FRAME_PATH] = {"sha256": frame_sha, "bytes": int(UNIFIED.stat().st_size)}
    inputs[FRAME_PATH]["rows"] = int(pq.ParquetFile(UNIFIED).metadata.num_rows)
    inputs[FRAME_PATH]["columns"] = int(len(pq.read_schema(UNIFIED).names))
    inputs[_relative(LEGACY_FINDINGS)] = {
        "sha256": sha256_of(LEGACY_FINDINGS),
        "bytes": int(LEGACY_FINDINGS.stat().st_size),
    }
    inputs[_relative(PERSONA_CONTENT)] = {
        "sha256": sha256_of(PERSONA_CONTENT),
        "bytes": int(PERSONA_CONTENT.stat().st_size),
    }

    measured_register = register(registry, frame_sha, inputs)
    rows = measured_register["rows"]
    scans = absence_scans()
    # The sibling set is defined by the register's own series list, never by
    # signing status: a set built from "rows that are signed" would gain this
    # page's own ledger at the moment the page is signed.
    siblings = [row for row in rows if not row["self"]]
    sibling_set = {
        "rule": (
            "the register's series list minus the page's own series, then each "
            "sibling's signed ledger; series membership, not signing status, so "
            "this page's own signature cannot change the set"
        ),
        "series": [row["id"] for row in siblings],
        "seriesCount": len(siblings),
        "excludedSelfSeries": [row["id"] for row in rows if row["self"]],
        "ledgersScanned": 0,
        "siblingsWithoutPinnedLedger": [
            row["id"] for row in siblings if row["ledger"]["path"] is None
        ],
    }
    scan_paths = sorted(
        {REPO_ROOT / str(row["ledger"]["path"]) for row in siblings if row["ledger"]["path"]}
    )
    sibling_set["ledgersScanned"] = len(scan_paths)

    claims = legacy_claims()
    payload: dict[str, Any] = {
        "schemaVersion": SCHEMA_VERSION,
        "study": "RS15",
        "series": "findings",
        "scope": (
            "RS15 findings evidence: the register of the fifteen RF08 series as the "
            "app registry records it and as the files on disk measure it, the "
            "dependency graph of the summary page with its blocked list derived, what "
            "this checkout cannot supply, and the disposition of every quantitative "
            "sentence of the frozen findings text against the edition that owns it"
        ),
        "definition": DEFINITION,
        "gate": GATE,
        "inputs": {key: inputs[key] for key in sorted(inputs)},
        "registryReadRule": REGISTRY_READ_RULE,
        "cutoff": measured_cutoff,
        "seriesRegister": measured_register,
        "dependencies": dependencies(rows),
        "notMeasurable": not_measurable(rows, measured_cutoff, scans),
        "absenceScans": scans,
        "sentinelScan": sentinel_scan(scan_paths, sibling_set),
        "missingnessStates": {
            "states": MISSINGNESS_STATES,
            "meaning": (
                "the states are kept apart everywhere in this ledger: a null pin is "
                "not an absent block, an absent block is not zero claims, an empty "
                "attestation list is not a missing one, and a placeholder string is "
                "not a value"
            ),
        },
        "claimStatuses": CLAIM_STATUSES,
        "legacyClaims": claims,
    }
    payload["legacyQuoteCheck"] = legacy_quote_check(claims)
    payload["claimKeyCheck"] = check_claim_keys(payload, claims)
    payload["crossLedgerCheck"] = cross_ledger_check(claims, rows)
    return payload


def _top_level_drift(old: dict[str, Any], new: dict[str, Any]) -> list[str]:
    return [key for key in sorted(set(old) | set(new)) if old.get(key) != new.get(key)]


def check(output: Path) -> int:
    if not output.is_file():
        print(f"FAILED: no ledger at {output}; run the tool without --check first")
        return 1
    recorded = output.read_bytes()
    measured = canonical_bytes(build())
    if recorded == measured:
        print("Pass: RS15 ledger re-measures byte-identically from this checkout.")
        print(f"Ledger sha256: {hashlib.sha256(measured).hexdigest()}")
        return 0
    try:
        old = json.loads(recorded)
        new = json.loads(measured)
    except json.JSONDecodeError:
        print("FAILED: ledger bytes differ and are not both valid JSON")
        return 1
    for key in _top_level_drift(old, new):
        print(f"  - drift in {key}")
    print("FAILED: RS15 ledger does not match this checkout")
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    if args.check:
        return check(args.output)

    evidence = build()
    payload = canonical_bytes(evidence)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(payload)

    register_payload = evidence["seriesRegister"]
    summary = register_payload["summary"]
    print(
        f"Register: {summary['seriesCount']} series, {summary['signedCount']} signed, "
        f"unsigned {summary['unsignedSeries']}"
    )
    print(
        "Text pins: "
        f"{summary['textPinChecks']['matched']}/{summary['textPinChecks']['checked']} match; "
        "ledger pins: "
        f"{summary['ledgerPinChecks']['contentMatched']}/{summary['ledgerPinChecks']['checked']} "
        f"content match, raw {summary['ledgerPinChecks']['rawMatched']}/"
        f"{summary['ledgerPinChecks']['checked']}"
    )
    for row in register_payload["rows"]:
        split = row["claimDispositions"]
        split_text = (
            ", ".join(f"{key}={value}" for key, value in split["byValue"].items())
            if split["state"] == "measured" and split["byValue"]
            else split["state"]
        )
        if row["self"]:
            print(
                f"  {row['id']:<26} {'self':<10} "
                f"legacy={row['legacyEdition']['editionId']} "
                f"legacy-sha={row['editionFile']['sha256'][:12]}"
            )
            continue
        print(
            f"  {row['id']:<26} {row['currentEdition']['evidenceStatus']:<10} "
            f"text-pin={'n/a' if row['editionFile']['matchesPin'] is None else row['editionFile']['matchesPin']} "
            f"ledger-raw={row['ledger']['rawMatchesPin']} "
            f"ledger-content={row['ledger']['contentMatchesPin']} "
            f"window={row['ledgerCutoff']['lastCompleteMonth']} "
            f"claims[{split_text}]"
        )
    print(f"Blocked dependencies: {evidence['dependencies']['blocked']}")
    print(
        f"Legacy claims: {evidence['legacyQuoteCheck']['claimsChecked']} verbatim, "
        f"cross-ledger checked {evidence['crossLedgerCheck']['checked']}"
    )
    print(
        f"Sentinel-string matches (cited fields): {evidence['sentinelScan']['citedFields']['matchCount']}"
    )
    print(f"Ledger bytes: {len(payload)}")
    print(f"Ledger sha256: {hashlib.sha256(payload).hexdigest()}")
    try:
        label = args.output.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        label = str(args.output)
    print(f"Ledger: {label}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
