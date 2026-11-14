import { test, expect, type Page } from "@playwright/test";

import { servePackBytesFromDisk } from "./utils/servePackBytes";

/**
 * `/explore` observed-comparison workspace.
 *
 * Every assertion below binds to published values (`map_metrics.year_2025_hdb`
 * through the shared dataset builder) or to the URL round trip, so reverting the
 * data binding or the hydration path fails the suite rather than silently
 * rendering an empty shell.
 */

const LIST_NAME = "Planning areas";

// v2 is the shipped release mode, so most /explore paths read the pack. Preview
// re-labels `.gz` with `Content-Encoding`; serve the pinned bytes raw so the
// verification path under test is the one the deployed host exercises.
test.beforeEach(async ({ page }) => {
  await servePackBytesFromDisk(page);
});

function areaList(page: Page) {
  return page.getByRole("list", { name: LIST_NAME });
}

test.describe("Explore - published windows", () => {
  test("shows the verified window panel above the selected table", async ({ page }) => {
    await page.goto("/explore");
    const panel = page.locator('[data-observed-cutoff="2026-10"]');
    await expect(panel).toBeVisible();
    await expect(panel).toContainText("12 months to 2026-10");
    await expect(panel).toContainText("25,483");
    // The shipped build opens on the published window, so the caption says the
    // table reads the same verified pack (the legacy caption is exercised by
    // the explicit-era tests below).
    await expect(panel).toContainText("same verified pack");
  });
});

