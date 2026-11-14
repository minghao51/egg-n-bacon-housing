/**
 * RF02 unit tests: chart data preparation honesty.
 *
 * Covers the two defects fixed in this slice: an all-missing series (for
 * example a "±18.58%" uncertainty column) was silently plotted as an empty
 * legend entry, and mixed-unit columns shared one numeric axis.
 */

import { describe, expect, it } from "bun:test";
import {
  dropEmptyDatasets,
  inferChartUnit,
  parseNumericValue,
  splitDatasetsByUnit,
  tableToChartData,
  type ChartData,
} from "@/utils/data-parser";

describe("inferChartUnit", () => {
  it("recognises percentages, currency, counts and scores", () => {
    expect(inferChartUnit("Median Yield")).toBe("percent");
    expect(inferChartUnit("Directional Acc")).toBe("percent");
    expect(inferChartUnit("R² (magnitude fit)")).toBe("percent");
    expect(inferChartUnit("MRT Premium per 100m")).toBe("currency");
    expect(inferChartUnit("Mean Price PSF")).toBe("currency");
    expect(inferChartUnit("Transactions")).toBe("count");
    expect(inferChartUnit("Records")).toBe("count");
    expect(inferChartUnit("School Quality Score")).toBe("number");
  });
});

describe("splitDatasetsByUnit", () => {
  it("keeps a single-unit table as one group", () => {
    const data: ChartData = {
      labels: ["A", "B"],
      datasets: [{ label: "Directional Acc", data: [99.4, 97.1] }],
    };

    const groups = splitDatasetsByUnit(data);

    expect(groups).toHaveLength(1);
    expect(groups[0].unit).toBe("percent");
    expect(groups[0].data.datasets).toHaveLength(1);
  });

  it("separates a currency premium from a transaction count", () => {
    const data: ChartData = {
      labels: ["Central Area", "Sengkang"],
      datasets: [
        { label: "MRT Premium per 100m", data: [59.19, -16.88] },
        { label: "Mean Price PSF", data: [903, 558] },
        { label: "Transactions", data: [599, 7585] },
      ],
    };

    const groups = splitDatasetsByUnit(data);

    expect(groups.map((group) => group.unit)).toEqual([
      "currency",
      "count",
    ]);
    expect(groups[0].data.datasets.map((dataset) => dataset.label)).toEqual([
      "MRT Premium per 100m",
      "Mean Price PSF",
    ]);
    expect(groups[1].data.datasets.map((dataset) => dataset.label)).toEqual([
      "Transactions",
    ]);
  });
});

describe("dropEmptyDatasets", () => {
  it("drops an all-missing series and reports its label", () => {
    const data: ChartData = {
      labels: ["HDB", "EC"],
      datasets: [
        { label: "R² (magnitude fit)", data: [79.8, 98.5] },
        { label: "95% CI Width", data: [null, null] },
      ],
    };

    const result = dropEmptyDatasets(data);

    expect(result.data.datasets.map((dataset) => dataset.label)).toEqual([
      "R² (magnitude fit)",
    ]);
    expect(result.dropped).toEqual(["95% CI Width"]);
  });

  it("keeps a partially missing series", () => {
    const data: ChartData = {
      labels: ["A", "B"],
      datasets: [{ label: "Median Price", data: [null, 520000] }],
    };

    const result = dropEmptyDatasets(data);

    expect(result.dropped).toEqual([]);
    expect(result.data.datasets[0].data).toEqual([null, 520000]);
  });
});

describe("parseNumericValue", () => {
  it("parses currency and counts", () => {
    expect(parseNumericValue("+$59.19")).toBe(59.19);
    expect(parseNumericValue("$1,538")).toBe(1538);
    expect(parseNumericValue("1,853")).toBe(1853);
  });

  it("parses plain percentages", () => {
    expect(parseNumericValue("79.8%")).toBe(79.8);
    expect(parseNumericValue("-38.54%")).toBe(-38.54);
  });

  it("refuses uncertainty notation instead of turning it into a point estimate", () => {
    expect(parseNumericValue("±18.58%")).toBeNull();
    expect(parseNumericValue("±1877.88%")).toBeNull();
  });

  it("refuses ranges and descriptive cells", () => {
    expect(parseNumericValue("~5-7%")).toBeNull();
    expect(parseNumericValue("$1,200-1,600")).toBeNull();
    expect(parseNumericValue("Rising")).toBeNull();
    expect(parseNumericValue("")).toBeNull();
  });
});

describe("tableToChartData", () => {
  it("returns null when the requested columns are absent", () => {
    const table = {
      headers: ["Period", "SORA Rate", "HDB Price Trend"],
      rows: [["2023", "3.5-4.0%", "Flat"]],
    };

    expect(
      tableToChartData(table, ["SORA Rate (%)", "HDB Median Price Index"]),
    ).toBeNull();
  });

  it("yields an all-missing dataset for range-only columns, which the caller drops", () => {
    const table = {
      headers: ["Planning Area", "CAGR"],
      rows: [["Bukit Timah", "~5-7%"]],
    };

    const data = tableToChartData(table, ["CAGR"]);

    expect(data?.datasets[0].data).toEqual([null]);
    expect(dropEmptyDatasets(data as ChartData).dropped).toEqual(["CAGR"]);
  });

  it("keeps null cells for partially published columns", () => {
    const table = {
      headers: ["Town", "MRT Premium per 100m"],
      rows: [
        ["Central Area", "+$59.19"],
        ["Sengkang", "n/a"],
      ],
    };

    const data = tableToChartData(table, ["MRT Premium per 100m"]);

    expect(data?.datasets[0].data).toEqual([59.19, null]);
  });
});
