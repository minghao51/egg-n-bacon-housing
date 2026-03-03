import { test, expect } from '@playwright/test';
import { expectPageToLoadWithoutErrors } from '../utils/pageHealth';

test.describe('Dashboard - Market Overview', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/dashboard');
  });

  test('should load market overview page', async ({ page }) => {
    await expect(page).toHaveURL(/dashboard/);
    await expect(page.getByRole('heading', { name: 'Market Overview' })).toBeVisible();
  });

  test('should display sidebar navigation', async ({ page }) => {
    await expect(page.getByText('Egg n Bacon Housing')).toBeVisible();
    await expect(page.getByText('Market Overview').first()).toBeVisible();
    await expect(page.getByText('Interactive Map')).toBeVisible();
    await expect(page.getByText('Analysis Tools')).toBeVisible();
  });

  test('should display market overview dashboard content', async ({ page }) => {
    await expect(page.locator('main')).toBeVisible();
  });

  test('should have working navigation links in sidebar', async ({ page }) => {
    await page.getByText('Interactive Map').click();
    await expect(page).toHaveURL(/dashboard\/map/);
    await page.goBack();

    await page.getByText('Analysis Tools').click();
    await expect(page).toHaveURL(/dashboard\/trends/);
    await page.goBack();

    await page.getByText('Market Segments').click();
    await expect(page).toHaveURL(/dashboard\/segments/);
  });

  test('should navigate to analytics section', async ({ page }) => {
    await page.getByText('Analytics Index').click();
    await expect(page).toHaveURL(/analytics\/?$/);
  });

  test('should not have critical console errors', async ({ page }) => {
    await expectPageToLoadWithoutErrors(page, '/dashboard');
  });
});
