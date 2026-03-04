import { test, expect } from '@playwright/test';

test.describe('Cross-Page Navigation', () => {
  test('should navigate from home to dashboard and back', async ({ page }) => {
    await page.goto('/');
    await page.getByText('Live Dashboard').click();
    await expect(page).toHaveURL(/dashboard/);
    await page.goto('/');
    await expect(page).toHaveURL('/');
  });

  test('should navigate from dashboard to analytics and back', async ({ page }) => {
    await page.goto('/dashboard');
    await page.getByText('Analytics Index').click();
    await expect(page).toHaveURL(/analytics/);
    await page.getByText('Overview').click();
    await expect(page).toHaveURL(/dashboard/);
  });

  test('should navigate from analytics to persona and back', async ({ page }) => {
    await page.goto('/analytics/');
    await page.getByRole('link', { name: /First-Time Buyer/i }).first().click();
    await expect(page).toHaveURL(/personas\/first-time-buyer/);
    await page.getByText('Analytics Index').click();
    await expect(page).toHaveURL(/analytics\/?$/);
  });

  test('should navigate between different dashboard pages', async ({ page }) => {
    await page.goto('/dashboard');
    
    await page.getByRole('link', { name: /Explore Areas/ }).first().click();
    await expect(page).toHaveURL(/dashboard\/map/);
    
    await page.getByRole('link', { name: /Decision Tools/ }).first().click();
    await expect(page).toHaveURL(/dashboard\/trends/);
    
    await page.getByRole('link', { name: /Discover Segments/ }).first().click();
    await expect(page).toHaveURL(/dashboard\/segments/);
    
    await page.getByRole('link', { name: /Compare Areas/ }).first().click();
    await expect(page).toHaveURL(/dashboard\/leaderboard/);
  });
});

test.describe('Dark Mode Toggle', () => {
  test('should have dark mode toggle in sidebar', async ({ page }) => {
    await page.goto('/dashboard');
    const toggle = page.locator('button[class*="toggle"], [aria-label*="dark"], [class*="DarkMode"]');
    const count = await toggle.count();
    expect(count).toBeGreaterThan(0);
  });
});

test.describe('Responsive Behavior', () => {
  test('should display correctly on desktop', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.goto('/');
    await expect(page).toHaveTitle(/Egg n Bacon/);
    await expect(page.getByText('Egg n Bacon Housing')).toBeVisible();
  });

  test('should display correctly on tablet', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto('/');
    await expect(page).toHaveTitle(/Egg n Bacon/);
  });

  test('should display correctly on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');
    await expect(page).toHaveTitle(/Egg n Bacon/);
  });
});

test.describe('Data Loading', () => {
  test('should load dashboard data', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');
    const content = await page.locator('main').textContent();
    expect(content).toBeTruthy();
  });

  test('should load analytics index data', async ({ page }) => {
    await page.goto('/analytics/');
    await page.waitForLoadState('networkidle');
    await expect(page.getByText('Total Reports')).toBeVisible();
  });
});

test.describe('Accessibility', () => {
  test('should have proper page titles', async ({ page }) => {
    const pages = [
      { url: '/', title: 'Egg n Bacon' },
      { url: '/dashboard', title: 'Dashboard' },
      { url: '/analytics/', title: 'Analytics' },
    ];

    for (const { url, title } of pages) {
      await page.goto(url);
      const pageTitle = await page.title();
      expect(pageTitle).toContain(title);
    }
  });

  test('should have heading hierarchy', async ({ page }) => {
    await page.goto('/dashboard');
    const h1 = page.locator('h1');
    await expect(h1).toBeVisible();
  });

  test('should have link text', async ({ page }) => {
    await page.goto('/');
    const links = page.locator('a');
    const count = await links.count();
    expect(count).toBeGreaterThan(0);
    
    for (let i = 0; i < Math.min(count, 10); i++) {
      const link = links.nth(i);
      const text = await link.textContent();
      expect(text?.trim()).toBeTruthy();
    }
  });
});