test.describe("Explore workspace", () => {
  test.use({ viewport: { width: 1440, height: 1000 } });

  test("renders one page heading and a page of observed areas", async ({
    page,
  }) => {
    await page.goto("/explore");

    await expect(page.getByRole("heading", { level: 1 })).toHaveText(
      "Same year. Same housing type.",
    );

    // v2 is the shipped build: the bare URL adopts D03's window and says so.
    await expect(
      page.locator('[data-observed-default-notice="true"]'),
    ).toBeVisible();

    const list = areaList(page);
    await expect(list.getByRole("listitem")).toHaveCount(12);
    await expect(list.getByText("Ang Mo Kio").first()).toBeVisible();
    // 12 months to 2026-10, HDB: Ang Mo Kio S$513,000 on 889 sales.
    await expect(list.getByText("S$513,000").first()).toBeVisible();
    await expect(list.getByText("889").first()).toBeVisible();
    await expect(page.getByText(/^Page 1 of \d+$/).first()).toBeVisible();

    // The national baseline is the pack's own SG scope, named as such.
    await expect(
      page.getByText(/National HDB median transaction price: S\$631,000/),
    ).toBeVisible({ timeout: 20_000 });
    await expect(
      page.getByText(/observed pack · SG · 12 months to 2026-10/).first(),
    ).toBeVisible();
    await expect(
      page.getByText(/National comparison could not be verified/i),
    ).toHaveCount(0);
    await expect(
      page.getByText(/Assets do not share one publication generation/i),
    ).toHaveCount(0);
  });

  test("a deep link keeps its selection after hydration", async ({ page }) => {
    await page.goto(
      "/explore?property=hdb&period=year_2025&metric=median_price&sort=median_price&direction=asc",
    );

    await expect(page.getByRole("radio", { name: "HDB" })).toBeChecked();
    await expect(
      page.getByRole("radio", { name: "2025 complete year" }),
    ).toBeChecked();
    await expect(
      page.getByRole("radio", { name: "At least 150 sales" }),
    ).toBeChecked();
    await expect(page.getByLabel("Sort by")).toHaveValue("median_price");
    await expect(page.getByLabel("Search planning areas")).toHaveValue("");

    await expect(areaList(page).getByText("S$499,000").first()).toBeVisible();
    await expect(page.getByText(/^Page 1 of \d+$/).first()).toBeVisible();

    // Re-opening whatever the writer left in the address bar reproduces the
    // same comparison (the serializer drops parameters that equal the default).
    await page.goto(page.url());
    await expect(areaList(page).getByText("S$499,000").first()).toBeVisible();
    await expect(page.getByText(/^Page 1 of \d+$/).first()).toBeVisible();
  });

  test("a non-default deep link is applied, not overwritten by defaults", async ({
    page,
  }) => {
    await page.goto(
      "/explore?property=condo&period=whole&metric=volume&sort=volume&direction=desc&minSales=all&search=tampines",
    );

    await expect(page.getByRole("radio", { name: "Condo" })).toBeChecked();
    await expect(
      page.getByRole("radio", { name: "All history" }),
    ).toBeChecked();
    await expect(
      page.getByRole("radio", { name: "Show thin samples" }),
    ).toBeChecked();
    await expect(page.getByLabel("Sort by")).toHaveValue("volume");
    await expect(page.getByLabel("Search planning areas")).toHaveValue(
      "tampines",
    );

    const list = areaList(page);
    await expect(list.getByRole("listitem")).toHaveCount(1);
    await expect(list.getByText("Tampines").first()).toBeVisible();
    await expect(list.getByText("8,203 sales").first()).toBeVisible();
    await expect(
      page.getByText("map_metrics.whole_condo").first(),
    ).toBeVisible();

    const params = new URL(page.url()).searchParams;
    expect(params.get("property")).toBe("condo");
    expect(params.get("period")).toBe("whole");
    expect(params.get("metric")).toBe("volume");
    expect(params.get("sort")).toBe("volume");
    expect(params.get("direction")).toBe("desc");
    expect(params.get("minSales")).toBe("all");
    expect(params.get("search")).toBe("tampines");
  });

  test("search narrows the list to the matching area", async ({ page }) => {
    await page.goto("/explore");
    await expect(areaList(page).getByRole("listitem")).toHaveCount(12);

    await page.getByLabel("Search planning areas").fill("tampines");

    const list = areaList(page);
    await expect(list.getByRole("listitem")).toHaveCount(1);
    await expect(list.getByText("Tampines").first()).toBeVisible();
    await expect(list.getByText("S$720,000").first()).toBeVisible();
    expect(new URL(page.url()).searchParams.get("search")).toBe("tampines");
  });

  test("changing the period changes the published section shown", async ({
    page,
  }) => {
    await page.goto("/explore");
    // The default is a published window, not a map_metrics era.
    await expect(
      page.getByText("observed pack", { exact: false }).first(),
    ).toBeVisible();

    await page.getByRole("radio", { name: "All history" }).check();

    await expect(page.getByText("map_metrics.whole_hdb").first()).toBeVisible();
    await expect(page.getByText(/observed pack · ttm_2026_10/)).toHaveCount(0);
    expect(new URL(page.url()).searchParams.get("period")).toBe("whole");
  });

  test("the 150-sale rule hides thin samples and can be turned off", async ({
    page,
  }) => {
    await page.goto("/explore");
    // 12 months to 2026-10 HDB: 45 areas, 21 below the threshold.
    await expect(
      page.getByText(/21 thin-sample areas hidden/).first(),
    ).toBeVisible();

    await page.goto("/explore?minSales=all");

    await expect(
      page.getByRole("radio", { name: "Show thin samples" }),
    ).toBeChecked();
    await expect(page.getByText(/thin-sample areas hidden/)).toHaveCount(0);
    // Every published area is back: 45 rows, four pages of twelve.
    const list = areaList(page);
    await expect(page.getByText(/^Page 1 of 4$/).first()).toBeVisible();
    await expect(list.getByRole("listitem")).toHaveCount(12);
  });

  test("sort direction flips the first row", async ({ page }) => {
    await page.goto("/explore");

    const list = areaList(page);
    await expect(list.getByRole("listitem").first()).toContainText(
      "Ang Mo Kio",
    );

    await page.getByRole("button", { name: /sort direction/i }).click();

    const first = list.getByRole("listitem").first();
    await expect(first).toContainText("Queenstown");
    await expect(first).toContainText("S$863,944");
    expect(new URL(page.url()).searchParams.get("direction")).toBe("desc");
  });
});

/**
 * The baseline gate is runtime-verified against `dashboard-release.json`. These
 * tests synthesise manifests from the real asset bytes and serve them through
 * route interception, so both directions stay covered: matching hashes reveal
 * the national number, a tampered hash withholds it with the incompatibility
 * wording.
 */
