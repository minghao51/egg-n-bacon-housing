import { test, expect } from "@playwright/test";
import { expectPageToLoadWithoutErrors } from "../utils/pageHealth";

/**
 * Frozen edition archive (RF07).
 *
 * The archive renders RF00's originals with their own identity and status. The
 * assertions bind to the edition identity in the path, the historical status,
 * the frozen source path and the link back to the series entry — never to a
 * claim that the edition is current.
 */

const LEGACY = "/analytics/archive/2026/legacy-2026-11-12";

test.describe("Analytics archive", () => {
  test("renders the frozen edition with its own identity and status", async ({
    page,
  }) => {
    const response = await page.goto(`${LEGACY}/mrt-impact`);
    expect(response?.status()).toBe(200);

    // One H1: the shell owns it, the article's leading H1 is stripped.
    await expect(page.locator("h1")).toHaveCount(1);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(
      "MRT Impact",
    );

    const status = page.locator('[data-edition-status="historical"]');
    await expect(status).toBeVisible();
    await expect(status).toContainText("Historical edition");
    await expect(status).toContainText("legacy-2026-11-12");
    await expect(status).toContainText(
      "docs/analytics/editions/legacy/2026-11-12/mrt-impact.md",
    );

    // The link back to the series entry is present and resolves.
    await status
      .getByRole("link", { name: "Open the current series entry" })
      .click();
    await expect(page).toHaveURL(/\/analytics\/mrt-impact$/);
  });

  test("a unit-review study keeps its charts withheld in the archive", async ({
    page,
  }) => {
    await page.goto(`${LEGACY}/lease-decay`);

    const status = page.locator('[data-edition-status="historical"]');
    await expect(status).toContainText("Charts stay withheld");
    // The chart island is not mounted on a withheld study.
    await expect(
      page.locator('astro-island[component-url*="InlineChartRenderer"]'),
    ).toHaveCount(0);
  });

  test("the series entry states that no approved edition exists and links the archive", async ({
    page,
  }) => {
    await page.goto("/analytics/mrt-impact");

    const panel = page.locator('[data-edition-status="no-approved-edition"]');
    await expect(panel).toBeVisible();
    await expect(panel).toContainText("No approved current edition");

    const archiveLink = panel.getByRole("link", {
      name: /Archived edition legacy-2026-11-12/,
    });
    await expect(archiveLink).toHaveAttribute("href", `${LEGACY}/mrt-impact`);
  });

  test("an approved edition is offered as the series' current edition", async ({
    page,
  }) => {
    // RF08: the three sign-offs exist for these two editions, so the series entry
    // must name the approved edition and link it, not claim there is none.
    const approved = [
      { series: "data-sources", edition: "data-sources-2026-11-14" },
      { series: "rental-yields", edition: "rental-yields-2026-11-14" },
    ];

    for (const { series, edition } of approved) {
      await expectPageToLoadWithoutErrors(page, `/analytics/${series}`);

      const panel = page.locator('[data-edition-status="approved"]');
      await expect(panel).toBeVisible();
      await expect(panel).toContainText(`Approved edition ${edition}`);
      await expect(
        panel.getByRole("link", { name: /Read the approved edition/ }),
      ).toHaveAttribute("href", `/analytics/archive/2026/${edition}/${series}`);

      // The approved edition renders as approved, not as a frozen historical one.
      const archive = page.locator('[data-edition-status="approved"]');
      await page.goto(`/analytics/archive/2026/${edition}/${series}`);
      await expect(archive).toHaveCount(1);
    }
  });

  test("every archived edition route loads without page errors", async ({
    page,
  }) => {
    for (const slug of [
      "amenity-impact",
      "findings",
      "price-forecasts",
      "spatial-hotspots",
      "temporal-evolution",
    ]) {
      await expectPageToLoadWithoutErrors(page, `${LEGACY}/${slug}`);
    }
  });
});
