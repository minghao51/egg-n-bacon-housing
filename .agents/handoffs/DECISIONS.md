# Decision Log — src/ Improvement Program

> **Archive status:** This decision log records the completed historical
> work-order program. Do not dispatch the `🔄`/`⏳` entries as new work. For the
> current implementation state and next actions, use
> [`docs/plans/2026-09-10-hamilton-dag-next-thread-handoff.md`](../../docs/plans/2026-09-10-hamilton-dag-next-thread-handoff.md).

## Round 1 — original plan (all executed in Batches 1-2)
| ID | Decision | Status |
|---|---|---|
| D1a | Rental join: sentinel-aware merge (drop constant `flat_type` from rental frame → falls to `(town, month)`) | ✅ WS2 |
| D2a | Empty datasets persist as 0-row parquet (no marker files) | ✅ WS5 |
| D3a | Full pydantic validation on all 3 platinum outputs (policy-respecting) | ✅ WS3 |
| D4a | `large_table_policy="fail"` = full validation + raise; `sample` logs unvalidated count | ✅ WS1 |
| D5b | Wiki-mall: fix the remedy (working `--refresh 'raw_wiki_shopping_mall*'`), branch removal later | ✅ WS4 |
| D6a | MRT fallback: fix interchange aggregation + loud warnings (full fallback derivation deferred) | ✅ WS4 |
| D7a | Cache versioning: caller-embedded convention, go-forward only | ✅ WS6 |
| D8 | School prune to pipeline-consumed columns only; analytics docs NOT a constraint | ✅ WS9' |
| D9a | Same working tree, strict per-WS file ownership, sequenced batches | ✅ used throughout |
| D10 | Verify per-WS: focused pytest + ruff check/format + mypy on owned files; full gates at integration | ✅ |

## Round 2 — residual roadmap (Batch 3+)
| ID | Decision | Status |
|---|---|---|
| 1 | A1 materializer migration proceeds NOW (Batch 3) | 🔄 WS11 |
| 2 | B1 income interpolation ACCEPTED — `median_monthly_income` values shift intentionally | 🔄 WS12 |
| 3 | B3 hotspots floor `>= 5` — MUST live in config (`MetricsConfig`) + pipeline injection (not bare node default) | 🔄 WS13 (wave 2) |
| 4 | B5 coverage policy = per-property-type thresholds (HDB strict / condo lenient) — "the former" | ⏳ WS16 (Batch 4) |
| 5 | A3 keep coarse full-dir cache invalidation — safe/simple, no work | ✅ closed |
| 6 | D1 refresh scheduling = LOCAL for now (no GitHub Actions) | ⏳ WS18 (Batch 5) |

## Structural constraints derived from ownership
- Batch 3 = two waves: WS13 needs `pipeline.py` + `config.py`; `pipeline.py` belongs to WS11 → WS13 runs after Wave 1 merges.
- Batch 4 = two waves: WS17 needs `pipeline.py` (repository-param unwiring); `pipeline.py` belongs to WS15 → WS17 runs after Wave 1 merges.
- Batches never share files within a wave. `tests/conftest.py` + `pyproject.toml` are never owned.
