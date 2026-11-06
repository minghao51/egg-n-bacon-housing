import { test, expect, type Page } from "@playwright/test";
import { expectPageToLoadWithoutErrors } from "../utils/pageHealth";

/**
 * Legacy `/dashboard/segments` wrapper.
 *
 * The workspace moved to `/research/segments`; this route must keep working and
 * keep every query ID. The behaviour suite lives in
 * `tests/e2e/research/segments.spec.ts` — this file only pins compatibility.
 */

const H1 = "Find an archetype. Then inspect its evidence.";

async function openLegacy(page: Page, query = "") {
  await page.goto(`/dashboard/segments${query}`);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(H1);
  await expect(
    page.getByRole("heading", { name: "Six stored research segments" }),
  ).toBeVisible();
}

test.describe("Dashboard - segments wrapper", () => {
  test("still renders the workspace and says it is a compatibility route", async ({
    page,
  }) => {
    await openLegacy(page);

    await expect(page.getByText(/Compatibility route:/)).toBeVisible();
    await expect(page.getByText("Research / Segments").first()).toBeVisible();
    await expect(
      page.getByText(/archetypes match \(weighted fit\)/),
    ).toBeVisible();
    await expect(
      page.getByText(/not listed in the dashboard release manifest/i),
    ).toBeVisible();
  });

  test("preserves persona, segment and area from a legacy deep link", async ({
    page,
  }) => {
    await openLegacy(
      page,
      "?persona=upgrader&tab=investigate&segment=mid_tier_value&area=lim%20chu%20kang",
    );

    await expect
      .poll(() => new URL(page.url()).searchParams.get("area"))
      .toBe("LIM CHU KANG");
    const params = new URL(page.url()).searchParams;
    expect(params.get("segment")).toBe("mid_tier_value");
    expect(params.get("persona")).toBe("upgrader");
    expect(params.get("tab")).toBe("investigate");

    await expect(
      page.getByRole("heading", {
        name: "Lim Chu Kang / selected research area",
      }),
    ).toBeVisible();
  });

  test("the same workspace is reachable at the research route", async ({
    page,
  }) => {
    await openLegacy(page);
    const navLink = page
      .getByRole("link", { name: /Discover Segments/ })
      .first();
    await expect(navLink).toHaveAttribute("href", /\/research\/segments$/);
    await navLink.click();
    await expect(page).toHaveURL(/\/research\/segments/);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(H1);
  });

  test("should not have console errors", async ({ page }) => {
    await expectPageToLoadWithoutErrors(page, "/dashboard/segments", {
      ignoreConsoleErrors: ["does not provide an export", "SyntaxError"],
      ignorePageErrors: ["does not provide an export", "SyntaxError"],
    });
  });
});
