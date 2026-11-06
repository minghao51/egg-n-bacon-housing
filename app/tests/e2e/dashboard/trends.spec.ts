import { test, expect } from "@playwright/test";
import { expectPageToLoadWithoutErrors } from "../utils/pageHealth";

/**
 * `/dashboard/trends` — the compatibility wrapper over the S8 four-tool
 * workspace.
 *
 * The page is no longer the only home for the tools: `/research/tools` is the
 * research destination, and this route must keep working with the same island
 * and the same query state. The financing arithmetic itself is covered by
 * `tests/e2e/research/tools.spec.ts`; this file pins route compatibility.
 */

const H1 = "Make the assumptions editable.";

test.describe("Dashboard - Decision Tools wrapper", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/dashboard/trends");
  });

  test("loads the shared workspace under the legacy URL", async ({ page }) => {
    await expect(page).toHaveURL(/dashboard\/trends/);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(H1);
    await expect(page.getByText(/Compatibility route/)).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Financing scenario" }),
    ).toBeVisible();
  });

  test("keeps the sidebar and all four tools", async ({ page }) => {
    await expect(
      page.getByRole("navigation", { name: "Main navigation" }),
    ).toBeVisible();
    await expect(
      page.getByRole("link", { name: /Overview/ }).first(),
    ).toBeVisible();
    await expect(page.getByRole("tab")).toHaveCount(4);
  });

  test("preserves the tool query parameter", async ({ page }) => {
    await page.goto("/dashboard/trends?tool=lease");
    await expect(page).toHaveURL(/tool=lease/);
    await expect(page.getByText("74–79 years")).toBeVisible();
    await expect(
      page.getByRole("tab", { name: /Lease bands/ }),
    ).toHaveAttribute("aria-selected", "true");
  });

  test("navigation back to the overview still works", async ({ page }) => {
    await page.getByRole("link", { name: "Overview" }).first().click();
    await expect(page).toHaveURL(/dashboard$/);
  });

  test("does not have critical console errors", async ({ page }) => {
    await expectPageToLoadWithoutErrors(page, "/dashboard/trends");
  });
});
