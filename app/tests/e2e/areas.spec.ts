import { test, expect, type Page } from "@playwright/test";

import { servePackBytesFromDisk } from "./utils/servePackBytes";

/**
 * `/areas/[slug]` area fieldnote (slice S6).
 *
 * The assertions bind to the published `map_metrics.year_2025_hdb` values for
 * Tampines, to the build-time release verdict of this tree (a
 * `dashboard-release.json` is published and verifies, so the national
 * comparison must render), and to the explorer → fieldnote → explorer round
 * trip.
 */

// Tests that start on /explore read the shipped v2 default window; serve the
// pinned pack bytes raw so preview's `.gz` re-labelling cannot mask the path.
test.beforeEach(async ({ page }) => {
  await servePackBytesFromDisk(page);
});

function areaList(page: Page) {
  return page.getByRole("list", { name: "Planning areas" });
}

function backLink(page: Page) {
  return page.getByRole("link", { name: /back to explore/i });
}

test.describe("Area fieldnote", () => {
  test.use({ viewport: { width: 1440, height: 1000 } });

  test("Tampines shows its published 2025 HDB medians and count", async ({
    page,
  }) => {
    await page.goto("/areas/tampines");

    // One page heading: the area name.
    await expect(page.locator("h1")).toHaveCount(1);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(
      "Tampines",
    );

    // The exact section identity, not a generic "2025" label.
    await expect(
      page.getByText("map_metrics.year_2025_hdb").first(),
    ).toBeVisible();

    // Median price, count and PSF as published (710000 / 1921 / 620).
    await expect(page.getByText("S$710,000").first()).toBeVisible();
    await expect(page.getByText("1,921").first()).toBeVisible();
    await expect(page.getByText("S$620").first()).toBeVisible();

    // The limits panel is explicit about what the aggregate cannot answer.
    await expect(page.getByText(/not a valuation/i).first()).toBeVisible();
    await expect(
      page.getByText(/No flat-type, floor, lease or size filters/i),
    ).toBeVisible();
    await expect(
      page.getByText(/No confidence interval is published/i),
    ).toBeVisible();

    // Source & method names both asset sections and forbids dividing the two
    // medians.
    await expect(
      page.getByText("dashboard_overview.stats.year_2025_hdb").first(),
    ).toBeVisible();
    await expect(
      page.getByText(/do not divide one by the other/i),
    ).toBeVisible();
  });

  test("the published manifest verifies, so the national comparison renders", async ({
    page,
  }) => {
    await page.goto("/areas/tampines");

    // This tree publishes `dashboard-release.json`; the build-time verdict is
    // a verified generation, carried on the page instead of a warning.
    await expect(
      page.getByText(/Publication generation verified at build time/i),
    ).toBeVisible();
    await expect(
      page.getByText(/National comparison could not be verified; withheld/i),
    ).toHaveCount(0);
    await expect(
      page.getByText(/ Assets do not share one publication generation/i),
    ).toHaveCount(0);

    // The national row is present with the published 2025 HDB figures.
    await expect(
      page.getByText(/dashboard_overview\.stats\.year_2025_hdb/).first(),
    ).toBeVisible();
    await expect(page.getByText(/S\$628,000/).first()).toBeVisible();
    await expect(page.getByText(/S\$82,000/).first()).toBeVisible();

    // Scoped to the comparison panel: the fieldnote also renders the RF10
    // activity table, and an unscoped `getByRole("table")` would count both.
    const table = page
      .locator('section[aria-labelledby="area-comparison-heading"]')
      .getByRole("table");
    await expect(table.getByRole("row")).toHaveCount(3);
    await expect(
      table.getByRole("rowheader", { name: "Singapore" }),
    ).toBeVisible();
    await expect(
      table.getByRole("rowheader", { name: "Tampines" }),
    ).toBeVisible();
  });

  test("the availability panel names every combination, including the missing EC one", async ({
    page,
  }) => {
    await page.goto("/areas/bedok");

    await expect(
      page.getByRole("heading", { name: /what else is published/i }),
    ).toBeVisible();

    // Bedok publishes 2025 HDB but no EC transactions in the joint section.
    const availabilityList = page.locator(
      'section[aria-labelledby="area-availability-heading"]',
    );
    // The label also exists as a <option> in the section selector, so the
    // availability assertions are scoped to the list they describe.
    await expect(
      availabilityList.getByText("2025 complete year · HDB").first(),
    ).toBeVisible();
    await expect(
      availabilityList.getByText("2025 complete year · EC").first(),
    ).toBeVisible();
    await expect(
      availabilityList
        .getByText(/no transactions published in this joint section/i)
        .first(),
    ).toBeVisible();
    // Missing is not zero: the EC row never renders a S$0 median.
    await expect(page.getByText(/S\$0\b/)).toHaveCount(0);

    // Lim Chu Kang has no 2025 HDB block, so its fieldnote is anchored on the
    // all-history section; 2025 still appears in the availability panel as
    // "not published" rather than as a zero.
    await page.goto("/areas/lim-chu-kang");
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(
      "Lim Chu Kang",
    );
    // The default section for this area is all-history HDB; the label also
    // exists as a hidden <option>, so the visible assertion targets the panel.
    await expect(
      page
        .locator('section[aria-labelledby="area-comparison-heading"]')
        .getByText(/map_metrics\.whole_hdb/)
        .first(),
    ).toBeVisible();
    await expect(
      page.getByText(/no transactions published in year_2025_hdb/i).first(),
    ).toHaveCount(0);
    const availability = page.locator(
      'section[aria-labelledby="area-availability-heading"]',
    );
    await expect(
      availability.getByText("Not published", { exact: false }).first(),
    ).toBeVisible();
    await expect(page.getByText(/S\$0\b/)).toHaveCount(0);
  });

  test("an explorer row links here and the return link keeps the query", async ({
    page,
  }) => {
    await page.goto("/explore");

    const rowLink = areaList(page).getByRole("link", { name: "Ang Mo Kio" });
    // The explorer default is a published window, so the row carries its
    // concrete id; the fieldnote then reports it instead of substituting 2025.
    await expect(rowLink).toHaveAttribute(
      "href",
      /\/areas\/ang-mo-kio\?from=explore&property=hdb&period=ttm_2026_10$/,
    );

    await rowLink.click();
    await expect(page).toHaveURL(/\/areas\/ang-mo-kio\?from=explore/);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(
      "Ang Mo Kio",
    );
    // The fieldnote says it does not carry the current window, and still shows
    // its fixed default section (2025 HDB: S$499,000).
    await expect(
      page.locator('[data-area-selection-notice="true"]'),
    ).toContainText("ttm_2026_10");
    await expect(page.getByText("S$499,000").first()).toBeVisible();

    // The return link carries the explorer query (validated keys only),
    // including the concrete published period.
    await expect(backLink(page)).toHaveAttribute(
      "href",
      /\/explore\?from=explore&property=hdb&period=ttm_2026_10$/,
    );

    await backLink(page).click();
    await expect(page).toHaveURL(/\/explore/);
    await expect(areaList(page).getByText("Ang Mo Kio").first()).toBeVisible();
    // The return lands on the same published window the row carried, not on a
    // different one (the footer names the period id in its own <code>).
    await expect(
      page.locator("footer").getByText("ttm_2026_10", { exact: true }).first(),
    ).toBeVisible();
    expect(new URL(page.url()).searchParams.get("period")).toBe("ttm_2026_10");
  });

  test("a direct visit returns to the plain explorer route", async ({
    page,
  }) => {
    await page.goto("/areas/tampines");

    // No `?from=explore` marker, so no query is echoed back.
    await expect(backLink(page)).toHaveAttribute("href", /\/explore$/);

    await backLink(page).click();
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(
      "Same year. Same housing type.",
    );
  });
});

