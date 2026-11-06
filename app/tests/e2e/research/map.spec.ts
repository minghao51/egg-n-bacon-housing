import { test, expect } from "@playwright/test";
import { expectPageToLoadWithoutErrors } from "../utils/pageHealth";

/**
 * `/research/map` and the `/dashboard/map` wrapper (slice S9).
 *
 * The research map keeps the observed transaction fill and exposes the nine
 * archived model layers for inspection only. The archived values are uniform
 * placeholders and the forecast target is in the past, so the tests bind to
 * those disclosures rather than to an analytical fill.
 */

const H1 = "A layer is a claim. Inspect its contract.";

async function openMap(page: import("@playwright/test").Page, query = "") {
  await page.goto(`/research/map${query}`);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(H1);
  await expect(page.locator(".leaflet-container")).toBeVisible({
    timeout: 30_000,
  });
}

test.describe("Research map", () => {
  test.use({ viewport: { width: 1440, height: 1000 } });

  test("renders the archive gate, nine layer IDs and the observed fill", async ({
    page,
  }) => {
    await openMap(page);

    await expect(
      page.getByText("Research / Map / Archive").first(),
    ).toBeVisible();
    await expect(
      page.getByText(/Archive · .* · not validated for current use/),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Archive layer controls" }),
    ).toBeVisible();
    await expect(
      page.getByText(/Output gate — not validated for current use/),
    ).toBeVisible();

    // Exactly the nine retained layer IDs are offered as checkboxes.
    await expect(page.locator('input[type="checkbox"]')).toHaveCount(9);

    // The observed legend names quantity, unit, period and status.
    const legend = page.locator("div.absolute");
    await expect(legend.getByText("Median price")).toBeVisible();
    await expect(legend.getByText(/Unit: SGD/)).toBeVisible();
    await expect(
      legend.getByText(/Evidence: Observed transactions/),
    ).toBeVisible();
    await expect(legend.getByText(/No observed value/)).toBeVisible();
  });

  test("archived fields are inspectable and placeholders are disclosed", async ({
    page,
  }) => {
    await openMap(
      page,
      "?metric=median_price&timeBasis=year_2025&propertyType=hdb&area=BISHAN&layers=spatial.lisa,spatial.hotspot",
    );

    const inspector = page.getByRole("heading", {
      name: "Archived field inspector",
    });
    await expect(inspector).toBeVisible();
    const inspectorPanel = page.getByRole("region", {
      name: "Archived field inspector",
    });
    await expect(inspectorPanel.getByText("BISHAN")).toBeVisible();
    await expect(page.getByText("Stored LISA class")).toBeVisible();
    await expect(page.getByText("STABLE").first()).toBeVisible();
    await expect(
      page.getByText(
        /All 41 archived areas share the same stored spatial pattern/,
      ),
    ).toBeVisible();
    await expect(
      page.getByText(
        "Coverage: 41 archived areas against 55 planning-area polygons. An absent area is shown as unavailable, never as a neutral value.",
      ),
    ).toBeVisible();

    // The observed fill remains the map's only polygon shading.
    await expect(
      page.getByRole("heading", { name: "Area Inspector" }),
    ).toBeVisible();
  });

  test("a historical forecast keeps its target and is never labelled current", async ({
    page,
  }) => {
    await openMap(
      page,
      "?metric=median_price&timeBasis=year_2025&propertyType=hdb&area=BISHAN&layers=predictive.forecast",
    );

    await expect(
      page.getByText("Stored forecast target", { exact: true }),
    ).toBeVisible();
    await expect(page.getByText("2025-07-01", { exact: true })).toBeVisible();
    await expect(
      page.getByText(
        /is an archived forecast, never a current or forward-looking one/,
      ),
    ).toBeVisible();
    await expect(
      page.getByText(/Stored signal \(archive, not advice\)/),
    ).toBeVisible();
  });

  test("a failing source disables only its own layers", async ({ page }) => {
    await page.route("**/data/analytics/spatial_analysis.json.gz", (route) =>
      route.abort(),
    );
    await page.goto(
      "/research/map?area=BISHAN&layers=spatial.lisa,feature.mrt",
    );
    await expect(page.locator(".leaflet-container")).toBeVisible({
      timeout: 30_000,
    });

    // Spatial rows report unavailable; feature rows keep working.
    await expect(page.getByText("Unavailable").first()).toBeVisible({
      timeout: 30_000,
    });
    await expect(page.getByText("Ready").first()).toBeVisible();
    // The observed map is not erased by the archive failure.
    await expect(
      page.getByText(/Evidence: Observed transactions/),
    ).toBeVisible();
    await expect(
      page.locator(".leaflet-overlay-pane path").first(),
    ).toBeVisible();
  });

  test("clicking an area exposes its archive fields without BUY/SELL advice", async ({
    page,
  }) => {
    await openMap(page, "?layers=predictive.policy&area=BISHAN");
    await expect(page.getByText(/Stored cooling sensitivity/)).toBeVisible();
    await expect(page.getByText(/Stored risk label/)).toBeVisible();
    await expect(page.getByText(/BUY\/SELL/)).toHaveCount(0);
  });

  test("the legacy wrapper keeps the workspace and its query state", async ({
    page,
  }) => {
    await page.goto(
      "/dashboard/map?metric=median_psf&timeBasis=year_2025&propertyType=hdb&area=TAMPINES&layers=spatial.lisa",
    );
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(H1);
    await expect(page.getByText(/Compatibility route/)).toBeVisible();
    await expect(page).toHaveURL(/\/dashboard\/map/);
    await page.waitForTimeout(1_000);
    const url = new URL(page.url());
    expect(url.searchParams.get("metric")).toBe("median_psf");
    expect(url.searchParams.get("timeBasis")).toBe("year_2025");
    expect(url.searchParams.get("propertyType")).toBe("hdb");
    expect(url.searchParams.get("area")).toBe("TAMPINES");
    expect(url.searchParams.get("layers")).toBe("spatial.lisa");
  });

  test("the navigation points at the research destination", async ({
    page,
  }) => {
    await page.goto("/dashboard");
    const nav = page.getByRole("navigation", { name: "Main navigation" });
    await nav
      .getByRole("link", { name: /Research map/ })
      .first()
      .click();
    await expect(page).toHaveURL(/research\/map/);
    await expect(
      page
        .getByRole("navigation", { name: "Main navigation" })
        .getByRole("link", { name: /Research map/ }),
    ).toHaveAttribute("aria-current", "page");
  });

  test("does not log errors", async ({ page }) => {
    await expectPageToLoadWithoutErrors(page, "/research/map");
  });
});

test.describe("Research map on a narrow viewport", () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test("keeps the page inside the viewport", async ({ page }) => {
    await openMap(page);
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth > window.innerWidth + 1,
    );
    expect(overflow).toBe(false);
    await expect(page.locator('input[type="checkbox"]')).toHaveCount(9);
  });
});
