# RF08 — RS01/RS02 edition sign-off record

- **Date:** 2026-11-14
- **Slices:** RF08 (refreshed studies), series `data-sources` (RS01) and `rental-yields` (RS02)
- **Evidence packs:** [RS01](2026-11-14-rs01-source-inventory.md) · [RS02](2026-11-14-rs02-rental-yield-evidence.md)
- **Contract:** [D12](../plans/2026-11-12-reporting-refresh-decisions.md) (three distinct attestations on one artifact, no self-approval), [D07](../plans/2026-11-12-reporting-refresh-decisions.md) (edition ≠ observation window)
- **Registry:** `app/src/components/studies/lib/edition-registry.ts`

This note is the durable record of the RF08 gate sequence for these two editions. The
registry entry is the machine-readable approval; this file is where the verbatim
attestations and their conditions are kept, so a reviewer's words survive outside a
one-line `statement` field.

## Gate 1 — source/cutoff signature (recorded 2026-11-14)

Given by the repo owner as `howt` on both ledger hashes, after the agent reported them
verified against this tree (`source_inventory.py --check` → `Pass: RS01 ledger matches
the tree`; both ledger files re-hashed on disk).

| Ledger | sha256 | What the owner accepted |
| --- | --- | --- |
| RS01 `artifacts/rs01-source-inventory.json` | `65ce7a10c257d13fd4250b2e8fd1519f8c35718497379aa103effc5594bfe8ae` | the measured inventory and the cutoff/dispositions it implies |
| RS02 `artifacts/rs02-rental-yield-evidence.json` | `db1345253c4c9e4d80b7e3067962199a12f120ccfdfe1b6f599a7d95459f0313` | the measured coverage 2021-01 → 2026-10 and the §5 regenerate disposition |

Because `validateEditionRegistry()` rejects any sign-off on a non-approved edition, this
attestation is recorded in the [decision ledger](../plans/2026-11-12-reporting-refresh-decisions.md)
(D12 "Recorded decisions") and is materialised into `signoffs[]` in the same edit that
flips the editions to `approved`.

## Gate 2 — refreshed edition text (authored 2026-11-14)

New frozen sources; the RF00 originals were **not** edited. `verify_reporting_baseline.py
--assets` still passes 15 frozen sources / 72 assets, which is the byte-level proof.

| Series | Frozen source | Edition id | Signed text sha256 |
| --- | --- | --- | --- |
| `data-sources` | `docs/analytics/editions/data-sources/2026-11-14/data-sources.md` | `data-sources-2026-11-14` | `bde11c61b720c2504cdf78bde9238c5e57925e319457d52356cde0bcdeeafb81` |
| `rental-yields` | `docs/analytics/editions/rental-yields/2026-11-14/rental-yields.md` | `rental-yields-2026-11-14` | `f6b0bd9d811bb9b348b0e897b66a482add281e38f2803c61193978c97ca0ab67` |

The signed hashes above are the post-review bytes — the text as it stood when the
passing verdict was given. Any further edit to either file changes the hash and the
build-time pin check fails until the editions are re-reviewed and re-signed.

What the text does: RS01 replaces inferred ranges with the measured ledger
(89 files, 30 recorded / 59 unrecorded, measured coverage per source, macro lag
table, amenity feature counts, grain, the two recorded source defects) and withdraws
the unmeasured median-distance column and the column/amenity/macro roll-ups. RS02
states the gross-proxy definition, the 86.6–95.6% matched-group share, the 1,749
town-month denominators and their distribution, and withdraws the per-flat-type bands,
the yield-vs-appreciation claim, the top-combination league table, the affordability
ratio, the growth/seasonality figures and the downside-floor claim.

No chart marker is used, so `assetsPinned: 0` is honest for both.

## Gate 3 — scientific re-review of the article text (2026-11-14)

Run: `codex-luna-reviewer` on `openai-codex/gpt-6-luna`, reasoning `xhigh`, three
exchanges. **Verdict: PASS** on the final text. The first pass returned **FAIL** with
three hard defects and one note, all fixed before the passing review:

