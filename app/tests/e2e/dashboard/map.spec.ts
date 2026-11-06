import { test, expect } from "@playwright/test";
import { expectPageToLoadWithoutErrors } from "../utils/pageHealth";

/**
 * `/dashboard/map` compatibility route (S9).
 *
 * The research map moved to `/research/map`; this legacy URL must keep working
 * with the same island. Query compatibility is also covered by the S1
 * regression and the research-map spec.
 */

const H1 = "A layer is a claim. Inspect its contract.";

test.describe("Dashboard - map wrapper", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/dashboard/map");
  });

  test("loads the shared workspace under the legacy URL", async ({ page }) => {
    await expect(page).toHaveURL(/dashboard\/map/);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(H1);
    await expect(page.getByText(/Compatibility route/)).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Archive layer controls" }),
    ).toBeVisible();
  });

  test("keeps the sidebar and observed map", async ({ page }) => {
    await expect(
      page.getByRole("navigation", { name: "Main navigation" }),
    ).toBeVisible();
    await expect(page.locator(".leaflet-container")).toBeVisible({
      timeout: 30_000,
    });
    await expect(
      page.getByRole("heading", { name: "Area Inspector" }),
    ).toBeVisible();
  });

  test("navigation back to the overview still works", async ({ page }) => {
    await page.getByRole("link", { name: "Overview" }).first().click();
    await expect(page).toHaveURL(/dashboard$/);
  });

  test("does not have critical console errors", async ({ page }) => {
    await expectPageToLoadWithoutErrors(page, "/dashboard/map");
  });
});
