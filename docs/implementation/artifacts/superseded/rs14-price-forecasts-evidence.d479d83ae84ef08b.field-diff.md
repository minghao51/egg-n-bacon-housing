# RS14 ledger re-measure: d479d83a… → ea3a006c…

Reviewed ledger bytes `d479d83ae84ef08b2224f5b4dd36ea7765d39232fa7fd3181b47b076dd6b200f` are retained verbatim as `rs14-price-forecasts-evidence.d479d83ae84ef08b.json`.

Re-measured with `uv run python scripts/tools/price_forecasts_evidence.py` during review-closure of the edition text, because gate 1 (`--check`) no longer re-measured byte-identically: the ledger's disclosed whole-tree filename scan (`absenceScans.trainTestSplitFiles.roots`, boundary note "build outputs included") had picked up files written by concurrent sibling sessions after the reviewed build (coverage/htmlcov, cache and data artefacts). The edition text edited during closure sits under `docs/analytics/editions/` and is excluded from that scan, so the drift is not caused by the closure edits.

Field diff (reviewed bytes → re-measured bytes), complete and exactly one field:

- `absenceScans.trainTestSplitFiles.filesScanned`: 18886 → 18891

No claim, cutoff, score, quote check, claim-key check or input pin changed. All other fields are byte-identical. New ledger sha256: `ea3a006c24399bce07972a5c01fb0d3ff86520ae5988ceb911c775224c6c21a9` (191999 bytes).
