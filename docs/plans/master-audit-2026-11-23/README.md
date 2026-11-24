# Master audit — 2026-11-23

**Baseline:** `449b921d499a8c55ec1eacb1a423baa7632456d3`.

This pack is a new audit of the current codebase, not a continuation of obsolete finding statuses. Earlier audit and implementation records are context only. No production remediation or published-data refresh is authorised by this pack; implementation is specified for subsequent agents.

## Reading order

1. [Discovery](01-discovery.md): observations, measurements, contracts and explicit inspection limits.
2. [Findings register](02-findings.md): 18 findings with evidence, impact, confidence and scores; rejected candidates listed.
3. [Remediation specification](03-remediation-spec.md): verdict, conditional gates, quick wins, phased roadmap, gap register, machine-readable baseline.
4. [Handoffs](handoffs/README.md): 11 dispatchable work orders with waves, file ownership, tests and done criteria.
5. [baseline.yaml](baseline.yaml): delta baseline for the next audit.

## Short version

Verdict **CONCERNS (7/10)**. Site is green and shippable; the data plane is not yet trustworthy enough for the next refresh. No CRITICAL. Three HIGH integrity defects (warm-cache geocode plausibility, partial pagination persisted as bronze, size-only R2 sync) gate the next authorised data refresh and R2 sync. Five MEDIUM frontend/release gaps are tracked debt. Nothing here was fixed in production code; this pack is the specification for the next agents.

## Evidence

- [Execution provenance](evidence/execution-provenance.md): commands and fresh verification results.
- [Inventory](evidence/discovery-inventory.md), [full tree](evidence/full-file-tree.txt), [machine census](evidence/inventory.json).
- [Complexity](evidence/complexity.csv): every measured source file; nesting estimates are not cyclomatic complexity.
- [Public-entry index](evidence/public-entrypoints.csv), [error surfaces](evidence/error-surfaces.csv), [schema declarations](evidence/schema-declarations.csv), [observability](evidence/observability.csv): mechanical indexes, not exhaustive semantic review.
- Discovery source maps: [pipeline](evidence/discovery-core.md), [frontend](evidence/discovery-ui.md), [direct dependencies](evidence/discovery-dependencies.md).
- Analysis reports: [core](evidence/analysis-core.md), [frontend](evidence/analysis-ui.md), [release/supply chain](evidence/analysis-release.md).
- Reproduced probes: [core PoC results](evidence/core-poc-results.json) and its [independent re-run](evidence/core-poc-verification.log), [financing PoC](evidence/financing-poc.log), [browser observation](evidence/browser-map.log).
- Runtime gate logs: `evidence/{build,e2e,pages-build,pages-e2e,data-validation,reporting-baseline,fresh-coverage,core-coverage}.log`.
- Measurement verification: [measurement-verification.md](evidence/measurement-verification.md).
- Registry/audit snapshots: `evidence/dependency-registry.jsonl`, `evidence/dependency-pip-audit.txt`, `evidence/dependency-bun-audit.txt`.
- [Measurement methodology and tooling](evidence/measurement/README.md).

Evidence collection excludes local secret files, ignored data/cache directories, vendored dependencies and build output from the source census. Tests and registry queries have separately recorded scopes. Advisory records are not synonymous with unique CVEs or reachable exploits. Missing proof is recorded as a gap or an unconfirmed candidate, never upgraded into a confirmed vulnerability.
