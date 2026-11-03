import { readFileSync } from "node:fs";
import { gunzipSync } from "node:zlib";
import { expect, test, type Page } from "@playwright/test";
import { expectPageToLoadWithoutErrors } from "./utils/pageHealth";

/**
 * Dashboard overview headline honesty (slice S4b).
 *
 * Every number asserted here is derived from the published
 * `public/data/dashboard_overview.json.gz` at test time, so a reverted data
 * binding (hardcoded copy, a stale block, or a figure read from the wrong
 * property type) fails instead of passing quietly. The asset's values for the
 * 2025 complete year are also pinned, so a silent asset swap is visible.
 */

const ASSET_PATH = new URL(
  "../../public/data/dashboard_overview.json.gz",
  import.meta.url,
);

interface StatBlock {
  median_price: number;
  volume: number;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

const OVERVIEW: unknown = JSON.parse(
  gunzipSync(readFileSync(ASSET_PATH)).toString("utf-8"),
);

const STATS: Record<string, unknown> =
  isRecord(OVERVIEW) && isRecord(OVERVIEW["stats"]) ? OVERVIEW["stats"] : {};

const METADATA: Record<string, unknown> =
  isRecord(OVERVIEW) && isRecord(OVERVIEW["metadata"])
    ? OVERVIEW["metadata"]
    : {};

function statBlock(section: string): StatBlock | null {
  const block = STATS[section];
  if (!isRecord(block)) return null;
  const { median_price: medianPrice, volume, count } = block;
  const sales =
    typeof volume === "number"
      ? volume
      : typeof count === "number"
        ? count
        : NaN;
  if (typeof medianPrice !== "number" || !Number.isFinite(sales)) return null;
  return { median_price: medianPrice, volume: sales };
}

function requiredStatBlock(section: string): StatBlock {
  const block = statBlock(section);
  if (block === null) {
    throw new Error(
      `The published overview asset has no usable ${section} stats block.`,
    );
  }
  return block;
}

function formatSgd(value: number): string {
  return `S$${Math.round(value).toLocaleString("en-US")}`;
}

function formatSales(value: number): string {
  return `${Math.round(value).toLocaleString("en-US")} transactions`;
}

/** `2026-10-24T21:26:26.831603` -> `24 Oct 2026`, matching the page's own parse. */
function formatPublishedDate(iso: unknown): string | null {
  if (typeof iso !== "string") return null;
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso);
  if (match === null) return null;
  const months = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
  ];
  const month = months[Number(match[2]) - 1];
  return month === undefined
    ? null
    : `${Number(match[3])} ${month} ${match[1]}`;
}

/**
 * Property types the overview must label individually. `2025` is the fixed,
 * verified complete year used by the published snapshot.
 */
const SCOPED_TYPES = [
  { section: "year_2025_hdb", label: "HDB", median: 628_000, sales: 25_084 },
  { section: "year_2025_ec", label: "EC", median: 1_578_000, sales: 6_209 },
  {
    section: "year_2025_condo",
    label: "Condominium",
    median: 1_938_976,
    sales: 47_506,
  },
] as const;

function medianCards(page: Page) {
  return page.getByRole("list", { name: "2025 medians by property type" });
}

