import { test, expect } from "@playwright/test";
import { expectPageToLoadWithoutErrors } from "./utils/pageHealth";

/**
 * The site root is the **Overview** destination (see `shell/destinations.ts`),
 * not a marketing hero. Each test below names the Overview fact it proves: the
 * editorial question is the page's one `h1`, the three 2025 property-type
 * medians carry their transaction counts, the pathways out are real links, and
 * `/dashboard` is still reachable as the compatibility address for the same
 * surface (canonical link pinned to the root).
 */
test.describe("Home Page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
  });

  test("should load the Overview without errors", async ({ page }) => {
    await expect(page).toHaveTitle(/Egg n Bacon Housing/);
    // The title now describes the Overview question rather than the old
    // "Singapore Market Intelligence" banner.
    await expect(page).toHaveTitle(/what does a home cost here/i);
    await expect(page.locator("body")).toBeVisible();
  });

  test("should display the editorial question as the only level-1 heading", async ({
    page,
  }) => {
    // What this proves: the marketing hero (gradient wordmark + tagline) is
    // gone and the Overview's editorial header has taken its place. One `h1`,
    // the Fieldnotes eyebrow above it, and the "how to start" line below it.
    const headings = page.getByRole("heading", { level: 1 });
    await expect(headings).toHaveCount(1);
    await expect(headings).toHaveText("What does a home cost here?");
    await expect(
      page.getByText("The Singapore housing field guide", { exact: true }),
    ).toBeVisible();
    await expect(
      page.getByText("Start with the kind of home.", { exact: false }).first(),
    ).toBeVisible();

    // What this proves: one quiet provenance line states how much data the page
    // rests on and what span it covers — the period and its published
    // transaction total, the all-history row count, the observed span and the
    // export stamp, each derived from `dashboard_overview` at build time. The
    // shapes are asserted rather than the figures, so a re-export still passes.
    const provenance = page.locator('[data-overview-provenance="true"]');
    await expect(provenance).toBeVisible();
    await expect(provenance).toContainText(/\d{4} complete year/);
    await expect(provenance).toContainText(/[\d,]+ transactions/);
    await expect(provenance).toContainText(/[\d,]+ rows in all history/);
    await expect(provenance).toContainText(/\d{4}–\d{4} \(\d+ years\)/);
    await expect(provenance).toContainText(/nominal SGD/);
    await expect(provenance).toContainText(
      /exported \d{1,2} [A-Z][a-z]{2} \d{4}/,
    );
    await expect(provenance.locator("code")).toHaveText("dashboard_overview");
  });

  test("should display the three property-type medians with their transaction counts", async ({
    page,
  }) => {
    // What this proves: the 2025 medians block is on `/`, one card per property
    // type, each showing a median price and the number of transactions the
    // median was taken over. It replaced the hero's single HDB median and the
    // "36 yrs of data" tile, which the published asset now covers per type.
    const medians = page.getByRole("list", {
      name: "2025 medians by property type",
    });
    await expect(medians).toBeVisible();
    await expect(medians.getByRole("listitem")).toHaveCount(3);

    for (const label of ["HDB", "EC", "Condominium"]) {
      const card = medians.getByRole("listitem").filter({
        has: page.getByRole("heading", { name: label, exact: true }),
      });
      await expect(card).toHaveCount(1);
      // A formatted SGD median ...
      await expect(card).toContainText(/S\$[\d,]{4,}/);
      // ... and the transaction count beside it, from the same stats block.
      await expect(card).toContainText(/[\d,]+ transactions/);
      await expect(card).toContainText("2025 complete year");
    }

    // The not-a-price-index caveat travels with the figures, so a reader cannot
    // read the three medians as a like-for-like comparison.
    await expect(
      page.getByText(/not a like-for-like comparison/i).first(),
    ).toBeVisible();
  });

  test("should display the pathways out of the Overview", async ({ page }) => {
    // What this proves: the two old navigation cards ("Market dashboard" /
    // "Analytics Reports") and the two insight cards are replaced by the one
    // "Keep exploring" pathway row, and every pathway is a base-correct link.
    const pathways = page.getByRole("navigation", { name: "Keep exploring" });
    await expect(pathways).toBeVisible();

    for (const name of [
      "Observed explorer",
      "Monthly trends",
      "Tampines fieldnote",
      "Compare Areas",
      "Decision Tools",
      "Discover Segments",
    ]) {
      const link = pathways.getByRole("link", { name: new RegExp(name) });
      await expect(link).toHaveCount(1);
      await expect(link).toHaveAttribute("href", /^\/.*\S$/);
    }
  });

  test("should navigate to the dashboard compatibility address from the Overview", async ({
    page,
  }) => {
    // What this proves: `/dashboard` is still reachable from `/` (the sidebar's
    // Overview entry) and the surface it renders says it is an alias — the
    // canonical link points at the root instead.
    await page.locator('a[href="/dashboard"]').first().click();
    await expect(page).toHaveURL(/dashboard/);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(
      "What does a home cost here?",
    );
    await expect(page.locator('link[rel="canonical"]')).toHaveCount(1);
    // The canonical is the root under the deployment base — `/` in the root
    // suite, `/egg-n-bacon-housing/` on Pages — not this alias and not merely
    // "something ending in a slash". The origin is the configured site, so only
    // the path is compared.
    const canonicalHref = await page
      .locator('link[rel="canonical"]')
      .getAttribute("href");
    const here = new URL(page.url());
    const rootPath = here.pathname.replace(/dashboard\/?$/, "");
    expect(new URL(canonicalHref ?? "", here).pathname).toBe(rootPath);
    await expect(page.locator('[data-compat-route="true"]')).toContainText(
      "Compatibility address for the Overview",
    );
  });

  test("should navigate to analytics through the Research destination", async ({
    page,
  }) => {
    // What this proves: the Overview still reaches the Studies library, but
    // through the shell's Research destination rather than a home-page card.
    await page
      .getByRole("navigation", { name: "Primary" })
      .getByRole("link", { name: "Research", exact: true })
      .click();
    await expect(page).toHaveURL(/analytics\/?$/);
    await expect(
      page.getByRole("heading", {
        name: "Stories with a visible evidence trail.",
      }),
    ).toBeVisible();
  });

  test("should reach the monthly series from the keep-exploring pathways", async ({
    page,
  }) => {
    // Replaces the deleted "Lease decay, measured" insight card. The Overview
    // no longer advertises that study, so the assertion now proves the trend
    // pathway is wired to the trends surface instead.
    await page
      .getByRole("navigation", { name: "Keep exploring" })
      .getByRole("link", { name: /Monthly trends/ })
      .click();
    await expect(page).toHaveURL(/research\/trends/);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  });

  test("should reach the decision tools from the keep-exploring pathways", async ({
    page,
  }) => {
    // Replaces the deleted "CBD and MRT" insight card: the MRT/lease/scenario
    // tools are now reached through this one pathway, which is where the
    // Overview sends a reader who wants to test an assumption.
    await page
      .getByRole("navigation", { name: "Keep exploring" })
      .getByRole("link", { name: /Decision Tools/ })
      .click();
    await expect(page).toHaveURL(/research\/tools/);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(
      /Make the assumptions editable/,
    );
  });

  test("should not have critical console errors", async ({ page }) => {
    await expectPageToLoadWithoutErrors(page, "/");
  });
});
