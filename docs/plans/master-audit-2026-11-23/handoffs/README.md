# Handoffs — master audit remediation

Dispatch one `worker` subagent per work order. Read the work order in full, then execute it: read-first, changes, tests, verification, constraints, definition of done. Do not exceed the `Owns` list.

Source of truth: [02-findings.md](../02-findings.md) and [03-remediation-spec.md](../03-remediation-spec.md).

## Waves

| Wave | Work orders                                                                                                                                                                                   | Why grouped                                                            |
| ---- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| 0    | [WS-A4](WS-A4-pacing-and-refresh.md), [WS-B3](WS-B3-financing-hardening.md)                                                                                                                   | Small, independent, no shared files                                    |
| 1    | [WS-A1](WS-A1-geocode-cache-contract.md), [WS-A2](WS-A2-pagination-completeness.md), [WS-A3](WS-A3-sync-integrity.md), [WS-C1](WS-C1-pages-release-gate.md), [WS-D1](WS-D1-types-and-docs.md) | Independent file ownership                                             |
| 2    | [WS-B1](WS-B1-verified-bytes.md), then [WS-B2](WS-B2-map-accessibility.md)                                                                                                                    | Both touch `ExplorerWorkspace.tsx`; B2 reads B1's result               |
| 3    | [WS-C2](WS-C2-evidence-reproducibility.md), [WS-D2](WS-D2-dependency-hygiene.md)                                                                                                              | C2 owns `.github/workflows/ci.yml` alone; D2 owns dependency manifests |

## Standing rules (every work order)

- **No commits.** Leave changes in the working tree.
- **Restore generated data.** `cd app && bun run build` rewrites `app/public/data/catalog.jsonl.gz`; `git checkout -- app/public/data/catalog.jsonl.gz` afterwards unless a data refresh is authorised.
- **Bun pin.** Use `~/.bun/bin/bun` (1.2.23). Never `npm i -g bun`. A newer bun rewriting `app/bun.lock` means `git checkout -- app/bun.lock`.
- **Python via `uv run`.** Never bare `python`.
- **Do not weaken tests** to make an implementation fit. Do not edit `tests/conftest.py` or `pyproject.toml` unless the work order owns it.
- **Skills.** Pipeline/ingestion work reads `.agents/skills/change-hamilton-pipeline/SKILL.md` and/or `.agents/skills/change-data-ingestion/SKILL.md` first.
- **Migration boundaries.** `LayerWriter` for new silver/gold/platinum outputs; computing nodes stay side-effect-free; no parallel production runner.

## Gate (run after every wave)

```bash
uv run pytest tests/ -q --no-cov
uv run ruff check . && uv run ruff format --check . && uv run mypy
uv run python scripts/tools/validate_docs_layout.py
uv run python scripts/tools/validate_agent_skills.py
uv run python scripts/tools/check_catalog.py
git diff --check
cd app && PATH="$HOME/.bun/bin:$PATH" bun run test:unit && bun run astro check && bun run validate-data
```

E2E plus the Pages-prefixed suite when a frontend slice lands:

```bash
cd app && PLAYWRIGHT_HTML_OPEN=never PLAYWRIGHT_SERVER_COMMAND='bun run preview -- --host 127.0.0.1' \
  PLAYWRIGHT_BASE_URL='http://127.0.0.1:4321' bunx playwright test --workers=2
cd app && bun run build:pages && PLAYWRIGHT_HTML_OPEN=never \
  PLAYWRIGHT_SERVER_COMMAND='bun run serve:pages' \
  PLAYWRIGHT_BASE_URL='http://127.0.0.1:4402/egg-n-bacon-housing/' \
  PAGES_ORIGIN='http://127.0.0.1:4402' PAGES_BASE_PATH='/egg-n-bacon-housing' \
  bunx playwright test tests/e2e/pages-base.spec.ts --workers=2
git checkout -- app/public/data/catalog.jsonl.gz
```

Baseline expectations at `449b921`: 1,136 Python tests, 534 frontend unit tests, 237 E2E passed / 9 skipped, 9 Pages-base passed, `astro check` 0 errors / 0 warnings / 22 hints, coverage 95.53 % lines. Touched files must not add errors or hints.
