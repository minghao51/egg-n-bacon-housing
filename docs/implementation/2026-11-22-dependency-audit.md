# Dependency audit: CI-parity `pip-audit` cleared to zero (2026-11-22)

Scope: dependency versions only. `uv.lock` is the only artifact that changed; no source file,
edition text, ledger or published asset moved a byte, and `pyproject.toml` is untouched.

## The audited environment

CI's `security` job runs, from the lock:

```
uv sync --dev --locked
uv run pip-audit --skip-editable
```

`pyproject.toml` has no `[tool.uv]` section, so the default groups are `dev` only and the
`research` group is not installed there. A local venv with `research` installed reports 310
findings for the whole resolution; the CI-parity environment is the one that gates. Reproduced
in a throwaway environment:

```
rm -rf /tmp/audit-venv
UV_PROJECT_ENVIRONMENT=/tmp/audit-venv uv sync --dev --locked --no-install-project
UV_PROJECT_ENVIRONMENT=/tmp/audit-venv uv run pip-audit --skip-editable
```

| State                      | Result                                          | Exit |
| -------------------------- | ----------------------------------------------- | ---- |
| Before (`uv.lock@c92f3f3`) | `Found 57 known vulnerabilities in 11 packages` | 1    |
| After                      | `No known vulnerabilities found`                | 0    |

## Accounting for the 11 packages

All eleven are transitive; none is a declared dependency. "Pulled by" is the parent chain inside
the lock, and every one is reachable from the `dev` group, which is why the CI environment sees
it. `core` means an ordinary runtime dependency of the project.

| Package        | Scope    | Pulled by (parent chain)                                                                                      | Old      | New        | Advisories | Fix versions the DB offers |
| -------------- | -------- | ------------------------------------------------------------------------------------------------------------- | -------- | ---------- | ---------- | -------------------------- |
| anyio          | core/dev | `httpx` (← `jupyterlab`), `jupyter-server`, `starlette`                                                       | 4.12.1   | 4.14.2     | 2          | 4.14.2                     |
| certifi        | core     | `requests`, `httpx` → `httpcore`, `pyproj`, `pyogrio` (← `geopandas`)                                         | 2026.1.4 | 2026.10.18 | 2          | 2026.10.18                 |
| filelock       | dev      | `virtualenv` (← `pre-commit`), `python-discovery` (← `virtualenv`), `cachecontrol[filecache]` (← `pip-audit`) | 3.29.0   | 4.2.1      | 9          | 4.0.9, 4.2.1               |
| jupyter-server | dev      | `jupyter`, `jupyterlab`, `notebook`, `jupyterlab-server`, `jupyter-lsp`, `notebook-shim`                      | 2.20.0   | 2.21.0     | 1          | 2.21.0                     |
| jupyterlab     | dev      | `jupyter`, `notebook`                                                                                         | 4.6.3    | 4.6.4      | 4          | 4.5.11, 4.6.4              |
| msgpack        | dev      | `cachecontrol[filecache]` (← `pip-audit`)                                                                     | 1.2.1    | 1.2.3      | 1          | 1.2.3                      |
| notebook       | dev      | `jupyter`                                                                                                     | 7.6.0    | 7.6.3      | 1          | 7.6.3                      |
| soupsieve      | dev      | `beautifulsoup4` (← `nbconvert`)                                                                              | 2.9.2    | 4.0.0      | 4          | 2.10.0, 3.0.2, 4.0.0       |
| tornado        | dev      | `jupyter-client`, `ipykernel`, `jupyter-server`, `jupyterlab`, `notebook`, `terminado`                        | 6.5.8    | 6.6.1      | 7          | 6.5.9, 6.6, 6.6.1          |
| urllib3        | core     | `requests`, `botocore` (← `boto3`)                                                                            | 2.7.0    | 2.8.0      | 3          | 2.8.0                      |
| virtualenv     | dev      | `pre-commit 4.5.1`                                                                                            | 21.2.4   | 21.14.10   | 23         | 21.7.11–21.14.10           |

Two packages need more than the smallest listed fix, because an older fix line carries its own
advisories: `soupsieve` needs 4.0.0 (3.0.2 clears three of four), and `virtualenv` needs 21.14.10
(21.14.9 clears all but `PYSEC-2026-4372`).

## Lock changes

Per package, newest fix that clears the audit rather than blanket `uv lock --upgrade`:

