import { test, expect } from '@playwright/test';
import { expectPageToLoadWithoutErrors } from '../utils/pageHealth';

test.describe('Analytics Index Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/analytics/');
  });

  test('should load analytics index page', async ({ page }) => {
    await expect(page).toHaveURL(/analytics\/?$/);
    await expect(page.getByRole('heading', { name: 'Singapore Housing Market Analytics' })).toBeVisible();
  });

  test('should display sidebar navigation', async ({ page }) => {
    await expect(page.getByText('Egg n Bacon Housing')).toBeVisible();
  });

  test('should display persona cards', async ({ page }) => {
    await expect(page.getByText('First-Time Buyer').first()).toBeVisible();
    await expect(page.getByText('Property Investor').first()).toBeVisible();
    await expect(page.getByText('Upsizer / Upgrader').first()).toBeVisible();
  });

  test('should navigate to first-time-buyer persona', async ({ page }) => {
    await page.getByRole('link', { name: /First-Time Buyer/i }).first().click();
    await expect(page).toHaveURL(/analytics\/personas\/first-time-buyer/);
  });

  test('should navigate to investor persona', async ({ page }) => {
    await page.getByText('Property Investor').click();
    await expect(page).toHaveURL(/analytics\/personas\/investor/);
  });

  test('should navigate to upgrader persona', async ({ page }) => {
    await page.getByText('Upsizer / Upgrader').click();
    await expect(page).toHaveURL(/analytics\/personas\/upgrader/);
  });

  test('should display quick stats', async ({ page }) => {
    await expect(page.getByText('Total Reports')).toBeVisible();
    await expect(page.getByText('Data Coverage')).toBeVisible();
    await expect(page.getByText('Categories')).toBeVisible();
  });

  test('should display category sections', async ({ page }) => {
    const content = page.locator('main');
    await expect(content).toBeVisible();
  });

  test('should navigate to an analytics article', async ({ page }) => {
    const articles = page.locator('main a[href*="/analytics/"]');
    const firstArticle = articles.first();
    await firstArticle.click();
    await expect(page).toHaveURL(/\/analytics\/.+/);
  });

  test('should not have critical console errors', async ({ page }) => {
    await expectPageToLoadWithoutErrors(page, '/analytics/');
  });
});
