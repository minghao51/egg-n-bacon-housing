import { test, expect } from '@playwright/test';
import { expectPageToLoadWithoutErrors } from '../utils/pageHealth';

test.describe('Dashboard - Decision Tools', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/dashboard/trends');
  });

  test('should load decision tools page', async ({ page }) => {
    await expect(page).toHaveURL(/dashboard\/trends/);
    await expect(page.getByRole('heading', { name: 'Decision Tools' })).toBeVisible();
  });

  test('should display sidebar navigation', async ({ page }) => {
    await expect(page.getByText('Egg n Bacon Housing')).toBeVisible();
    await expect(page.getByRole('link', { name: /Overview/ }).first()).toBeVisible();
  });

  test('should display trends dashboard content', async ({ page }) => {
    await expect(page.locator('main')).toBeVisible();
  });

  test('should display tool tabs if available', async ({ page }) => {
    const tabs = page.locator('button[role="tab"], .tab, [class*="tab"]');
    const count = await tabs.count();
    if (count > 0) {
      await expect(tabs.first()).toBeVisible();
    }
  });

  test('should have working navigation back to overview', async ({ page }) => {
    await page.getByRole('link', { name: 'Overview' }).first().click();
    await expect(page).toHaveURL(/dashboard$/);
  });

  test('should not have critical console errors', async ({ page }) => {
    await expectPageToLoadWithoutErrors(page, '/dashboard/trends', {
      ignoreConsoleErrors: [
        'does not provide an export',
        'SyntaxError',
        'GeoJSON',
        'compressed data',
        'Invalid value for prop',
      ],
      ignorePageErrors: [
        'does not provide an export',
        'SyntaxError',
        'GeoJSON',
        'compressed data',
        'Invalid value for prop',
      ],
    });
  });
});
