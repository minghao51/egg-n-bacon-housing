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

/**
 * Reach a control using only the Tab key.
 *
 * The work order's keyboard claim is about the page's real tab order, so the
 * test walks it rather than calling `focus()` — a control that is focusable in
 * a script but never reached by Tab would otherwise pass.
 */
async function tabToId(
  page: import("@playwright/test").Page,
  id: string,
  maxTabs = 80,
) {
  for (let index = 0; index <= maxTabs; index += 1) {
    const focused = await page.evaluate(
      () => document.activeElement?.id ?? "",
    );
    if (focused === id) return;
    await page.keyboard.press("Tab");
  }
  throw new Error(`Tab order never reached #${id}`);
}

/** The Area Inspector rail, scoped so its text cannot match the map's. */
function areaInspector(page: import("@playwright/test").Page) {
  return page
    .locator("aside")
    .filter({ has: page.getByRole("heading", { name: "Area Inspector" }) });
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

test.describe("Research map — keyboard and handoff (WS-B2)", () => {
  test.use({ viewport: { width: 1440, height: 1000 } });

  test("a keyboard user selects an area and inspects a layer without the pointer", async ({
    page,
  }) => {
    await openMap(page);

    // Tab to the area control: the polygons are not focusable, so this is the
    // keyboard path to the same `selectedArea` state a polygon click sets.
    await tabToId(page, "map-area-select");
    const areaSelect = page.getByLabel("Area", { exact: true });
    await expect(areaSelect).toBeFocused();
    await expect(areaSelect).toHaveValue("");

    // A native <select> changes on ArrowDown and fires `change` — no pointer.
    await page.keyboard.press("ArrowDown");
    await expect(areaSelect).not.toHaveValue("");
    const chosen = await areaSelect.inputValue();
    expect(chosen.length).toBeGreaterThan(0);

    // The inspector updates with no pointer input at all.
    const inspector = areaInspector(page);
    await expect(inspector.getByText(chosen, { exact: true }).first()).toBeVisible();

    // Every inspector value is a real dt/dd pair, so the label and the value
    // are programmatically associated rather than visually adjacent.
    await expect(inspector.locator("dl dt")).toHaveCount(6);
    await expect(inspector.locator("dl dd")).toHaveCount(6);
    await expect(inspector.locator("dl dt").first()).toHaveText(
      "Current Metric",
    );

    // The selection reached the URL the same way a polygon click does.
    expect(new URL(page.url()).searchParams.get("area")).toBe(chosen);

    // Toggle an archived layer with the keyboard and confirm the archive
    // inspector follows the same area.
    await tabToId(page, "archive-layer-spatial.lisa");
    await page.keyboard.press(" ");
    await expect(page.locator('[id="archive-layer-spatial.lisa"]')).toBeChecked();
    await expect(
      page
        .getByRole("region", { name: "Archived field inspector" })
        .getByText(chosen),
    ).toBeVisible();
  });

  test("the metric control has an accessible name and the filters expose pressed state", async ({
    page,
  }) => {
    await openMap(page);

    // A real <label for> gives the select its name — not adjacent text.
    const metric = page.getByLabel("Metric", { exact: true });
    await expect(metric).toBeVisible();
    await expect(metric).toHaveAccessibleName("Metric");
    await expect(metric).toHaveValue("median_price");

    // Period: exactly one option is pressed, and selecting another moves it.
    const allTime = page.getByRole("button", { name: "All Time", exact: true });
    const preCovid = page.getByRole("button", {
      name: "Pre-COVID",
      exact: true,
    });
    await expect(allTime).toHaveAttribute("aria-pressed", "true");
    await expect(preCovid).toHaveAttribute("aria-pressed", "false");

    await preCovid.click();
    await expect(preCovid).toHaveAttribute("aria-pressed", "true");
    await expect(allTime).toHaveAttribute("aria-pressed", "false");

    // Type: same contract, and the controls stay real buttons.
    const allTypes = page.getByRole("button", { name: "All", exact: true });
    const condo = page.getByRole("button", { name: "CONDO", exact: true });
    await expect(allTypes).toHaveAttribute("aria-pressed", "true");
    await expect(allTypes).toHaveAttribute("type", "button");
    await expect(condo).toHaveAttribute("type", "button");

    await condo.click();
    await expect(condo).toHaveAttribute("aria-pressed", "true");
    await expect(allTypes).toHaveAttribute("aria-pressed", "false");

    // Changing the metric keeps the name and the value in step.
    await metric.selectOption("median_psf");
    await expect(metric).toHaveValue("median_psf");
  });

  test("the handoff preserves the property type and period the map showed", async ({
    page,
  }) => {
    // The reported link: condo + pre-COVID used to arrive as HDB + 2025.
    await openMap(
      page,
      "?area=TAMPINES&metric=median_price&timeBasis=pre_covid&propertyType=condo",
    );

    const link = page.getByRole("link", {
      name: "Open observed comparison",
    });
    await expect(link).toHaveAttribute("href", /area=TAMPINES/);
    await expect(link).toHaveAttribute("href", /property=condo/);
    await expect(link).toHaveAttribute("href", /period=pre_covid/);
    // No silent substitution on a metric the explorer does compare.
    await expect(link).not.toHaveAttribute("href", /metric=/);

    await link.click();
    await expect(page).toHaveURL(/\/explore\?/);

    // The destination's controls match the map's scope ...
    await expect(page.getByRole("radio", { name: "Condo" })).toBeChecked();
    await expect(
      page.getByRole("radio", { name: "Through 2021" }),
    ).toBeChecked();
    await expect(page.getByRole("radio", { name: "HDB" })).not.toBeChecked();

    // ... and the source section is the joint section the map drew.
    await expect(
      page.getByText("map_metrics.pre_covid_condo").first(),
    ).toBeVisible();
  });

  test("an unsupported metric discloses the substitution instead of hiding it", async ({
    page,
  }) => {
    // YoY growth has no observed-comparison equivalent in the explorer.
    await openMap(
      page,
      "?area=TAMPINES&metric=yoy_change_pct&timeBasis=pre_covid&propertyType=condo",
    );

    const link = page.getByRole("link", {
      name: "Open observed comparison",
    });
    await expect(link).toHaveAccessibleDescription(
      /has no observed-comparison equivalent/,
    );
    await expect(
      page.getByText(/The map's YoY Growth has no observed-comparison equivalent/),
    ).toBeVisible();

    // It never claims to carry the unsupported metric through.
    await expect(link).not.toHaveAttribute("href", /yoy_change_pct/);
    // The scope it can preserve is still preserved.
    await expect(link).toHaveAttribute("href", /property=condo/);
    await expect(link).toHaveAttribute("href", /period=pre_covid/);
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