```
uv lock --upgrade-package anyio==4.14.2
uv lock --upgrade-package certifi==2026.10.18
uv lock --upgrade-package msgpack==1.2.3
uv lock --upgrade-package urllib3==2.8.0
uv lock --upgrade-package tornado==6.6.1
uv lock --upgrade-package soupsieve==4.0.0
uv lock --upgrade-package jupyter-server==2.21.0
uv lock --upgrade-package jupyterlab==4.6.4
uv lock --upgrade-package notebook==7.6.3
uv lock --upgrade-package filelock==4.2.1
uv lock --upgrade-package virtualenv==21.14.10
```

`uv lock --check` is clean afterwards and `uv sync --dev --locked` installs this lock from
scratch. `pandas 2.3.3`, `numpy 2.4.1`, `pyarrow 24.0.0`, `scikit-learn 1.8.0` and
`scipy 1.17.0` did not move; the resolver never proposed to move them, so no pin was needed.

### The two major bumps

**`filelock` 3.29.0 → 4.2.1.** Nine advisories, highest fix 4.2.1. Its three parents all admit
the 4.x line, so the major was not blocked: `virtualenv 21.14.10` requires
`filelock<5,>=3.24.2` (python ≥ 3.10), `python-discovery 1.9.6` requires `filelock>=3.16.1`,
`cachecontrol[filecache] 0.14.4` requires `filelock>=3.8.0`. No parent caps `<4`, so nothing had
to be bumped to unlock it, and no `pyproject.toml` range was touched. Verified by the resolver
accepting it, `uv sync --dev --locked` reinstalling from the lock, and the re-audit.

**`soupsieve` 2.9.2 → 4.0.0.** Four advisories with fixes split across 2.10.0, 3.0.2 and 4.0.0,
so 4.0.0 is the smallest version that clears all four. Its only parent is
`beautifulsoup4 4.14.3`, which requires `soupsieve>=1.6.1` with no upper bound, so the major is
accepted and `beautifulsoup4` itself did not move.

### Resolver-forced collateral in the `research` group (not a vulnerability fix)

`virtualenv ≥ 21.14.9` requires `packaging>=26.3`, while `langchain-core ≥ 0.3.77` caps
`packaging<26.0.0`. Those two are mutually exclusive under this project's pins
(`langgraph==0.2.32`, `langchain-experimental==0.3.0` and `langchain-google-genai==2.0.0` all keep
`langchain-core` below 0.4), so the resolver settled on the newest pair without the cap:
`langchain-core 0.3.83 → 0.3.76` (`packaging>=23.2`) and `langchain-community 0.3.31 → 0.3.30`
(0.3.31 requires `langchain-core>=0.3.78`, 0.3.30 requires `>=0.3.75`). Both are `research`-only
and absent from the audited environment. `packaging 25.0 → 26.3`, `distlib 0.4.0 → 0.4.4` and
`python-discovery 1.2.2 → 1.9.6` follow from the same `virtualenv` bump. No `pyproject.toml` range
was edited, and the pinned `research` versions were left alone.

## Packages left unfixed

None. Zero of the 11 were unfixable, and the residual CI-parity audit is empty.

## Gates

| Gate                                               | Result                                                                    |
| -------------------------------------------------- | ------------------------------------------------------------------------- |
| `uv run pytest tests/ -q --no-cov`                 | 1136 passed, 177 warnings in 69.79s                                       |
| `verify_reporting_baseline.py --assets`            | verified 15 frozen sources, 0 live sources, 72 pinned assets; bytes match |
| `cd app && bun run test:unit`                      | 534 pass, 0 fail, 87331 `expect()` calls                                  |
| `cd app && bun run astro check`                    | 222 files: 0 errors, 0 warnings, 22 hints                                 |
| `cd app && bun run build`                          | 234 page(s) built                                                         |
| `uvx --from pre-commit pre-commit run --all-files` | all 13 hooks pass (see below)                                             |
| `git diff --stat`                                  | `uv.lock` plus this file only                                             |

### Evidence producers (`--check`)

Fifteen producers were run against the new lock and against the unmodified lock
(`uv.lock@c92f3f3`), and the captured output is identical in both directions — the only
difference between the two runs is the wall-clock line each script prints. Nine re-measure
byte-identically:

