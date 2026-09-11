# WS21 — Docs Sync + Platinum Validation Cost Measurement (D5 + D3, Batch 5)

## Context

Batches 1-4 changed many pipeline behaviors; `docs/guides/pipeline-development.md` and `docs/guides/usage-guide.md` were only partially updated in passing (WS11 updated the materializer section). Also: D3 — the D3a decision (full platinum validation) was never costed; if `unified_dataset` validation is slow, a config escape hatch should be PROPOSED (not implemented without approval).

Run this WS AFTER Batch 4 completes so docs reflect the final state.

## Read first

- All `.agents/handoffs/*.md` (change inventory), `docs/guides/pipeline-development.md`, `docs/guides/usage-guide.md`, `docs/guides/data-ingestion-development.md` (already partially synced — don't duplicate)
- `.agents/skills/change-hamilton-pipeline/SKILL.md` (docs-accuracy is part of its checklist)

## Owned files (EXCLUSIVE)

- `docs/guides/pipeline-development.md`
- `docs/guides/usage-guide.md`
- `docs/data-sources.md` (only if it describes validation/coverage behavior that changed)

## Forbidden

All `src/`, `tests/`, `scripts/`, other docs, `.agents/skills/*`, `tests/conftest.py`, `pyproject.toml`.

## Changes

### 1. Docs sync — `pipeline-development.md` (+ usage-guide where user-facing)

Verify-and-update sections for (each = read code first, then write):

- Single persistence regime: nodes validate `persist=False`; ALL published outputs via `materialization.py` companions; `_PERSISTED_VARS`/recompute hack deleted (WS11).
- Cache invalidation: `ensure_published_outputs_or_invalidate` runs BEFORE `build_pipeline` on the CLI path; empty outputs persist as 0-row parquet (WS5).
- Validation semantics: `fail` = full validation + raise; `sample` = persist + logged unvalidated count; NaN-required rows → quarantine (WS1); platinum models + validation (WS3).
- Bronze: central cache helpers, `manual_dir` injection (WS15), manifest + stale warnings (WS10), interpolated income medians (WS12 — note the value-shift), per-type geocoding coverage (WS16), hotspots floor + `METRICS__MIN_TRANSACTIONS_FOR_HOTSPOT` (WS13).
- If any statement in the docs contradicts current code beyond this list, fix it too (docs must match code, not the handoffs).

### 2. D3 measurement — platinum validation cost (report-only, no code changes)

- If `data/pipeline/04_platinum/unified_dataset.parquet` exists locally: time `validate_schema(pd.read_parquet(...), HUnifiedRecord, ...)` (a tiny timing snippet in a throwaway `uv run python -c` — NOT a committed file) and record wall time.
- If data is absent, document the exact measurement command for later.
- Deliverable: number + a one-paragraph recommendation (keep full / add config toggle) in the report. Do NOT implement anything.

## Verification

```
uv run python scripts/tools/validate_docs_layout.py
uv run python scripts/tools/validate_agent_skills.py
uv run ruff format --check docs 2>/dev/null || true
git diff --check
```

## Constraints

- NO commits. Owned docs only. No code changes anywhere.

## Definition of done

Docs match code across all batch behaviors; D3 number (or measurement instructions) + recommendation reported.

## Report back

Sections updated (file:heading), contradictions found+fixed beyond the list, D3 timing + recommendation.
