# Remediation Follow-ups — Handoff

**Date:** 2026-09-12
**Status:** Open — small, non-blocking follow-ups from the completed
code-audit remediation roadmap
(`docs/plans/2026-09-10-code-audit-remediation-roadmap.md`, flipped to
`Status: Completed` 2026-09-12; closeout evidence in the final section of
`docs/plans/2026-09-11-hamilton-dag-e2e-evidence.md`).

Everything here is optional polish or deferred-by-decision; none of it is a
regression. Verify against the tree before starting — items may be partially
addressed by later work.

## Follow-ups

1. **Amenity catalog descriptions.** The 9 amenity parse-cache rows
   (`external__busstops`, `chascclinics`, `childcareservices`,
   `communityclubs`, `hawkercentresgeojson`, `nparksparksandnaturereserves`,
   `preschoolslocation`, `sportsgfacilities`, `supermarketsgeojson`) have
   empty `description` fields in `data/catalog/catalog.jsonl`. Add entries to
   `data/catalog/descriptions.yml`, regenerate
   (`uv run python scripts/generate_catalog.py`), re-check
   (`scripts/tools/check_catalog.py`). The generator tolerates empty
   descriptions, so this is purely documentation value.

2. **Deferred: quarantine-only persist mode.** The one deferred item from the
   src-audit program (`docs/plans/2026-09-07-src-audit-improvement-program.md`,
   decision 4): the `ValidationGateway` `persist` parameter remains
   available-but-unused in production (nodes run `persist=False`;
   `LayerWriter` companions are the single persistence path). Do not
   reintroduce `persist=True` into nodes without a dedicated migration — see
   `.agents/skills/change-hamilton-pipeline/SKILL.md`.

3. **New published-output baseline.** Future equivalence checks should use the
   2026-09-12 closeout table in the evidence doc, not the 2026-09-11 rows:
   the sampled-validation flip (roadmap item 22) legitimately changed
   quarantine semantics (vectorized-precheck rejects only, dropped from
   published frames) and the closeout run used fresh rolling data.

4. **Rolling manifests are now warm.** The four rolling sources
   (`raw_condo_transactions`, `raw_hdb_resale`, `raw_hdb_rental`,
   `raw_rental_index`) have fresh `bronze_manifest.json` entries as of
   2026-09-12, so `scripts/40_refresh_rolling.py --stale-only --run` is a true
   no-op until their `STALE_WARN_DAYS` thresholds (35/35/35/100) lapse. The
   2026-09-12 stale-only run refreshed them only because pre-manifest bronze
   counts as stale by design.

5. **CI coverage floor is 70.** `.github/workflows/ci.yml` now enforces
   `--min-coverage 70` (measured 95% total at closeout, 994 tests). New code
   landing without tests can fail CI where it previously passed at 60.

6. **pip-audit volatility.** Advisories landed mid-session during the original
   remediation. If CI security fails on a fresh advisory:
   `uv lock --upgrade-package <pkg> && uv sync && uv run pip-audit --skip-editable`,
   then commit the lock. (Carried over from the 2026-09-11 handoff.)

## Operational notes carried forward

- Warm full run ≈ 1:12–1:14 via CLI; the 1:22:53 closeout run was a full
  recompute (Hamilton cache + four rolling sources refreshed), not a
  regression signal. Serial execution remains the deliberate default
  (benchmark gate not met — see evidence doc).
- Never clear `data/cache` except for intentional cold runs
  (`scripts/99_cleanup.py`).
