# Audit measurement tooling (not production code)

Read-only harness used to produce the Phase 1 discovery artifacts for the
master audit at HEAD 449b921d499a8c55ec1eacb1a423baa7632456d3.

| script           | role                                                                                                                                                                                                      |
| ---------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `measure.py`     | scope enumeration, Python `ast`/`tokenize` metrics, LOC, dead-code candidate grep, coverage/manifest inspection; writes `inventory.json`, `complexity.csv`, `full-file-tree.txt`, `raw-measurements.json` |
| `indexes.py`     | entrypoint/error/observability/schema indexes; patches `inventory.json`; copies these scripts                                                                                                             |
| `ts_measure.mjs` | TypeScript compiler AST parsing for `.ts/.tsx/.mjs` and `.astro` frontmatter (loaded read-only from `app/node_modules/typescript`)                                                                        |

Run from anywhere: `uv run python <repo>/docs/plans/master-audit-2026-11-23/evidence/measurement/measure.py`
then the same for `indexes.py`. No absolute paths or installs are required: the scripts
resolve the repo root with `git rev-parse --show-toplevel` and read measured content
from a `git archive HEAD` snapshot.

These files are audit evidence only: they do not import, modify or execute
application code, and they are not part of the shipped package.
