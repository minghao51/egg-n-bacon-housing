# Discovery Inventory — Master Audit Phase 1 (observational)

HEAD `449b921d499a8c55ec1eacb1a423baa7632456d3`. Read-only measurement. No severity, no findings, no judgment — counts and artifact references only.

## 1. Snapshot and scope

| Item                                              | Value                                                                                                                                                                                                             |
| ------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- | --------- | ----- | ---- | ----------------------------------------------------------------------------------------- |
| Canonical scope                                   | fixed git-tracked snapshot at HEAD (`git ls-files`); content read from a **`git archive HEAD` snapshot**, never the worktree                                                                                      |
| Files in scope                                    | **820**                                                                                                                                                                                                           |
| Self-excluded audit artifacts                     | 31 files under `docs/plans/master-audit-2026-11-23/` at run time (count grows as workers write; never counted)                                                                                                    |
| Revision verification                             | `git rev-parse HEAD` = pinned sha; `git status --porcelain --untracked-files=no` empty (tracked worktree clean); snapshot 820 files / 38,292,684 bytes                                                            |
| Supplemental untracked (non-ignored, not counted) | 0 at snapshot time                                                                                                                                                                                                |
| Excluded by design (ignored, never read)          | `.git`, `.env`/`.env.keys`, `node_modules`, `app/node_modules`, `.venv`, `__pycache__`, `.pytest_cache`, `.ruff_cache`, `.mypy_cache`, `.hypothesis`, `build/`, `dist/`, `app/dist`, `app/.astro`, `data/pipeline | analysis | forecasts | cache | logs | manual`, `htmlcov/`, `coverage.xml`, `playwright-report/`, `test-results/`, `.worktrees/` |

No tracked vendored source tree exists. `data/raw/external/datagov/*.geojson` are downloaded upstream datasets (data category). Reproducible from the pinned HEAD via `evidence/measurement/` (`measure.py` → `indexes.py`), which refuse to count their own output.

## 2. Category census (820 files)

| Category                                                                                                                                                                                                                             | Files |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----- |
| docs:evidence-and-plans                                                                                                                                                                                                              | 270   |
| web:source                                                                                                                                                                                                                           | 156   |
| artifact:published-web-data                                                                                                                                                                                                          | 88    |
| web:test                                                                                                                                                                                                                             | 65    |
| python:test                                                                                                                                                                                                                          | 49    |
| python:source                                                                                                                                                                                                                        | 48    |
| design-asset                                                                                                                                                                                                                         | 34    |
| docs:agent-context                                                                                                                                                                                                                   | 32    |
| python:script                                                                                                                                                                                                                        | 30    |
| data:tracked-input                                                                                                                                                                                                                   | 12    |
| web:config 8 · notebook 6 · docs:root 5 · web:script 4 · config:repo 3 · ci:workflow 2 · docs:web 2 · config:python-manifest 2 · config:env-template 1 · config:secret-scan-baseline 1 · python:entrypoint 1 · config:web-manifest 1 | 45    |

## 3. Source size and test ratio

350 source files measured (Python 128, web ts/tsx/mjs/astro 221, CSS 1); 6 notebooks measured separately.

| Area                 | Files   | Physical lines | Code lines      |
| -------------------- | ------- | -------------- | --------------- |
| Python `src/`        | 48      | 10,248         | 8,181           |
| Python `tests/`      | 49      | 20,277         | 15,830          |
| Python `scripts/`    | 30      | 33,699         | 30,404          |
| Python `main.py`     | 1       | 109            | 88              |
| Web `app/src`        | 153     | 33,485         | 27,607          |
| Web `app/tests`      | 61      | 15,889         | 13,124          |
| Web `app/scripts`    | 4       | 891            | 758             |
| CSS                  | 1       | 266            | 232             |
| **Total**            | **350** | **115,034**    | **96,376**      |
| Notebooks (separate) | 6       | 4,704 raw      | 1,091 code-cell |

Test:source — Python **1.94x** by code lines (1.02x by files); web **0.48x** by code lines (0.40x by files).

## 4. Top-level modules (code lines)

Python: `scripts/tools` 27,200 (24 files) · `tests` 15,830 (49) · `components` 3,356 (14) · `utils` 3,299 (21) · `scripts` 3,204 (6) · `adapters` 803 (6) · `schemas` 292 (4) · package root 431 (3) · `main.py` 88 (1).
Web: `components` 17,411 (86) · `tests/unit` 9,068 (35) · `utils` 6,419 (29) · `tests/e2e` 4,056 (26) · `pages` 2,168 (19) · `types` 720 (5) · `app/scripts` 758 (4) · `hooks` 662 (8) · `constants` 145 (3) · layouts/config/root 166.

## 5. Size concentration

**116 files >300 lines, of which 62 are >500 lines** (54 in the 300–500 band). `size_flag` in `complexity.csv` uses mutually exclusive buckets — `>500` supersedes `>300` — so the >300 total is 62 + 54 = 116, not the `>300`-only flag count.

Independently recomputed two ways: (a) direct count over the `lines` column of `complexity.csv`; (b) line counts of the same 350 files read from pinned blobs via `git cat-file --batch` (`HEAD:<path>`) — **116 / 62 both ways, 0 of 350 files mismatched** against the CSV.

