# E2E Testing Guide

**Last Updated**: 2026-02-26 | **Status**: Active

---

## Overview

This guide covers end-to-end (E2E) testing for the Egg n Bacon Housing webapp using Playwright.

**Testing Framework**: Playwright with Chromium browser

**Test Location**: `app/tests/e2e/`

---

## Quick Reference

All commands should be run from the `app/` directory:

| Command | Purpose |
|---------|---------|
| `cd app && npm run test:e2e` | Run all E2E tests |
| `cd app && npm run test:e2e:prod` | Build the app, then run E2E tests against `astro preview` |
| `cd app && npm run test:e2e:headed` | Run tests in headed mode (visible browser) |
| `cd app && npm run test:e2e:ui` | Run tests in UI mode |
| `cd app && npm run test:e2e:debug` | Debug mode with auto-opening browser |
| `cd app && npm run test:e2e:report` | View HTML test report |

---

## Installation

Playwright is already installed in the `app/` directory. If you need to reinstall:

```bash
cd app
npm install
npx playwright install chromium
```

---

## Running Tests

### Run All Tests

```bash
cd app && npm run test:e2e
```

This will:
1. Start the Astro dev server (`npm run dev -- --host 127.0.0.1`)
2. Run all E2E tests in headless Chromium
3. Generate HTML report in `playwright-report/`

### Run Against the Production Build

```bash
cd app && npm run test:e2e:prod
```

This will:
1. Build the app with `npm run build`
2. Start `astro preview` on `127.0.0.1:4321`
3. Run the same E2E suite against the built output

### Run in Headed Mode

```bash
cd app && npm run test:e2e:headed
```

Useful for:
- Watching tests execute in real-time
- Debugging visual issues
- Understanding test flow

### Run in UI Mode

```bash
cd app && npm run test:e2e:ui
```

Features:
- Interactive test selection
- Live execution view
- Time-travel debugging
- Trace viewer integration

### Debug Mode

```bash
cd app && npm run test:e2e:debug
```

Opens browser automatically on test failure with full debugging tools.

### View Report

```bash
cd app && npm run test:e2e:report
```

Opens the HTML test report in your browser.

---

## Test Structure

```
app/tests/e2e/
├── home.spec.ts           # Homepage tests
├── cross-page.spec.ts     # Navigation & interaction tests
├── dashboard/
│   ├── overview.spec.ts   # Market Overview page
│   ├── map.spec.ts        # Interactive Map page
│   ├── trends.spec.ts     # Analysis Tools page
│   ├── segments.spec.ts   # Market Segments page
│   └── leaderboard.spec.ts # Area Rankings page
└── analytics/
    ├── index.spec.ts      # Analytics index page
    ├── articles.spec.ts   # Individual article pages
    └── personas.spec.ts   # Persona pages
```

---

## Test Coverage

### Home Page
- Page loads without errors
- Hero section displays correctly
- Navigation cards work
- Key insights display
- Navigation to dashboard/analytics

### Dashboard Pages
- Market Overview
- Interactive Map
- Analysis Tools (Trends)
- Market Segments
- Area Rankings (Leaderboard)

Each dashboard page tests:
- Page loads correctly
- Sidebar navigation works
- Content displays
- No console errors

### Analytics Pages
- Analytics index page
- All 8+ analytics articles
- 3 persona pages (First-Time Buyer, Investor, Upgrader)

### Cross-Page Tests
- Navigation between pages
- Dark mode toggle presence
- Responsive behavior (desktop, tablet, mobile)
- Data loading
- Accessibility (headings, links)

---

## Writing Tests

### Basic Test Structure

```typescript
import { test, expect } from '@playwright/test';

test.describe('Page Name', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/page-url');
  });

  test('should display page title', async ({ page }) => {
    await expect(page).toHaveURL(/page-url/);
    await expect(page.getByRole('heading', { name: 'Page Title' })).toBeVisible();
  });

  test('should navigate correctly', async ({ page }) => {
    await page.getByText('Link Text').click();
    await expect(page).toHaveURL(/destination/);
  });
});
```

