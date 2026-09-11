# App data provenance

These compressed JSON files are precomputed dashboard assets. They are not
written by the Hamilton runtime. Regenerate them from the maintained analytics
documents and pipeline outputs, then run `bun run validate-data` before a
frontend build. The manifest is the required-file and schema-shape contract.

Refresh guidance:

- `dashboard_*`, `map_metrics.json.gz`, and `hotspots.json.gz` are exports of
  the platinum pipeline outputs (`unified_dataset`, profile tables, and
  `appreciation_hotspots`). Refresh them after a successful `main.py --stage
  all` run using the dashboard export workflow.
- `interactive_tools/*` and `segments_enhanced.json.gz` are maintained
  research/analytics extracts. Refresh them with the corresponding research
  notebook or generator documented in `docs/analytics/`.
- `analytics/*` is maintained analytics content; its provenance and refresh
  method are documented alongside each report in `docs/analytics/`.
- `planning_areas*` and `catalog.jsonl.gz` are generated reference/catalog
  assets. Regenerate the catalog with `uv run python scripts/generate_catalog.py`.