test.describe("Dashboard overview - published 2025 medians", () => {
  test("each property type card shows its own 2025 median and sales count", async ({
    page,
  }) => {
    await page.goto("/dashboard");

    const cards = medianCards(page);
    await expect(cards.getByRole("listitem")).toHaveCount(3);

    for (const entry of SCOPED_TYPES) {
      const block = requiredStatBlock(entry.section);

      // The pinned snapshot values must still be what the asset publishes; the
      // page must then render exactly those, not a constant of its own.
      expect(
        block,
        `${entry.section} should hold the documented 2025 values`,
      ).toEqual({ median_price: entry.median, volume: entry.sales });

      const card = cards
        .getByRole("listitem")
        .filter({ has: page.getByRole("heading", { name: entry.label }) });

      await expect(
        card.getByRole("heading", { name: entry.label, exact: true }),
      ).toBeVisible();
      await expect(
        card.getByText(formatSgd(block.median_price), { exact: true }),
      ).toBeVisible();
      await expect(
        card.getByText(formatSales(block.volume), { exact: true }),
      ).toBeVisible();
      await expect(
        card.getByText(`dashboard_overview.stats.${entry.section}`, {
          exact: true,
        }),
      ).toBeVisible();
      await expect(card).toContainText("2025 complete year");
    }

    // The 2025 medians are a description of observed sales, not an index.
    await expect(
      page.getByText(/2025 medians of observed sales/i),
    ).toBeVisible();
    await expect(
      page.getByText(/not an index and not\s+a forecast/i),
    ).toBeVisible();
  });

  test("the snapshot scope note names the period, type, count and asset section", async ({
    page,
  }) => {
    await page.goto("/dashboard");

    const scope = page.locator("[data-overview-scope]");
    await expect(scope).toBeVisible();

    // Default state is unfiltered, and the note must say so rather than let a
    // reader assume the figures are type-specific.
    await expect(scope).toContainText("All history");
    await expect(scope).toContainText("All property types");
    await expect(scope).toContainText(
      formatSales(requiredStatBlock("whole").volume),
    );
    await expect(scope).toContainText("dashboard_overview.stats.whole");

    await page.getByRole("button", { name: "2025", exact: true }).click();
    await expect(scope).toContainText("2025 complete year");
    await expect(scope).toContainText(
      formatSales(requiredStatBlock("year_2025").volume),
    );
    await expect(scope).toContainText("dashboard_overview.stats.year_2025");

    await page.getByRole("button", { name: "HDB", exact: true }).click();
    await expect(scope).toContainText("HDB");
    await expect(scope).toContainText(
      formatSales(requiredStatBlock("year_2025_hdb").volume),
    );
    await expect(scope).toContainText("dashboard_overview.stats.year_2025_hdb");

    // The KPI cards follow the same scope, so an unfiltered median cannot sit
    // beside a type-specific label.
    await expect(
      page
        .getByText(formatSgd(requiredStatBlock("year_2025_hdb").median_price), {
          exact: true,
        })
        .first(),
    ).toBeVisible();
  });

  test("the page describes the published snapshot, not a refresh cadence", async ({
    page,
  }) => {
    test.skip(
      /daily/i.test(JSON.stringify(METADATA)),
      "The asset metadata now publishes a daily cadence, so the copy may state one.",
    );

    await page.goto("/dashboard");

    await expect(
      page.getByText(/refreshed\s+daily|updated\s+daily|daily\s+refresh/i),
    ).toHaveCount(0);

    const dataNote = page.getByText(/Export time is not source freshness/i);
    await expect(dataNote.first()).toBeVisible();

    const exportDate = formatPublishedDate(METADATA["generated_at"]);
    if (exportDate !== null) {
      await expect(
        page.getByText(new RegExp(`exported ${exportDate}`)).first(),
      ).toBeVisible();
    }
  });

  test("the capability strip links to the published destinations only", async ({
    page,
  }) => {
    await page.goto("/dashboard");

    const strip = page.getByRole("navigation", { name: "Keep exploring" });
    await expect(strip).toBeVisible();

    const destinations = [
      { href: "/explore", label: "Observed explorer" },
      { href: "/research/trends", label: "Monthly trends" },
      { href: "/areas/tampines", label: "Tampines fieldnote" },
      { href: "/dashboard/leaderboard", label: "Compare Areas" },
      { href: "/dashboard/trends", label: "Decision Tools" },
    ];

    for (const destination of destinations) {
      const link = strip.getByRole("link", { name: destination.label });
      await expect(link).toBeVisible();
      await expect(link).toHaveAttribute("href", destination.href);
    }

    // `/research/segments` is not published in this repository yet, so it must
    // not be linked from here.
    await expect(strip.locator('a[href*="/research/segments"]')).toHaveCount(0);
  });

  test("the old unscoped highlights and their claims are gone", async ({
    page,
  }) => {
    await page.goto("/dashboard");

    await expect(page.getByText(/What Changed Recently/i)).toHaveCount(0);
    await expect(page.getByText(/from \$1,230,000/i)).toHaveCount(0);
    await expect(page.getByText(/from 5,577/i)).toHaveCount(0);
    await expect(
      page.getByText(/monthly averages, latest month vs a year ago/i),
    ).toHaveCount(0);
    await expect(
      page.getByText(/monthly totals, latest month vs a year ago/i),
    ).toHaveCount(0);
    await expect(page.getByText(/records in the current dataset/i)).toHaveCount(
      0,
    );
    await expect(page.getByText(/^(YoY|MoM)$/)).toHaveCount(0);
    await expect(page.getByText(/Largest Market Share/i)).toHaveCount(0);
  });

  test("the page keeps exactly one level-1 heading", async ({ page }) => {
    await page.goto("/dashboard");

    const headings = page.getByRole("heading", { level: 1 });
    await expect(headings).toHaveCount(1);
    await expect(headings).toHaveText("Overview");
  });

  test("the overview loads without console or page errors", async ({
    page,
  }) => {
    await expectPageToLoadWithoutErrors(page, "/dashboard");
  });
});
