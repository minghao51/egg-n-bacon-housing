import { test, expect } from "@playwright/test";
import { expectPageToLoadWithoutErrors } from "../utils/pageHealth";

test.describe("Analytics Articles", () => {
  const articles = [
    { slug: "lease-decay", title: "Lease Decay" },
    { slug: "mrt-impact", title: "MRT Impact" },
    { slug: "price-forecasts", title: "Price Forecasts" },
    { slug: "findings", title: "Findings" },
    { slug: "spatial-hotspots", title: "Spatial Hotspots" },
    { slug: "spatial-autocorrelation", title: "Spatial Autocorrelation" },
    { slug: "school-quality", title: "School Quality" },
    { slug: "causal-inference-overview", title: "Causal Inference" },
  ];

  articles.forEach(({ slug, title }) => {
    test(`should load ${title} article`, async ({ page }) => {
      await page.goto(`/analytics/${slug}`);
      await expect(page).toHaveURL(new RegExp(`/analytics/${slug}`));
      await expect(page.locator("main")).toBeVisible();
    });

    test(`should display sidebar on ${title} article`, async ({ page }) => {
      await page.goto(`/analytics/${slug}`);
      await expect(
        page.getByRole("navigation", { name: "Main navigation" }),
      ).toBeVisible();
    });

    test(`should not have critical errors on ${title} article`, async ({
      page,
    }) => {
      await expectPageToLoadWithoutErrors(page, `/analytics/${slug}`);
    });
  });

  test("should navigate between articles using sidebar", async ({ page }) => {
    await page.goto("/analytics/lease-decay");
    await page
      .getByRole("link", { name: /MRT Impact/i })
      .first()
      .click();
    await expect(page).toHaveURL(/analytics\/mrt-impact/);
  });

  test("should not emit chart sizing warnings on lease decay article", async ({
    page,
  }) => {
    await expectPageToLoadWithoutErrors(page, "/analytics/lease-decay", {
      failOnConsoleWarnings: true,
    });
  });

  test("renders exactly one level-1 heading on a study page", async ({
    page,
  }) => {
    await page.goto("/analytics/lease-decay");
    await expect(page.getByRole("heading", { level: 1 })).toHaveCount(1);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(
      "Lease Decay Impact",
    );
    // The stripped markdown H1 must not survive as a hidden duplicate.
    await expect(
      page.locator("article").getByRole("heading", { level: 1 }),
    ).toHaveCount(0);
  });

  test("withholds the lease study chart and states the unit review", async ({
    page,
  }) => {
    await page.goto("/analytics/lease-decay");
    await expect(
      page.getByText("Unit review required", { exact: true }),
    ).toBeVisible();
    await expect(page.getByText(/per-square-metre statistic/)).toBeVisible();
    await expect(
      page.getByText(/Charts are withheld on this study/),
    ).toBeVisible();
    // The opt-in markers still exist in the source tables; no chart is drawn.
    await page.waitForTimeout(1_000);
    await expect(page.locator(".chart-container")).toHaveCount(0);
    // The source tables remain readable.
    await expect(page.locator("article table").first()).toBeVisible();
  });

  test("still renders opt-in charts on a study without a unit review", async ({
    page,
  }) => {
    await page.goto("/analytics/findings");
    await expect(
      page.getByText("Published research", { exact: false }).first(),
    ).toBeVisible();
    await expect
      .poll(async () => page.locator(".chart-container").count(), {
        timeout: 15_000,
      })
      .toBeGreaterThan(0);
    await expect(page.getByRole("heading", { level: 1 })).toHaveCount(1);
  });
});
