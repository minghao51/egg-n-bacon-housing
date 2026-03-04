import { test, expect } from '@playwright/test';
import { expectPageToLoadWithoutErrors } from '../utils/pageHealth';

async function gotoLeaderboard(page: import('@playwright/test').Page) {
  await page.goto('/dashboard/leaderboard');
  await page.waitForSelector('[data-interactive-ready="true"]');
}

test.describe('Dashboard - Compare Areas', () => {
  test('loads the redesigned leaderboard shell', async ({ page }) => {
    await gotoLeaderboard(page);
    await expect(page).toHaveURL(/dashboard\/leaderboard/);
    await expect(page.getByRole('heading', { name: 'Compare Areas', exact: true })).toBeVisible();
    await expect(page.getByLabel('Rank by')).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Filters' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Detailed Rankings' })).toBeVisible();
  });

  test('uses page-specific filters instead of the segments panel', async ({ page }) => {
    await gotoLeaderboard(page);
    await expect(page.getByText('Investment Goal')).toHaveCount(0);
    await expect(page.getByText('Spatial Hotspot')).toHaveCount(0);
    await expect(page.getByRole('heading', { name: 'Property Type' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Time Basis' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Median Price Range' })).toBeVisible();
  });

  test('rank by control drives the summary and table ordering', async ({ page }) => {
    await gotoLeaderboard(page);
    const summary = page.getByText(/Showing \d+ areas ranked by/i).first();
    await expect(summary).toContainText('year-over-year growth');

    await page.getByLabel('Rank by').selectOption('median_price');
    await expect(summary).toContainText('median price');

    const firstRow = page.locator('tbody tr').first();
    await expect(firstRow).toContainText('#1');
  });

  test('search and filters update the visible results', async ({ page }) => {
    await gotoLeaderboard(page);
    const summary = page.getByText(/Showing \d+ areas ranked by/i).first();
    await page.getByLabel('Search planning areas').fill('YISHUN');
    await expect(summary).toContainText('Showing 1 areas');
    await expect(page.locator('tbody tr')).toHaveCount(1);

    await page.getByRole('button', { name: 'Reset', exact: true }).click();
    await expect(page.locator('tbody tr')).not.toHaveCount(1);
  });

  test('mobile filter drawer opens and can be dismissed', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await gotoLeaderboard(page);
    await expect(page.getByRole('button', { name: /Filters \(\d+\)/ })).toBeVisible();
    await page.getByRole('button', { name: /Filters \(\d+\)/ }).click();
    await expect(page.getByRole('heading', { name: 'Leaderboard Filters' })).toBeVisible();
    await page.getByRole('button', { name: 'Close filters' }).click();
    await expect(page.getByRole('heading', { name: 'Leaderboard Filters' })).toHaveCount(0);
  });

  test('should have working navigation back to overview', async ({ page }) => {
    await gotoLeaderboard(page);
    await page.getByRole('link', { name: 'Overview' }).first().click();
    await expect(page).toHaveURL(/dashboard$/);
  });

  test('should not have critical console errors', async ({ page }) => {
    await expectPageToLoadWithoutErrors(page, '/dashboard/leaderboard', {
      ignoreConsoleErrors: ['does not provide an export', 'SyntaxError'],
      ignorePageErrors: ['does not provide an export', 'SyntaxError'],
    });
  });
});
