import { readFileSync } from "node:fs";
import path from "node:path";

import { test, expect } from "@playwright/test";
import { expectPageToLoadWithoutErrors } from "../utils/pageHealth";
import { servePackBytesFromDisk } from "../utils/servePackBytes";

// The published generation is republished per release (RF09 changed it), so
// the summary must be matched against the manifest rather than a pinned hex.
const PACK_GENERATION = (
  JSON.parse(
    readFileSync(path.resolve("public/data/dashboard-release-v2.json"), "utf8"),
  ) as { generation: string }
).generation.slice(0, 12);

async function gotoLeaderboard(page: import("@playwright/test").Page) {
  await page.goto("/dashboard/leaderboard");
  await page.waitForSelector('[data-interactive-ready="true"]');
}

test.describe("Dashboard - Compare Areas", () => {
  test("loads the redesigned leaderboard shell", async ({ page }) => {
    await gotoLeaderboard(page);
    await expect(page).toHaveURL(/dashboard\/leaderboard/);
    await expect(
      page.getByRole("heading", { name: "Compare Areas", exact: true }),
    ).toBeVisible();
    await expect(page.getByLabel("Rank by")).toBeVisible();
    // Legacy-mode build: the bare URL still opens on "2022 onward", so there is
    // no updated-default notice.
    await expect(
      page.locator('[data-observed-default-notice="true"]'),
    ).toHaveCount(0);
    await expect(page.getByRole("heading", { name: "Filters" })).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Detailed Rankings" }),
    ).toBeVisible();
  });

  test("uses page-specific filters instead of the segments panel", async ({
    page,
  }) => {
    await gotoLeaderboard(page);
    await expect(page.getByText("Investment Goal")).toHaveCount(0);
    await expect(page.getByText("Spatial Hotspot")).toHaveCount(0);
    await expect(
      page.getByRole("heading", { name: "Property Type" }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Time Basis" }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Median Price Range" }),
    ).toBeVisible();
  });

  test("rank by control drives the summary and table ordering", async ({
    page,
  }) => {
    await gotoLeaderboard(page);
    const summary = page.getByText(/Showing \d+ areas? ranked by/i).first();
    await expect(summary).toContainText("median price");

    await page.getByLabel("Rank by").selectOption("volume");
    await expect(summary).toContainText("sales");

    const firstRow = page.locator("tbody tr").first();
    await expect(firstRow).toContainText("#1");
  });

  test("only jointly published metrics are offered", async ({ page }) => {
    await gotoLeaderboard(page);
    const options = page.getByLabel("Rank by").locator("option");
    await expect(options).toHaveCount(3);
    await expect(page.getByLabel("Rank by")).not.toContainText(
      "Year-over-Year Growth",
    );
  });

  test("reads Punggol HDB 2025 from the joint section", async ({ page }) => {
    // Regression: the page used to show the property-only margin
    // (S$500,000 / 24,854 sales) instead of the joint HDB x 2025 section.
    await page.goto(
      "/dashboard/leaderboard?propertyType=hdb&timeBasis=year_2025&metric=median_price&area=PUNGGOL",
    );
    await page.waitForSelector('[data-interactive-ready="true"]');
    const row = page.locator('tr[data-area="PUNGGOL"]');
    await expect(row).toHaveAttribute("data-ranked", "true");
    await expect(row).toContainText("$672,000");
    await expect(row).toContainText("1,538");
    await expect(row).not.toContainText("$500,000");
    await expect(row).not.toContainText("24,854");
  });

  test("uses published planning regions, not CCR/RCR/OCR", async ({ page }) => {
    await gotoLeaderboard(page);
    await expect(page.getByLabel("East (EAST)")).toBeChecked();
    await expect(page.getByLabel("North-East (NORTH-EAST)")).toBeChecked();
    await expect(page.getByText("Core Central Region")).toHaveCount(0);
    await expect(page.getByText("Outside Central Region")).toHaveCount(0);
  });

  test("search and filters update the visible results", async ({ page }) => {
    await gotoLeaderboard(page);
    const summary = page.getByText(/Showing \d+ areas? ranked by/i).first();
    await page.getByLabel("Search planning areas").fill("YISHUN");
    await expect(summary).toContainText("Showing 1 area ranked by");
    await expect(page.locator("tbody tr")).toHaveCount(1);

    await page.getByRole("button", { name: "Reset", exact: true }).click();
    await expect(page.locator("tbody tr")).not.toHaveCount(1);
  });

  test("mobile filter drawer opens and can be dismissed", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await gotoLeaderboard(page);
    await expect(
      page.getByRole("button", { name: /Filters \(\d+\)/ }),
    ).toBeVisible();
    await page.getByRole("button", { name: /Filters \(\d+\)/ }).click();
    await expect(
      page.getByRole("heading", { name: "Leaderboard Filters" }),
    ).toBeVisible();
    await page.getByRole("button", { name: "Close filters" }).click();
    await expect(
      page.getByRole("heading", { name: "Leaderboard Filters" }),
    ).toHaveCount(0);
  });

  test("should have working navigation back to overview", async ({ page }) => {
    await gotoLeaderboard(page);
    await page.getByRole("link", { name: "Overview" }).first().click();
    await expect(page).toHaveURL(/dashboard$/);
  });

  test("should not have critical console errors", async ({ page }) => {
    await expectPageToLoadWithoutErrors(page, "/dashboard/leaderboard", {
      ignoreConsoleErrors: ["does not provide an export", "SyntaxError"],
      ignorePageErrors: ["does not provide an export", "SyntaxError"],
    });
  });
});

