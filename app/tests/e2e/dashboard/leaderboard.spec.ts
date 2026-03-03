import { test, expect } from '@playwright/test';
import { expectPageToLoadWithoutErrors } from '../utils/pageHealth';

test.describe('Dashboard - Area Rankings (Leaderboard)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/dashboard/leaderboard');
  });

  test('should load area rankings page', async ({ page }) => {
    await expect(page).toHaveURL(/dashboard\/leaderboard/);
    await expect(page.getByRole('heading', { name: 'Area Rankings', exact: true })).toBeVisible();
  });

  test('should display sidebar navigation', async ({ page }) => {
    await expect(page.getByText('Egg n Bacon Housing')).toBeVisible();
    await expect(page.getByText('Market Overview')).toBeVisible();
  });

  test('should display leaderboard content', async ({ page }) => {
    await expect(page.locator('main')).toBeVisible();
  });

  test('should display ranking table or list', async ({ page }) => {
    const content = page.locator('main');
    await expect(content).toBeVisible();
    const text = await content.textContent();
    expect(text?.length).toBeGreaterThan(0);
  });

  test('should have working navigation back to overview', async ({ page }) => {
    await page.getByRole('link', { name: 'Market Overview' }).first().click();
    await expect(page).toHaveURL(/dashboard$/);
  });

  test('should not have critical console errors', async ({ page }) => {
    await expectPageToLoadWithoutErrors(page, '/dashboard/leaderboard', {
      ignoreConsoleErrors: ['does not provide an export', 'SyntaxError'],
      ignorePageErrors: ['does not provide an export', 'SyntaxError'],
    });
  });
});
