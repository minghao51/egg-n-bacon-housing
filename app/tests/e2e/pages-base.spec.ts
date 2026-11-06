import { test, expect } from "@playwright/test";

/**
 * Pages-base release verification (S10).
 *
 * The root suite runs against `astro preview`, where every URL starts at `/`.
 * GitHub Pages serves the same build under `/egg-n-bacon-housing/`, so this spec
 * runs against a static mount of a `ASTRO_PAGES=true` build:
 *
 *   bun run build:pages
 *   PAGES_ORIGIN=http://127.0.0.1:4402 PAGES_BASE_PATH=/egg-n-bacon-housing \
 *   PLAYWRIGHT_BASE_URL=http://127.0.0.1:4402/egg-n-bacon-housing/ \
 *   PLAYWRIGHT_SERVER_COMMAND='bun run serve:pages' \
 *   bunx playwright test tests/e2e/pages-base.spec.ts
 *
 * It is skipped during a normal root run so a missing Pages server never reads
 * as a failure. Every URL here is absolute on purpose: Playwright's `baseURL`
 * does not prefix a path that starts with `/`.
 */

const ORIGIN = process.env.PAGES_ORIGIN ?? "";
const BASE = process.env.PAGES_BASE_PATH ?? "/egg-n-bacon-housing";
const at = (pathname = "/") => `${ORIGIN}${BASE}${pathname}`;

test.skip(
  !ORIGIN,
  "Set PAGES_ORIGIN after `bun run build:pages` and `bun run serve:pages`.",
);

