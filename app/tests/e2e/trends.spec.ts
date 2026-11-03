import { test, expect, type Page } from "@playwright/test";
import { expectPageToLoadWithoutErrors } from "./utils/pageHealth";

/**
 * `/research/trends` — monthly price and volume destination.
 *
 * Every assertion binds to a published value from `dashboard_trends` (2025 HDB
 * totals/sums, December 2025, EC December 2025) or to the URL round trip, so
 * reverting the series binding, the window filter or the hydration path fails
 * the suite instead of silently rendering an empty shell.
 */

const TABLE = "#trends-monthly-table";

function tableRows(page: Page) {
  return page.locator(`${TABLE} tbody tr`);
}

test.describe("Research trends", () => {
  test.use({ viewport: { width: 1440, height: 1000 } });

  test("renders one heading and the default 2025 HDB series", async ({
    page,
  }) => {
    await page.goto("/research/trends");

    await expect(page.getByRole("heading", { level: 1 })).toHaveText(
      "A year of prices, with the sales behind them.",
    );
    await expect(page.getByRole("heading", { level: 1 })).toHaveCount(1);
    await expect(
      page.getByText(/not an adjusted price index/i).first(),
    ).toBeVisible();

    // The default selection is HDB, 2025 complete year.
    await expect(page.getByRole("radio", { name: "HDB" })).toBeChecked();
    await expect(
      page.getByRole("radio", { name: "2025 complete year" }),
    ).toBeChecked();

    // Latest-value summary block: December 2025 and the twelve-month count.
    const summary = page.locator("section", {
      has: page.getByRole("heading", { name: /HDB · 2025 complete year/ }),
    });
    await expect(summary).toContainText("2025-12");
    await expect(summary).toContainText("S$635,000");
    await expect(summary).toContainText("2,024");
    await expect(summary).toContainText("25,084");
    await expect(summary).toContainText("published across the twelve months");
  });

  test("lists every month of 2025 with its price and count", async ({
    page,
  }) => {
    await page.goto("/research/trends");

    await expect(tableRows(page)).toHaveCount(12);
    await expect(tableRows(page).first()).toContainText("2025-01");
    await expect(tableRows(page).last()).toContainText("2025-12");

    const december = page.locator(`${TABLE} tbody tr`, {
      hasText: "2025-12",
    });
    await expect(december).toContainText("635,000");
    await expect(december).toContainText("2,024");
  });

  test("a window selector change keeps the calendar bounds", async ({
    page,
  }) => {
    await page.goto("/research/trends");
    await expect(tableRows(page)).toHaveCount(12);

    await page.getByRole("radio", { name: "All history" }).check();

    await expect(tableRows(page)).toHaveCount(442);
    await expect(tableRows(page).first()).toContainText("1990-01");
    await expect(tableRows(page).last()).toContainText("2026-10");
    expect(new URL(page.url()).searchParams.get("window")).toBe("all");

    // The asset's last month is stated in the source footer, not inferred from
    // the selected window.
    await expect(
      page.getByText(/Last month actually present in the asset/i).first(),
    ).toBeVisible();
    await expect(
      page.locator("footer").getByText("2026-10", { exact: true }),
    ).toBeVisible();
  });

  test("a deep link keeps its series and window after hydration", async ({
    page,
  }) => {
    await page.goto("/research/trends?series=ec&window=year_2025");

    await expect(page.getByRole("radio", { name: "EC" })).toBeChecked();
    await expect(
      page.getByRole("radio", { name: "2025 complete year" }),
    ).toBeChecked();

    // Twelve 2025 months, and the EC values rather than the HDB ones.
    await expect(tableRows(page)).toHaveCount(12);
    await expect(tableRows(page).first()).toContainText("2025-01");
    await expect(tableRows(page).last()).toContainText("2025-12");
    const december = page.locator(`${TABLE} tbody tr`, {
      hasText: "2025-12",
    });
    await expect(december).toContainText("1,630,000");
    await expect(december).toContainText("298");

    // The writer only rewrites the URL when it differs; the EC selection is
    // kept, and the default window is omitted from the canonical URL.
    expect(new URL(page.url()).searchParams.get("series")).toBe("ec");

    // Re-opening whatever the writer left in the address bar reproduces it.
    await page.goto(page.url());
    await expect(page.getByRole("radio", { name: "EC" })).toBeChecked();
    await expect(tableRows(page)).toHaveCount(12);

    // An invalid series falls back to the documented default, not to a
    // different valid series.
    await page.goto("/research/trends?series=detached-house&window=forever");
    await expect(page.getByRole("radio", { name: "HDB" })).toBeChecked();
    await expect(
      page.getByRole("radio", { name: "2025 complete year" }),
    ).toBeChecked();
  });

  test("discloses the zoomed price axis and the zero-based volume axis", async ({
    page,
  }) => {
    await page.goto("/research/trends");

    await expect(page.getByText(/Zoomed price axis:/i).first()).toBeVisible();
    await expect(
      page.getByText(/does not start at zero/i).first(),
    ).toBeVisible();
    await expect(page.getByText(/Zero-based axis:/i).first()).toBeVisible();
    await expect(
      page.getByText(/the scale starts at 0/i).first(),
    ).toBeVisible();

    // The published minimum and maximum of the window are stated, not implied.
    await expect(
      page.getByText(/published minimum S\$612,888/i).first(),
    ).toBeVisible();
    await expect(page.getByText(/maximum S\$645,000/i).first()).toBeVisible();
  });

  test("the combined series publishes no invented transaction count", async ({
    page,
  }) => {
    await page.goto("/research/trends?series=all");

    await expect(
      page.getByRole("radio", { name: "All property types" }),
    ).toBeChecked();

    const summary = page.locator("section", {
      has: page.getByRole("heading", { name: /All property types · 2025/ }),
    });
    // A price is published; a combined count is not, so it reads N/A.
    await expect(summary).toContainText("S$1,169,000");
    await expect(summary).toContainText("N/A");

    const december = page.locator(`${TABLE} tbody tr`, {
      hasText: "2025-12",
    });
    await expect(december).toContainText("1,169,000");
    await expect(december).toContainText("N/A");
  });

  test("loads without console or page errors", async ({ page }) => {
    await expectPageToLoadWithoutErrors(page, "/research/trends");
  });
});

test.describe("Research trends on a narrow viewport", () => {
  test("keeps the reading inside the viewport", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 900 });
    await page.goto("/research/trends");

    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await expect(tableRows(page)).toHaveCount(12);

    const overflow = await page.evaluate(
      () =>
        document.documentElement.scrollWidth -
        document.documentElement.clientWidth,
    );
    expect(overflow).toBeLessThanOrEqual(0);
  });
});
