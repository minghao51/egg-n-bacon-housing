# S3 implementation report — Fieldnotes tokens and accessible shell

Visual identity and shell accessibility only. No route, label, collection or data behaviour changed. **No commit.**

## 1. What changed

- `app/src/styles/globals.css` — light theme retuned to the Fieldnotes palette, keeping the existing `hsl(var(--token))` scheme so every existing utility keeps working. Sources: paper `#F6F3EC`, ink `#172E33`, teal `#006B65`, rust `#B64426`, plum `#66508A`, muted ink `#526368`, control border `#7A8583`, card `#FFFEFA` from `assets/svg/00-design-system.svg`; separator `#CDD2CA`, selected fill `#E5EFEB` and review note `#F8E8CC` from `assets/svg/design-rationale.md`. `--muted` (`#ECE7DB`) is labelled **derived**, because the design system has no neutral surface token. No external fonts: body is a local Arial/Helvetica stack, `h1`/`h2` are local Georgia. Tabular numerals for tables and `[data-numeric]`. Visible teal `:focus-visible` ring; reduced motion covers the drawer and the page-margin transition.
- `app/src/layouts/Layout.astro` — skip link ("Skip to main content") as the first focusable element.
- `app/src/components/Sidebar.astro` — exactly one `aria-current="page"` per page, base-path-aware matching (`Astro.url.pathname` includes the deployment base), slash-tolerant section matching, mobile drawer as a real modal surface: focus trap, Escape, focus restore to the toggle, backdrop click, `inert` when closed on mobile, background siblings `inert` while open, and a full silent reset when crossing the `lg` breakpoint.
- 11 route files — `id="main-content" tabindex="-1"` on `<main>`; `src/pages/index.astro` gained a real `<main>` wrapper (it had none, so the skip link had no target there).

Dark mode is deliberately untouched and explicitly unreviewed; it is not claimed to be validated.

## 2. Verification

| Check | Result |
|---|---|
| `cd app && bun run astro check` | **36 errors / 0 warnings / 43 hints / 125 files** — identical to the 36-error baseline, zero diagnostics in the touched files |
| `bun run build` (root base) | passes |
| `ASTRO_PAGES=true bun run build` (Pages base) | passes; exactly one `aria-current="page"` per page, hrefs prefixed `/egg-n-bacon-housing/` |
| Playwright suite | **103 pass** (unchanged count, no label/route regressions) |
| Browser: tokens | body `rgb(246,243,236)` on `rgb(23,46,51)` → 12.85:1; Arial body, Georgia `h1` |
| Browser: skip link | first tab stop on `/` and `/dashboard`; Enter moves focus to `main#main-content` |
| Browser: aria-current | exactly one per route on `/dashboard`, `/dashboard/map`, `/dashboard/leaderboard`, `/analytics/lease-decay`, `/catalog` |
| Browser: drawer | `inert` when closed; focus starts inside and stays inside across 40 Tab presses; Escape restores focus to the toggle; backdrop click closes it; background content is `inert` while open and cleared afterwards |
| Browser: breakpoint | open drawer → widen to 1400px → shrink to 390px leaves no backdrop, no stale translation, no stale `aria-expanded` and no stuck `inert` |
| Browser: reduced motion | page-margin transition duration `1e-05s` under `prefers-reduced-motion: reduce` |

## 3. Known limits

- The mobile drawer's close animation is unaffected for users who keep motion; only reduced-motion users get an instant close.
- `inert` is applied by script, so a JavaScript-disabled mobile visitor can still tab to the off-screen drawer (the drawer is only translated, not `display:none`). Progressive enhancement for that case needs a `no-js` class and is not implemented.
- The dashboard charts and KPI cards still use their component-level colours (blue series, red/green deltas). Restyling them is S4/S5 work, not part of the token layer; the page currently reads as editorial chrome around legacy chart colours.
- Dark mode remains the pre-existing palette and has not been contrast-checked; do not cite these results for dark mode.
