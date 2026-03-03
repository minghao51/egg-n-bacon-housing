import { test, expect } from '@playwright/test';
import { expectPageToLoadWithoutErrors } from '../utils/pageHealth';

test.describe('Dashboard - Market Segments', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/dashboard/segments');
  });

  test('should load market segments page', async ({ page }) => {
    await expect(page).toHaveURL(/dashboard\/segments/);
    await expect(page.locator('main')).toBeVisible();
  });

  test('should display sidebar navigation', async ({ page }) => {
    await expect(page.getByText('Egg n Bacon Housing')).toBeVisible();
    await expect(page.getByText('Market Overview').first()).toBeVisible();
  });

  test('should display segments analysis content', async ({ page }) => {
    await expect(page.locator('main')).toBeVisible();
  });

  test('should have interactive elements', async ({ page }) => {
    const buttons = page.locator('button');
    const count = await buttons.count();
    expect(count).toBeGreaterThan(0);
  });

  test('should have working navigation back to overview', async ({ page }) => {
    await page.getByRole('link', { name: 'Market Overview' }).first().click();
    await expect(page).toHaveURL(/dashboard$/);
  });

  test('should not have critical console errors', async ({ page }) => {
    await expectPageToLoadWithoutErrors(page, '/dashboard/segments', {
      ignoreConsoleErrors: ['does not provide an export', 'SyntaxError'],
      ignorePageErrors: ['does not provide an export', 'SyntaxError'],
    });
  });
});
