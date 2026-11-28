/**
 * Navigation current-state contract.
 *
 * The shell gives every page exactly one `aria-current="page"`, and marks the
 * destination that *contains* the page with `aria-current="location"`. Both
 * halves have already regressed once each while the page still looked fine:
 *
 * - a destination and a section link both claimed `page` (two current links);
 * - `Data & methods` moved to `/data` and `/catalog/*` silently stopped
 *   marking any destination, so a reader there had fallen out of the model.
 *
 * Both are invisible to a screenshot and only show up as an attribute, so they
 * are pinned here per route rather than left to the unit matcher — which was
 * correct in isolation both times.
 */
import { test, expect, type Page } from "@playwright/test";

/**
 * `PAGES_BASE_PATH` is set when this runs against the Pages-prefixed build, and
 * Playwright's `baseURL` swallows a base path, so every navigation here is an
 * absolute path built from it — the same convention as `pages-base.spec.ts`.
 */
const BASE_PREFIX = process.env.PAGES_BASE_PATH ?? "";

/** Destination labels in the header, in `DESTINATIONS` order. */
const DESTINATIONS = ["Overview", "Explore", "Research", "Data & methods"];

interface RouteExpectation {
  path: string;
  /** The single `aria-current="page"` link's visible text, or null. */
  page: string | null;
  /** The destination that contains this page, when one does. */
  location: string | null;
}

const ROUTES: RouteExpectation[] = [
  { path: "/", page: "Overview", location: null },
  { path: "/explore", page: "Explore", location: null },
  { path: "/analytics/", page: "Studies", location: "Research" },
  { path: "/research/trends", page: "Trends", location: "Research" },
  { path: "/research/map", page: "Research map", location: "Research" },
  { path: "/data", page: "Data & methods", location: null },
  // The catalog lives under the guide, so it must keep pointing at it.
  // `/catalog/`'s own index link is labelled "Overview" in the section menu;
  // the header's Overview destination is not marked here, so there is still
  // exactly one page marker.
  { path: "/catalog/", page: "Overview", location: "Data & methods" },
  { path: "/catalog/bronze", page: "Bronze", location: "Data & methods" },
];

/** Visible `aria-current` markers, as `{ value, text }`, deduplicated by text. */
async function visibleCurrent(page: Page) {
  return page.evaluate(() => {
    const seen: { value: string; text: string }[] = [];
    const counted = new Set<string>();
    for (const el of document.querySelectorAll("[aria-current]")) {
      const visible = (el as HTMLElement).offsetParent !== null;
      if (!visible) continue;
      const value = el.getAttribute("aria-current") ?? "";
      const text = (el.textContent ?? "").trim().split("\n")[0].trim();
      // The header renders a bar instance and a drawer instance; only one is
      // displayed at a given width, so identical markers are one marker.
      const key = `${value}:${text}`;
      if (counted.has(key)) continue;
      counted.add(key);
      seen.push({ value, text });
    }
    return seen;
  });
}

test.describe("Navigation current state", () => {
  for (const route of ROUTES) {
    test(`${route.path} marks one page and the right destination`, async ({
      page,
    }) => {
      await page.goto(`${BASE_PREFIX}${route.path}`);

      const markers = await visibleCurrent(page);
      const pages = markers.filter((marker) => marker.value === "page");
      const locations = markers.filter((marker) => marker.value === "location");

      // Exactly one page marker, whatever else the route renders.
      expect(
        pages,
        `expected one aria-current="page" on ${route.path}`,
      ).toHaveLength(1);

      if (route.page === null) {
        expect(pages[0].text).toBe("");
      } else {
        expect(pages[0].text).toContain(route.page);
      }

      if (route.location === null) {
        expect(
          locations,
          `did not expect a location marker on ${route.path}`,
        ).toHaveLength(0);
      } else {
        expect(locations).toHaveLength(1);
        expect(locations[0].text).toBe(route.location);
      }
    });
  }

  test("every route in the model resolves a destination in the header", async ({
    page,
  }) => {
    // A page whose header marks nothing has fallen out of the navigation model.
    for (const route of ROUTES.filter((entry) => entry.location !== null)) {
      await page.goto(`${BASE_PREFIX}${route.path}`);
      const header = page.getByRole("navigation", { name: "Primary" }).first();
      const marked = header.locator(
        '[aria-current="page"], [aria-current="location"]',
      );
      await expect(
        marked,
        `no destination marked on ${route.path}`,
      ).toHaveCount(1);
    }
  });

  test("the header lists the four destinations, in order", async ({ page }) => {
    await page.goto(`${BASE_PREFIX}/`);
    const header = page.getByRole("navigation", { name: "Primary" }).first();
    await expect(header.getByRole("link")).toHaveText(DESTINATIONS);
  });
});