Largest: `scripts/tools/school_quality_evidence.py` 2,846 · `lease_decay_evidence.py` 2,681 · `findings_evidence.py` 2,630 · `price_forecasts_evidence.py` 2,529 · `market_segments_evidence.py` 2,360 · `mrt_impact_evidence.py` 2,071 · `tests/test_ingestion.py` 2,026. Per-file rows in `complexity.csv` (with `size_flag`).

## 6. Parse reliability

0 parse failures across 350 files (Python `ast` on 3.12; TS via repo `typescript@5.9.3`). `.astro` = frontmatter AST + unanalyzed template (labelled per row). 6 notebooks are not Python-parseable as whole files; measured separately by cell. `max_nesting_estimate` = block nesting depth, **not** cyclomatic complexity.

## 7. Test/coverage report freshness

| Artifact                                                 | Generated (UTC)      | lines-valid | covered   | missed | line-rate (header) |
| -------------------------------------------------------- | -------------------- | ----------- | --------- | ------ | ------------------ |
| `coverage.xml` (stale worktree artifact, git-ignored)    | 2026-11-22T10:54:45Z | 4,076       | **96**    | 3,980  | **0.02355**        |
| `/tmp/master-audit-coverage.xml` (fresh audit execution) | 2026-11-23T04:10:26Z | 4,076       | **3,894** | 182    | **0.9553**         |

Both headers quoted verbatim; recomputed rates match declared rates. 48 files/classes in each. `htmlcov/` present. These are two runs of the same suite, not two readings of one file.

## 8. Manifests

`pyproject.toml`, `uv.lock`, `package.json`, `app/package.json`, `app/bun.lock`, `app/tsconfig.json`, `app/astro.config.mjs`, `app/tailwind.config.mjs`, `app/playwright.config.ts`, `.pre-commit-config.yaml`, `.github/workflows/{ci,deploy}.yml`, `.secrets.baseline`, `.env.example`, `.bun-version`, `app/.bun-version`, `.gitignore`, `app/.gitignore`, `data/catalog/descriptions.yml`. Top Python external imports by file count: pandas 86, pytest 49, numpy 26, hamilton 15, pyarrow 15, pydantic 15, requests 14.

## 9. Generated indexes (mechanical, exhaustive, **unreviewed**)

| Artifact                                                        | Rows  | Coverage                |
| --------------------------------------------------------------- | ----- | ----------------------- |
| `complexity.csv`                                                | 350   | all source files        |
| `public-entrypoints.csv`                                        | 2,596 | 272 files               |
| `error-surfaces.csv`                                            | 596   | 117 files               |
| `observability.csv`                                             | 349   | all source files        |
| `schema-declarations.csv`                                       | 432   | 106 files               |
| `complexity-notebooks.csv`                                      | 6     | notebooks               |
| `full-file-tree.txt`, `inventory.json`, `raw-measurements.json` | —     | scope + per-file detail |

Harness lives in `measurement/` (`measure.py` → `indexes.py`, plus `ts_measure.mjs`). It is portable: repo root from `git rev-parse --show-toplevel`, sibling-relative script lookup, no absolute paths, and all measured content comes from the pinned `git archive HEAD` snapshot, so a dirty worktree cannot change the numbers. Re-running it reproduced the five metric CSVs byte-identically (`sha256sum -c`), changing only provenance fields in `inventory.json` / `full-file-tree.txt`.

Entrypoints by kind: method 927, function 901, class 260, interface 174, const 138, type-alias 115, cli-main-guard 31, async-function 19, route 19, re-export 8, default-export 3, star-re-export 1.
Error surfaces: raise 217, throw 168, except 128, catch 56, sys.exit 26, process.exit 1.
Observability: print 277, logger 292, `logging.*` 0, console 33; 273 of 349 files have zero logging calls.
Schemas: interface 263, type-alias 131, pydantic-model 21, dataclass 6, pydantic-settings 5, protocol 3, namedtuple 1, typeddict 1, zod-object 1.

## 10. Dead-code candidates — UNCONFIRMED

Identifier grep: symbol defined in `src/` or `app/src/` with zero textual references elsewhere. Python 25, web 207. NOT proof of dead code (dynamic dispatch, registry/framework hooks, string refs, re-exports unresolved). List in `inventory.json`.

## 11. Method limitations

Static-analysis notes on the harness itself (reported, deliberately not silenced): semgrep flags `tarfile.extractall` on the `git archive` stream and ast-grep flags two unguarded `read_text`/`json.loads` calls. Both are fail-fast by design — the snapshot is produced from the pinned commit of this same repository (with `filter="data"`), and a missing or malformed input should abort the measurement rather than be swallowed. No suppression comments were added.

Rows are automated scans, not reviewed judgement. Nesting ≠ complexity. Web comment/line classification is lexical (template-literal text can be miscounted). `.astro` template markup and Astro component-script escapes are not analyzed; only frontmatter. Signatures are reconstructed and approximate (defaults/annotations clipped). No dynamic binding analysis, no runtime execution of application code. Absence of a row is not proof of absence of behaviour.
