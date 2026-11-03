import { test, expect, type Page } from "@playwright/test";

/**
 * `/explore` observed-comparison workspace.
 *
 * Every assertion below binds to published values (`map_metrics.year_2025_hdb`
 * through the shared dataset builder) or to the URL round trip, so reverting the
 * data binding or the hydration path fails the suite rather than silently
 * rendering an empty shell.
 */

const LIST_NAME = "Planning areas";

function areaList(page: Page) {
  return page.getByRole("list", { name: LIST_NAME });
}

test.describe("Explore workspace", () => {
  test.use({ viewport: { width: 1440, height: 1000 } });

  test("renders one page heading and a page of observed areas", async ({
    page,
  }) => {
    await page.goto("/explore");

    await expect(page.getByRole("heading", { level: 1 })).toHaveText(
      "Same year. Same housing type.",
    );

    const list = areaList(page);
    await expect(list.getByRole("listitem")).toHaveCount(12);
    await expect(list.getByText("Ang Mo Kio").first()).toBeVisible();
    await expect(list.getByText("S$499,000").first()).toBeVisible();
    await expect(list.getByText("971").first()).toBeVisible();
    await expect(page.getByText(/^Page 1 of \d+$/).first()).toBeVisible();

    // This repository publishes a verified release manifest, so the national
    // baseline is shown rather than withheld, and it carries its own section
    // identity instead of a bare number.
    await expect(
      page.getByText(/National HDB median transaction price: S\$628,000/),
    ).toBeVisible({ timeout: 20_000 });
    await expect(
      page.getByText(/dashboard_overview\.stats\.year_2025_hdb/).first(),
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
    await expect(list.getByText("S$710,000").first()).toBeVisible();
    expect(new URL(page.url()).searchParams.get("search")).toBe("tampines");
  });

  test("changing the period changes the published section shown", async ({
    page,
  }) => {
    await page.goto("/explore");
    await expect(
      page.getByText("map_metrics.year_2025_hdb").first(),
    ).toBeVisible();

    await page.getByRole("radio", { name: "All history" }).check();

    await expect(page.getByText("map_metrics.whole_hdb").first()).toBeVisible();
    await expect(page.getByText("map_metrics.year_2025_hdb")).toHaveCount(0);
    expect(new URL(page.url()).searchParams.get("period")).toBe("whole");
  });

  test("the 150-sale rule hides thin samples and can be turned off", async ({
    page,
  }) => {
    await page.goto("/explore");
    await expect(
      page.getByText(/6 thin-sample areas hidden/).first(),
    ).toBeVisible();

    await page.goto("/explore?minSales=all");

    await expect(
      page.getByRole("radio", { name: "Show thin samples" }),
    ).toBeChecked();
    await expect(page.getByText(/thin-sample areas hidden/)).toHaveCount(0);
    // The thin areas are back in the ordering: 8-sale Changi becomes the
    // cheapest 2025 HDB area.
    const list = areaList(page);
    await expect(list.getByRole("listitem").first()).toContainText("Changi");
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
    await expect(first).toContainText("Bishan");
    await expect(first).toContainText("S$849,000");
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
    await page.goto("/explore");

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
    await page.goto("/explore");

    await expect(
      page.getByText(/Assets do not share one publication generation/i),
    ).toBeVisible({ timeout: 20_000 });
    await expect(page.getByText(/628,000/)).toHaveCount(0);
  });
});