/**
 * The build-time verdict is baked into the static page, so a manifest injected
 * in the browser cannot change it in either direction: this tree's manifest
 * already verified the generation, and serving a tampered one over the route
 * must not withdraw or alter the comparison the build proved.
 */
test.describe("Area fieldnote with a verified generation", () => {
  test.use({ viewport: { width: 1440, height: 1000 } });

  test("ignores a client-injected manifest because the verdict is build-time", async ({
    page,
  }) => {
    const { createHash } = await import("node:crypto");
    const { readFileSync } = await import("node:fs");
    const { gunzipSync } = await import("node:zlib");
    const { join } = await import("node:path");

    const assets = [
      "dashboard_overview.json.gz",
      "dashboard_trends.json.gz",
      "dashboard_segments.json.gz",
      "dashboard_leaderboard.json.gz",
      "map_metrics.json.gz",
      "hotspots.json.gz",
      "amenity_summary.json.gz",
    ];
    const dataDir = join(process.cwd(), "public", "data");

    const canonical = (value: unknown): string => {
      if (Array.isArray(value)) return `[${value.map(canonical).join(",")}]`;
      if (value && typeof value === "object") {
        const entries = Object.entries(value as Record<string, unknown>)
          .filter(([, v]) => v !== undefined)
          .sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0));
        return `{${entries
          .map(([k, v]) => `${JSON.stringify(k)}:${canonical(v)}`)
          .join(",")}}`;
      }
      return JSON.stringify(value);
    };

    const manifestBody = {
      schemaVersion: "1.0.0",
      generatedAt: "2026-11-02T00:00:00Z",
      observationRange: {
        startMonth: "1990-01",
        endMonth: "2026-10",
        completeYear: 2025,
      },
      periodDefinitions: {},
      inclusionRules: {},
      provenance: { sources: [] },
      assets: assets.map((path) => {
        const bytes = readFileSync(join(dataDir, path));
        const text = gunzipSync(bytes).toString("utf8");
        return {
          path,
          sha256: createHash("sha256").update(bytes).digest("hex"),
          contentSha256: createHash("sha256")
            .update(new TextEncoder().encode(text))
            .digest("hex"),
          bytes: bytes.length,
          shape: text.trimStart()[0] === "[" ? "array" : "object",
          metricScopes: ["median_price"],
        };
      }),
    };
    // Tamper one recorded hash: this manifest does not describe the published
    // bytes, so anything that trusted it would have to withhold the number.
    manifestBody.assets[0] = {
      ...manifestBody.assets[0],
      sha256: "0".repeat(64),
    };
    const manifest = {
      ...manifestBody,
      generation: createHash("sha256")
        .update(canonical(manifestBody))
        .digest("hex"),
    };

    await page.route("**/data/dashboard-release.json", (route) =>
      route.fulfill({ json: manifest }),
    );
    await page.goto("/areas/tampines");

    // Static page: the build-time verdict cannot see the intercepted manifest,
    // so the tampered hashes neither withdraw nor change the comparison.
    await expect(
      page.getByText(/Publication generation verified at build time/i),
    ).toBeVisible();
    await expect(page.getByText(/S\$82,000/).first()).toBeVisible();
    await expect(page.getByText(/S\$628,000/).first()).toBeVisible();
    await expect(
      page.getByText(/Assets do not share one publication generation/i),
    ).toHaveCount(0);
    await expect(
      page.getByText(/National comparison could not be verified/i),
    ).toHaveCount(0);
  });
});

