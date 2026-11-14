import { test, expect } from "@playwright/test";
import { expectPageToLoadWithoutErrors } from "./utils/pageHealth";

test.describe("Home Page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
  });

  test("should load the home page without errors", async ({ page }) => {
    await expect(page).toHaveTitle(/Egg n Bacon Housing/);
    await expect(page.locator("body")).toBeVisible();
  });

  test("should display hero section with title", async ({ page }) => {
    await expect(page.getByText("Egg n Bacon")).toBeVisible();
    await expect(page.getByText("Housing", { exact: true })).toBeVisible();
    await expect(
      page.getByText("Singapore Housing Market Intelligence"),
    ).toBeVisible();
  });

  test("should display navigation cards", async ({ page }) => {
    await expect(page.getByText("Market dashboard")).toBeVisible();
    await expect(page.getByText("Analytics Reports")).toBeVisible();
  });

  test("should display key insights", async ({ page }) => {
    await expect(page.getByText("Lease decay, measured")).toBeVisible();
    await expect(page.getByText("CBD and MRT")).toBeVisible();
  });

  test("should navigate to dashboard when clicking the dashboard card", async ({
    page,
  }) => {
    await page.getByText("Market dashboard").click();
    await expect(page).toHaveURL(/dashboard/);
    await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
  });

  test("should navigate to analytics when clicking Analytics Reports card", async ({
    page,
  }) => {
    await page.getByText("Analytics Reports").click();
    await expect(page).toHaveURL(/analytics\/?$/);
    await expect(
      page.getByRole("heading", {
        name: "Stories with a visible evidence trail.",
      }),
    ).toBeVisible();
  });

  test("should navigate to lease decay article", async ({ page }) => {
    await page.getByText("Lease decay, measured").click();
    await expect(page).toHaveURL(/analytics\/lease-decay/);
  });

  test("should navigate to MRT impact article", async ({ page }) => {
    await page.getByText("CBD and MRT").click();
    await expect(page).toHaveURL(/analytics\/mrt-impact/);
  });

  test("should not have critical console errors", async ({ page }) => {
    await expectPageToLoadWithoutErrors(page, "/");
  });
});
