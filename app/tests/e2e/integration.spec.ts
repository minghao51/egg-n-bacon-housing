import { test, expect, type Page } from "@playwright/test";

/**
 * S10 integration regressions.
 *
 * These cover the release gates the per-slice specs did not: the mobile drawer's
 * focus contract, real modal dialogs (leaderboard metric guide, segment guide,
 * mobile filters), no-results states, a refresh failure while published data is
 * already on screen, revalidation of server-rendered data, private financing
 * inputs, the Spatial patterns tab and the legacy routes.
 */

async function activeElementId(page: Page): Promise<string> {
  return page.evaluate(() => document.activeElement?.id ?? "");
}

async function waitForHydration(page: Page, component: string): Promise<void> {
  const island = page.locator(`astro-island[component-url*="${component}"]`);
  await expect(island).toHaveCount(1);
  // Astro removes the `ssr` attribute only after the island's component has
  // mounted, so this is the deterministic point at which handlers work.
  await expect
    .poll(() => island.evaluate((element) => !element.hasAttribute("ssr")), {
      timeout: 20_000,
    })
    .toBe(true);
}

async function focusIsInside(page: Page, selector: string): Promise<boolean> {
  return page.evaluate((css) => {
    const container = document.querySelector(css);
    return container !== null && container.contains(document.activeElement);
  }, selector);
}

test.describe("Mobile navigation drawer", () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test("opens by keyboard, traps focus and restores it on Escape", async ({
    page,
  }) => {
    await page.goto("/dashboard");
    const toggle = page.getByRole("button", {
      name: /Open navigation menu/i,
    });
    await expect(toggle).toBeVisible();
    await expect(toggle).toHaveAttribute("aria-expanded", "false");

    await toggle.focus();
    await page.keyboard.press("Enter");
    await expect(toggle).toHaveAttribute("aria-expanded", "true");
    // Focus starts inside the drawer, and the covered page leaves the
    // accessibility tree and tab order.
    expect(await activeElementId(page)).toBe("mobile-menu-close");
    await expect(page.locator("#main-content")).toHaveAttribute("inert", "");

    for (let index = 0; index < 5; index += 1) {
      await page.keyboard.press("Tab");
      expect(await focusIsInside(page, "#sidebar-drawer")).toBe(true);
    }

    await page.keyboard.press("Escape");
    await expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(await activeElementId(page)).toBe("mobile-menu-toggle");
    await expect(page.locator("#main-content")).not.toHaveAttribute(
      "inert",
      "",
    );
  });

  test("closes on navigation and follows the base link", async ({ page }) => {
    await page.goto("/dashboard");
    await page.getByRole("button", { name: /Open navigation menu/i }).click();
    await page
      .getByRole("navigation", { name: "Main navigation" })
      .getByRole("link", { name: /Research map/ })
      .click();
    await expect(page).toHaveURL(/\/research\/map/);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(
      /A layer is a claim/,
    );
  });
});