1. `rental-yields.md` said no source carries a "unit or block identifier" — it contradicted
   the feasible block-level proxy measured in the same file. Now unit-only.
2. Both files' sign-off sections asserted the attestations were already recorded in the
   registry. Two successive corrections were needed here; the final wording describes
   the gate conditionally and does not claim any signature exists.
3. `data-sources.md` claimed unavailable files and absent published assets are "reported
   separately". The ledger inventories the acquisition tree only; corrected.
4. Note: a Superseded-figures row used a synthesised quotation. Now quotes the previous
   edition's actual phrases and withdraws the counts it cannot measure.

Verbatim attestation (final, passing review):

> I reviewed the 2026-11-14 Data Sources and Rental Yields editions against RS01 ledger
> hash `65ce7a10c257d13fd4250b2e8fd1519f8c35718497379aa103effc5594bfe8ae` and RS02 ledger
> hash `db1345253c4c9e4d80b7e3067962199a12f120ccfdfe1b6f599a7d95459f0313`; the
> ledger-backed numerical claims and withdrawals were verified in the preceding review,
> and the revised sign-off language accurately describes the current registry state and
> approval gate. I confirm neither section asserts that attestations are already
> recorded or attributes all three to the decision ledger. This attestation does not
> cover the evidence packs themselves, other studies, or any future edit or approval.

Scope note: this attestation covers **these two article files at these ledger hashes**.
It does not extend to the packs (attested separately, 2026-11-14), to the other thirteen
studies, or to any later edit — which is why the registry pins `editionSha256` and the
archive route re-verifies it at build time.

## Gate 4 — publication signature (recorded 2026-11-14)

Given by the repo owner as `howt` on the two frozen text hashes above, and recorded in
the [decision ledger](../plans/2026-11-12-reporting-refresh-decisions.md) under D12 and
in each edition's `signoffs[]`.

What the registry now carries, per edition: `evidenceStatus: "approved"`,
`editorialStatus: "published"`, `editionSha256` = the signed text hash, and three
attestations — `source` (`howt`, the ledger hash), `scientific`
(`openai-codex/gpt-6-luna (xhigh)`, `automated: true`, the ledger hash, pointing at this
record) and `publication` (`howt`, the ledger hash). All three pin one evidence artifact
as `validateEditionRegistry()` requires; the text is pinned separately by
`editionSha256`, which the archive route re-verifies against the frozen bytes on every
build.

Consequence for the app: `approvedEditionFor()` now offers these two editions as the
current editions of `data-sources` and `rental-yields`. The series entries changed from
"No approved current edition" to `Approved edition <edition id>` with a link to the approved
edition, and state that the narrative below is the series text which may predate it —
otherwise the withdrawn claims would sit on the same page as the signed correction with
nothing distinguishing them.

The other thirteen studies remain `historical` with no sign-offs, so their entries still
say "No approved current edition".

## Verification at freeze

| Check | Result |
| --- | --- |
| `uv run python scripts/tools/source_inventory.py --check` | Pass: RS01 ledger matches the tree |
| `uv run python scripts/tools/rental_yield_evidence.py` | re-measured; ledger hash unchanged |
| `uv run pytest tests/test_research_evidence_tools.py tests/test_rental_yield_metrics.py --no-cov -q` | 25 passed |
| `uv run python scripts/tools/verify_reporting_baseline.py --assets` | Pass: 15 sources, 72 assets |
| `uv run ruff check` / `ruff format --check scripts/` | clean / 14 files formatted |
| `cd app && bun run test:unit` | 508 passed (32 files) |
| `cd app && bun run astro check` | 0 errors, 0 warnings, 22 hints |
| `cd app && bun run build` | 221 pages (+2 archive routes) |
| `cd app && bunx playwright test tests/e2e --workers=4` | 230 → 231 passed / 9 skipped after the approved-edition test |
| Archive routes render | `data-edition-status="historical"` — the honest pre-approval state |
| Build-time pin check | proven: an approved entry with a wrong `editionSha256` fails the build with the mismatch named |
