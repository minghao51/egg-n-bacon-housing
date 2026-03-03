import { test, expect } from '@playwright/test';
import { expectPageToLoadWithoutErrors } from '../utils/pageHealth';

test.describe('Analytics Articles', () => {
  const articles = [
    { slug: 'lease-decay', title: 'Lease Decay' },
    { slug: 'mrt-impact', title: 'MRT Impact' },
    { slug: 'price-forecasts', title: 'Price Forecasts' },
    { slug: 'findings', title: 'Findings' },
    { slug: 'spatial-hotspots', title: 'Spatial Hotspots' },
    { slug: 'spatial-autocorrelation', title: 'Spatial Autocorrelation' },
    { slug: 'school-quality', title: 'School Quality' },
    { slug: 'causal-inference-overview', title: 'Causal Inference' },
  ];

  articles.forEach(({ slug, title }) => {
    test(`should load ${title} article`, async ({ page }) => {
      await page.goto(`/analytics/${slug}`);
      await expect(page).toHaveURL(new RegExp(`/analytics/${slug}`));
      await expect(page.locator('main')).toBeVisible();
    });

    test(`should display sidebar on ${title} article`, async ({ page }) => {
      await page.goto(`/analytics/${slug}`);
      await expect(page.getByText('Egg n Bacon Housing')).toBeVisible();
    });

    test(`should not have critical errors on ${title} article`, async ({ page }) => {
      await expectPageToLoadWithoutErrors(page, `/analytics/${slug}`);
    });
  });

  test('should navigate between articles using sidebar', async ({ page }) => {
    await page.goto('/analytics/lease-decay');
    await page.getByRole('link', { name: /MRT Impact/i }).first().click();
    await expect(page).toHaveURL(/analytics\/mrt-impact/);
  });
});
