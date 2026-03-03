import { test, expect } from '@playwright/test';
import { expectPageToLoadWithoutErrors } from '../utils/pageHealth';

test.describe('Persona Pages', () => {
  test.describe('First-Time Buyer Persona', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/analytics/personas/first-time-buyer');
    });

    test('should load first-time-buyer persona page', async ({ page }) => {
      await expect(page).toHaveURL(/analytics\/personas\/first-time-buyer/);
      await expect(page.getByText('First-Time Buyer')).toBeVisible();
    });

    test('should display sidebar navigation', async ({ page }) => {
      await expect(page.getByText('Egg n Bacon Housing')).toBeVisible();
    });

    test('should display persona content', async ({ page }) => {
      await expect(page.locator('main')).toBeVisible();
    });

    test('should navigate back to analytics index', async ({ page }) => {
      await page.getByText('Analytics Index').click();
      await expect(page).toHaveURL(/analytics\/?$/);
    });
  });

  test.describe('Investor Persona', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/analytics/personas/investor');
    });

    test('should load investor persona page', async ({ page }) => {
      await expect(page).toHaveURL(/analytics\/personas\/investor/);
      await expect(page.getByRole('heading', { name: 'Property Investor' })).toBeVisible();
    });

    test('should display sidebar navigation', async ({ page }) => {
      await expect(page.getByText('Egg n Bacon Housing')).toBeVisible();
    });

    test('should display persona content', async ({ page }) => {
      await expect(page.locator('main')).toBeVisible();
    });
  });

  test.describe('Upgrader Persona', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/analytics/personas/upgrader');
    });

    test('should load upgrader persona page', async ({ page }) => {
      await expect(page).toHaveURL(/analytics\/personas\/upgrader/);
      await expect(page.getByRole('heading', { name: 'Upsizer / Upgrader' })).toBeVisible();
    });

    test('should display sidebar navigation', async ({ page }) => {
      await expect(page.getByText('Egg n Bacon Housing')).toBeVisible();
    });

    test('should display persona content', async ({ page }) => {
      await expect(page.locator('main')).toBeVisible();
    });
  });

  test('should not have critical console errors on persona pages', async ({ page }) => {
    const personas = ['first-time-buyer', 'investor', 'upgrader'];
    for (const persona of personas) {
      await expectPageToLoadWithoutErrors(page, `/analytics/personas/${persona}`);
    }
  });
});
