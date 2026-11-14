# RF11 report — catalog, reference vintages and unused assets

- **Date:** 2026-11-13
- **Status:** **Complete.** The catalog was regenerated from the current platinum build as an authorized slice, the recorded audit observation was reconciled with the earlier finding preserved, and an asset-disposition table is recorded for RF12. No reference or geometry asset was replaced, and no unused asset was removed.
- **Parent:** [implementation map](../plans/2026-11-12-reporting-refresh-implementation-map.md) §6 · [handoff](../plans/2026-11-12-reporting-refresh-handoffs.md) RF11
- **Requires:** [RF03 sources](2026-11-13-rf03-source-reconciliation.md) · [RF00 baseline](2026-11-12-rf00-baseline.md)
- **Evidence:** [S0 baseline](s0-baseline.md) (the preserved earlier observation)

## 1. The three counts, labelled

Step 1 asks for the old catalog generation and the discrepancy, inspected directly rather than inferred from the app:

| What | Rows | Generation / provenance |
| --- | --- | --- |
| Catalog snapshot before RF11 | 1,233,405 | `catalog.jsonl` generated `2026-09-12T08:05:07Z` |
| S0 audit observation | 1,234,928 | recorded in [S0 baseline](s0-baseline.md) |
| Platinum artifact before RF11 | 1,236,310 | `data/pipeline/04_platinum/unified_dataset.parquet`, 97 columns, 78,381,526 bytes, sha256 `39d234f703c9d6e0…` |

The catalog row count and the S0 audit were themselves different snapshots, which is why neither could be "the" answer. The artifact was read with parquet metadata, not from the app's overview or from the catalog.

## 2. Regeneration (authorized)

```bash
uv run python scripts/generate_catalog.py
```

Result — no structural drift, values refreshed:

```text
4 layers, 125 datasets, 2333 lineage edges
catalog.jsonl        sha256 7f75527f8275eb2f71f796a563b66d2b33190f6a7db01975f0f399b0415dd48e
catalog.jsonl.gz     rewritten by app/scripts/sync-catalog.mjs during `bun run build`
generated_at         2026-11-13T16:32:53Z
unified_dataset      1,236,310 rows · 97 columns · 78,381,526 bytes
```

The regenerated snapshot and the inspected artifact now agree, so the catalog page's "Snapshot discrepancy" banner is gone. The finding itself was **not** deleted: `CATALOG_AUDIT.unified_dataset` now carries the new observation with its artifact hash, and `CATALOG_AUDIT_HISTORY` keeps the S0 entry (1,234,928 vs 1,233,405) as evidence. The page shows the agreement; the constants keep both generations distinguishable.

## 3. Lineage, schema and requiredness

- Layer/dataset/edge counts are unchanged (4 / 125 / 2333), so this was a value refresh, not a lineage-layout change.
- Declared requiredness and observed nullness stay separate columns; the regenerated catalog keeps the same split (the catalog E2E still asserts it).
- No SSR prop or table shape changed; the dataset page still server-renders the snapshot counts and filenames.

## 4. Geometry and reference provenance

Not replaced. The refresh is a transaction refresh, which does not authorize a boundary change: `planning_areas.geojson(.gz)`, the canonical area ids and the five planning-region labels are untouched, and the historical area routes were preserved separately in [RF06](2026-11-13-rf06-fieldnotes.md) (union + slug-collision guard). A future boundary change needs its own evidence, not this report.

## 5. `interactive_tools/affordability_metrics.json.gz`

- Present at `app/public/data/interactive_tools/affordability_metrics.json.gz` (2,282 bytes).
- **No consumer**: `app/src/components/tools/lib/tool-reference.ts` and `ToolsSurface.astro` mention it only to say it is *not* read (the financing reference uses `map_metrics.year_2025_*` joint sections instead).
- **Not in the release manifest**: the v1 `dashboard-release.json` lists the seven exporter assets and does not include it, so it is outside the verified generation.
- **Disposition: retain.** Removing it is a data-boundary decision (and would need the required-file contract checked first); this slice only records the finding. Proposed follow-up for the data owner: either list it in a manifest with a period/source identity, or approve removal.

## 6. Asset disposition (for RF12)

| Asset | Disposition | Identity |
| --- | --- | --- |
| v1 release payloads (7 files) | **frozen**, served unchanged | generation `0e1013ee485f…` |
| v2 observed pack (`dashboard-release-v2.json` + `observed/<gen>/{periods,summary}.json.gz`) | **published beside v1**, cutoff 2026-10, 8 periods, 1,472 observations | generation `6cd4510f26ec…` |
| `catalog.jsonl` / `catalog.jsonl.gz` | **regenerated** (authorized RF11 output) | `7f75527f…` / rebuild-time gzip |
| `unified_dataset.parquet` | **inspected source**, unchanged | sha256 `39d234f703c9d6e0…` |
| `interactive_tools/affordability_metrics.json.gz` | **retained, unused**, outside the manifest | 2,282 bytes |
| `planning_areas.geojson(.gz)` and reference assets | **unchanged** | not re-pinned in this slice |
| `public/data/observed/**` | immutable generation path | verified by `validate-data` |

## 7. Verification

```bash
uv run pytest tests/test_catalog_generator.py --no-cov -q   # 30 passed
uv run python scripts/tools/check_catalog.py                # valid: 4 layers, 125 datasets, 2333 edges
uv run python scripts/tools/validate_docs_layout.py         # pass
uv run ruff check                                           # pass
cd app && bun run test:unit                                 # catalog-audit tests updated (3 pass in file)
cd app && bun run astro check                               # 0 errors, 0 warnings, 22 hints
cd app && bun run build                                     # 204 pages
cd app && bunx playwright test tests/e2e/catalog.spec.ts    # 8 passed
```

## 8. Note for RF12: two gzip producers

`generate_catalog.py` writes `catalog.jsonl.gz` itself, and `app/scripts/sync-catalog.mjs` rewrites it from `catalog.jsonl` during `bun run build`. Both produce the same decompressed content, but the compressed bytes differ by encoder, so the published `.gz` hash depends on which ran last. RF12's release evidence should pin the **post-build** artefact (or the `.jsonl` source plus a deterministic encoder). This slice kept the post-build output, which is what the site serves.
