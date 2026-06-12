# E2E Testing Guide

**Last Updated**: 2026-06-12 | **Status**: Active

## Overview

This guide covers Playwright-based end-to-end testing for the Astro app under `app/`.

## Quick Reference

Run commands from `app/`:

| Command                   | Purpose                                       |
| ------------------------- | --------------------------------------------- |
| `bun run test:e2e`        | Run the full E2E suite                        |
| `bun run test:e2e:prod`   | Build first, then run against `astro preview` |
| `bun run test:e2e:headed` | Run with a visible browser                    |
| `bun run test:e2e:ui`     | Open Playwright UI mode                       |
| `bun run test:e2e:debug`  | Run in debug mode                             |
| `bun run test:e2e:report` | Open the HTML report                          |

## Installation

```bash
cd app
bun install
bunx playwright install chromium
```

## Running Tests

### Dev-server flow

```bash
cd app
bun run test:e2e
```

This starts the local dev server and runs the suite in headless Chromium.

### Preview build flow

```bash
cd app
bun run test:e2e:prod
```

This builds the app, starts `astro preview`, and runs the same suite against the built output.

## Test Location

```text
app/tests/e2e/
├── home.spec.ts
├── cross-page.spec.ts
├── dashboard/
└── analytics/
```

## Common Issues

| Issue               | Fix                                            |
| ------------------- | ---------------------------------------------- |
| Server not starting | Run `bun run dev -- --host 127.0.0.1` manually |
| Browser missing     | Run `bunx playwright install chromium`         |
| Build-only failure  | Run `bun run build` before the suite           |

## Related Files

- [app/package.json](../../app/package.json)
- [app/playwright.config.ts](../../app/playwright.config.ts)
- [CI workflow](../../.github/workflows/ci.yml)
