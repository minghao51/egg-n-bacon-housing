import { test, expect } from "@playwright/test";
import { expectPageToLoadWithoutErrors } from "../utils/pageHealth";

test.describe("Dashboard - Market Overview", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/dashboard");
  });

  test("should load market overview page", async ({ page }) => {
    await expect(page).toHaveURL(/dashboard/);
    // Same surface as the root, so the same one `h1`. This URL is the
    // compatibility address: it says so, and its canonical points at the root.
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(
      "What does a home cost here?",
    );
    await expect(page.locator('link[rel="canonical"]')).toHaveAttribute(
      "href",
      /\/$/,
    );
    await expect(page.locator('[data-compat-route="true"]')).toContainText(
      "Compatibility address for the Overview",
    );
    await expect(
      page.locator('[data-compat-route="true"]').getByRole("link"),
    ).toHaveAttribute("href", /^\/.*$/);
  });

  test("shows the verified current-data window", async ({ page }) => {
    const strip = page.locator('[data-current-data="2026-10"]');
    await expect(strip).toBeVisible();
    await expect(
      strip.getByRole("heading", { name: "Current data" }),
    ).toBeVisible();
    await expect(strip).toContainText("cutoff 2026-10");
    await expect(strip).toContainText("21,801 sales");
    await expect(strip).toContainText("+1.9% vs prior year");
    // Private scopes are labelled as records under review, not as a headline.
    await expect(strip).toContainText("still under coverage review");
  });

  test("should display sidebar navigation", async ({ page }) => {
    await expect(
      page.getByRole("navigation", { name: "Main navigation" }),
    ).toBeVisible();
    await expect(
      page.getByRole("link", { name: /Overview/ }).first(),
    ).toBeVisible();
    await expect(
      page.getByRole("link", { name: /Research map/ }).first(),
    ).toBeVisible();
    await expect(
      page.getByRole("link", { name: /Decision Tools/ }).first(),
    ).toBeVisible();
  });

  test("should display market overview dashboard content", async ({ page }) => {
    await expect(page.locator("main")).toBeVisible();
  });

  test("should have working navigation links in sidebar", async ({ page }) => {
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
  });

  test("should navigate to analytics section", async ({ page }) => {
    // The Studies library is the research landing page and is reached from the
    // header's Research destination, not from a flat sidebar list.
    await page
      .getByRole("navigation", { name: "Primary" })
      .getByRole("link", { name: "Research", exact: true })
      .click();
    await expect(page).toHaveURL(/analytics\/?$/);
  });

  test("should not have critical console errors", async ({ page }) => {
    await expectPageToLoadWithoutErrors(page, "/dashboard");
  });
});
