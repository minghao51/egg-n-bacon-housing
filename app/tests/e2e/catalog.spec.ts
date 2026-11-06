import { test, expect } from "@playwright/test";
import { expectPageToLoadWithoutErrors } from "./utils/pageHealth";

/**
 * Catalog routes (slice S9).
 *
 * The catalog is a separate snapshot from the platinum artifacts, so the tests
 * bind to both labelled counts, the declared-vs-observed schema columns and the
 * retained dependency/nested-external URLs. No count is rewritten to match the
 * other generation.
 */

test.describe("Data catalog", () => {
  test.use({ viewport: { width: 1440, height: 1000 } });

  test("labels the catalog snapshot instead of claiming live data", async ({
    page,
  }) => {
    await page.goto("/catalog/");
    await expect(
      page.getByRole("heading", { level: 1, name: "Data Catalog" }),
    ).toBeVisible();
    await expect(
      page.getByText("Catalog snapshot, not a live run"),
    ).toBeVisible();
    await expect(page.getByText(/Generated 12 Sept? 2026/)).toBeVisible();
    await expect(
      page.getByText(
        /“Available” means the artifact was present when the catalog was generated/,
      ),
    ).toBeVisible();

    // The dataset table keeps its filter and labels snapshot counts.
    await expect(page.getByLabel("Search datasets")).toBeVisible();
    await expect(
      page.getByRole("columnheader", { name: /Rows \(snapshot\)/ }),
    ).toBeVisible();
    await expect(
      page.getByRole("columnheader", { name: /Artifact presence/ }),
    ).toBeVisible();
  });

  test("shows the snapshot discrepancy without rewriting either count", async ({
    page,
  }) => {
    await page.goto("/catalog/platinum/unified_dataset");
    await expect(
      page.getByRole("heading", { level: 1, name: "Unified Dataset" }),
    ).toBeVisible();
    await expect(page.getByText("Snapshot discrepancy")).toBeVisible();
    await expect(
      page.getByText("Catalog reports (this generation)"),
    ).toBeVisible();
    await expect(page.getByText("1,233,405 rows")).toBeVisible();
    await expect(page.getByText("Inspected artifact")).toBeVisible();
    await expect(page.getByText("1,234,928 rows")).toBeVisible();
    await expect(
      page.getByText(/Neither count replaces the other/),
    ).toBeVisible();
    await expect(
      page.getByText(/Catalog snapshot generated 12 Sept? 2026/),
    ).toBeVisible();
  });

  test("keeps declared requiredness and observed nullness separate", async ({
    page,
  }) => {
    await page.goto("/catalog/platinum/unified_dataset");
    await expect(
      page.getByRole("columnheader", { name: "Declared in schema" }),
    ).toBeVisible();
    await expect(
      page.getByRole("columnheader", { name: "Observed nulls" }),
    ).toBeVisible();
    await expect(
      page.getByRole("columnheader", { name: "Observed null %" }),
    ).toBeVisible();
    await expect(
      page.getByRole("columnheader", { name: "Requiredness check" }),
    ).toBeVisible();
    // lat/lon are declared required but carry observed nulls in this artifact.
    await expect(
      page.getByText("2 required fields show observed nulls"),
    ).toBeVisible();
    await expect(
      page.getByText("required · observed nulls").first(),
    ).toBeVisible();
  });

  test("schema search and sorting are keyboard operable", async ({ page }) => {
    await page.goto("/catalog/platinum/unified_dataset");
    const search = page.getByLabel("Search schema fields");
    await expect(search).toBeVisible();
    await search.fill("psf");
    await expect(page.getByText(/^\d+ fields$/)).toBeVisible();
    await expect(
      page.getByRole("rowheader", { name: "psf", exact: true }),
    ).toHaveCount(0); // field names render as cells, not row headers
    await expect(
      page.getByRole("cell", { name: "psf", exact: true }),
    ).toBeVisible();

    // The sort control is a real button, reachable and activatable by keyboard.
    const fieldSort = page.getByRole("button", { name: /^Field/ });
    await fieldSort.focus();
    await page.keyboard.press("Enter");
    const fieldHeader = page
      .getByRole("columnheader", { name: /^Field/ })
      .first();
    await expect(fieldHeader).toHaveAttribute("aria-sort", "ascending");
    await expect(fieldSort).toBeFocused();
  });

  test("dependency and nested external links survive", async ({ page }) => {
    await page.goto("/catalog/platinum/unified_dataset");

    // Named upstream dependency list, not only the graph.
    const upstream = page
      .getByRole("heading", { name: /Upstream/ })
      .locator("xpath=..");
    const dependency = upstream.getByRole("link", {
      name: "Enriched Transactions",
      exact: true,
    });
    await expect(dependency).toBeVisible();
    await dependency.click();
    await expect(page).toHaveURL(/catalog\/gold\/transactions_enriched/);
    await expect(
      page.getByRole("heading", { level: 1, name: "Enriched Transactions" }),
    ).toBeVisible();

    // Nested external dataset IDs keep their slug conversion.
    await page.goto("/catalog/bronze/external/BusStops");
    await expect(
      page.getByRole("heading", {
        level: 1,
        name: "Bus Stops (Parse Cache)",
      }),
    ).toBeVisible();
    await expect(page.getByText("Upstream (0)").first()).toBeVisible();
  });

  test("does not log errors", async ({ page }) => {
    await expectPageToLoadWithoutErrors(page, "/catalog/");
    await expectPageToLoadWithoutErrors(
      page,
      "/catalog/platinum/unified_dataset",
    );
  });
});
