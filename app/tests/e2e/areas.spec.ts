import { test, expect, type Page } from "@playwright/test";

/**
 * `/areas/[slug]` area fieldnote (slice S6).
 *
 * The assertions bind to the published `map_metrics.year_2025_hdb` values for
 * Tampines, to the build-time release verdict of this tree (no
 * `dashboard-release.json`, so the national comparison must be withheld), and
 * to the explorer → fieldnote → explorer round trip.
 */

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

  test("this tree publishes no manifest, so the national comparison is withheld", async ({
    page,
  }) => {
    await page.goto("/areas/tampines");

    await expect(
      page.getByText(/National comparison could not be verified; withheld/i),
    ).toBeVisible();
    await expect(page.getByText(/status: absent/i).first()).toBeVisible();

    // An unverifiable generation is not described as a mixed one.
    await expect(
      page.getByText(/Assets do not share one publication generation/i),
    ).toHaveCount(0);

    // No national value and no difference anywhere on the page.
    await expect(page.getByText(/628,000/)).toHaveCount(0);
    await expect(page.getByText(/82,000/)).toHaveCount(0);
    await expect(page.getByText(/National HDB median/i)).toHaveCount(0);

    // Area row + header only: the national row is absent, not blanked.
    const table = page.getByRole("table");
    await expect(table.getByRole("row")).toHaveCount(2);
    await expect(
      table.getByRole("rowheader", { name: "Singapore" }),
    ).toHaveCount(0);
    await expect(table.getByRole("rowheader", { name: "Tampines" })).toHaveCount(
      1,
    );
  });

  test("the availability panel names every combination, including the missing EC one", async ({
    page,
  }) => {
    await page.goto("/areas/bedok");

    await expect(
      page.getByRole("heading", { name: /what else is published/i }),
    ).toBeVisible();

    // Bedok publishes 2025 HDB but no EC transactions in the joint section.
    await expect(
      page.getByText("2025 complete year · HDB").first(),
    ).toBeVisible();
    await expect(
      page.getByText("2025 complete year · EC").first(),
    ).toBeVisible();
    await expect(
      page.getByText(/no transactions published in this joint section/i).first(),
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
    await expect(page.getByText(/All history · HDB/i).first()).toBeVisible();
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
    await expect(rowLink).toHaveAttribute(
      "href",
      /\/areas\/ang-mo-kio\?from=explore&property=hdb&period=year_2025$/,
    );

    await rowLink.click();
    await expect(page).toHaveURL(/\/areas\/ang-mo-kio\?from=explore/);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(
      "Ang Mo Kio",
    );
    await expect(page.getByText("S$499,000").first()).toBeVisible();

    // The return link carries the explorer query (validated keys only).
    await expect(backLink(page)).toHaveAttribute(
      "href",
      /\/explore\?from=explore&property=hdb&period=year_2025$/,
    );

    await backLink(page).click();
    await expect(page).toHaveURL(/\/explore/);
    await expect(
      areaList(page).getByText("Ang Mo Kio").first(),
    ).toBeVisible();
    await expect(page.getByText("map_metrics.year_2025_hdb").first()).toBeVisible();
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
 * The verified path is unreachable in this repository (no manifest is
 * published), so it is exercised with a manifest synthesised from the real
 * asset bytes and served through route interception.
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
    // so the page must still withhold the number rather than trust the client.
    await expect(page.getByText(/could not be verified/i)).toBeVisible();
    await expect(page.getByText(/82,000/)).toHaveCount(0);
    await expect(page.getByText(/628,000/)).toHaveCount(0);
  });
});
