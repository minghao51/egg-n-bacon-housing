import { describe, expect, test } from "bun:test";
import { formatNumber, formatPercent } from "../../src/utils/format";

describe("formatNumber", () => {
  test("formats a real zero instead of treating it as absent", () => {
    expect(formatNumber(0)).toBe("0.0");
    expect(formatNumber(0, 2)).toBe("0.00");
  });

  test("formats finite values with the requested precision", () => {
    expect(formatNumber(620.843)).toBe("620.8");
    expect(formatNumber(-5, 0)).toBe("-5");
  });

  test("never renders a missing measurement as a number", () => {
    expect(formatNumber(null)).toBe("N/A");
    expect(formatNumber(undefined)).toBe("N/A");
    expect(formatNumber(Number.NaN)).toBe("N/A");
    expect(formatNumber(Number.POSITIVE_INFINITY)).toBe("N/A");
  });
});

describe("formatPercent", () => {
  test("converts a fractional ratio and keeps a real zero", () => {
    expect(formatPercent(0)).toBe("0.0%");
    expect(formatPercent(0.23)).toBe("23.0%");
    expect(formatPercent(0.0585, 2)).toBe("5.85%");
  });

  test("supports negative ratios without hiding the sign", () => {
    expect(formatPercent(-0.012)).toBe("-1.2%");
  });

  test("never renders a missing ratio as 0%", () => {
    expect(formatPercent(null)).toBe("N/A");
    expect(formatPercent(undefined)).toBe("N/A");
    expect(formatPercent(Number.NaN)).toBe("N/A");
  });
});
