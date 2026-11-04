/**
 * Formatting helpers for evidence-facing copy.
 *
 * These exist so a missing measurement can never be rendered as a plausible
 * number. `0` is a real value; `null`, `undefined` and `NaN` are not.
 */

/** Format a finite number with fixed decimals, or return "N/A" when absent. */
export function formatNumber(
  value: number | null | undefined,
  digits = 1,
): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return "N/A";
  }
  return value.toFixed(digits);
}

/**
 * Format a 0–1 ratio as a percentage, or return "N/A" when absent.
 * Fractional ratios are converted; already-scaled percentages are not.
 */
export function formatPercent(
  ratio: number | null | undefined,
  digits = 1,
): string {
  if (ratio === null || ratio === undefined || !Number.isFinite(ratio)) {
    return "N/A";
  }
  return `${(ratio * 100).toFixed(digits)}%`;
}