test.describe("Modal dialogs", () => {
  test.use({ viewport: { width: 1440, height: 1000 } });

  test("the leaderboard metric guide traps Tab, closes on Escape and restores focus", async ({
    page,
  }) => {
    await page.goto("/dashboard/leaderboard");
    const trigger = page.getByRole("button", {
      name: "View metric definitions",
    });
    await expect(trigger).toBeVisible({ timeout: 30_000 });
    await trigger.focus();
    await trigger.click();

    const dialog = page.getByRole("dialog", { name: /Metric Definitions/ });
    await expect(dialog).toBeVisible();
    expect(
      await focusIsInside(
        page,
        '[role="dialog"][aria-labelledby="metric-help-title"]',
      ),
    ).toBe(true);

    for (let index = 0; index < 6; index += 1) {
      await page.keyboard.press("Tab");
      expect(
        await focusIsInside(
          page,
          '[role="dialog"][aria-labelledby="metric-help-title"]',
        ),
      ).toBe(true);
    }

    await page.keyboard.press("Escape");
    await expect(dialog).toHaveCount(0);
    await expect(trigger).toBeFocused();
  });

  test("the segment evidence guide behaves as a dialog", async ({ page }) => {
    await page.goto("/research/segments");
    const trigger = page.getByRole("button", { name: "Metrics guide" });
    await expect(trigger).toBeVisible({ timeout: 30_000 });
    await trigger.focus();
    await trigger.click();

    const dialog = page.getByRole("dialog", { name: /Segment evidence guide/ });
    await expect(dialog).toBeVisible();
    expect(await focusIsInside(page, '[role="dialog"]')).toBe(true);

    await page.keyboard.press("Escape");
    await expect(dialog).toHaveCount(0);
    await expect(trigger).toBeFocused();
  });

  test("the mobile filters sheet is a dialog and closes on Escape", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/dashboard/leaderboard");
    const trigger = page.getByRole("button", { name: /^Filters \(/ });
    await expect(trigger).toBeVisible({ timeout: 30_000 });
    await waitForHydration(page, "LeaderboardDashboard");
    await trigger.focus();
    const dialog = page.getByRole("dialog", { name: "Leaderboard Filters" });
    await trigger.click();
    await expect(dialog).toBeVisible();
    expect(await focusIsInside(page, '[role="dialog"]')).toBe(true);

    await page.keyboard.press("Escape");
    await expect(dialog).toHaveCount(0);
    await expect(trigger).toBeFocused();
  });
});

test.describe("No-results states", () => {
  test("the observed explorer keeps its list after a no-match search", async ({
    page,
  }) => {
    await page.goto("/explore");
    const search = page.getByLabel("Search planning areas");
    await expect(search).toBeVisible({ timeout: 30_000 });
    await search.fill("zzzz-no-such-area");
    await expect(
      page.getByText("No planning areas match these settings"),
    ).toBeVisible();

    await search.fill("");
    await expect(page.getByLabel("Area results")).toBeVisible();
    await expect(
      page.getByLabel("Planning areas").getByRole("listitem"),
    ).toHaveCount(12);
  });

  test("the studies library reports no match and resets", async ({ page }) => {
    await page.goto("/analytics/");
    const search = page.getByLabel("Free text");
    await expect(search).toBeVisible();
    await waitForHydration(page, "StudiesLibrary");
    await search.fill("zzzz-no-such-study");
    await expect(page.getByText("No study matches.")).toBeVisible();
    await expect(
      page.getByText("0 of 15 studies match these filters."),
    ).toBeVisible();

    await page.getByRole("button", { name: "Reset filters" }).click();
    await expect(page.getByText("15 of 15 studies.")).toBeVisible();
    await expect(search).toHaveValue("");
  });

  test("the catalog schema table reports no matching field", async ({
    page,
  }) => {
    await page.goto("/catalog/platinum/unified_dataset");
    const search = page.getByLabel("Search schema fields");
    // The schema table hydrates only when it scrolls into view; wait for that
    // before typing, or the controlled input resets the query.
    await search.scrollIntoViewIfNeeded();
    await waitForHydration(page, "SchemaTable");
    await search.fill("zzzz_no_such_field");
    await expect(page.getByText("0 fields")).toBeVisible();
    await expect(page.getByText(/No schema fields match/)).toBeVisible();

    await search.fill("");
    await expect(page.getByText("0 fields")).toHaveCount(0);
    await expect(page.getByText("psf", { exact: true })).toBeVisible();
  });
});

test.describe("Resilience with data already on screen", () => {
  test("a failed refresh keeps the published leaderboard and offers a retry", async ({
    page,
  }) => {
    await page.route("**/data/dashboard_leaderboard.json.gz", (route) =>
      route.abort(),
    );
    await page.goto("/dashboard/leaderboard");

    // The server-rendered ranking is visible before the revalidation fails.
    await expect(page.getByText(/Showing \d+ areas ranked by/)).toBeVisible({
      timeout: 30_000,
    });
    const alert = page.getByRole("alert").filter({ hasText: "Refresh failed" });
    await expect(alert).toBeVisible({ timeout: 30_000 });
    await expect(
      page.getByText(/showing the last published leaderboard/i),
    ).toBeVisible();

    await page.unroute("**/data/dashboard_leaderboard.json.gz");
    await alert.getByRole("button", { name: "Try again" }).click();
    await expect(alert).toHaveCount(0);
    await expect(page.getByText(/Showing \d+ areas ranked by/)).toBeVisible();
  });

  test("revalidates the server-rendered leaderboard instead of trusting it", async ({
    page,
  }) => {
    let requests = 0;
    page.on("request", (request) => {
      if (request.url().includes("dashboard_leaderboard.json.gz")) {
        requests += 1;
      }
    });

    await page.goto("/dashboard/leaderboard");
    await expect(page.getByText(/Showing \d+ areas ranked by/)).toBeVisible({
      timeout: 30_000,
    });
    await expect.poll(() => requests, { timeout: 15_000 }).toBeGreaterThan(0);
  });
});