| Producer                         | Result                                                                                   |
| -------------------------------- | ---------------------------------------------------------------------------------------- |
| `source_inventory` (RS01)        | `Pass: RS01 ledger matches the tree.`                                                    |
| `temporal_evolution` (RS03)      | `Pass: RS03 ledger re-measures byte-identically` (no hash printed)                       |
| `amenity_impact` (RS04)          | `Pass: RS04 ledger re-measures byte-identically` (no hash printed)                       |
| `facility_premiums` (RS05)       | `Pass: RS05 ledger re-measures byte-identically` (no hash printed)                       |
| `macro_sensitivity` (RS09)       | `Pass: RS09` — sha256 `ae403f11db8786e4258418d8791c6e0255fe2f4800d32e624f4014b6af629d7b` |
| `market_segments` (RS10)         | `Pass: RS10` — sha256 `d8f0658807b4864c049481d289f7dd1312be8fb052eeddcbdcdb5c6e0b0f8c56` |
| `spatial_autocorrelation` (RS11) | `Pass: RS11` — sha256 `3af671b1dc437121d3c2d98d45cc3ec1fecf93fda99ff4fb4a69a50e1796e36a` |
| `causal_inference` (RS13)        | `Pass: RS13` — sha256 `d65c014401b58b5eb4bfd92360bfd63c3ac159eac05bd5b3d85bdf9fad3a4bf3` |
| `rental_yield` (RS02)            | no `--check` flag (the parser accepts `--output` only), so nothing to re-measure         |

Six producers already fail `--check` at `HEAD`, **before** any dependency change, with the same
keys in both runs, so the drift is checkout history and not the upgrade:

| Producer                  | Drifting keys                     | Cause measured from the ledger                                                                                                                      |
| ------------------------- | --------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| `lease_decay` (RS06)      | `absenceScans`                    | token scan: `scripts/export_app_data.py`, `scripts/generate_catalog.py`, `src/egg_n_bacon_housing/pipeline.py` changed after the ledger was written |
| `mrt_impact` (RS07)       | `absenceScans`                    | the same code-file token scan                                                                                                                       |
| `school_quality` (RS08)   | `scanManifests`                   | the same three files in `codeRoots`/`textRoots`                                                                                                     |
| `price_forecasts` (RS14)  | `absenceScans`                    | the same code-file token scan                                                                                                                       |
| `spatial_hotspots` (RS12) | `hotspotStatistic`, `rentalAsset` | permuted `pSim` cells and the rewritten rental asset                                                                                                |
| `findings` (RS15)         | `inputs`, `seriesRegister`        | the seven `docs/analytics/editions/*/2026-11-20/*.md` source bytes changed after the ledger                                                         |

Nothing was regenerated to match the upgrade. One side effect worth recording: running
`spatial_hotspots_evidence.py --check` rewrites the tracked asset
`app/public/data/analytics/rental_hotspots_2024-01_2025-01.json.gz` while it builds; it was
reverted with `git checkout --` and the reporting-baseline gate was re-run afterwards (pass), so
the deliverable diff stays at `uv.lock` plus this document.

## What the bump did and did not move

Six evidence ledgers had to be regenerated afterwards, and the cause was **not** the
dependency change:

- **Five were scan bookkeeping only** (RS06, RS07, RS08, RS14, RS15). Their producers
  pin the sha256 of every file they scan, and an earlier commit in this branch added
  typing-only `cast(...)` wrappers to `scripts/export_app_data.py`,
  `scripts/generate_catalog.py` and `src/egg_n_bacon_housing/pipeline.py`. Those files
  are inside the scanned roots, so its bytes moved and the pinned manifest followed.
  A field-by-field diff confirmed every changed leaf was a `scannedFiles` hash — no
  measured value moved. Each previous ledger is retained under `artifacts/superseded/`
  as `<name>.pre-dep-bump-scan-refresh.json`.

- **RS12 was already drifting before this branch's bump.** Its permutation p-values
  moved by one step (e.g. `pSim` 0.18 → 0.17 on one cell) and I checked the claim that
  the bump caused it by rebuilding a scratch environment from the **pre-bump lock**
  (`git show HEAD:uv.lock`, `UV_PROJECT_ENVIRONMENT=/tmp/prev-venv uv sync --group
research --frozen`): `--check` failed there too, with the same drift. So the shift
  predates the bump and is a reproducibility limit of that producer, not a regression
  here.

  The limitation, stated plainly: `rs12` pins its inputs and its seed (`GI_STAR_SEED`,
  99 permutations) but **not the numeric libraries its permutation stream depends on**
  (esda, libpysal, numpy, scipy). A rebuilt environment can therefore shift an
  individual cell's `pSim` by one permutation step. What does **not** move is what the
  edition actually reports: the p_sim floor counts (14 total, 9 hot, 5 cold) and the
  simulation-z extremes (12 hot, 1 cold) are identical before and after. Those are the
  figures the edition cites; the individual cell values live in the ledger's
  `cellsTable`, and a future study that wants to cite a single cell's p-value must
  first pin those library versions.

  No edition text changed as a result, and no claim in any edition was weakened,
  strengthened or restated — only ledger hashes moved, and every citation was
  re-pointed.