test.describe("Pages base path", () => {
  test.use({ viewport: { width: 1440, height: 1000 } });

  test("serves HTML, CSS and JS under the repository prefix", async ({
    page,
  }) => {
    await page.goto(at("/"));
    await expect(page).toHaveTitle(/Egg n Bacon/);
    await expect(
      page.getByRole("heading", { level: 1, name: /Egg n Bacon/ }),
    ).toBeVisible();

    const stylesheets = await page
      .locator('link[rel="stylesheet"]')
      .evaluateAll((links) => links.map((link) => link.getAttribute("href")));
    const scripts = await page
      .locator("script[src]")
      .evaluateAll((nodes) => nodes.map((node) => node.getAttribute("src")));

    // The external KaTeX stylesheet is allowed; every local asset must carry
    // the base prefix or the Pages deployment would 404 it.
    const local = [...stylesheets, ...scripts].filter((href): href is string =>
      Boolean(href && href.startsWith("/")),
    );
    expect(local.length).toBeGreaterThan(0);
    for (const href of local) {
      expect(href.startsWith(`${BASE}/`)).toBe(true);
    }
  });

  test("hydrates an island and fetches data under the prefix", async ({
    page,
  }) => {
    const failed: string[] = [];
    page.on("response", (response) => {
      if (response.url().startsWith(ORIGIN) && response.status() >= 400) {
        failed.push(`${response.status()} ${response.url()}`);
      }
    });

    await page.goto(at("/explore/"));
    await expect(
      page.getByRole("heading", {
        level: 1,
        name: /Same year\. Same housing type\./,
      }),
    ).toBeVisible();
    // This status only appears after the island fetches dashboard-release.json
    // and verifies the published assets; it proves hydration + base-prefixed
    // data URLs in one assertion.
    await expect(page.getByText(/Publication generation verified/)).toBeVisible(
      { timeout: 30_000 },
    );
    await expect(page.getByLabel("Search planning areas")).toBeVisible();
    await expect(page.getByLabel("Area results")).toBeVisible();

    expect(failed).toEqual([]);
    await expect(
      page.locator('input[type="search"], input[type="text"]').first(),
    ).toBeVisible();
  });

  test("every shipped route renders its heading", async ({ page }) => {
    const routes: Array<[string, RegExp]> = [
      ["/", /Egg n Bacon/],
      ["/dashboard/", /Overview/],
      ["/dashboard/map/", /A layer is a claim/],
      ["/dashboard/trends/", /Make the assumptions editable/],
      ["/dashboard/segments/", /Find an archetype/],
      ["/dashboard/leaderboard/", /Compare Areas/],
      ["/explore/", /Same year\. Same housing type\./],
      ["/research/trends/", /A year of prices, with the sales behind them/],
      ["/research/map/", /A layer is a claim/],
      ["/research/tools/", /Make the assumptions editable/],
      ["/research/segments/", /Find an archetype/],
      ["/analytics/", /Stories with a visible evidence trail\./],
      ["/analytics/lease-decay/", /Lease Decay Impact/],
      ["/analytics/personas/investor/", /Property Investor/],
      ["/catalog/", /Data Catalog/],
      ["/catalog/platinum/unified_dataset/", /Unified Dataset/],
      ["/areas/bishan/", /Bishan/],
    ];

    for (const [pathname, heading] of routes) {
      const response = await page.goto(at(pathname));
      expect(response?.status(), pathname).toBe(200);
      await expect(
        page.getByRole("heading", { level: 1 }).first(),
        pathname,
      ).toHaveText(heading, { timeout: 15_000 });
    }
  });

  test("keeps deep links and their query state", async ({ page }) => {
    await page.goto(
      at("/research/tools/?tool=mrt&ref=QUEENSTOWN&rt=condo&rv=1"),
    );
    await expect(page.getByText("Model review required")).toBeVisible({
      timeout: 30_000,
    });
    await expect
      .poll(() => new URL(page.url()).searchParams.get("tool"), {
        timeout: 10_000,
      })
      .toBe("mrt");
    let url = new URL(page.url());
    expect(url.pathname).toBe(`${BASE}/research/tools/`);
    expect(url.searchParams.get("tool")).toBe("mrt");
    expect(url.searchParams.get("ref")).toBe("QUEENSTOWN");
    expect(url.searchParams.get("rt")).toBe("condo");
    expect(url.searchParams.get("rv")).toBe("1");

    await page.goto(
      at(
        "/dashboard/map/?metric=median_psf&timeBasis=year_2025&propertyType=hdb&area=TAMPINES&layers=spatial.lisa",
      ),
    );
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(
      /A layer is a claim/,
    );
    await expect(page.getByText("Stored LISA class")).toBeVisible({
      timeout: 30_000,
    });
    await expect
      .poll(() => new URL(page.url()).searchParams.get("area"), {
        timeout: 10_000,
      })
      .toBe("TAMPINES");
    url = new URL(page.url());
    expect(url.searchParams.get("metric")).toBe("median_psf");
    expect(url.searchParams.get("timeBasis")).toBe("year_2025");
    expect(url.searchParams.get("propertyType")).toBe("hdb");
    expect(url.searchParams.get("area")).toBe("TAMPINES");
    expect(url.searchParams.get("layers")).toBe("spatial.lisa");
  });

  test("never emits a root-relative internal link", async ({ page }) => {
    await page.goto(at("/dashboard/"));
    const hrefs = await page
      .locator('a[href^="/"]')
      .evaluateAll((links) =>
        links.map((link) => link.getAttribute("href") ?? ""),
      );
    expect(hrefs.length).toBeGreaterThan(5);
    const outside = hrefs.filter(
      (href) => !href.startsWith(`${BASE}/`) && href !== BASE,
    );
    expect(outside).toEqual([]);
  });

  test("every same-origin home link resolves", async ({ page, request }) => {
    await page.goto(at("/"));
    const hrefs = await page
      .locator('a[href^="/"]')
      .evaluateAll((links) =>
        links.map((link) => link.getAttribute("href") ?? ""),
      );
    const unique = [...new Set(hrefs)]
      .map((href) => href.split("#")[0])
      .filter((href) => href.startsWith(`${BASE}/`))
      .slice(0, 30);

    for (const href of unique) {
      const response = await request.get(`${ORIGIN}${href}`);
      expect(response.status(), href).toBe(200);
    }
  });

  test("key routes load without a same-origin 4xx or page error", async ({
    page,
  }) => {
    const failed: string[] = [];
    const errors: string[] = [];
    page.on("response", (response) => {
      if (response.url().startsWith(ORIGIN) && response.status() >= 400) {
        failed.push(`${response.status()} ${response.url()}`);
      }
    });
    page.on("pageerror", (error) => errors.push(String(error)));

    for (const pathname of [
      "/",
      "/dashboard/",
      "/research/tools/",
      "/research/segments/",
      "/research/trends/",
      "/analytics/",
      "/catalog/",
      "/explore/",
    ]) {
      await page.goto(at(pathname));
      // Wait for the browser to settle outstanding chunk/data requests rather
      // than guessing a fixed delay; prefetch can keep this busy on slow hosts.
      await page
        .waitForLoadState("networkidle", { timeout: 5_000 })
        .catch(() => undefined);
    }

    expect(errors).toEqual([]);
    expect(failed).toEqual([]);
  });
});

test.describe("Pages base path on a narrow viewport", () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test("opens the drawer and reaches a research route", async ({ page }) => {
    await page.goto(at("/dashboard/"));
    const toggle = page.getByRole("button", { name: /Open navigation menu/i });
    await expect(toggle).toBeVisible();
    await toggle.click();
    await expect(toggle).toHaveAttribute("aria-expanded", "true");
    await page
      .getByRole("navigation", { name: "Main navigation" })
      .getByRole("link", { name: /Research map/ })
      .click();
    await expect(page).toHaveURL(new RegExp(`${BASE}/research/map(?:/|\\?|$)`));
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(
      /A layer is a claim/,
    );
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth > window.innerWidth + 1,
    );
    expect(overflow).toBe(false);
  });
});
