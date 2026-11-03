/**
 * Unit tests for the monthly trend series (`src/utils/trend-series.ts`).
 *
 * Two kinds of coverage:
 * - hermetic fixtures for the calendar rules (aligned null gaps, calendar-bounded
 *   windows, partial-window flag, malformed payloads, incomplete-year sums);
 * - the published `public/data/dashboard_trends.json.gz`, read once, for the
 *   values the design and the S4 acceptance criteria name: a 2025 HDB volume sum
 *   of 25,084, December 2025 at 635,000 / 2,024, and a series that ends 2026-09.
 *
 * The published asset is read because those numbers are the contract; every
 * other case uses synthetic fixtures so the rules stay testable independently.
 */

import { describe, expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { gunzipSync } from "node:zlib";

import {
  buildTrendSeries,
  filterWindow,
  formatTrendNumber,
  summarize,
  yearSum,
  TREND_QUERY_DEFAULTS,
  TREND_SERIES_IDS,
  TREND_WINDOWS,
  type TrendPoint,
  type TrendSeries,
  type TrendSeriesId,
} from "../../src/utils/trend-series";

/** One payload row; every price/volume field carries the given values. */
function row(
  month: string,
  price: number | null,
  volume: number | null,
): Record<string, unknown> {
  return {
    date: month,
    "Overall Price": price,
    "HDB Price": price,
    "HDB Volume": volume,
    "EC Price": price,
    "EC Volume": volume,
    "Condominium Price": price,
    "Condominium Volume": volume,
  };
}

/** Twelve 2025 rows as points, for the functions that take points directly. */
function points2025(volumes: readonly number[]): TrendPoint[] {
  return volumes.map((volume, index) => ({
    month: `2025-${String(index + 1).padStart(2, "0")}`,
    price: 635000,
    volume,
  }));
}

function point(
  month: string,
  price: number | null,
  volume: number | null,
): TrendPoint {
  return { month, price, volume };
}

function seriesOf(
  points: TrendPoint[],
  id: TrendSeriesId = "hdb",
): TrendSeries {
  const published = points.filter(
    (entry) => entry.price !== null || entry.volume !== null,
  );
  return {
    id,
    label: id === "hdb" ? "HDB" : "All property types",
    points,
    coverageStart: published[0]?.month ?? null,
    coverageEnd: published[published.length - 1]?.month ?? null,
  };
}

/** The published payload, read once. */
const published: unknown = JSON.parse(
  gunzipSync(
    readFileSync(
      join(process.cwd(), "public", "data", "dashboard_trends.json.gz"),
    ),
  ).toString("utf8"),
);

describe("published dashboard_trends payload", () => {
  test("builds 441 monthly HDB points from 1990-01 to 2026-09", () => {
    const series = buildTrendSeries(published, "hdb");
    if (series === null) throw new Error("HDB series unusable");

    expect(series.points).toHaveLength(441);
    expect(series.points[0].month).toBe("1990-01");
    expect(series.points[series.points.length - 1].month).toBe("2026-09");
  });

  test("2025 HDB is twelve points whose volumes sum to 25,084", () => {
    const series = buildTrendSeries(published, "hdb");
    if (series === null) throw new Error("HDB series unusable");

    const window = filterWindow(series, "year_2025");
    expect(window.points).toHaveLength(12);
    expect(window.points[0].month).toBe("2025-01");
    expect(window.points[11].month).toBe("2025-12");
    expect(yearSum(window.points, "2025", "volume")).toBe(25084);
    expect(summarize(window, "year_2025").isPartialWindow).toBe(false);
  });

  test("December 2025 is 635,000 / 2,024", () => {
    const series = buildTrendSeries(published, "hdb");
    if (series === null) throw new Error("HDB series unusable");

    const december = filterWindow(series, "year_2025").points[11];
    expect(december.month).toBe("2025-12");
    expect(december.price).toBe(635000);
    expect(december.volume).toBe(2024);
  });

  test("the latest published month is 2026-09, not the end of 2025", () => {
    const series = buildTrendSeries(published, "hdb");
    if (series === null) throw new Error("HDB series unusable");

    const all = summarize(filterWindow(series, "all"), "all");
    expect(all.endMonth).toBe("2026-09");
    expect(all.months).toBe(441);
    expect(all.isPartialWindow).toBe(false);
    // The 2025 window ends in 2025 while the asset runs to 2026-09.
    expect(summarize(filterWindow(series, "year_2025"), "year_2025").endMonth).toBe(
      "2025-12",
    );
  });

  test("EC keeps the calendar and leaves pre-2021 months unpublished", () => {
    const ec = buildTrendSeries(published, "ec");
    if (ec === null) throw new Error("EC series unusable");

    // Never dropped: the 1990–2020 months exist as null points, so nothing
    // shifts and the table can show N/A for them.
    expect(ec.points).toHaveLength(441);
    expect(ec.points[0].month).toBe("1990-01");
    const firstPublished = ec.points.find((entry) => entry.price !== null);
    expect(firstPublished?.month).toBe("2021-01");

    // "All history" means all *published* history for that series: pre-2021
    // months are trimmed from the window rather than rendered as blank rows,
    // while internal gaps would still be preserved.
    const allWindow = filterWindow(ec, "all");
    expect(allWindow.points[0].month).toBe("2021-01");
    const all = summarize(allWindow, "all");
    expect(all.nullPriceMonths).toBe(0);
    expect(all.endMonth).toBe("2026-09");
    expect(allWindow.coverageStart).toBe("2021-01");

    // 2025 is fully covered for EC even though 2021 and earlier are not.
    const year = filterWindow(ec, "year_2025");
    expect(year.points).toHaveLength(12);
    expect(summarize(year, "year_2025").isPartialWindow).toBe(false);
    expect(year.points.every((entry) => entry.price === null)).toBe(false);
  });

  test("the combined series publishes a price but no invented count", () => {
    const all = buildTrendSeries(published, "all");
    if (all === null) throw new Error("combined series unusable");

    expect(all.points).toHaveLength(441);
    expect(all.points.every((entry) => entry.volume === null)).toBe(true);
    expect(yearSum(all.points, "2025", "volume")).toBeNull();
    expect(
      summarize(filterWindow(all, "year_2025"), "year_2025").latestPrice,
    ).toBe(1169000);
  });
});

describe("buildTrendSeries", () => {
  test("a missing value keeps a null point and the calendar does not shift", () => {
    const series = buildTrendSeries(
      [
        row("2025-01", 612888, 2313),
        row("2025-02", null, 2091),
        row("2025-03", 625000, null),
      ],
      "hdb",
    );
    if (series === null) throw new Error("series unusable");

    expect(series.points).toHaveLength(3);
    expect(series.points[1]).toEqual(point("2025-02", null, 2091));
    expect(series.points[2]).toEqual(point("2025-03", 625000, null));
  });

  test("rows are sorted by month and an omitted month becomes an explicit gap", () => {
    const series = buildTrendSeries(
      [row("2025-03", 630000, 3), row("2025-01", 610000, 1)],
      "hdb",
    );
    if (series === null) throw new Error("series unusable");

    // February is absent from the payload: it is inserted as a null point so a
    // chart cannot draw January-to-March as an adjacent segment and a table
    // cannot silently skip it.
    expect(series.points.map((entry) => entry.month)).toEqual([
      "2025-01",
      "2025-02",
      "2025-03",
    ]);
    expect(series.points[1].price).toBeNull();
    expect(series.points[1].volume).toBeNull();
  });

  test("an unusable value becomes null, never zero and never negative", () => {
    const payload = [
      {
        date: "2025-01",
        "HDB Price": "635000",
        "HDB Volume": -4,
        "EC Price": Number.NaN,
        "EC Volume": null,
      },
    ];

    const hdb = buildTrendSeries(payload, "hdb");
    if (hdb === null) throw new Error("HDB series unusable");
    expect(hdb.points[0]).toEqual(point("2025-01", null, null));

    const ec = buildTrendSeries(payload, "ec");
    if (ec === null) throw new Error("EC series unusable");
    expect(ec.points[0]).toEqual(point("2025-01", null, null));
  });

  test("a real zero is kept as a measurement", () => {
    const series = buildTrendSeries([row("2025-01", 0, 0)], "hdb");
    if (series === null) throw new Error("series unusable");
    expect(series.points[0]).toEqual(point("2025-01", 0, 0));
  });

  test("a malformed payload returns null instead of a partial series", () => {
    expect(buildTrendSeries(null, "hdb")).toBeNull();
    expect(buildTrendSeries(undefined, "hdb")).toBeNull();
    expect(buildTrendSeries("[]", "hdb")).toBeNull();
    expect(buildTrendSeries({}, "hdb")).toBeNull();
    expect(buildTrendSeries([], "hdb")).toBeNull();
    expect(buildTrendSeries([null], "hdb")).toBeNull();
    expect(buildTrendSeries([["2025-01"]], "hdb")).toBeNull();
    expect(buildTrendSeries([{}], "hdb")).toBeNull();
    expect(buildTrendSeries([row("2025-1", 1, 1)], "hdb")).toBeNull();
    expect(buildTrendSeries([row("2025-13", 1, 1)], "hdb")).toBeNull();
    expect(buildTrendSeries([row("2025-00", 1, 1)], "hdb")).toBeNull();
    // Two rows for one month would silently change what "monthly" means.
    expect(
      buildTrendSeries([row("2025-01", 1, 1), row("2025-01", 2, 2)], "hdb"),
    ).toBeNull();
  });
});

describe("filterWindow", () => {
  const series = seriesOf([
    point("2021-12", 1, 10),
    point("2022-01", 2, 20),
    point("2024-12", 3, 30),
    point("2025-01", 4, 40),
    point("2025-06", 5, null),
    point("2025-12", 6, 60),
    point("2026-01", 7, 70),
  ]);

  test("year_2025 keeps exactly the 2025 months", () => {
    const window = filterWindow(series, "year_2025");
    expect(window.points.map((entry) => entry.month)).toEqual([
      "2025-01",
      "2025-06",
      "2025-12",
    ]);
    expect(window.id).toBe("hdb");
    expect(window.label).toBe("HDB");
  });

  test("recent starts at 2022-01 and ends at the series coverage", () => {
    const window = filterWindow(series, "recent");
    expect(window.points[0].month).toBe("2022-01");
    expect(window.points[window.points.length - 1].month).toBe("2026-01");
    expect(window.points).toHaveLength(6);
  });

  test("all history keeps every point in order", () => {
    const window = filterWindow(series, "all");
    expect(window.points).toHaveLength(7);
    expect(window.points[0].month).toBe("2021-12");
  });

  test("a window with no published month is empty, not zero-filled", () => {
    const early = filterWindow(
      seriesOf([point("2021-01", 1, 1), point("2021-02", 2, 2)]),
      "year_2025",
    );
    expect(early.points).toEqual([]);
  });
});

describe("summarize", () => {
  test("reports the last month in the window, gaps included", () => {
    const window = filterWindow(
      seriesOf([point("2025-01", 612888, 2313), point("2025-02", null, 2091)]),
      "year_2025",
    );
    const summary = summarize(window, "year_2025");

    expect(summary.months).toBe(2);
    expect(summary.startMonth).toBe("2025-01");
    expect(summary.endMonth).toBe("2025-02");
    // The last month's own value, not the previous non-null price.
    expect(summary.latestPrice).toBeNull();
    expect(summary.latestVolume).toBe(2091);
    expect(summary.nullPriceMonths).toBe(1);
  });

  test("flags a partial window when a calendar boundary is unpublished", () => {
    const missingDecember = seriesOf([
      point("2025-01", 1, 1),
      point("2025-11", 2, 2),
    ]);
    expect(summarize(missingDecember, "year_2025").isPartialWindow).toBe(true);

    const lateStart = seriesOf([
      point("2023-01", 1, 1),
      point("2023-02", 2, 2),
    ]);
    expect(summarize(lateStart, "recent").isPartialWindow).toBe(true);

    const complete = seriesOf([
      point("2025-01", 1, 1),
      point("2025-12", 2, 2),
    ]);
    expect(summarize(complete, "year_2025").isPartialWindow).toBe(false);
  });

  test("an unbounded window is never partial and an empty range always is", () => {
    expect(
      summarize(seriesOf([point("1990-01", 1, 1)]), "all").isPartialWindow,
    ).toBe(false);
    expect(summarize(seriesOf([]), "all").isPartialWindow).toBe(false);
    expect(summarize(seriesOf([]), "recent").isPartialWindow).toBe(true);
  });

  test("an empty series has no latest values", () => {
    const summary = summarize(seriesOf([]));
    expect(summary.months).toBe(0);
    expect(summary.startMonth).toBeNull();
    expect(summary.endMonth).toBeNull();
    expect(summary.latestPrice).toBeNull();
    expect(summary.latestVolume).toBeNull();
    expect(summary.nullPriceMonths).toBe(0);
  });
});

describe("yearSum", () => {
  test("sums a complete year without rounding", () => {
    const volumes = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12];
    expect(yearSum(points2025(volumes), "2025", "volume")).toBe(78);
    expect(yearSum(points2025(volumes), "2025", "price")).toBe(635000 * 12);
    expect(yearSum(points2025([0.5, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]), "2025", "volume")).toBe(
      0.5,
    );
  });

  test("returns null when the year is incomplete", () => {
    const eleven = points2025([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]);
    expect(eleven).toHaveLength(11);
    expect(yearSum(eleven, "2025", "volume")).toBeNull();
    expect(yearSum(points2025([1, 2]), "2025", "volume")).toBeNull();
  });

  test("returns null when one month is unpublished or duplicated", () => {
    const points = points2025([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]);
    const withGap = points.map((entry) =>
      entry.month === "2025-02" ? { ...entry, volume: null } : entry,
    );

    expect(yearSum(withGap, "2025", "volume")).toBeNull();
    expect(yearSum(withGap, "2025", "price")).toBe(635000 * 12);

    // A thirteenth row repeating an existing month is a duplicate, not a sum.
    const duplicated = [...points, points[5]];
    expect(yearSum(duplicated, "2025", "price")).toBeNull();
  });

  test("rejects a year that is not four digits", () => {
    expect(yearSum([], "25", "volume")).toBeNull();
    expect(yearSum([], "2025-01", "volume")).toBeNull();
  });
});

