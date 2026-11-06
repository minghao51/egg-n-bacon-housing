import { test, expect, type Page } from "@playwright/test";
import { expectPageToLoadWithoutErrors } from "../utils/pageHealth";

/**
 * `/research/tools` and the `/dashboard/trends` wrapper.
 *
 * Every assertion binds to published values or to the slice's output contract:
 * the amortization exit values (S$2,357 / 23.6% / 5.92× / 2,107–3,202), the
 * lease band at 75 years (74–79, +19.1%, 29,913 rows), the MRT total being
 * withheld, and the spatial archive exposing 40 towns without an allocation.
 */

const H1 = "Make the assumptions editable.";

async function openTools(
  page: Page,
  query = "",
  heading = "Financing scenario",
) {
  await page.goto(`/research/tools${query}`);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(H1);
  await expect(page.getByRole("heading", { name: heading })).toBeVisible();
}

function params(page: Page) {
  return new URL(page.url()).searchParams;
}

test.describe("Research tools", () => {
  test.use({ viewport: { width: 1440, height: 1000 } });

  test("renders one heading, the four tools and the financing scenario", async ({
    page,
  }) => {
    await openTools(page);

    await expect(page.getByRole("heading", { level: 1 })).toHaveCount(1);
    await expect(page.getByText("Research / Tools").first()).toBeVisible();
    await expect(
      page.getByText("Illustrative arithmetic · archived models gated"),
    ).toBeVisible();

    const tabs = page.getByRole("tab");
    await expect(tabs).toHaveCount(4);
    await expect(
      page.getByRole("tab", { name: /Financing scenario/ }),
    ).toHaveAttribute("aria-selected", "true");
    await expect(page.getByRole("tab", { name: /Lease bands/ })).toBeVisible();
    await expect(page.getByRole("tab", { name: /MRT \/ CBD/ })).toBeVisible();
    await expect(
      page.getByRole("tab", { name: /Spatial patterns/ }),
    ).toBeVisible();
  });

  test("the documented scenario reproduces the amortization exit values", async ({
    page,
  }) => {
    await openTools(page);

    await expect(page.locator("#financing-price")).toHaveValue("710000");
    await expect(page.locator("#financing-income")).toHaveValue("120000");
    await expect(page.locator("#financing-down")).toHaveValue("30");
    await expect(page.locator("#financing-term")).toHaveValue("25");
    await expect(page.locator("#financing-rate")).toHaveValue("3.0");

    // The reference price is named and source-bound.
    const reference = page.locator("#financing-reference-status");
    await expect(reference).toContainText("Imported from");
    await expect(reference).toContainText("map_metrics.year_2025_hdb");
    await expect(reference).toContainText("Tampines");
    await expect(reference).toContainText("S$710,000");
    await expect(reference).toContainText("1,921 sales");
    await expect(reference).toContainText("published through 2026-10");

    await expect(page.getByText("S$2,357").first()).toBeVisible();
    await expect(page.getByText("S$213,000")).toBeVisible();
    await expect(page.getByText("S$497,000")).toBeVisible();
    await expect(page.getByText("S$10,000")).toBeVisible();
    await expect(page.getByText("23.6%")).toBeVisible();
    await expect(page.getByText("5.92×")).toBeVisible();

    // Sensitivity rows: same principal and term at 2–6%.
    for (const [rate, payment] of [
      ["2%", "S$2,107"],
      ["3%", "S$2,357"],
      ["4%", "S$2,623"],
      ["5%", "S$2,905"],
      ["6%", "S$3,202"],
    ] as const) {
      await expect(
        page.getByRole("row", {
          name: new RegExp(`${rate} ${payment.replace("$", "\\$")}`),
        }),
      ).toBeVisible();
    }

    await expect(page.getByText(/Not a loan offer/)).toBeVisible();
    await expect(page.getByText(/no CPF, MSR or TDSR/)).toBeVisible();
  });

  test("blank or invalid inputs withhold every output and name the field", async ({
    page,
  }) => {
    await openTools(page);

    await page.locator("#financing-income").fill("");
    await expect(page.getByText("Monthly payment withheld")).toBeVisible();
    await expect(page.getByText(/Annual household income:/)).toBeVisible();
    await expect(page.getByText(/S\$2,357/)).toHaveCount(0);

    await page.locator("#financing-income").fill("abc");
    await expect(page.getByText(/Annual household income:/)).toBeVisible();

    await page.locator("#financing-income").fill("0");
    await expect(page.getByText(/greater than 0/).first()).toBeVisible();

    // Restoring a valid income brings the outputs back.
    await page.locator("#financing-income").fill("120000");
    await expect(page.getByText("S$2,357").first()).toBeVisible();
  });

  test("a zero interest rate uses the principal ÷ months branch", async ({
    page,
  }) => {
    await openTools(page);

    await page.locator("#financing-rate").fill("0");
    await expect(page.getByText("S$1,657").first()).toBeVisible();
    await expect(page.getByText(/principal ÷ months/)).toBeVisible();
    // The sensitivity table still reports the 3% row by design; only the
    // headline payment changes to the zero-rate branch.
    await expect(page.getByRole("row", { name: /3% S\$2,357/ })).toBeVisible();
  });

  test("the named reference is imported, and a manual price stops applying it", async ({
    page,
  }) => {
    await openTools(page);

    await page.getByLabel("Planning area").selectOption("QUEENSTOWN");
    await page.getByLabel("Property type").selectOption("condo");

    await expect.poll(() => params(page).get("ref")).toBe("QUEENSTOWN");
    expect(params(page).get("rt")).toBe("condo");
    expect(params(page).get("rv")).toBe("1");
    // Queenstown condominium 2025 median in the published snapshot.
    await expect(page.locator("#financing-price")).toHaveValue("2088000");
    await expect(
      page.locator("code", { hasText: "map_metrics.year_2025_condo" }).first(),
    ).toBeVisible();

    await page.locator("#financing-price").fill("700000");
    await expect(page.getByText(/Price entered manually/)).toBeVisible();

    await page
      .getByRole("button", { name: "Import observed 2025 median" })
      .click();
    await expect(page.locator("#financing-price")).toHaveValue("2088000");
  });

  test("a cold deep link selects the tool and the named reference", async ({
    page,
  }) => {
    await openTools(
      page,
      "?tool=lease&ref=QUEENSTOWN&rt=condo&rv=1",
      "Lease bands",
    );

    await expect(page.getByText(/74–79 years/)).toBeVisible();
    await expect(
      page.getByRole("tab", { name: /Lease bands/ }),
    ).toHaveAttribute("aria-selected", "true");
    // The reference is preserved even though another tool is open.
    await expect.poll(() => params(page).get("ref")).toBe("QUEENSTOWN");
    expect(params(page).get("tool")).toBe("lease");

    // An unknown tool falls back to the documented default, without throwing.
    await openTools(page, "?tool=hotspots");
    await expect(
      page.getByRole("tab", { name: /Financing scenario/ }),
    ).toHaveAttribute("aria-selected", "true");
  });

  test("lease bands show the stored interval, signed statistic and endpoint policy", async ({
    page,
  }) => {
    await openTools(page);
    await page.getByRole("tab", { name: /Lease bands/ }).click();

    await expect(page.getByText("74–79 years")).toBeVisible();
    await expect(page.getByText(/\+19\.1%/).first()).toBeVisible();
    await expect(page.getByText(/29,913 source rows/)).toBeVisible();
    await expect(page.getByText(/Stored annual-rate field/)).toBeVisible();
    await expect(page.getByText(/first-match rule/)).toBeVisible();
    await expect(page.getByText(/negative value means/)).toBeVisible();
    await expect(page.getByText("Stored labels conflict")).toBeVisible();
    await expect(
      page.getByText(/No stored band covers 10–38 years/),
    ).toBeVisible();

    // A shared endpoint names every containing band and the archive's choice.
    await page.locator("#lease-years").fill("94");
    await expect(page.getByText(/94 is a shared endpoint/)).toBeVisible();
    await expect(page.getByText(/0-5 \(94–99/)).toBeVisible();
    await expect(page.getByText(/5-10 \(89–94/)).toBeVisible();

    // A blank input withholds the lookup rather than guessing a band.
    await page.locator("#lease-years").fill("");
    await expect(page.getByText("No band selected")).toBeVisible();
    await expect(
      page.getByText(/Enter a remaining lease between 40 and 99/),
    ).toBeVisible();
  });

  test("MRT/CBD keeps the controls and withholds the total-dollar estimate", async ({
    page,
  }) => {
    await openTools(page);
    await page.getByRole("tab", { name: /MRT \/ CBD/ }).click();

    await expect(page.getByText("Model review required")).toBeVisible();
    await expect(
      page.getByText(/Total-dollar premium is withheld/),
    ).toBeVisible();
    await expect(
      page.getByText(
        "Stored MRT premium term: (500 ÷ 100) × 9 × 1000 · total withheld",
      ),
    ).toBeVisible();
    await expect(
      page.getByText(
        "CBD term (as supplied, not combined): (10 km × 15000 per km) · total withheld",
      ),
    ).toBeVisible();
    await expect(page.locator("#mrt-town")).toHaveValue("BISHAN");
    await expect(page.getByText(/Stored key: BISHAN/)).toBeVisible();
    await expect(
      page.getByLabel(/Floor area \(S8 explicit input\)/),
    ).toBeVisible();
    // Retired boilerplate must not return.
    await expect(page.getByText(/15x|7x|15×|7×/)).toHaveCount(0);

    await page.locator("#mrt-distance").fill("900");
    await expect(page.getByText(/capped from 900 m/)).toBeVisible();

    await page.getByLabel("Property type").selectOption("Condominium");
    await expect(
      page.getByText(/\(500 ÷ 100\) × 63 × 1000/, { exact: false }),
    ).toBeVisible();
    await expect(
      page.getByText(/\(10 km × 35000 per km\)/, { exact: false }),
    ).toBeVisible();
  });

  test("spatial patterns inspect stored labels without an allocation", async ({
    page,
  }) => {
    await openTools(page);
    await page.getByRole("tab", { name: /Spatial patterns/ }).click();

    await expect(
      page.getByText("4 cluster types across 40 published town records."),
    ).toBeVisible();
    await expect(
      page.getByText(/Portfolio allocation, BUY\/SELL prompts/),
    ).toBeVisible();
    await expect(
      page.getByText(/no aggregate clusters\[\] block/),
    ).toBeVisible();

    const rows = page.locator("table tbody tr");
    await expect(rows).toHaveCount(40);

    await page.getByLabel("Stored cluster label").selectOption("HH");
    const filteredCount = await rows.count();
    expect(filteredCount).toBeGreaterThan(0);
    expect(filteredCount).toBeLessThan(40);
    await expect(
      page.getByText(/Sample size, analysis date and method are not supplied/),
    ).toBeVisible();
  });

  test("the legacy wrapper renders the same workspace and keeps its query", async ({
    page,
  }) => {
    await page.goto("/dashboard/trends?tool=mrt");
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(H1);
    await expect(page.getByText(/Compatibility route/)).toBeVisible();
    await expect(page).toHaveURL(/\/dashboard\/trends/);
    await expect(page.getByText("Model review required")).toBeVisible();
    await expect(
      page.locator("p", { hasText: "total withheld" }).first(),
    ).toBeVisible();
  });

  test("the navigation points at the research destination", async ({
    page,
  }) => {
    await page.goto("/dashboard");
    const nav = page.getByRole("navigation", { name: "Main navigation" });
    await nav
      .getByRole("link", { name: /Decision Tools/ })
      .first()
      .click();
    await expect(page).toHaveURL(/research\/tools/);
    await expect(
      page
        .getByRole("navigation", { name: "Main navigation" })
        .getByRole("link", { name: /Decision Tools/ }),
    ).toHaveAttribute("aria-current", "page");
  });

  test("tool tabs follow the keyboard tab pattern", async ({ page }) => {
    await openTools(page);
    const financing = page.getByRole("tab", { name: /Financing scenario/ });
    const lease = page.getByRole("tab", { name: /Lease bands/ });
    const spatial = page.getByRole("tab", { name: /Spatial patterns/ });

    await financing.focus();
    await page.keyboard.press("ArrowRight");
    await expect(lease).toBeFocused();
    await expect(lease).toHaveAttribute("aria-selected", "true");

    await page.keyboard.press("End");
    await expect(spatial).toBeFocused();
    await expect(spatial).toHaveAttribute("aria-selected", "true");

    await page.keyboard.press("Home");
    await expect(financing).toBeFocused();
    await expect(financing).toHaveAttribute("aria-selected", "true");
  });

  test("a popstate navigation updates the selected tool", async ({ page }) => {
    await openTools(page, "?tool=lease", "Lease bands");
    await page.evaluate(() => {
      const url = new URL(window.location.href);
      url.searchParams.set("tool", "mrt");
      window.history.pushState({}, "", url);
      window.dispatchEvent(new PopStateEvent("popstate"));
    });
    await expect(page.getByRole("tab", { name: /MRT \/ CBD/ })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    await expect(page.getByText("Model review required")).toBeVisible();
  });

  test("the legacy wrapper keeps a financing reference import", async ({
    page,
  }) => {
    for (const path of ["/research/tools", "/dashboard/trends"]) {
      await page.goto(`${path}?tool=financing&ref=QUEENSTOWN&rt=condo&rv=1`);
      await expect(page.locator("#financing-price")).toHaveValue("2088000");
      const reference = page.locator("#financing-reference-status");
      await expect(reference).toContainText("Queenstown");
      await expect(reference).toContainText("S$2,088,000");
      await expect(reference).toContainText("year_2025_condo");
    }
  });

  test("does not log errors on either route", async ({ page }) => {
    await expectPageToLoadWithoutErrors(page, "/research/tools");
    await expectPageToLoadWithoutErrors(page, "/dashboard/trends");
  });
});

test.describe("Research tools on a narrow viewport", () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test("the native tool select replaces the tabs and financing stays usable", async ({
    page,
  }) => {
    await openTools(page);

    await expect(page.locator("#tool-select")).toBeVisible();
    await expect(
      page.getByRole("tab", { name: /Financing scenario/ }),
    ).toBeHidden();
    await expect(page.getByText("S$2,357").first()).toBeVisible();

    await page.locator("#tool-select").selectOption("lease");
    await expect(page.getByText("74–79 years")).toBeVisible();

    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth > window.innerWidth + 1,
    );
    expect(overflow).toBe(false);
  });
});