test.describe("Explore baseline gate", () => {
  test.use({ viewport: { width: 1440, height: 1000 } });

  const ASSETS = [
    "dashboard_overview.json.gz",
    "dashboard_trends.json.gz",
    "dashboard_segments.json.gz",
    "dashboard_leaderboard.json.gz",
    "map_metrics.json.gz",
    "hotspots.json.gz",
    "amenity_summary.json.gz",
  ] as const;

  function canonical(value: unknown): string {
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
  }

  async function buildManifest(tamper: boolean) {
    const { createHash } = await import("node:crypto");
    const { readFileSync } = await import("node:fs");
    const { gunzipSync } = await import("node:zlib");
    const { join } = await import("node:path");
    const dataDir = join(process.cwd(), "public", "data");
    const assets = ASSETS.map((path) => {
      const bytes = readFileSync(join(dataDir, path));
      const sha256 = createHash("sha256").update(bytes).digest("hex");
      const text = gunzipSync(bytes).toString("utf8");
      const contentSha256 = createHash("sha256")
        .update(new TextEncoder().encode(text))
        .digest("hex");
      return {
        path,
        sha256:
          tamper && path === "map_metrics.json.gz" ? "0".repeat(64) : sha256,
        contentSha256:
          tamper && path === "map_metrics.json.gz"
            ? "0".repeat(64)
            : contentSha256,
        bytes: bytes.length,
        shape: text.trimStart()[0] === "[" ? "array" : "object",
        metricScopes: ["median_price"],
      };
    });
    const body = {
      schemaVersion: "1.0.0",
      generatedAt: "2026-11-02T00:00:00Z",
      observationRange: {
        startMonth: "1990-01",
        endMonth: "2026-09",
        completeYear: 2025,
      },
      periodDefinitions: {},
      inclusionRules: {},
      provenance: { sources: [] },
      assets,
    };
    // The generation hashes the manifest content without `generation` or
    // `generatedAt`, mirroring the Python exporter.
    const { generatedAt: _ignored, ...content } = body;
    const generation = createHash("sha256")
      .update(canonical(content))
      .digest("hex");
    return { ...body, generation };
  }

  test("matching hashes reveal the national baseline", async ({ page }) => {
    const manifest = await buildManifest(false);
    await page.route("**/data/dashboard-release.json", (route) =>
      route.fulfill({ json: manifest }),
    );
    // The generation gate is a legacy-asset check; the pack carries its own
    // verification. Pin the era that uses the two assets named below.
    await page.goto("/explore?period=year_2025");

    await expect(
      page.getByText(/National HDB median transaction price:\s*S\$628,000/),
    ).toBeVisible({ timeout: 20_000 });
    await expect(
      page.getByText(/dashboard_overview\.stats\.year_2025_hdb/).first(),
    ).toBeVisible();
    await expect(
      page.getByText(/National comparison could not be verified/i),
    ).toHaveCount(0);
  });

  test("a tampered manifest withholds the national baseline", async ({
    page,
  }) => {
    const manifest = await buildManifest(true);
    await page.route("**/data/dashboard-release.json", (route) =>
      route.fulfill({ json: manifest }),
    );
    await page.goto("/explore?period=year_2025");

    await expect(
      page.getByText(/Assets do not share one publication generation/i),
    ).toBeVisible({ timeout: 20_000 });
    await expect(page.getByText(/628,000/)).toHaveCount(0);
  });
});

/**
 * Published-period rows: the same workspace, reading the verified v2 pack
 * instead of `map_metrics`. The figures below come from the pack published with
 * this tree (`ttm_2026_10`, HDB: 24 areas at or above the 150-sale threshold,
 * national median S$631,000, 25,483 sales).
 */
