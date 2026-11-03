# Validation record

## Scope

Design assets and documentation only. No production source edits, dependency changes, pipeline refresh, deployment or commits. Initial tree clean; work isolated on `design/sol-editorial-spec`.

## Checks performed

- Revision 2: parsed all **21 SVGs** with Python `xml.etree.ElementTree` using `uv run python`.
- Checked explicit viewBox, title/description, selectable text, unique element IDs, and absence of scripts, raster image elements, foreignObject, external href references.
- Rendered every SVG in **Playwright Chromium** at its declared native dimensions, including all 390px mobile pages. Revision 2 added screen-edge checks using rendered client rectangles, not only SVG-local text bounds. Chromium initially lacked shared-library lookup; using pre-existing libraries under `/tmp/qna-browser-libs/root/usr/lib/x86_64-linux-gnu` enabled rendering. No repository dependency or browser installation changes were needed.
- Visually inspected all 21 native renders. Corrected mobile research/title overflow, control-boundary contrast, sort affordances, spacing, missing page position and source notes. Added capability pathways to overview, signed lease intervals, comparison removal controls and a clear incompatible-generation state.
- Browser text rendered-rectangle checks found no text extending outside any final SVG viewport. This complements, not replaces, visual inspection for overlap.
- Checked primary overview/design example values against decompressed public assets; independently checked platinum row count and coordinate/yield missingness in aggregate. Recorded selected values and SHA-256 hashes in [data-evidence.json](data-evidence.json).
- Numerically checked overview desktop/mobile bars, detail bars, 12 explorer dots, four mobile mini-bars, 12 desktop/mobile monthly points, 12 volume bars, five amortization bars, 12 lease interval marks and all 110 actual-geometry fills (55 each in observed/research maps), plus sample gates and cross-screen values. 25,084 + 6,209 + 47,503 = 78,796. 710,000 − 628,000 = 82,000; difference / 628,000 = 13.0573…%, displayed 13.1%.
- Checked WCAG sRGB contrast for text palette combinations and control boundaries; full numerical results are in [validation-results.json](validation-results.json). Light separators are decorative, not the sole control boundary.
- Checked local Markdown links in this asset folder resolve; no invented proposed route is represented as an existing file link. External reference fetches and redirects are documented in design-rationale.md, not claimed to reproduce original archived layouts.
- `cd app && bun run validate-data`: **passed, 19 assets**. This is a shape/required-key gate, not proof of model accuracy or compatible generations.
- Revision 2 data: independently recalculated 2025 HDB national 25,084 / S$628,000 / raw PSF 603.870→603 and Tampines 1,921 / S$710,000 / raw PSF 620.843→620 from one local platinum frame. Area-map counts sum 25,082; the 2-record difference is 2 Sungei Kadut rows excluded by residential-area policy. No 2025 HDB row lacks a planning area. Evidence/checksums in [expanded-data-evidence.json](expanded-data-evidence.json). This proves a **selected reconciled snapshot**, not production cross-file generation identity.
- `git diff --check`: checked for tracked diff whitespace; new asset text also checked separately. Production files remain unchanged.
- `cd app && bun run astro check` baseline: **109 errors, 0 warnings, 45 hints, 112 files**. This is pre-existing application debt; it is not a passed type-check and no source was modified to mask it.
- Existing runtime checks: local routes loaded 200. Spatial Hotspots tab reproduced `Cannot read properties of undefined (reading 'flatMap')`. Legacy map URL hydration reproduced loss of metric/timeBasis/propertyType/area before incoming filters are read. These are recorded for S0/S1 and are not claimed fixed.

## Local application investigation

Started the existing Astro development server, then loaded `/`, `/dashboard`, `/dashboard/leaderboard`, `/dashboard/map`, `/analytics/lease-decay`, `/catalog` in Chromium. All returned HTTP 200, with no captured page exceptions during short smoke visits. Visually inspected the full existing leaderboard. Its basemap displayed a provider “API KEY REQUIRED” warning. At 390px, leaderboard document scrollWidth was 390.

These visits do not prove every feature works end to end. The current report page showed duplicate article H1 text, and Astro development-toolbar headings appeared in browser DOM probes; neither was treated as an accessibility pass. No provider credentials were inspected.

## Reproduction guidance

- XML: `uv run python` with `xml.etree.ElementTree.parse` over `assets/svg/*.svg`.
- Browser: open each SVG directly at its width/height; capture a screenshot, inspect labels/edges and mobile reflow. The SVGs are self-contained; no application server is required.
- Chart geometry: SVG group IDs `lead-comparison-chart`, `mobile-comparison-chart`, `area-comparison`, `comparison-dotplot-table`, `mobile-area-list` correspond to the source rows in data-evidence.json. Scales are documented in screen-data-map.md and interaction-spec.md.
- Source assets: decompress gzip JSON and verify checksums before comparing values. Newer repository exports may legitimately change the design snapshot.

PNG previews and temporary investigation scripts/logs were kept outside the repository; the editable SVGs are the authoritative deliverables. They are not raster screenshot wrappers.

## Explicitly not verified

- Full frontend build/E2E suite, repository-wide lint/type-check, Python tests or full pipeline. Sol asked for preferred lint/type-check commands; no answer was available during this phase. No production code changed, and these gates are not reported as passed.
- Revision 2 Safari/Firefox render validation, design-tool import fidelity, alternate local font metrics, dark mode, screen readers, real keyboard operation of proposed interactions, 200% text resize, reduced motion or real-user comprehension. Static SVGs specify these requirements; they do not implement or certify them.
- Full research reproduction/model accuracy, complete-market capture, source freshness, all-time duplicate semantics, or compatibility of independently produced asset generations.
- All upstream repository documentation links. A pre-existing missing `docs/analytics/README.md` provenance pointer is explicitly recorded as a defect, not repaired within this phase.

The next planning agent must rerun relevant gates against the implementation checkout and preserve this distinction between asset validation and application validation.