### Testing Interactions

```typescript
test('should filter data correctly', async ({ page }) => {
  await page.goto('/dashboard/segments');
  await page.getByRole('button', { name: 'Filter Option' }).click();
  await expect(page.locator('.results')).toContainText('Expected Result');
});
```

### Handling Async Data

```typescript
test('should load dashboard data', async ({ page }) => {
  await page.goto('/dashboard');
  await page.waitForLoadState('networkidle');
  await expect(page.locator('main')).toBeVisible();
});
```

### Checking Console Errors

```typescript
test('should not have console errors', async ({ page }) => {
  const errors: string[] = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      errors.push(msg.text());
    }
  });
  await page.goto('/');
  await page.waitForLoadState('networkidle');
  const criticalErrors = errors.filter(e => !e.includes('favicon'));
  expect(criticalErrors).toHaveLength(0);
});
```

---

## Configuration

The `playwright.config.ts` file is configured with:

- **Base URL**: `http://127.0.0.1:4321` by default
- **Browser**: Chromium only
- **Web Server**: Configurable via `PLAYWRIGHT_SERVER_COMMAND` (defaults to Astro dev)
- **Retries**: 2 in CI, 0 locally
- **Reporters**: HTML + List

### Modifying Configuration

To change browser:
```typescript
projects: [
  {
    name: 'chromium',
    use: { ...devices['Desktop Chrome'] },
  },
  // Add more browsers:
  // { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
  // { name: 'webkit', use: { ...devices['Desktop Safari'] } },
],
```

To change base URL:
```typescript
use: {
  baseURL: 'http://localhost:4321',
  // ...
},
```

---

## Debugging

### Using Trace Viewer

1. Run tests with trace on retry:
   ```bash
   npx playwright test --trace on
   ```

2. View trace:
   ```bash
   npx playwright show-trace trace.zip
   ```

### Using UI Mode

```bash
cd app && npm run test:e2e:ui
```

Click on a test to see:
- Screenshot per step
- Console logs
- Network requests
- Actionable locators

### Using Headed Mode

```bash
cd app && npm run test:e2e:headed
```

### Common Issues

| Issue | Solution |
|-------|----------|
| Server not starting | Run `cd app && npm run dev` manually first |
| Port 4321 in use | Kill process using port 4321 |
| Tests timeout | Increase timeout in config |
| Locator not found | Check element exists, use waitFor |

---

## CI/CD Integration

Add to your CI workflow:

```yaml
- name: E2E Tests
  working-directory: app
  run: |
    npm install
    npx playwright install chromium
    npm run test:e2e
```

---

## Best Practices

1. **Use descriptive test names**: `should display navigation` not `test1`

2. **Test one thing per test**: Separate navigation tests from content tests

3. **Use proper locators**:
   ```typescript
   // Good
   await page.getByRole('button', { name: 'Submit' })
   await page.getByText('Dashboard')
   
   // Avoid
   await page.locator('.btn-primary').first()
   ```

4. **Handle async properly**: Use `waitForLoadState('networkidle')` for data-driven pages

5. **Check for console errors**: Filter out expected errors (favicon, 404s)

6. **Test critical paths**: Focus on user journeys that matter

---

## Running Specific Tests

```bash
cd app

# Run only home tests
npx playwright test tests/e2e/home.spec.ts

# Run only dashboard tests
npx playwright test tests/e2e/dashboard/

# Run tests matching pattern
npx playwright test -g "should load"

# Run with grep
npx playwright test --grep "navigation"
```

---

## Related Documentation

- [Playwright Docs](https://playwright.dev/docs/intro)
- [Testing Guide](./testing-guide.md) - Python/pytest testing
- [Architecture Guide](./architecture.md) - System overview