/**
 * Area activity (RF10).
 *
 * The activity block is rendered from the verified pack at build time, so these
 * assertions bind to the published structure and to the neutrality rules — not
 * to a generation literal or to a count that a republished pack may change.
 */
test.describe("Area activity", () => {
  test.use({ viewport: { width: 1440, height: 1000 } });

  test("Punggol shows both quarters, the floor verdict and the TTM context", async ({
    page,
  }) => {
    await page.goto("/areas/punggol");

    const activity = page.locator('[data-area-activity="published"]');
    await expect(activity).toBeVisible();
    await expect(
      activity.getByRole("heading", { name: "Observed transaction activity" }),
    ).toBeVisible();
    // The quarter is named with its months, not just a period id.
    await expect(activity).toContainText("Rolling quarter");
    await expect(activity).toContainText(/\d{4}-\d{2} → \d{4}-\d{2}/);

    const hdb = page.locator('[data-activity-row="hdb"]');
    await expect(hdb).toHaveAttribute("data-activity-eligible", "true");
    // Current quarter, prior-year quarter, change, TTM and the floor verdict are
    // five separate cells; the TTM number is never folded into the quarter.
    await expect(hdb.locator("td")).toHaveCount(5);
    await expect(hdb).toContainText(/\d[\d,]*/);
    await expect(hdb).toContainText(/[+−]\d/);
    await expect(hdb).toContainText("Yes");

    // EC cannot clear a quarter-scaled floor; the row states why instead of
    // being coloured or scored.
    const ec = page.locator('[data-activity-row="ec"]');
    if ((await ec.count()) > 0) {
      await expect(ec).toHaveAttribute("data-activity-eligible", "false");
      await expect(ec).toContainText(
        /fewer than 150 observed sales|no observed sales/i,
      );
    }

    // Neutral vocabulary only: no demand/cold/hot wording, and the count is
    // never presented as a zero when nothing sold.
    await expect(activity).toContainText(/not demand, liquidity/i);
    await expect(activity).toContainText(/No directional label/i);
    await expect(activity.getByText(/\bcold\b|\bhot\b/i)).toHaveCount(0);

    // The block links to the same window in Explore.
    await expect(
      activity.getByRole("link", { name: /open this quarter in explore/i }),
    ).toHaveAttribute("href", /\/explore\?period=rolling3_\d{4}_\d{2}$/);
  });

  test("the activity table stays inside a narrow viewport", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/areas/punggol");

    const activity = page.locator('[data-area-activity="published"]');
    await expect(activity).toBeVisible();

    // The table scrolls inside its own container; the page itself must not.
    const overflow = await page.evaluate(
      () =>
        document.documentElement.scrollWidth -
        document.documentElement.clientWidth,
    );
    expect(overflow).toBeLessThanOrEqual(1);
  });
});

