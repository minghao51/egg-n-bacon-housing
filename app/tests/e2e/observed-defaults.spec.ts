import { test, expect } from "@playwright/test";

import { servePackBytesFromDisk } from "./utils/servePackBytes";

/**
 * Observed default migration (plan §5.3 / §5.5 step 4).
 *
 * `PUBLIC_OBSERVED_RELEASE=v2` is the shipped build, so this ran against it and
 * is part of the root suite. A legacy build (`bun run build:legacy`) keeps its
 * historical defaults and shows no notice; the root suite assumes the shipped
 * mode, which is v2.
 */

test.use({ viewport: { width: 1440, height: 1000 } });

test.beforeEach(async ({ page }) => {
  // Preview re-labels `.gz` with Content-Encoding; serve the pinned bytes raw.
  await servePackBytesFromDisk(page);
});

test.describe("Observed default migration (switch on)", () => {
  test("a bare /explore opens on the published window and says so", async ({
    page,
  }) => {
    await page.goto("/explore");

    await expect(
      page.getByRole("radio", { name: "12 months to 2026-10" }),
    ).toBeChecked({ timeout: 30_000 });
    // The address bar is written by an effect after the selection commits, so the
    // assertion polls: the contract is that the URL ends up naming the window,
    // not that it is already rewritten in the same tick.
    await expect
      .poll(() => new URL(page.url()).searchParams.get("period"), {
        timeout: 10_000,
      })
      .toBe("ttm_2026_10");

    const notice = page.locator('[data-observed-default-notice="true"]');
    await expect(notice).toBeVisible();
    await expect(notice).toContainText("opens on 12 months to 2026-10");
    await expect(notice).toContainText("2025 complete year");

    const link = notice.getByRole("link", { name: "open that view" });
    await expect(link).toHaveAttribute("href", /\/explore\?period=year_2025$/);

    // The link resolves to the previously explicit window.
    await link.click();
    await expect(
      page.getByRole("radio", { name: "2025 complete year" }),
    ).toBeChecked();
    await expect(
      page.locator('[data-observed-default-notice="true"]'),
    ).toHaveCount(0);
  });

  test("an explicit window never earns the migration notice", async ({
    page,
  }) => {
    await page.goto("/explore?period=ttm_2026_10");

    await expect(
      page.getByRole("radio", { name: "12 months to 2026-10" }),
    ).toBeChecked({ timeout: 30_000 });
    await expect(
      page.locator('[data-observed-default-notice="true"]'),
    ).toHaveCount(0);
  });

  test("a bare Compare Areas keeps its ranked default and explains why", async ({
    page,
  }) => {
    await page.goto("/dashboard/leaderboard");
    await page.waitForSelector('[data-interactive-ready="true"]');

    // D03's ranking default is only adopted when the page's default scope
    // (`all`) is cleared to publish. It is `limited-display` in this release,
    // so Compare Areas keeps "2022 onward" — a ranked default — and therefore
    // has no moved default to announce.
    await expect(
      page.locator('[data-observed-default-notice="true"]'),
    ).toHaveCount(0);
    expect(new URL(page.url()).searchParams.get("timeBasis")).toBe("recent");
    await expect(page.getByText(/2022 onward/i).first()).toBeVisible();
  });
});
