# Egg n Bacon Housing App

Astro app for the dashboard and analytics browsing experience.

## Stack

- Bun
- Astro
- React
- Playwright

## Install

```bash
bun install
```

## Development

```bash
bun run dev
```

## Build

```bash
bun run build
bun run preview
```

## Content and Data Sources

- analytics markdown is loaded directly from `../docs/analytics/` through `app/src/content.config.ts`
- dashboard and interactive-tool data is served from `public/data/`
- analytics images used by articles are served from `public/data/analysis/`

There is no supported generated analytics-content copy or legacy sync-shell step in the current repo shape.

## E2E Tests

```bash
bun run test:e2e
bun run test:e2e:prod
```
