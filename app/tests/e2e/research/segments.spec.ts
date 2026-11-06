import { test, expect, type Page } from "@playwright/test";
import { expectPageToLoadWithoutErrors } from "../utils/pageHealth";

/**
 * `/research/segments` — stored research archive.
 *
 * Every assertion binds to something the archive actually supplies (the six
 * segments, Bishan 644 PSF, the 99% stored confidence label) or to the URL
 * contract, so reverting the evidence gate, the parse-before-serialise fix or
 * the two-to-four shortlist fails loudly instead of quietly rendering defaults.
 */

const H1 = "Find an archetype. Then inspect its evidence.";

async function openResearchSegments(page: Page, query = "") {
  await page.goto(`/research/segments${query}`);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(H1);
  // The island is client-only; wait for the archive to render.
  await expect(
    page.getByRole("heading", { name: "Six stored research segments" }),
  ).toBeVisible();
}

function params(page: Page) {
  return new URL(page.url()).searchParams;
}

test.describe("Research segments", () => {
  test.use({ viewport: { width: 1440, height: 1000 } });

  test("renders one heading, the archive status and all six segments", async ({
    page,
  }) => {
    await openResearchSegments(page);

    await expect(page.getByRole("heading", { level: 1 })).toHaveCount(1);
    await expect(page.getByText("Research / Segments").first()).toBeVisible();
    await expect(page.getByText(/Archive: /).first()).toBeVisible();
    await expect(
      page.getByText(/not listed in the dashboard release manifest/i),
    ).toBeVisible();

    await expect(
      page.getByText(/archetypes match \(weighted fit\)/),
    ).toBeVisible();
    await expect(page.getByText("Stored avg PSF").first()).toBeVisible();
    await expect(
      page.getByText(/Period \/ yield provenance require review/).first(),
    ).toBeVisible();
    // Every card reports its declared cohort size, none report yield/growth.
    await expect(
      page.getByRole("button", { name: /^Add .* to comparison$/ }),
    ).toHaveCount(6);
    await expect(
      page.getByText(/not a return probability/).first(),
    ).toBeVisible();
  });

  test("a cold deep link keeps all five query IDs", async ({ page }) => {
    await openResearchSegments(
      page,
      "?persona=investor&tab=investigate&segment=large_size_stable&segments=large_size_stable,high_growth_recent&area=bishan",
    );

    // Parse-before-serialise: the parameters survive the load, and the
    // workspace writes back through its own serialiser (area is normalised).
    await expect.poll(() => params(page).get("area")).toBe("BISHAN");
    expect(params(page).get("segment")).toBe("large_size_stable");
    expect(params(page).get("persona")).toBe("investor");
    expect(params(page).get("tab")).toBe("investigate");
    expect(params(page).get("segments")).toBe(
      "large_size_stable,high_growth_recent",
    );

    // …and they drove the workspace: investor persona, investigation of Bishan.
    await expect(page.getByText("Comparison set: 2 of 4")).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Bishan / selected research area" }),
    ).toBeVisible();
  });

  test("an unknown segment ID is dropped without breaking the tab", async ({
    page,
  }) => {
    await openResearchSegments(page, "?tab=compare&segments=ghost_a,ghost_b");

    await expect(
      page.getByRole("heading", { name: /Comparison needs 2-4 segments/ }),
    ).toBeVisible();
    await expect.poll(() => params(page).get("segments")).toBeNull();
    expect(params(page).get("tab")).toBe("compare");
  });

  test("the shortlist enforces four slots and explains the removal", async ({
    page,
  }) => {
    await openResearchSegments(
      page,
      "?tab=compare&segments=large_size_stable,high_growth_recent,speculator_hotspots,declining_areas",
    );

    await expect(
      page.getByText(/Comparison set is full \(4 of 4\)/),
    ).toBeVisible();
    await expect(
      page.getByText("Two segments, one research vocabulary"),
    ).toBeVisible();
    await expect(
      page.getByText(/not additive and are not market coverage/).first(),
    ).toBeVisible();
    await expect(
      page.getByRole("rowheader", { name: "Observation period" }),
    ).toBeVisible();
    await expect(page.getByText("Not supplied").first()).toBeVisible();

    await page.getByRole("button", { name: "Remove Declining Areas" }).click();

    await expect(
      page.getByText(/Add another segment .* 1 slot available/),
    ).toBeVisible();
    await expect(page.getByText("Remove Declining Areas")).toHaveCount(0);
  });

  test("a single shortlisted segment explains the two-segment minimum", async ({
    page,
  }) => {
    await openResearchSegments(page, "?tab=compare&segments=large_size_stable");

    await expect(
      page.getByRole("heading", { name: /Comparison needs 2-4 segments/ }),
    ).toBeVisible();
    await expect(page.getByText(/One segment is shortlisted/)).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Remove Large Size Stable" }),
    ).toBeVisible();
  });

  test("investigation labels stored archive values and gates model fields", async ({
    page,
  }) => {
    await openResearchSegments(
      page,
      "?tab=investigate&segment=large_size_stable&area=bishan",
    );

    const panel = page.locator("text=Bishan / selected research area").first();
    await expect(panel).toBeVisible();
    await expect(page.getByText("S$644").first()).toBeVisible();
    await expect(page.getByText(/stored confidence label 99%/)).toBeVisible();
    await expect(
      page.getByText(/No sample count or observation period is supplied/i),
    ).toBeVisible();
    // All ten declared areas fit the default constraints; none are dropped.
    await expect(page.getByText(/Showing 10 of 10/)).toBeVisible();

    // Selecting a gated field surfaces its caveat rather than a current value.
    await page.getByRole("button", { name: /Stored 6M forecast/ }).click();
    await expect(
      page.getByText(
        /A historical archive forecast with no supplied model definition/i,
      ),
    ).toBeVisible();
    await expect(
      page.getByText(/never as current recommendations/i),
    ).toBeVisible();

    // Two entry points link to the observed surface: the shortlist rail and
    // the selected-area panel. Assert the panel's link specifically.
    const observed = page.getByRole("link", {
      name: "Open observed comparison →",
    });
    await expect(observed).toHaveAttribute("href", /\/explore\?area=BISHAN$/);
  });

  test("constraints can empty the declared-area list without substituting", async ({
    page,
  }) => {
    await openResearchSegments(
      page,
      "?tab=investigate&segment=large_size_stable",
    );

    await page.getByLabel("Core Central Region").uncheck();
    await page.getByLabel("Rest of Central Region").uncheck();

    await expect(
      page.getByRole("heading", {
        name: "No declared areas fit these constraints",
      }),
    ).toBeVisible();
    await expect(page.getByText(/10 linked areas are declared/)).toBeVisible();
    await expect(
      page.getByText(/Nothing has been added or substituted/),
    ).toBeVisible();
  });

  test("constraints round-trip through the URL, versioned by fv", async ({
    page,
  }) => {
    await openResearchSegments(page);
    await page.getByLabel("Core Central Region").uncheck();

    await expect.poll(() => params(page).get("fv")).toBe("1");
    expect(params(page).get("regions")).toBe("RCR,OCR");
    expect(params(page).get("psf")).toBe("400-1000");

    // Reloading the same URL restores the constraint, not the preset.
    await page.reload();
    await expect(page.getByLabel("Core Central Region")).not.toBeChecked();
    await expect(page.getByLabel("Rest of Central Region")).toBeChecked();
  });

  test("navigation points at the research route and marks it current", async ({
    page,
  }) => {
    await openResearchSegments(page);

    const navLink = page
      .getByRole("link", { name: /Discover Segments/ })
      .first();
    await expect(navLink).toHaveAttribute("href", /\/research\/segments$/);
    await expect(navLink).toHaveAttribute("aria-current", "page");
  });

  test("should not have console errors", async ({ page }) => {
    await expectPageToLoadWithoutErrors(page, "/research/segments", {
      ignoreConsoleErrors: ["does not provide an export", "SyntaxError"],
      ignorePageErrors: ["does not provide an export", "SyntaxError"],
    });
  });
});

test.describe("Research segments - mobile", () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test("no horizontal overflow and the shortlist stays reachable", async ({
    page,
  }) => {
    await openResearchSegments(page);

    const overflow = await page.evaluate(
      () =>
        document.documentElement.scrollWidth -
        document.documentElement.clientWidth,
    );
    expect(overflow).toBeLessThanOrEqual(1);
    await expect(
      page.getByText(/archetypes match \(weighted fit\)/),
    ).toBeVisible();
  });
});
