import { test, expect, type Page } from "@playwright/test";
import { expectPageToLoadWithoutErrors } from "./utils/pageHealth";

/**
 * `/explore` map and table views.
 *
 * The assertions bind to the published data, not to the presence of an SVG:
 * the default 2025 HDB selection shows 25 of the 31 areas in that joint section,
 * so the map must colour exactly 25 areas, mask 6 thin-sample areas and leave the
 * 24 geometries outside the section neutral. If the map renders without its data
 * binding (no fills, or every area treated as "no value"), these counts and the
 * legend quantities fail.
 */

/** The 2 MB geometry plus projection can take a moment on a cold cache. */
const MAP_TIMEOUT = 30_000;

function mapFigure(page: Page) {
  return page.getByRole("figure");
}

function areaPaths(page: Page) {
  return mapFigure(page).locator("path[data-area-state]");
}

async function openMap(page: Page, url = "/explore?view=map") {
  await page.goto(url);
  await expect(areaPaths(page).first()).toBeVisible({ timeout: MAP_TIMEOUT });
  await expect(areaPaths(page)).toHaveCount(55, { timeout: MAP_TIMEOUT });
}

async function stateCounts(page: Page): Promise<Record<string, number>> {
  return areaPaths(page).evaluateAll((nodes) => {
    const counts: Record<string, number> = {};
    for (const node of nodes) {
      const state = node.getAttribute("data-area-state") ?? "unknown";
      counts[state] = (counts[state] ?? 0) + 1;
    }
    return counts;
  });
}

test.describe("Explore map view", () => {
  test.use({ viewport: { width: 1440, height: 1000 } });

  test("draws all 55 planning areas and colours only the ones with data", async ({
    page,
  }) => {
    await openMap(page);

    // 55 published geometries; 25 (>=150 sales) coloured, 6 thin-sample areas
    // masked, 24 areas outside year_2025_hdb neutral.
    expect(await stateCounts(page)).toEqual({
      binned: 25,
      // The six thin-sample areas have published values; they are hidden by the
      // sample threshold, which is a different state from "no value".
      filtered: 6,
      outside: 24,
    });

    // The fills come from the data palette, not from the neutral no-data fill.
    const binnedFills = await mapFigure(page)
      .locator('path[data-area-state="binned"]')
      .evaluateAll((nodes) =>
        Array.from(new Set(nodes.map((node) => node.getAttribute("fill") ?? ""))),
      );
    expect(binnedFills.length).toBeGreaterThan(1);
    for (const fill of binnedFills) {
      expect(fill).toMatch(/^#[0-9A-Fa-f]{6}$/);
    }
    const outsideFill = await mapFigure(page)
      .locator('path[data-area-state="outside"]')
      .first()
      .getAttribute("fill");
    expect(outsideFill).not.toBeNull();
    expect(binnedFills).not.toContain(outsideFill);

    // The legend lists every bin with its range and count, plus the masked
    // counts, and says how the bins were cut.
    const legend = mapFigure(page).getByRole("list", { name: "Map legend" });
    // 5 quantile bins + three masked groups (filtered, no value, outside).
    await expect(legend.locator("li")).toHaveCount(8);
    // Rank-based quantiles over the 25 observations, five areas per bin, with
    // half-open upper bounds marked so a boundary value is not misread.
    await expect(
      legend.getByText("S$499,000 to under S$568,000"),
    ).toBeVisible();
    await expect(legend.getByText("S$761,500 to S$849,000")).toBeVisible();
    await expect(legend.getByText("5 areas").first()).toBeVisible();
    await expect(
      legend.getByText("Hidden by the current filters: 6 areas"),
    ).toBeVisible();
    await expect(legend.getByText("Outside this selection: 24 areas")).toBeVisible();
    await expect(
      mapFigure(page).getByText(
        /Bins are quantiles of the 25 areas currently shown, not a scientific classification/,
      ),
    ).toBeVisible();

    // The map states its own data section and needs no tiles.
    await expect(
      mapFigure(page).getByText("map_metrics.year_2025_hdb").first(),
    ).toBeVisible();
    await expect(
      mapFigure(page).getByText(/No map tiles are requested for this view/),
    ).toBeVisible();
  });

  test("an area path is a keyboard-focusable link to its fieldnote", async ({
    page,
  }) => {
    await openMap(page);

    const angMoKio = mapFigure(page).locator('a[href*="/areas/ang-mo-kio?"]');
    await expect(angMoKio).toHaveCount(1);
    await expect(angMoKio).toHaveAttribute(
      "href",
      /\/areas\/ang-mo-kio\?from=explore&property=hdb&period=year_2025$/,
    );

    // The tooltip/title names the area and the value it is coloured by.
    expect(await angMoKio.locator("title").textContent()).toBe(
      "Ang Mo Kio — S$499,000",
    );

    // Focusability plus a visible focus ring (the outline thickens on focus).
    const path = angMoKio.locator("path");
    await expect(path).toHaveAttribute("stroke-width", "0.75");
    await angMoKio.focus();
    await expect(angMoKio).toBeFocused();
    await expect(path).toHaveAttribute("stroke-width", "3");

    // Only areas in the current section are linked: the 24 areas outside it have
    // no fieldnote page carrying this property/period.
    await expect(mapFigure(page).locator("a[href*='/areas/']")).toHaveCount(31);
  });

  test("switching back to the list keeps the property and period", async ({
    page,
  }) => {
    await openMap(page, "/explore?view=map&property=condo&period=whole");

    await page.getByRole("tab", { name: "List" }).click();

    await expect(page.getByRole("radio", { name: "Condo" })).toBeChecked();
    await expect(page.getByRole("radio", { name: "All history" })).toBeChecked();
    const params = new URL(page.url()).searchParams;
    expect(params.get("property")).toBe("condo");
    expect(params.get("period")).toBe("whole");
    // The default view is omitted from the address bar.
    expect(params.get("view")).toBeNull();
    await expect(areaPaths(page)).toHaveCount(0);
  });

  test("changing the property type changes the section named on the map", async ({
    page,
  }) => {
    await openMap(page);

    await expect(
      mapFigure(page).getByText("map_metrics.year_2025_hdb").first(),
    ).toBeVisible();

    await page.getByRole("radio", { name: "Condo" }).check();

    await expect(
      mapFigure(page).getByText("map_metrics.year_2025_condo").first(),
    ).toBeVisible({ timeout: MAP_TIMEOUT });
    await expect(
      mapFigure(page).getByText("map_metrics.year_2025_hdb"),
    ).toHaveCount(0);
  });

  test("an empty selection shows the empty state instead of an empty map", async ({
    page,
  }) => {
    await page.goto("/explore?view=map&search=zzzz");

    await expect(
      mapFigure(page).getByText(/nothing to map/i),
    ).toBeVisible({ timeout: MAP_TIMEOUT });
    await expect(mapFigure(page).locator("svg")).toHaveCount(0);
  });

  test("a geometry failure keeps the values readable in the table", async ({
    page,
  }) => {
    await page.route("**/data/planning_areas.geojson", (route) =>
      route.fulfill({ status: 500, body: "" }),
    );
    await page.goto("/explore?view=map");

    await expect(mapFigure(page).getByRole("alert")).toContainText(
      /planning-area boundaries could not be drawn/i,
      { timeout: MAP_TIMEOUT },
    );
    await expect(mapFigure(page).locator("svg")).toHaveCount(0);

    // The same dataset is still readable without the geometry.
    await page.getByRole("tab", { name: "Table" }).click();
    await expect(
      page.getByRole("table").getByRole("cell", { name: "S$499,000" }),
    ).toBeVisible();
  });

  test("the map and legend fit a 390px viewport", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await openMap(page);

    const overflow = await page.evaluate(
      () =>
        document.documentElement.scrollWidth -
        document.documentElement.clientWidth,
    );
    expect(overflow).toBeLessThanOrEqual(0);

    const svgBox = await mapFigure(page).locator("svg").boundingBox();
    expect(svgBox).not.toBeNull();
    expect(svgBox?.width ?? 0).toBeLessThanOrEqual(390);
  });

  test("loads without console or page errors", async ({ page }) => {
    // A missing publication manifest is an expected 404: the page treats it as
    // "absent" and withholds the national baseline, so it is not a failure.
    await expectPageToLoadWithoutErrors(page, "/explore?view=map", {
      ignoreFailedRequests: [/dashboard-release\.json$/],
    });
    await expect(areaPaths(page)).toHaveCount(55, { timeout: MAP_TIMEOUT });
  });
});