/**
 * RF06: the fieldnote honours `?property=` / `?period=` for the sections it
 * publishes, states its fixed build-time scope without JavaScript, and keeps a
 * concrete v2 period in the explorer return link without pretending to carry
 * that window itself.
 */
test.describe("Area fieldnote - section selection", () => {
  test.use({ viewport: { width: 1440, height: 1000 } });

  test("a deep link swaps values, label and provenance together", async ({
    page,
  }) => {
    await page.goto("/areas/tampines?property=hdb&period=whole");

    const selector = page.getByLabel("Section");
    await expect(selector).toHaveValue("whole_hdb");

    // Tampines all-history HDB: 330800 / 276 / 84847, national 311000.
    const panel = page.locator(
      'section[aria-labelledby="area-comparison-heading"]',
    );
    await expect(panel.getByText("map_metrics.whole_hdb").first()).toBeVisible();
    await expect(panel.getByText("S$330,800").first()).toBeVisible();
    await expect(panel.getByText("S$276").first()).toBeVisible();
    await expect(panel.getByText("84,847").first()).toBeVisible();
    await expect(panel.getByText("S$19,800").first()).toBeVisible();

    // Inside the panel the 2025 default is replaced, not shown alongside. (The
    // availability list still names every published combination, by design.)
    await expect(panel.getByText("S$710,000")).toHaveCount(0);
  });

  test("a concrete v2 window is reported, not substituted", async ({ page }) => {
    await page.goto("/areas/tampines?property=hdb&period=ttm_2026_10");

    const notice = page.locator('[data-area-selection-notice="true"]');
    await expect(notice).toBeVisible();
    await expect(notice).toContainText("ttm_2026_10");
    await expect(
      notice.getByRole("link", { name: "Open Explore" }),
    ).toBeVisible();

    // The fixed default stays on screen, and the URL keeps the request.
    await expect(page.getByLabel("Section")).toHaveValue("year_2025_hdb");
    await expect(page.getByText("S$710,000").first()).toBeVisible();
    expect(new URL(page.url()).searchParams.get("period")).toBe("ttm_2026_10");
  });

  test("the no-JS HTML states its fixed scope", async ({ page }) => {
    const response = await page.request.get("/areas/tampines");
    const html = await response.text();

    expect(html).toContain("Fixed build-time scope");
    expect(html).toContain("map_metrics.year_2025_hdb");
    // The section links are real links in the static HTML.
    expect(html).toMatch(/property=hdb(?:&amp;|&#38;)period=whole/);
  });

  test("a section link switches the panel", async ({ page }) => {
    await page.goto("/areas/tampines");

    await page
      .getByRole("link", { name: "All history · HDB", exact: true })
      .click();

    await expect(page).toHaveURL(/[?&]property=hdb&period=whole$/);
    await expect(page.getByLabel("Section")).toHaveValue("whole_hdb");
    await expect(page.getByText("S$330,800").first()).toBeVisible();
  });

  test("the return link keeps a concrete published period", async ({ page }) => {
    await page.goto(
      "/areas/tampines?from=explore&property=hdb&period=ttm_2026_10",
    );

    await expect(backLink(page)).toHaveAttribute(
      "href",
      /\/explore\?from=explore&property=hdb&period=ttm_2026_10$/,
    );
  });

  test("a current-only area keeps its route; the unassigned bucket does not", async ({
    page,
  }) => {
    // Mandai is published by the current pack but has no historical joint
    // section: the identity still owns its route.
    const mandai = await page.goto("/areas/mandai");
    expect(mandai?.status()).toBe(200);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("Mandai");
    await expect(page.getByText(/Not published/).first()).toBeVisible();

    const none = await page.goto("/areas/none");
    expect(none?.status()).toBe(404);
  });
});

/**
 * RF10 slice 2b: the monthly history is fetched only when asked, verified
 * against the published manifest, and a failed load keeps the retry honest.
 */
test.describe("Area monthly history", () => {
  test.use({ viewport: { width: 1440, height: 1000 } });

  async function waitForHistoryIsland(page: Page) {
    await page.waitForFunction(() => {
      const islands = document.querySelectorAll(
        'astro-island[component-url*="AreaHistoryPanel"]',
      );
      return islands.length > 0 && !islands[0]!.hasAttribute("ssr");
    });
  }

  test("loads the verified monthly payload only after the reader asks", async ({
    page,
  }) => {
    const payloadRequests: string[] = [];
    page.on("request", (request) => {
      if (request.url().includes("area-monthly-")) payloadRequests.push(request.url());
    });

    await page.goto("/areas/punggol");
    await waitForHistoryIsland(page);

    const load = page.locator("[data-history-load]");
    await expect(load).toBeVisible();
    // Nothing has been fetched for the table yet.
    expect(payloadRequests).toHaveLength(0);
    await expect(page.locator("[data-history-table]")).toHaveCount(0);

    await load.click();

    const table = page.locator("[data-history-table]");
    await expect(table).toBeVisible({ timeout: 20_000 });
    expect(payloadRequests.length).toBeGreaterThan(0);

    // Newest months first read oldest → newest, one row per grid month.
    const months = await page
      .locator("[data-history-row]")
      .evaluateAll((rows) =>
        rows.map((row) => row.getAttribute("data-history-row") ?? ""),
      );
    expect(months.length).toBeGreaterThan(6);
    expect([...months].sort()).toEqual(months);

    // A verified zero month is a sentence, never the digit 0.
    const zeroRows = page.locator('[data-history-status="no-sales"]');
    if ((await zeroRows.count()) > 0) {
      await expect(zeroRows.first()).toContainText(/no observed sales/i);
    }
    await expect(table).not.toContainText(/S\$0\b/);
  });

  test("a failed payload load reports the error and can be retried", async ({
    page,
  }) => {
    await page.goto("/areas/punggol");
    await waitForHistoryIsland(page);

    await page.route("**/area-monthly-hdb.json.gz", (route) => route.abort());
    await page.locator("[data-history-load]").click();

    await expect(page.locator("[data-history-error]")).toBeVisible({
      timeout: 20_000,
    });
    await expect(page.locator("[data-history-table]")).toHaveCount(0);

    // Unblocking the request and retrying resolves the same island.
    await page.unroute("**/area-monthly-hdb.json.gz");
    await page.locator("[data-history-retry]").click();
    await expect(page.locator("[data-history-table]")).toBeVisible({
      timeout: 20_000,
    });
    await expect(page.locator("[data-history-error]")).toHaveCount(0);
  });
});
