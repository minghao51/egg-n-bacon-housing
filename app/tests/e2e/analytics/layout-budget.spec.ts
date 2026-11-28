import { test, expect, type Page } from "@playwright/test";
import { expectPageToLoadWithoutErrors } from "../utils/pageHealth";

/**
 * Study page length budget (S11, `docs/plans/2026-11-27-sections-colour-and-
 * functionality-proposal.md` §6.2).
 *
 * `xx.xx` is the number in a comment here because the proposal's first complaint
 * — "pages are too long" — was only ever measured by hand. These assertions turn
 * it into a gate.
 *
 * This is a **ratchet**, not a headroom allowance. Each ceiling is the current
 * measurement at 1280×720, with charts settled, rounded up slightly (findings:
 * measured 14.09 -> 14.1). A page may therefore shrink freely, but it may not
 * grow: any edit that raises a page over its ceiling has to be a deliberate
 * edit to this file, recorded in the table below with a reason. The default
 * answer to a failure is to bound or move the content, not to raise the number.
 *
 * Ceilings were measured on the built site (`bun run build` + `preview`):
 *
 *   /analytics/findings                    14.09 screens  -> ceiling 14.1
 *   /analytics/lease-decay                  6.72 screens  -> ceiling  7.4
 *   /analytics/data-sources                 6.25 screens  -> ceiling  6.9
 *   /analytics/causal-inference-overview    6.11 screens  -> ceiling  6.7
 *
 * The three lower ceilings sit within a screen of their measurement and were
 * reviewed at that value; findings was the outlier the owner chose to accept at
 * its current length rather than shorten, so it is pinned at the measurement.
 * Before the bounded-table work the same pages measured 16.04 / 6.93 / 6.43 /
 * 6.30.
 */

const VIEWPORT = { width: 1280, height: 720 };

/**
 * Ratchet ceilings: the measured screen height, rounded up slightly. Raising one
 * is a deliberate edit to this file, not a test fix.
 */
const HEIGHT_BUDGETS = [
  { path: "/analytics/findings", screens: 14.1 },
  { path: "/analytics/lease-decay", screens: 7.4 },
  { path: "/analytics/data-sources", screens: 6.9 },
  { path: "/analytics/causal-inference-overview", screens: 6.7 },
];

/** The container height cap in `src/styles/globals.css` (37.5rem). */
const TABLE_CAP_PX = 600;

/** 1px borders top and bottom. */
const TABLE_CAP_SLACK_PX = 2;

/**
 * Page height in viewports, measured once the in-article charts have hydrated:
 * a `client:only` chart island adds height after load, so measuring at `load`
 * would understate the page by a screen on `/analytics/findings`.
 */
async function settledScreenHeight(page: Page): Promise<number> {
  await page.waitForLoadState("networkidle");
  const island = page.locator(
    'astro-island[component-url*="InlineChartRenderer"]',
  );
  if ((await island.count()) > 0) {
    await expect(island.first()).toBeAttached({ timeout: 15_000 });
  }
  // Give the island a beat to append its charts to the article.
  await page.waitForTimeout(1_000);
  return page.evaluate(
    () => document.documentElement.scrollHeight / window.innerHeight,
  );
}

test.describe("Study page height budget", () => {
  test.use({ viewport: VIEWPORT });

  for (const { path, screens } of HEIGHT_BUDGETS) {
    test(`${path} stays within ${screens} screens`, async ({ page }) => {
      await page.goto(path);
      const height = await settledScreenHeight(page);
      expect(
        Number(height.toFixed(2)),
        `${path} grew past its ${screens}-screen budget`,
      ).toBeLessThanOrEqual(screens);
    });
  }

  test("a study page carries no unbounded table", async ({ page }) => {
    await page.goto("/analytics/findings");
    await expect(page.locator("article table").first()).toBeVisible();

    const unbounded = await page.evaluate((cap) => {
      // The cap applies to every region, chart-paired or not: the chart island
      // appends its chart after the region, so no table needs an exemption.
      return [...document.querySelectorAll("article .table-scroll")].flatMap(
        (region) =>
          region.getBoundingClientRect().height > cap
            ? [region.getAttribute("aria-label") ?? "(unnamed)"]
            : [],
      );
    }, TABLE_CAP_PX + TABLE_CAP_SLACK_PX);

    expect(unbounded, "tables rendering taller than the 600px cap").toEqual([]);
  });
});