test.describe("Explore - published period rows", () => {
  test.use({ viewport: { width: 1440, height: 1000 } });

  test("a concrete period id reads the verified pack", async ({ page }) => {
    await page.goto("/explore?period=ttm_2026_10");

    await expect(
      page.getByRole("radio", { name: "12 months to 2026-10" }),
    ).toBeChecked();

    const list = areaList(page);
    await expect(list.getByRole("listitem")).toHaveCount(12);
    // Cheapest 2025-11..2026-10 HDB area at or above 150 sales.
    await expect(list.getByText("S$513,000").first()).toBeVisible();

    await expect(
      page.getByText(/National HDB median transaction price: S\$631,000/),
    ).toBeVisible({ timeout: 20_000 });
    await expect(
      page.getByText(/observed pack · SG · 12 months to 2026-10/).first(),
    ).toBeVisible();
    await expect(
      page.getByText(
        /The manifest, payload sizes and sha256 digests were checked/,
      ),
    ).toBeVisible();
    await expect(page.getByText(/map_metrics\./)).toHaveCount(0);

    expect(new URL(page.url()).searchParams.get("period")).toBe("ttm_2026_10");
  });

  test("an unpublished concrete id is reported, not replaced", async ({
    page,
  }) => {
    await page.goto("/explore?period=ttm_2026_07");

    await expect(
      page.getByText("ttm_2026_07 is not available in this build"),
    ).toBeVisible({ timeout: 20_000 });
    await expect(
      page.getByText(/does not publish a period with the id ttm_2026_07/),
    ).toBeVisible();

    // No other window's numbers are rendered in its place.
    await expect(page.getByRole("group", { name: "Area results" })).toHaveCount(
      0,
    );
    await expect(page.getByText(/National HDB median/)).toHaveCount(0);
    expect(new URL(page.url()).searchParams.get("period")).toBe("ttm_2026_07");

    // The historical eras stay selectable, and choosing one resolves again.
    // The era stays in the URL because the route's active default is the
    // concrete published window, not the legacy era.
    await page.getByRole("radio", { name: "2025 complete year" }).check();
    await expect(
      page.getByText(/map_metrics\.year_2025_hdb/).first(),
    ).toBeVisible();
    expect(new URL(page.url()).searchParams.get("period")).toBe("year_2025");
  });

  test("a limited-display scope shows its values but cannot be ranked", async ({
    page,
  }) => {
    await page.goto("/explore?period=ttm_2026_10&property=ec");

    await expect(
      page.getByText(/Coverage is limited for this scope/),
    ).toBeVisible({ timeout: 20_000 });
    await expect(
      page.getByText(/Areas are listed by name, not ranked, for this scope\./),
    ).toBeVisible();
    await expect(
      page.getByText(/National EC median transaction price/),
    ).toBeVisible();

    // No ranking control, and the row order is the name order.
    await expect(page.getByLabel("Sort by")).toHaveCount(0);
    await expect(page.getByLabel("Show metric")).toBeVisible();
    await expect(page.getByText(/listed by name · page 1 of/)).toBeVisible();
  });
});

/**
 * RF10: a rolling-quarter window carries its prior-year comparison in the list,
 * with the same D05 verdict the fieldnote shows. The numbers are asserted as
 * *shapes* (a count, a signed percentage, a stated reason) because the pack is
 * republished per release and its values are pinned by the unit tests instead.
 */
test.describe("Explore activity", () => {
  test.use({ viewport: { width: 1440, height: 1000 } });

  test("a rolling quarter row shows the prior-year comparison", async ({
    page,
  }) => {
    await page.goto("/explore?period=rolling3_2026_10&minSales=0");

    await expect(
      page.getByRole("radio", { name: /3 months to 2026-10/ }).first(),
    ).toBeChecked({ timeout: 20_000 });

    const list = areaList(page);
    await expect(list.getByRole("listitem").first()).toBeVisible();

    // The activity line is a sentence, not a colour or a badge.
    const activity = page.locator("[data-explorer-activity]").first();
    await expect(activity).toBeVisible();
    await expect(activity).toContainText(/Prior-year same window: \d/);
    await expect(activity).toContainText(/[+−]\d+\.\d%\)/);

    // A thin area states why it cannot be compared/ranked instead of a zero.
    // A row under the floor says so in words. It may still carry a computable
    // percentage (a small prior-year base is a real comparison), so the floor
    // verdict — not the absence of a number — is what the sentence must state.
    const ineligible = page
      .locator('[data-explorer-activity="ineligible"]')
      .first();
    if ((await ineligible.count()) > 0) {
      await expect(ineligible).toContainText(
        /below the 150-sale floor|Prior-year comparison: (no prior-year|no observed)/,
      );
    }
  });

  test("a limited-display scope keeps activity numbers but stays unranked", async ({
    page,
  }) => {
    await page.goto("/explore?period=rolling3_2026_10&property=ec&minSales=0");

    await expect(
      page.getByText(/Areas are listed by name, not ranked, for this scope\./),
    ).toBeVisible({ timeout: 20_000 });
    await expect(page.getByLabel("Sort by")).toHaveCount(0);
    // The activity line may still carry a percentage; it must never become a
    // ranking or a colour-coded verdict.
    // Thin rows are visible with the threshold off, so the activity line is
    // present and marked ineligible rather than dropped or ranked.
    const activity = page.locator("[data-explorer-activity]").first();
    await expect(activity).toBeVisible();
    await expect(activity).toHaveAttribute("data-explorer-activity", "ineligible");
  });
});
