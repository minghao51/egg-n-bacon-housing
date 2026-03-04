import { test, expect, type Page } from '@playwright/test';
import { expectPageToLoadWithoutErrors } from '../utils/pageHealth';

async function gotoSegments(page: Page) {
  await page.goto('/dashboard/segments');
  await expect(page.getByRole('heading', { name: 'Discover Segments', exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: /Discover/ }).first()).toBeVisible();
}

async function openFirstInvestigation(page: Page) {
  await gotoSegments(page);
  const investigateCtas = page.getByRole('button', { name: 'Investigate' });
  await expect(investigateCtas.last()).toBeVisible();
  await investigateCtas.last().click();
  await expect(page.getByRole('button', { name: 'Change Segment' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Investigation Lens' })).toBeVisible();
}

test.describe('Dashboard - Discover Segments', () => {
  test('loads the redesigned segments shell', async ({ page }) => {
    await gotoSegments(page);
    await expect(page).toHaveURL(/dashboard\/segments/);
    await expect(page.getByRole('button', { name: 'Metrics Guide' })).toBeVisible();
    await expect(page.getByText('Selected Segment').first()).toBeVisible();
    await expect(page.getByRole('button', { name: /Investigate/ }).first()).toBeDisabled();
    await expect(page.getByRole('heading', { name: 'Constraints' })).toBeVisible();
  });

  test('selecting a segment unlocks the investigation workspace', async ({ page }) => {
    await openFirstInvestigation(page);
    await expect(page.getByRole('button', { name: /Investigate/ }).first()).toBeEnabled();
    await expect(page.getByRole('heading', { name: 'Geographic Match Map' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Matching Areas' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Area Evidence' })).toBeVisible();
  });

  test('investigation metric controls update the shortlist ordering label', async ({ page }) => {
    await openFirstInvestigation(page);

    const sortLabel = page.getByText(/Sorted by /).first();
    await expect(sortLabel).toContainText('Avg PSF');

    await page.getByRole('button', { name: 'Avg Yield' }).click();
    await expect(sortLabel).toContainText('Avg Yield');

    await page.getByRole('button', { name: 'Persistence' }).click();
    await expect(sortLabel).toContainText('Persistence');
  });

  test('clicking a shortlist row updates the area evidence panel', async ({ page }) => {
    await openFirstInvestigation(page);

    const firstRow = page.locator('tbody tr').first();
    const firstAreaName = (await firstRow.locator('td').first().textContent())?.trim();
    expect(firstAreaName).toBeTruthy();

    await firstRow.click();
    await expect(page.getByRole('heading', { name: 'Area Evidence' })).toBeVisible();
    await expect(page.getByText(new RegExp(`${firstAreaName} is currently selected`, 'i'))).toBeVisible();
  });

  test('constraints can narrow the investigation to an explicit empty state', async ({ page }) => {
    await openFirstInvestigation(page);

    await page.getByLabel('Core Central Region').uncheck();
    await page.getByLabel('Rest of Central Region').uncheck();

    await expect(page.getByText('No candidate areas match the current constraints.')).toBeVisible();
  });

  test('should have working navigation back to overview', async ({ page }) => {
    await gotoSegments(page);
    await page.getByRole('link', { name: 'Overview' }).first().click();
    await expect(page).toHaveURL(/dashboard$/);
  });

  test('should not have critical console errors', async ({ page }) => {
    await expectPageToLoadWithoutErrors(page, '/dashboard/segments', {
      ignoreConsoleErrors: ['does not provide an export', 'SyntaxError'],
      ignorePageErrors: ['does not provide an export', 'SyntaxError'],
    });
  });
});