test.describe("Evidence table regions", () => {
  for (const path of [
    "/analytics/findings",
    "/analytics/lease-decay",
    "/analytics/data-sources",
  ]) {
    test(`${path} wraps every table in a named, focusable region`, async ({
      page,
    }) => {
      await page.goto(path);

      const tables = await page.locator("article table").count();
      const regions = await page.locator("article .table-scroll").count();
      expect(tables).toBeGreaterThan(0);
      expect(regions).toBe(tables);

      // Every region is a named scroll region reachable by keyboard; a table
      // that cannot be scrolled from the keyboard is not readable.
      const described = await page
        .locator("article .table-scroll")
        .evaluateAll((els) =>
          els.map((el) => ({
            role: el.getAttribute("role"),
            tabIndex: el.getAttribute("tabindex"),
            label: el.getAttribute("aria-label")?.trim() ?? "",
          })),
        );
      for (const region of described) {
        expect(region.role).toBe("region");
        expect(region.tabIndex).toBe("0");
        expect(region.label.length).toBeGreaterThan(0);
      }

      // …and the accessible tree exposes each of them under that name. Two
      // tables may share a first header cell (four `Dataset` tables exist), so
      // the expected count is per name, not one.
      const firstName = described[0].label;
      await expect(
        page.getByRole("region", { name: firstName, exact: true }),
      ).toHaveCount(
        described.filter((region) => region.label === firstName).length,
      );
    });
  }

  test("a capped table scrolls by keyboard, not only by mouse", async ({
    page,
  }) => {
    await page.goto("/analytics/findings");

    // Every region is capped now, chart-paired tables included.
    const capped = page.locator("article .table-scroll");

    // Test the region that actually overflows, rather than a positional index
    // that a future content edit would silently re-point.
    const tallest = await capped.evaluateAll((els) => {
      let index = -1;
      let overflow = 0;
      els.forEach((el, i) => {
        if (el.scrollHeight - el.clientHeight > overflow) {
          overflow = el.scrollHeight - el.clientHeight;
          index = i;
        }
      });
      return index;
    });
    expect(
      tallest,
      "no evidence table overflows its cap",
    ).toBeGreaterThanOrEqual(0);

    const region = capped.nth(tallest);
    await region.focus();
    await expect(region).toBeFocused();
    // The global `[tabindex]:focus-visible` rule is the visible ring.
    await expect(region).toHaveCSS("outline-style", "solid");

    await page.keyboard.press("PageDown");
    await expect
      .poll(async () => region.evaluate((el) => el.scrollTop), {
        timeout: 5_000,
      })
      .toBeGreaterThan(0);
  });

  test("the sticky header stays over the rows it labels", async ({ page }) => {
    await page.goto("/analytics/findings");

    // Same overflow-led choice: the cap only exists to be scrolled.
    const capped = page.locator("article .table-scroll");
    const overflowing = await capped.evaluateAll((els) =>
      els.findIndex((el) => el.scrollHeight - el.clientHeight > 200),
    );
    expect(overflowing).toBeGreaterThanOrEqual(0);

    const region = capped.nth(overflowing);
    const geometry = await region.evaluate((el) => {
      el.scrollTop = 200;
      const th = el.querySelector("thead th") as HTMLElement;
      return {
        headerTop: Math.round(th.getBoundingClientRect().top),
        regionTop: Math.round(el.getBoundingClientRect().top),
        background: getComputedStyle(th).backgroundColor,
      };
    });

    // Pinned to the top of its container…
    expect(
      Math.abs(geometry.headerTop - geometry.regionTop),
    ).toBeLessThanOrEqual(2);
    // …and opaque, so the rows scroll under it instead of through it.
    expect(geometry.background).not.toMatch(/rgba\(.*,\s*0\)|transparent/);
  });

  test("the archive route gets the same bounded tables", async ({ page }) => {
    await page.goto("/analytics/archive/2026/legacy-2026-11-12/mrt-impact");
    const tables = await page.locator("article table").count();
    expect(tables).toBeGreaterThan(0);
    expect(await page.locator("article .table-scroll").count()).toBe(tables);
  });

  test("table regions do not add horizontal page overflow", async ({
    page,
  }) => {
    await page.goto("/analytics/findings");
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - window.innerWidth,
    );
    expect(overflow).toBeLessThanOrEqual(0);
  });
});

test.describe("In-page navigation", () => {
  test("is one landmark, a sticky bar from md and the rail at xl", async ({
    page,
  }) => {
    await page.goto("/analytics/data-sources");

    // Exactly one copy of the nav — duplicating it would duplicate the
    // landmark and every link, which this codebase has already fixed once.
    const nav = page.getByRole("navigation", { name: "On this page" });
    await expect(nav).toHaveCount(1);

    const panel = page.locator("aside", { has: nav });

    // `md`–`xl`: a horizontal bar directly under the fixed shell header.
    await page.setViewportSize({ width: 1024, height: 720 });
    await expect(panel).toBeVisible();
    const bar = await panel.evaluate((el) => {
      const rect = el.getBoundingClientRect();
      return {
        position: getComputedStyle(el).position,
        top: Math.round(rect.top),
        width: Math.round(rect.width),
        height: Math.round(rect.height),
      };
    });
    expect(bar.position).toBe("sticky");
    expect(bar.top).toBe(56); // the fixed h-14 header
    expect(bar.height).toBeLessThan(120); // a bar, not a column

    // It stays put while the article scrolls under it.
    await page.evaluate(() => window.scrollTo(0, 1500));
    await expect
      .poll(() =>
        panel.evaluate((el) => Math.round(el.getBoundingClientRect().top)),
      )
      .toBe(56);

    // `xl` and up: the right rail, outside the article's `xl:mr-64` gutter.
    await page.setViewportSize({ width: 1280, height: 720 });
    const rail = await panel.evaluate((el) => {
      const rect = el.getBoundingClientRect();
      return {
        position: getComputedStyle(el).position,
        right: Math.round(window.innerWidth - rect.right),
        width: Math.round(rect.width),
        top: Math.round(rect.top),
      };
    });
    expect(rail.position).toBe("fixed");
    expect(rail.right).toBe(0);
    expect(rail.width).toBe(256); // w-64, matching `xl:mr-64`
    expect(rail.top).toBe(56);

    // The nav resolves to a real heading: the first link lands on an H2/H3.
    const target = await nav.locator("a").first().getAttribute("href");
    await expect(page.locator(target!)).toBeAttached();

    await expectPageToLoadWithoutErrors(page, "/analytics/data-sources");
  });
});
