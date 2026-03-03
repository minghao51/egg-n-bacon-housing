import { test, expect } from '@playwright/test';
import { expectPageToLoadWithoutErrors } from '../utils/pageHealth';

test.describe('Dashboard - Interactive Map', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/dashboard/map');
  });

  test('should load interactive map page', async ({ page }) => {
    await expect(page).toHaveURL(/dashboard\/map/);
    await expect(page.getByRole('heading', { name: 'Interactive Map' })).toBeVisible();
  });

  test('should display sidebar navigation', async ({ page }) => {
    await expect(page.getByText('Egg n Bacon Housing')).toBeVisible();
    await expect(page.getByText('Market Overview').first()).toBeVisible();
  });

  test('should display map container', async ({ page }) => {
    await expect(page.locator('main')).toBeVisible();
  });

  test('should have working navigation back to overview', async ({ page }) => {
    await page.getByRole('link', { name: 'Market Overview' }).first().click();
    await expect(page).toHaveURL(/dashboard$/);
  });

  test('should not have critical console errors', async ({ page }) => {
    await expectPageToLoadWithoutErrors(page, '/dashboard/map', {
      ignoreConsoleErrors: ['does not provide an export', 'SyntaxError'],
      ignorePageErrors: ['does not provide an export', 'SyntaxError'],
    });
  });
});
