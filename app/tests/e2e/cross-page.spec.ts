import { test, expect } from "@playwright/test";

test.describe("Cross-Page Navigation", () => {
  test("should navigate from home to dashboard and back", async ({ page }) => {
    await page.goto("/");
    // `/` is the Overview destination; `/dashboard` is its kept compatibility
    // address, still linked from the sidebar's Dashboard section.
    await page.locator('a[href="/dashboard"]').first().click();
    await expect(page).toHaveURL(/dashboard/);
    await page.goto("/");
    await expect(page).toHaveURL("/");
  });

  test("should navigate from dashboard to analytics and back", async ({
    page,
  }) => {
    await page.goto("/dashboard");
    // The header carries the four destinations; Research is the route to the
    // Studies library now that the sidebar is a per-section menu.
    await page
      .getByRole("navigation", { name: "Primary" })
      .getByRole("link", { name: "Research", exact: true })
      .click();
    await expect(page).toHaveURL(/analytics/);
    // The library no longer renders the dashboard group, so the way back is the
    // Overview destination (site root); the compatibility address for it is
    // still one click away from the sidebar.
    await page
      .getByRole("navigation", { name: "Primary" })
      .getByRole("link", { name: "Overview", exact: true })
      .click();
    await expect(page).toHaveURL("/");
    await page.locator('a[href="/dashboard"]').first().click();
    await expect(page).toHaveURL(/dashboard/);
  });

  test("should navigate from analytics to persona and back", async ({
    page,
  }) => {
    await page.goto("/analytics/");
    await page
      .getByRole("link", { name: /First-Time Buyer/i })
      .first()
      .click();
    await expect(page).toHaveURL(/personas\/first-time-buyer/);
    await page
      .getByRole("navigation", { name: "Main navigation" })
      .getByRole("link", { name: "Studies", exact: true })
      .click();
    await expect(page).toHaveURL(/analytics\/?$/);
  });

  test("should navigate between different dashboard pages", async ({
    page,
  }) => {
    await page.goto("/dashboard");

    // The dashboard group reaches each route: `/research/*` pages swap the
    // group for the research subnav, so return to `/dashboard` between hops.
    await page
      .getByRole("link", { name: /Research map/ })
      .first()
      .click();
    await expect(page).toHaveURL(/research\/map/);

    await page.goBack();
    await page
      .getByRole("link", { name: /Decision Tools/ })
      .first()
      .click();
    await expect(page).toHaveURL(/research\/tools/);

    await page.goBack();
    await page
      .getByRole("link", { name: /Discover Segments/ })
      .first()
      .click();
    await expect(page).toHaveURL(/research\/segments/);

    await page.goBack();
    await page
      .getByRole("link", { name: /Compare Areas/ })
      .first()
      .click();
    await expect(page).toHaveURL(/dashboard\/leaderboard/);
  });
});

test.describe("Light-only theme", () => {
  test("offers no dark-mode toggle and declares a light colour-scheme", async ({
    page,
  }) => {
    await page.goto("/dashboard");
    // Dark mode was removed: the old `.dark` token block was never
    // contrast-reviewed, so no control may offer it back.
    await expect(
      page.locator(
        'button[aria-label*="dark" i], [class*="DarkMode"], [class*="theme-toggle"]',
      ),
    ).toHaveCount(0);
    // Nothing applies the class, so the `dark:` utilities stay inert.
    await expect(page.locator("html")).not.toHaveClass(/\bdark\b/);
    // Native controls, scrollbars and form widgets stay light even when the
    // visitor's OS prefers dark.
    await expect(page.locator("html")).toHaveCSS("color-scheme", "light");
  });
});

test.describe("Responsive Behavior", () => {
  test("should display correctly on desktop", async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.goto("/");
    await expect(page).toHaveTitle(/Egg n Bacon/);
    // The four destinations are in the header bar at this width, and the
    // sidebar tapers to the section menu for the current section.
    const primary = page.getByRole("navigation", { name: "Primary" });
    await expect(primary.getByRole("link")).toHaveCount(4);
    await expect(
      primary.getByRole("link", { name: "Overview", exact: true }),
    ).toHaveAttribute("aria-current", "page");
    await expect(
      page.getByRole("navigation", { name: "Main navigation" }),
    ).toBeVisible();
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await expect(page.locator('a[href="/dashboard"]').first()).toBeVisible();
  });

  test("should display correctly on tablet", async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto("/");
    await expect(page).toHaveTitle(/Egg n Bacon/);
  });

  test("should display correctly on mobile", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto("/");
    await expect(page).toHaveTitle(/Egg n Bacon/);
  });
});

test.describe("Data Loading", () => {
  test("should load dashboard data", async ({ page }) => {
    await page.goto("/dashboard");
    await page.waitForLoadState("networkidle");
    const content = await page.locator("main").textContent();
    expect(content).toBeTruthy();
  });

  test("should load analytics index data", async ({ page }) => {
    await page.goto("/analytics/");
    await page.waitForLoadState("networkidle");
    await expect(
      page.getByText("Published studies", { exact: true }),
    ).toBeVisible();
  });
});

test.describe("Accessibility", () => {
  test("should have proper page titles", async ({ page }) => {
    const pages = [
      { url: "/", title: "Egg n Bacon" },
      { url: "/dashboard", title: "Dashboard" },
      { url: "/analytics/", title: "Studies" },
    ];

    for (const { url, title } of pages) {
      await page.goto(url);
      const pageTitle = await page.title();
      expect(pageTitle).toContain(title);
    }
  });

  test("should have heading hierarchy", async ({ page }) => {
    await page.goto("/dashboard");
    const h1 = page.locator("h1");
    await expect(h1).toBeVisible();
  });

  test("should have link text", async ({ page }) => {
    await page.goto("/");
    const links = page.locator("a");
    const count = await links.count();
    expect(count).toBeGreaterThan(0);

    for (let i = 0; i < Math.min(count, 10); i++) {
      const link = links.nth(i);
      const text = await link.textContent();
      expect(text?.trim()).toBeTruthy();
    }
  });
});