test.describe("Private inputs and model gates", () => {
  test("financing inputs never reach the URL, storage or requests", async ({
    page,
  }) => {
    const requests: Array<{ url: string; body: string | null }> = [];
    const consoleMessages: string[] = [];
    page.on("request", (request) =>
      requests.push({ url: request.url(), body: request.postData() }),
    );
    page.on("console", (message) => consoleMessages.push(message.text()));

    await page.goto("/research/tools");
    const income = page.locator("#financing-income");
    await expect(income).toHaveValue("120000", { timeout: 30_000 });
    await income.fill("137777");
    await expect(income).toHaveValue("137777");

    // S8-F1 persists the draft in the island, not in the address bar: the
    // price must stay private across a tool switch too.
    const price = page.locator("#financing-price");
    await price.fill("765432");
    await expect(price).toHaveValue("765432");
    await page.getByRole("tab", { name: /Lease bands/ }).click();
    await page.getByRole("tab", { name: /Financing scenario/ }).click();
    // The values survived the switch …
    await expect(income).toHaveValue("137777");
    await expect(price).toHaveValue("765432");

    // … and were still never serialised anywhere.
    const privateValues = ["137777", "765432"];
    for (const value of privateValues) {
      expect(page.url()).not.toContain(value);
      expect(requests.some(({ url }) => url.includes(value))).toBe(false);
      expect(requests.some(({ body }) => body?.includes(value))).toBe(false);
      expect(consoleMessages.join("\n")).not.toContain(value);
    }
    for (const key of new URL(page.url()).searchParams.keys()) {
      expect(["tool", "ref", "rt", "rv"]).toContain(key);
    }
    const storage = await page.evaluate(() =>
      JSON.stringify({ ...localStorage, ...sessionStorage }),
    );
    for (const value of privateValues) {
      expect(storage).not.toContain(value);
    }
  });

  test("reaches the Spatial patterns tab by keyboard and keeps inspection-only output", async ({
    page,
  }) => {
    await page.goto("/research/tools");
    const financing = page.getByRole("tab", { name: /Financing scenario/ });
    await expect(financing).toBeVisible({ timeout: 30_000 });
    await financing.focus();
    await page.keyboard.press("End");

    const spatial = page.getByRole("tab", { name: /Spatial patterns/ });
    await expect(spatial).toBeFocused();
    await expect(spatial).toHaveAttribute("aria-selected", "true");
    await expect(
      page.getByText("4 cluster types across 40 published town records."),
    ).toBeVisible();
    await expect(
      page.getByText(/Portfolio allocation, BUY\/SELL prompts/),
    ).toBeVisible();
    await expect(page.getByRole("table").getByRole("row")).toHaveCount(41);
  });
});

test.describe("Legacy routes", () => {
  test.use({ viewport: { width: 1440, height: 1000 } });

  test("every legacy URL renders its research equivalent", async ({ page }) => {
    const routes: Array<[string, RegExp]> = [
      ["/dashboard/segments", /Find an archetype/],
      ["/dashboard/trends", /Make the assumptions editable/],
      ["/dashboard/map", /A layer is a claim/],
      ["/dashboard/leaderboard", /Compare Areas/],
    ];
    for (const [pathname, heading] of routes) {
      const response = await page.goto(pathname);
      expect(response?.status(), pathname).toBe(200);
      await expect(
        page.getByRole("heading", { level: 1 }).first(),
        pathname,
      ).toHaveText(heading, { timeout: 30_000 });
    }
  });
});
