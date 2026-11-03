# S2 implementation report — dashboard publication compatibility

Additive metadata for the seven dashboard assets. No payload shape, generator formula, CLI flag or validation rule changed; no pipeline/Hamilton file touched; no published asset regenerated; no dependency added; **no commit**.

## 1. Contract

`scripts/export_app_data.py` now also writes `app/public/data/dashboard-release.json`:

- `schemaVersion` (`1.0.0`), content-derived `generation`, UTC `generatedAt` (export time only — never described as source freshness);
- `observationRange` (`startMonth`, `endMonth`, `completeYear`) derived from the published trends months, so a year is only claimed complete when all twelve months exist;
- `periodDefinitions` in literal words, derived from the real `ERA_FILTERS`;
- `inclusionRules`: national aggregates keep every row, the five area surfaces drop `NON_RESIDENTIAL_AREAS`, with the excluded area names and the excluded row count;
- `provenance.sources`: both input parquets with repo-relative path, SHA-256, bytes, rows, columns and `sourcePublishedAt: null` (the pipeline does not record a source publication time, so none is invented);
- `assets`: per file `path`, `sha256` (published `.gz` bytes), `contentSha256` (decompressed JSON text), `bytes`, `shape` and narrow `metricScopes`. The content hash was added during S5: hosts that serve `.gz` with `Content-Encoding: gzip` give the browser decoded bytes, so a browser cannot verify the file hash and would have withheld every baseline.

Publication order: stage seven payloads → hash the staged bytes → build and stage the manifest → verify the manifest against the staged bytes → replace the seven payloads → replace the manifest **last**. A failure before the first replace leaves the previous release untouched; the seven replaces are individually atomic but not one transaction, which is why the hashes — not the swap order — are the mixed-release detector.

## 2. Verification

| Check | Result |
|---|---|
| `uv run pytest tests/test_export_app_data.py --no-cov -q` | **29 pass** (14 pre-existing + 12 manifest + 3 contract-sync) |
| `uv run ruff check` / `ruff format --check` | clean |
| Real export to `/tmp/s2/out2` (`--output-dir`) | exit 0, 8 files, log now reports 8 |
| `verify_release_manifest` on that export | `[]` |
| Node `validate-data.mjs` against that export (`/tmp/s2/check2`) | `Validated 19 app data assets` + `Verified dashboard release 9330505655cd (7 assets)` |
| Node rejection paths | tampered hash, missing asset, extra asset, wrong schema version, wrong generation, `assets: 7` malformed → all fail closed with a descriptive error |
| Generation determinism | `generatedAt` alone does not change the id; an asset hash change does; Python and Node recompute the same id from real files |
| Repository `cd app && bun run validate-data` | passes, warns that no release manifest is published in this tree yet |

The manifest is **not** committed here: it is a generated artifact. It will appear the next time the maintenance exporter runs against real platinum data.

## 3. Scope discipline

`app/public/data/README.md` documents the new file, the failure window and the detector. Research assets (`segments_enhanced`, `interactive_tools/*`, `analytics/*`), `planning_areas*` and `catalog.jsonl.gz` stay outside this generation and keep their own vintages.

## 4. Follow-ups

- Consumers do not read the manifest yet. S2 exposes it; S5/S6 must withhold a cross-file national baseline until the loaded asset hashes match, and `setDataGeneration()` from S1 should be fed from the verified generation id.
- `sourcePublishedAt` stays `null` until a source-publication timestamp exists somewhere in the pipeline.
- `--output-dir` writes the manifest into the same directory as the assets; a deployment that serves assets from a different origin must pass the manifest path explicitly.