/**
 * Published-period rankings (RF05 T2). Figures come from the pack published
 * with this tree: `ttm_2026_10` HDB Punggol is S$672,888 on 1,702 sales.
 */
test.describe("Compare Areas - published periods", () => {
  test.beforeEach(async ({ page }) => {
    await servePackBytesFromDisk(page);
  });

  test("ranks a publish scope from the verified pack", async ({ page }) => {
    await page.goto(
      "/dashboard/leaderboard?timeBasis=ttm_2026_10&propertyType=hdb&metric=median_price&area=PUNGGOL",
    );
    await page.waitForSelector('[data-interactive-ready="true"]');

    const row = page.locator('tr[data-area="PUNGGOL"]');
    await expect(row).toHaveAttribute("data-ranked", "true");
    await expect(row).toContainText("$672,888");
    await expect(row).toContainText("1,702");

    await expect(page.getByText("Window:").first()).toBeVisible();
    await expect(
      page
        .getByText(
          new RegExp(`observed pack · ttm_2026_10 · ${PACK_GENERATION}`),
        )
        .first(),
    ).toBeVisible();
    expect(new URL(page.url()).searchParams.get("timeBasis")).toBe(
      "ttm_2026_10",
    );
  });

  test("a limited-display scope is readable but never ranked", async ({
    page,
  }) => {
    await page.goto(
      "/dashboard/leaderboard?timeBasis=ttm_2026_10&propertyType=ec&metric=median_price",
    );
    await page.waitForSelector('[data-interactive-ready="true"]');

    await expect(
      page.getByText(/listed by name because coverage is limited/i),
    ).toBeVisible();
    await expect(
      page.getByText(/Coverage is limited for this scope/).first(),
    ).toBeVisible();
    await expect(page.getByText(/Not colour-coded/)).toBeVisible();

    // Nothing in the table claims a rank.
    await expect(page.locator('tbody tr[data-ranked="true"]')).toHaveCount(0);
    const firstRow = page.locator("tbody tr").first();
    await expect(firstRow).toHaveAttribute("data-ranked", "false");
  });

  test("an unpublished window is reported, not substituted", async ({
    page,
  }) => {
    await page.goto(
      "/dashboard/leaderboard?timeBasis=ttm_2026_07&propertyType=hdb",
    );
    await page.waitForSelector('[data-interactive-ready="true"]');

    await expect(
      page.getByText("ttm_2026_07 is not available in this build"),
    ).toBeVisible();
    await expect(
      page.getByText(/does not publish a period with the id ttm_2026_07/),
    ).toBeVisible();
    await expect(page.locator("tbody tr")).toHaveCount(0);
    expect(new URL(page.url()).searchParams.get("timeBasis")).toBe(
      "ttm_2026_07",
    );
  });

  test("the historical eras stay selectable beside the published windows", async ({
    page,
  }) => {
    await gotoLeaderboard(page);
    const timeBasis = page
      .getByRole("heading", { name: "Time Basis" })
      .locator("..");
    await expect(
      timeBasis.getByRole("button", { name: "2022 onward" }),
    ).toBeVisible();
    await expect(
      timeBasis.getByRole("button", { name: "All history" }),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: "12 months to 2026-10" }),
    ).toBeVisible();
  });
});
