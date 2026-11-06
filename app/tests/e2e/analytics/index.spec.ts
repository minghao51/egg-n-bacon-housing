import { test, expect } from "@playwright/test";
import { expectPageToLoadWithoutErrors } from "../utils/pageHealth";

test.describe("Analytics Index Page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/analytics/");
  });

  test("should load analytics index page", async ({ page }) => {
    await expect(page).toHaveURL(/analytics\/?$/);
    await expect(
      page.getByRole("heading", {
        name: "Stories with a visible evidence trail.",
      }),
    ).toBeVisible();
  });

  test("should display sidebar navigation", async ({ page }) => {
    await expect(
      page.getByRole("navigation", { name: "Main navigation" }),
    ).toBeVisible();
  });

  test("should display persona cards", async ({ page }) => {
    await expect(page.getByText("First-Time Buyer").first()).toBeVisible();
    await expect(page.getByText("Property Investor").first()).toBeVisible();
    await expect(page.getByText("Upsizer / Upgrader").first()).toBeVisible();
  });

  test("should navigate to first-time-buyer persona", async ({ page }) => {
    await page
      .getByRole("link", { name: /First-Time Buyer/i })
      .first()
      .click();
    await expect(page).toHaveURL(/analytics\/personas\/first-time-buyer/);
  });

  test("should navigate to investor persona", async ({ page }) => {
    await page.getByText("Property Investor").click();
    await expect(page).toHaveURL(/analytics\/personas\/investor/);
  });

  test("should navigate to upgrader persona", async ({ page }) => {
    await page.getByText("Upsizer / Upgrader").click();
    await expect(page).toHaveURL(/analytics\/personas\/upgrader/);
  });

  test("should display counts derived from the collection", async ({
    page,
  }) => {
    await expect(page.getByText("Published studies")).toBeVisible();
    await expect(page.getByText("Topics", { exact: true })).toBeVisible();
    await expect(page.getByText("Under unit review")).toBeVisible();
    // The retired "11 Years" coverage KPI is not a collection fact.
    await expect(page.getByText("11 Years")).toHaveCount(0);
    await expect(page.getByText("Data Coverage")).toHaveCount(0);
  });

  test("filters the library by text, topic and audience", async ({ page }) => {
    const search = page.getByLabel("Free text");

    await expect(search).toBeVisible();
    await expect(page.getByText("15 of 15 studies")).toBeVisible();

    await search.fill("Lease Decay Impact");
    await expect(
      page.getByText("1 of 15 studies match these filters."),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Lease Decay Impact" }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Data Sources" }),
    ).toHaveCount(0);

    await search.fill("");
    await page.getByLabel("Topic").selectOption("quick-reference");
    await expect(
      page.getByRole("heading", { name: "Data Sources" }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Lease Decay Impact" }),
    ).toHaveCount(0);

    await page.getByLabel("Topic").selectOption("all");
    // Facility Premiums is the one study without a first-time-buyer entry.
    await page.getByLabel("Reading for").selectOption("first-time-buyer");
    await expect(
      page.getByText("14 of 15 studies match these filters."),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Facility Premiums" }),
    ).toHaveCount(0);
    await expect(
      page.getByRole("heading", { name: "Data Sources" }),
    ).toBeVisible();

    await page.getByRole("button", { name: "Reset filters" }).click();
    await expect(page.getByText("15 of 15 studies.")).toBeVisible();
  });

  test("keeps every published study reachable", async ({ page }) => {
    const studyLinks = page.locator('a[href*="/analytics/"]');
    expect(await studyLinks.count()).toBeGreaterThan(0);
    await expect(
      page.getByText(/Published research, not current transaction medians/i),
    ).toBeVisible();
  });

  test("should display category sections", async ({ page }) => {
    const content = page.locator("main");
    await expect(content).toBeVisible();
  });

  test("should navigate to an analytics article", async ({ page }) => {
    const firstArticle = page.getByRole("link", { name: /Read study/ }).first();
    await firstArticle.click();
    await expect(page).toHaveURL(/\/analytics\/.+/);
  });

  test("should not have critical console errors", async ({ page }) => {
    await expectPageToLoadWithoutErrors(page, "/analytics/");
  });
});
