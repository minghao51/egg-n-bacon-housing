import { test, expect } from "@playwright/test";

/**
 * S1 evidence-boundary regressions.
 *
 * These cover the defects recorded in docs/implementation/s0-baseline.md §4.1
 * (legacy map selection overwritten before it is read), §4.2 (Spatial Hotspots
 * crashing the whole tools workspace) and §4.3 (overlays silently failing to
 * match planning-area geometry keys).
 */

const DEEP_LINK =
  "/dashboard/map?metric=median_psf&timeBasis=year_2025&propertyType=hdb&area=TAMPINES&layers=spatial.lisa";

test.describe("S1 evidence boundary", () => {
  test("legacy map deep link keeps all five parameter groups", async ({
    page,
  }) => {
    await page.goto(DEEP_LINK);
    await expect(page.locator(".leaflet-container")).toBeVisible({
      timeout: 30_000,
    });
    // Give the writer effect time to run at least once after hydration.
    await page.waitForTimeout(1_500);

    const url = new URL(page.url());
    expect(url.searchParams.get("metric")).toBe("median_psf");
    expect(url.searchParams.get("timeBasis")).toBe("year_2025");
    expect(url.searchParams.get("propertyType")).toBe("hdb");
    expect(url.searchParams.get("area")).toBe("TAMPINES");
    expect(url.searchParams.get("layers")).toBe("spatial.lisa");

    // The selection must also be applied to the hydrated controls, not only
    // preserved in the address bar.
    await expect(page.locator("select").first()).toHaveValue("median_psf");
    await expect(page.getByText("TAMPINES").first()).toBeVisible();
    await expect
      .poll(() => page.url(), { timeout: 10_000 })
      .toContain("metric=median_psf&timeBasis=year_2025&propertyType=hdb");
  });

  test("spatial overlay paints analytic fills onto planning-area geometry", async ({
    page,
  }) => {
    const pageErrors: string[] = [];
    page.on("pageerror", (error) => pageErrors.push(String(error)));

    await page.goto(
      "/dashboard/map?metric=median_price&timeBasis=whole&propertyType=all&layers=spatial.hotspot",
    );
    await expect(page.locator(".leaflet-container")).toBeVisible({
      timeout: 30_000,
    });
    await expect
      .poll(
        async () =>
          page
            .locator(".leaflet-overlay-pane path")
            .evaluateAll((paths) => paths.length),
        { timeout: 30_000 },
      )
      .toBeGreaterThan(55);

    const fills = await page
      .locator(".leaflet-overlay-pane path")
      .evaluateAll((paths) =>
        paths.map((path) => path.getAttribute("fill")).filter(Boolean),
      );

    // The hotspot scale is #fee090 (not significant) / #cccccc (no record).
    // Before the geometry-key fix every feature resolved to "no record".
    const notSignificant = fills.filter((fill) => fill === "#fee090").length;
    const noRecord = fills.filter((fill) => fill === "#cccccc").length;
    expect(notSignificant).toBeGreaterThan(0);
    expect(notSignificant).toBeGreaterThan(noRecord);
    expect(pageErrors).toEqual([]);
  });

  test("spatial hotspot tool renders published towns instead of crashing", async ({
    page,
  }) => {
    const pageErrors: string[] = [];
    page.on("pageerror", (error) => pageErrors.push(String(error)));

    await page.goto("/dashboard/trends");
    const spatialTab = page.getByRole("tab", {
      name: /Spatial Hotspots/i,
    });
    await expect(spatialTab).toBeVisible({ timeout: 30_000 });
    // Retry until the island has hydrated; a pre-hydration click is a no-op.
    await expect(async () => {
      await spatialTab.click();
      await expect(spatialTab).toHaveAttribute("aria-selected", "true");
    }).toPass({ timeout: 30_000 });

    await expect(
      page.getByText("4 cluster types across 40 published town records"),
    ).toBeVisible({ timeout: 30_000 });
    // The published allocation path (or its explicit unavailable state) must
    // replace the retired hardcoded portfolio rationale.
    await expect(
      page.getByText(/snapshot publishes cluster allocations/i),
    ).toBeVisible();
    await expect(page.getByText(/Minimize LL exposure/)).toHaveCount(0);
    await expect(page.getByText(/pioneers for upside potential/)).toHaveCount(
      0,
    );

    // The old failure mode unmounted the entire tools workspace.
    await expect(
      page.getByRole("tab", { name: /MRT\/CBD Impact/i }),
    ).toBeVisible();
    await expect(page.getByRole("alert")).toHaveCount(0);
    expect(pageErrors).toEqual([]);
  });
});
