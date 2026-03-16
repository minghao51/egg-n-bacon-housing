# Agent Notes

## Analytics Doc Charting

Analytics tables in `docs/analytics/` render into `app/`, but charts are opt-in only.

Use this marker immediately before a markdown table when a chart should appear in the app:

```html
<div
  data-chart-metadata="true"
  data-chart="comparison"
  data-chart-title="Descriptive chart title"
  data-chart-columns="Column A,Column B"
></div>
```

Rules:
- Leave tables unmarked unless a chart clearly improves comprehension.
- `data-chart` may be `comparison`, `time-series`, or both separated by commas.
- Prefer `data-chart-columns` to limit charts to the few numeric series that matter.
- Do not opt in descriptive tables such as data dictionaries, methodology summaries, file inventories, or risk/mitigation matrices.
- Keep the marker directly adjacent to the target table so the renderer can bind it reliably.