describe("formatTrendNumber", () => {
  test("groups digits without rounding", () => {
    expect(formatTrendNumber(635000)).toBe("635,000");
    expect(formatTrendNumber(2024)).toBe("2,024");
    expect(formatTrendNumber(0)).toBe("0");
    expect(formatTrendNumber(1234567.25)).toBe("1,234,567.25");
    expect(formatTrendNumber(-1500)).toBe("-1,500");
  });

  test("renders an absent value as N/A", () => {
    expect(formatTrendNumber(null)).toBe("N/A");
    expect(formatTrendNumber(Number.NaN)).toBe("N/A");
    expect(formatTrendNumber(Number.POSITIVE_INFINITY)).toBe("N/A");
  });
});

describe("selection constants", () => {
  test("the default is a selectable series and window", () => {
    expect(TREND_SERIES_IDS).toContain(TREND_QUERY_DEFAULTS.series);
    expect(TREND_WINDOWS).toContain(TREND_QUERY_DEFAULTS.window);
  });
});


describe("yearSum calendar integrity", () => {
  test("rejects an out-of-range month instead of counting it as a month", () => {
    const points = Array.from({ length: 11 }, (_, index) => ({
      month: `2025-${String(index + 1).padStart(2, "0")}`,
      price: 500000,
      volume: 100,
    }));
    points.push({ month: "2025-13", price: 500000, volume: 100 });
    expect(yearSum(points, "2025", "volume")).toBeNull();
  });

  test("still sums a complete twelve-month year", () => {
    const points = Array.from({ length: 12 }, (_, index) => ({
      month: `2025-${String(index + 1).padStart(2, "0")}`,
      price: 500000,
      volume: 100,
    }));
    expect(yearSum(points, "2025", "volume")).toBe(1200);
  });
});