test.describe("Explore table view", () => {
  test.use({ viewport: { width: 1440, height: 1000 } });

  test("renders a real table with the same published values as the list", async ({
    page,
  }) => {
    await page.goto("/explore?view=table");

    const table = page.getByRole("table");
    await expect(table).toBeVisible();
    await expect(
      table.getByRole("columnheader", { name: "Planning area" }),
    ).toBeVisible();
    await expect(
      table.getByRole("columnheader", { name: "Median price" }),
    ).toBeVisible();
    await expect(
      table.getByRole("columnheader", { name: "Median PSF" }),
    ).toBeVisible();
    await expect(
      table.getByRole("columnheader", { name: "Transactions" }),
    ).toBeVisible();

    await expect(table.getByRole("rowheader", { name: "Ang Mo Kio" })).toBeVisible();
    await expect(table.getByRole("cell", { name: "S$499,000" })).toBeVisible();
    await expect(table.getByRole("cell", { name: "971" })).toBeVisible();
    await expect(table.locator("tbody tr")).toHaveCount(25);

    // The caption names the joint section and explains N/A.
    await expect(
      table.getByText("map_metrics.year_2025_hdb").first(),
    ).toBeVisible();
    await expect(table.getByText(/N\/A means/)).toBeVisible();

    // Rows keep their fieldnote link.
    await expect(
      table.getByRole("rowheader", { name: "Ang Mo Kio" }).getByRole("link"),
    ).toHaveAttribute("href", /\/areas\/ang-mo-kio\?from=explore/);
  });

  test("loads without console or page errors", async ({ page }) => {
    await expectPageToLoadWithoutErrors(page, "/explore?view=table", {
      ignoreFailedRequests: [/dashboard-release\.json$/],
    });
    await expect(page.getByRole("table")).toBeVisible();
  });
});
