Agent: f11fc084-54d8-49e
Type: Agent | Status: aborted (aborted — hit the turn limit before completion; output may be incomplete) | Tool uses: 547 | 136.2k token | Context: 27% | Duration: 577.6s
Model: openai-codex/gpt-6.1-sol, thinking: high
Description: Inventory dependencies and supply chain

## Scope and evidence

- Verified `HEAD = 449b921d499a8c55ec1eacb1a423baa7632456d3` using `git rev-parse HEAD`.
- Read all three tracked package manifests: `package.json`, `app/package.json`, `pyproject.toml`; both locks; both workflows; pre-commit configuration; Bun version files. `git ls-files` found no additional tracked requirements/Pipfile/setup/Docker dependency manifests.
- Root `package.json:1–6` declares **no dependencies**.
- No repository files changed. Raw network evidence is saved:
  - `/tmp/dependency-discovery-449b921-registry.jsonl`
  - `/tmp/dependency-discovery-449b921-pip-audit.txt`
  - `/tmp/dependency-discovery-449b921-bun-audit.txt`

**Provenance abbreviations**

- **P** = `pyproject.toml`; **U** = `uv.lock`; **A** = `app/package.json`; **B** = `app/bun.lock`.
- **S/** = `src/egg_n_bacon_housing/`; **E/** = `scripts/tools/`; **C/** = `app/src/components/`.
- **R** = live registry queries, **2026-11-23 04:08 UTC**: PyPI `/pypi/{name}/json` and locked-version endpoints; npm `/{package}` → `dist-tags.latest`. Results saved above. “Latest” is registry-reported, **not** a compatibility recommendation.
- **N** = no executable import or corresponding CLI/config reference found in tracked-source scans; **not proof of unusedness**. Python AST scan included every tracked `.py` and notebook code cell, with zero parse failures. Additional token scans covered 626 tracked text files, excluding manifests, locks, generated data/evidence and the previous dependency-audit document.
- Substitute column: **—** = no straightforward builtin/small equivalent identified; **?** = usage insufficient to assess; named alternatives indicate **limited plausibility only**, not removal recommendations.

## Complete Python direct-dependency table

Constraint declarations are cited individually; locked-version citations identify package records. Every “Latest” value comes from **R**.

### Runtime and optional tracking

| Dependency; declaration                  | Constraint    | Locked; evidence | Latest | Actual usage/evidence                                                             | Substitute plausibility                                                     |
| ---------------------------------------- | ------------- | ---------------- | ------ | --------------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| pandas P:8                               | `>=2.0.0`     | 2.3.3 U:3513     | 3.1.1  | DataFrames throughout; S/adapters/datagovsg.py:16                                 | —                                                                           |
| pyarrow P:9                              | `>=15.0.0`    | 24.0.0 U:4094    | 26.0.1 | Parquet inspection; scripts/generate_catalog.py:178                               | —                                                                           |
| numpy P:10                               | `>=1.24.0`    | 2.4.1 U:3372     | 2.5.5  | Numeric features; S/components/feature_rental.py:6                                | —                                                                           |
| scikit-learn P:11                        | unconstrained | 1.8.0 U:5050     | 1.9.1  | `BallTree`; S/utils/proximity.py:13                                               | SciPy trees potentially, but spherical-distance semantics differ            |
| pydantic P:12                            | `>=2.0`       | 2.12.5 U:4167    | 2.14.4 | Settings/schema validation; S/config.py:7                                         | —                                                                           |
| pydantic-settings P:13                   | `>=2.0`       | 2.14.2 U:4253    | 2.16.3 | `BaseSettings`; S/config.py:8                                                     | `os.environ` only with lost parsing/validation features                     |
| pyyaml P:14                              | `>=6.0`       | 6.0.3 U:4654     | 6.0.4  | Catalog YAML; scripts/generate_catalog.py:18                                      | No builtin YAML parser                                                      |
| geopandas P:15                           | unconstrained | 1.1.2 U:1336     | 1.2.0  | Vectorized spatial join; S/utils/data_loader.py:85                                | Shapely-only implementation possible, not equivalent simplicity/performance |
| requests P:16                            | unconstrained | 2.34.2 U:4846    | 2.34.2 | HTTP adapters; S/adapters/\_http.py:23                                            | `urllib.request`, with transport-behavior work                              |
| boto3 P:17                               | unconstrained | 1.42.30 U:377    | 1.44.9 | R2/S3 synchronization; scripts/00_sync_data.py:29                                 | —                                                                           |
| rapidfuzz P:18                           | `>=3.14.3`    | 3.14.3 U:4755    | 3.14.6 | N; historical claim at docs/archive/20260122-geocoding-enhancement-complete.md:51 | `difflib` for limited fuzzy matching                                        |
| scipy P:19                               | `>=1.17.0`    | 1.17.0 U:5094    | 1.18.1 | `cKDTree`; S/utils/school_features.py:12; statistical evidence tools              | —                                                                           |
| sf-hamilton P:20                         | `>=1.0`       | 1.89.0 U:5193    | 1.90.0 | DAG decorators/driver; S/components/cleaning.py:11                                | —                                                                           |
| tenacity P:21                            | unconstrained | 9.1.2 U:5591     | 9.2.1  | Retry policies; S/adapters/\_http.py:24                                           | Small retry loop possible; policy equivalence unverified                    |
| sf-hamilton-sdk **tracking extra**, P:26 | unconstrained | 0.9.0 U:5208     | 0.9.0  | Guarded optional import; S/pipeline.py:75–81                                      | —                                                                           |

### Development group

| Dependency; declaration | Constraint  | Locked; evidence | Latest   | Actual usage/evidence                                            | Substitute plausibility                                             |
| ----------------------- | ----------- | ---------------- | -------- | ---------------------------------------------------------------- | ------------------------------------------------------------------- |
| jupyter P:31            | `>=1.0.0`   | 1.1.1 U:1987     | 1.1.1    | Notebook CLI, not imported; docs/TROUBLESHOOTING.md:125          | —                                                                   |
| ipykernel P:32          | `>=6.0.0`   | 7.1.0 U:1769     | 7.4.0    | Kernel registration CLI; docs/TROUBLESHOOTING.md:126             | —                                                                   |
| pytest P:33             | `>=8.0`     | 9.0.3 U:4523     | 9.2.0    | Tests; tests/test_bronze.py:10                                   | `unittest`, requiring suite adaptation                              |
| pytest-cov P:34         | `>=4.0.0`   | 7.0.0 U:4552     | 7.1.0    | Plugin CLI flags; P:115–123; .github/workflows/ci.yml:72         | Direct coverage invocation possible                                 |
| pytest-mock P:35        | `>=3.10.0`  | 3.15.1 U:4566    | 3.17.0   | N; no `mocker` fixture references found                          | `unittest.mock` for equivalent mocking needs                        |
| pytest-asyncio P:36     | `>=0.21.0`  | 1.3.0 U:4539     | 1.5.0    | N; no asyncio marks/config references found                      | ?                                                                   |
| coverage[toml] P:37     | `>=7.0.0`   | 7.13.2 U:697     | 7.17.4   | Coverage configuration; P:132–154; pytest-cov integration        | —                                                                   |
| ruff P:38               | `>=0.3`     | 0.14.13 U:5012   | 0.17.6   | Config P:87–102; .pre-commit-config.yaml:83–96                   | —                                                                   |
| geopandas P:39          | `>=1.1.2`   | 1.1.2 U:1336     | 1.2.0    | Same runtime spatial join above; also notebook imports           | Same caveat above                                                   |
| shapely P:40            | `>=2.1.2`   | 2.1.2 U:5252     | 2.2.0    | **Runtime source imports**; S/components/ingestion/geojson.py:13 | —                                                                   |
| playwright P:41         | `>=1.58.0`  | 1.58.0 U:3744    | 1.65.2   | N for Python API/CLI; frontend uses separate npm package         | ?                                                                   |
| pre-commit P:42         | `>=3.0.0`   | 4.5.1 U:3843     | 4.7.0    | Hook runner; .pre-commit-config.yaml:15–106                      | Shell orchestration possible, not equivalent environment management |
| mypy P:43               | `>=1.8.0`   | 1.20.1 U:3185    | 2.4.1    | P:156–188; .github/workflows/ci.yml:32                           | —                                                                   |
| pip-audit P:44          | `>=2.0.0`   | 2.10.0 U:3701    | 2.10.1   | .github/workflows/ci.yml:43                                      | —                                                                   |
| hypothesis P:45         | `>=6.155.1` | 6.155.1 U:1712   | 6.170.17 | Property tests; tests/test_property_based.py:5–6                 | —                                                                   |

### Research group

| Dependency; declaration     | Constraint    | Locked; evidence | Latest  | Actual usage/evidence                                                                         | Substitute plausibility                          |
| --------------------------- | ------------- | ---------------- | ------- | --------------------------------------------------------------------------------------------- | ------------------------------------------------ |
| beautifulsoup4 P:49         | unconstrained | 4.14.3 U:338     | 4.15.0  | `bs4` imports in L0_wiki and L1_utilities notebooks; AST scan provenance                      | `html.parser` for simple parsing                 |
| cachetools P:50             | `>=6.2.4`     | 6.2.4 U:423      | 8.0.2   | N                                                                                             | `functools.lru_cache` for limited cache policies |
| esda P:51                   | `>=2.8.1`     | 2.8.1 U:1125     | 2.10.0  | Spatial statistics; E/spatial_autocorrelation_evidence.py:520                                 | —                                                |
| h3 P:52                     | `==4.1.0b2`   | 4.1.0b2 U:1614   | 4.5.1   | Hex indexing; E/spatial_hotspots_evidence.py:84                                               | —                                                |
| ipywidgets P:53             | unconstrained | 8.1.8 U:1838     | 8.1.9   | N; archived dependency list only                                                              | ?                                                |
| kaleido P:54                | `>=1.2.0`     | 1.2.0 U:2198     | 1.5.2   | N; no `write_image` references found                                                          | ?                                                |
| langchain P:55              | `>=0.3.0`     | 0.3.27 U:2300    | 1.5.2   | N; archived documentation references                                                          | ?                                                |
| langchain-community P:56    | unconstrained | 0.3.30 U:2318    | 0.4.2   | N; archived dependency list                                                                   | ?                                                |
| langchain-experimental P:57 | `==0.3.0`     | 0.3.0 U:2359     | 0.4.2   | N; archived dependency list                                                                   | ?                                                |
| langchain-google-genai P:58 | `==2.0.0`     | 2.0.0 U:2372     | 4.5.2   | N; archived dependency list                                                                   | ?                                                |
| langgraph P:59              | `==0.2.32`    | 0.2.32 U:2398    | 1.2.24  | N; archived dependency list                                                                   | ?                                                |
| langgraph-checkpoint P:60   | `==2.0.0`     | 2.0.0 U:2411     | 4.3.2   | N; archived dependency list                                                                   | ?                                                |
| libpysal P:61               | `>=4.14.1`    | 4.14.1 U:2452    | 4.15.1  | Spatial weights; E/spatial_autocorrelation_evidence.py:481                                    | —                                                |
| lifelines P:62              | `>=0.27.0`    | 0.30.0 U:2546    | 0.30.3  | N; planned analysis at docs/plans/2026-01-24-analytics-scripts-design.md:29                   | ?                                                |
| marimo P:63                 | `>=0.19.6`    | 0.19.6 U:2672    | 0.25.2  | N; ignored notebook directories mentioned in .gitignore:95–97                                 | ?                                                |
| patsy P:64                  | `>=1.0.2`     | 1.0.2 U:3587     | 1.0.3   | No direct import; formula API consumer E/mrt_impact_evidence.py:71,874                        | Explicit design matrices possible, not drop-in   |
| plotly P:65                 | `>=6.5.2`     | 6.5.2 U:3763     | 7.1.0   | No Python import; iframe wrapper C/PlotlyEmbed.astro:4–8 and export documentation             | — for general interactive plotting               |
| polars P:66                 | `>=1.40.0`    | 1.40.0 U:3785    | 2.1.0   | Only **commented imports**; notebooks/L0_datagovsg.ipynb:25, L1_utilities_processing.ipynb:20 | Existing pandas for some workloads               |
| prophet P:67                | `>=1.2.1`     | 1.2.1 U:3964     | 1.5.0   | N; planning-document reference                                                                | ?                                                |
| pygwalker P:68              | unconstrained | 0.5.0.0 U:4288   | 0.5.0.1 | N; archived dependency list                                                                   | ?                                                |
| seaborn P:69                | unconstrained | 0.13.2 U:5155    | 0.13.2  | N; documentation/planned code examples                                                        | ?                                                |
| shap P:70                   | `>=0.49.1`    | 0.49.1 U:5220    | 0.54.1  | No import; retrospective model-description strings, e.g. E/amenity_impact_evidence.py:1197    | — for SHAP semantics                             |
| statsmodels P:71            | `>=0.14.0`    | 0.14.6 U:5466    | 0.15.0  | Statistical models; E/macro_sensitivity_evidence.py:70                                        | —                                                |
| supabase P:72               | unconstrained | 2.27.2 U:5536    | 2.34.1  | N; archived export description docs/archive/20250120-data-pipeline.md:353                     | ?                                                |
| tabulate P:73               | `==0.9.0`     | 0.9.0 U:5582     | 0.10.0  | N; `to_markdown` found only in planned examples                                               | Small formatter for simple tables                |
| xgboost P:74                | `>=3.1.3`     | 3.1.3 U:6063     | 3.4.1   | No import; historical/model-inventory strings, e.g. E/amenity_impact_evidence.py:1197         | — for model equivalence                          |

### Build dependency

| Dependency; declaration | Constraint    | Locked                  | Latest | Usage                          | Substitute                               |
| ----------------------- | ------------- | ----------------------- | ------ | ------------------------------ | ---------------------------------------- |
| hatchling P:78–79       | unconstrained | **Absent from uv.lock** | 1.33.0 | Declared PEP 517 build backend | Other backends exist; no builtin drop-in |

## Complete frontend direct-dependency table

Runtime declarations: **A:36–61**, one row per declaration in that order. Development: **A:30–31**; peer: **A:33–34**. All latest values: **R**.

| Dependency               | Constraint | Locked; evidence | Latest | Actual usage/evidence                                                 | Substitute plausibility                                |
| ------------------------ | ---------- | ---------------- | ------ | --------------------------------------------------------------------- | ------------------------------------------------------ |
| @astrojs/check           | `^0.9.6`   | 0.9.6 B:44       | 0.9.12 | No source import; `astro check`, CI:112                               | —                                                      |
| @astrojs/react           | `^4.4.2`   | 4.4.2 B:56       | 7.1.9  | app/astro.config.mjs:4,50                                             | —                                                      |
| @astrojs/tailwind        | `^6.0.2`   | 6.0.2 B:58       | 6.0.2  | app/astro.config.mjs:5,51                                             | Direct CSS build integration possible                  |
| @tailwindcss/postcss     | `^4.1.18`  | 4.1.18 B:346     | 4.3.5  | N; no PostCSS config/reference found                                  | ?                                                      |
| @tanstack/react-table    | `^8.21.3`  | 8.21.3 B:348     | 9.3.1  | C/catalog/DatasetTable.tsx:20                                         | Native tables for simpler behavior                     |
| @types/dompurify         | `^3.0.5`   | 3.2.0 B:388      | 3.2.0  | No explicit import; registry identifies a stub; DOMPurify ships types | Bundled types; resolution not independently traced     |
| @types/leaflet           | `^1.9.21`  | 1.9.21 B:400     | 1.9.22 | Ambient/type-provider role; no explicit package import                | —                                                      |
| @xyflow/react            | `^12.11.1` | 12.11.1 B:440    | 13.0.2 | DAG graph/CSS; C/catalog/DagGraph.tsx:22–23                           | Small SVG only for substantially simpler graphs        |
| astro                    | `^5.16.16` | 5.16.16 B:468    | 7.4.13 | Site framework/CLI; app/astro.config.mjs:1; A:10–20                   | —                                                      |
| clsx                     | `^2.1.1`   | 2.1.1 B:518      | 2.1.1  | C/dashboard/segments/SegmentCard.tsx:11,37                            | Small conditional class helper                         |
| dompurify                | `^3.3.1`   | 3.3.1 B:614      | 3.5.0  | Sanitization; C/MarkdownContent.tsx:4                                 | No small equivalent identified                         |
| katex                    | `^0.16.28` | 0.16.28 B:774    | 0.19.1 | C/MathFormula.tsx:2,18                                                | —                                                      |
| leaflet                  | `^1.9.4`   | 1.9.4 B:778      | 1.9.4  | CSS plus React integration; C/dashboard/PriceMap.tsx:2,13             | —                                                      |
| lucide-react             | `^0.575.0` | 0.575.0 B:814    | 1.77.0 | C/dashboard/DeltaBadge.tsx:1                                          | Local SVGs for the small selected icon set             |
| react                    | `^19.2.4`  | 19.2.4 B:1014    | 19.3.1 | Components/hooks; C/DarkModeToggle.tsx:1                              | —                                                      |
| react-dom                | `^19.2.4`  | 19.2.4 B:1016    | 19.3.1 | `createRoot`; C/charts/InlineChartRenderer.tsx:13                     | —                                                      |
| react-leaflet            | `^5.0.0`   | 5.0.0 B:1020     | 5.0.0  | C/dashboard/PriceMap.tsx:2; dynamic imports in other maps             | Direct Leaflet integration, additional lifecycle work  |
| react-markdown           | `^10.1.0`  | 10.1.0 B:1022    | 10.1.0 | C/MarkdownContent.tsx:2                                               | —                                                      |
| recharts                 | `^3.7.0`   | 3.7.0 B:1032     | 3.11.0 | C/charts/ComparisonChart.tsx:10                                       | Small SVG only for restricted chart requirements       |
| rehype-katex             | `^7.0.0`   | 7.0.1 B:1046     | 7.0.1  | app/astro.config.mjs:8,57                                             | —                                                      |
| remark-gfm               | `^4.0.1`   | 4.0.1 B:1054     | 4.0.1  | C/MarkdownContent.tsx:3                                               | —                                                      |
| remark-math              | `^6.0.0`   | 6.0.0 B:1056     | 6.0.0  | app/astro.config.mjs:7,56                                             | —                                                      |
| shiki                    | `^3.21.0`  | 3.21.0 B:1098    | 4.6.0  | No direct import; also consumed by Astro markdown package B:52        | Framework-provided highlighting potentially sufficient |
| tailwind-merge           | `^3.4.0`   | 3.4.0 B:1124     | 3.7.1  | app/src/utils/cn.ts:2                                                 | Small helper would need conflict-rule parity           |
| tailwindcss              | `3`        | 3.4.19 B:1126    | 4.3.5  | app/tailwind.config.mjs:1; Astro integration                          | —                                                      |
| @playwright/test **dev** | `^1.52.0`  | 1.59.1 B:240     | 1.65.1 | app/playwright.config.ts:1; E2E imports                               | —                                                      |
| typescript **peer**      | `^5.9.3`   | 5.9.3 B:1158     | 7.0.2  | Type-check toolchain; app/tsconfig.json:2–16; check peer B:44         | —                                                      |

## CI, hooks and resolution surface

| Surface           | Verified pin/reference                                                                                             | Resolution/freshness evidence                                                               |
| ----------------- | ------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------- |
| Bun               | **1.2.23**, `.bun-version:1`, `app/.bun-version:1`, A:7; both workflows                                            | Local `bun --version` matched; newer-release freshness not checked                          |
| Python            | `>=3.12`, P:6                                                                                                      | U:3–8 partitions resolutions at Python 3.13/3.14; no exact interpreter pin identified       |
| GitHub runner     | `ubuntu-24.04`                                                                                                     | Both workflows; image digest/package contents uncollected                                   |
| Actions           | checkout `@v4`; setup-uv `@v6`; pre-commit/action `@v3.0.1`; codecov `@v4`; upload-artifact `@v4`; setup-bun `@v2` | `.github/workflows/ci.yml:17–22,78–87,102–104,154`; tag targets/latest versions not fetched |
| Pages actions     | upload-pages-artifact `@v3`; deploy-pages `@v4`                                                                    | `.github/workflows/deploy.yml:69–85`; same freshness gap                                    |
| pre-commit-hooks  | `v5.0.0`                                                                                                           | `.pre-commit-config.yaml:17–18`                                                             |
| uv-pre-commit     | `0.6.14`                                                                                                           | Same file:30–31                                                                             |
| mirrors-prettier  | `v4.0.0-alpha.4`; additional `prettier@3.4.2`                                                                      | Same file:36–53; isolated hook dependency resolution not captured                           |
| detect-secrets    | `v1.5.0`                                                                                                           | Same file:56–57                                                                             |
| Local hooks       | mypy, Ruff, Ruff format; manual pip-audit                                                                          | Same file:72–106; project-lock tooling above                                                |
| Runtime CDN asset | KaTeX CSS **0.16.9**                                                                                               | `app/src/layouts/Layout.astro:26`; separate from npm KaTeX 0.16.28                          |

**Lock parsing results:** Python: **308 records**, including editable project; 307 registry packages, all artifact entries hashed. Sources were PyPI plus the editable project. Bun: **671 package records**, all with SHA-512 integrity fields; no explicit `trustedDependencies` field found. These are record counts, not installed-package counts. Commands parsed the complete locks; they did not resolve or install packages.

CI uses `uv sync --dev --locked` and frontend `bun install --frozen-lockfile`; research/tracking are separate declared surfaces. See `.github/workflows/ci.yml:21,42–43,106–108`.

## Fresh audit observations — no prioritization or applicability judgment

Read-only commands exported frozen requirements and piped them to:

`uv run --no-sync pip-audit -r /dev/stdin --no-deps --disable-pip --skip-editable --format json`

| Scope                                           | Fresh result                                                          |
| ----------------------------------------------- | --------------------------------------------------------------------- |
| Frozen core + dev, current Python 3.12 platform | **165 dependencies; no known vulnerabilities reported; exit 0**       |
| Frozen all groups + extras, current platform    | **303 dependencies; 238 advisory records across 23 packages; exit 1** |
| `cd app && bun audit --json`, Bun 1.2.23        | **110 advisory records across 24 package names; exit 1**              |

Counts are **raw tool records**, containing duplicate/alias representations—not deduplicated CVE totals. Full outputs are preserved under `/tmp`.

Direct Python packages with returned CVE aliases:

- **langchain:** CVE-2026-55443, CVE-2026-45134.
- **langchain-experimental:** CVE-2024-46946.
- **langgraph:** CVE-2026-28277, CVE-2026-48776.
- **langgraph-checkpoint:** CVE-2025-64439, CVE-2026-27794, CVE-2026-48775.
- **marimo:** CVE-2026-39987, CVE-2026-54386.

Direct npm findings: **astro 14**, **dompurify 21**, **katex 1** advisory records. Identifiers and affected ranges are in the preserved Bun JSON; e.g. KaTeX **GHSA-238p-pmpm-9mq7**. No exploitability/reachability assessment was performed.

## Explicit evidence boundaries

- “No import” was separated from CLI, plugin, ambient-type, framework/transitive, commented-code and historical-documentation usage above.
- Registry existence was confirmed for every locked direct Python package; none returned a yanked release in that query. Hatchling has no locked version to check.
- License metadata was retrieved, **not license-text/legal validation**. npm reported `react-leaflet` as `Hippocratic-2.1` and DOMPurify as `(MPL-2.0 OR Apache-2.0)`. Latest PyPI metadata lacked usable license fields for pip-audit, pygwalker and seaborn. Complete locked/transitive license evidence remains unavailable.
- Maintenance health, ownership changes, signing/provenance verification, action/hook transitive inventories, browser-download provenance, and other-platform/Python-version audit results were **not established**.
- The previous audit document was context only; the tables and audit results above were independently measured from current files and live services.

Session file (every turn of this agent): /home/howt/.pi/agent/sessions/--home-howt-work-egg-n-bacon-housing--/2026-11-23T04-06-26-561Z_01a20695-7001-732a-81db-159e5d1c0693.jsonl
