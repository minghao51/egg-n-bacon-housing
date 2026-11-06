/**
 * Display formatting for the decision-tools workspace.
 *
 * A missing or non-finite value is `N/A`, never `0` or a plausible-looking
 * substitute (repository invariant "missing ≠ zero"). `0` is a real value.
 */

const SGD = new Intl.NumberFormat("en-SG", {
  minimumFractionDigits: 0,
  maximumFractionDigits: 0,
});

const SGD_ONE_DECIMAL = new Intl.NumberFormat("en-SG", {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});

/** `S$710,000` — whole dollars by default; `S$2,356.8` at one decimal. */
export function formatSgd(
  value: number | null | undefined,
  digits: 0 | 1 = 0,
): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return "N/A";
  }
  return `S$${(digits === 1 ? SGD_ONE_DECIMAL : SGD).format(value)}`;
}

/** `5.92×` (a dimensionless multiple), or `N/A`. */
export function formatMultiple(
  value: number | null | undefined,
  digits = 2,
): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return "N/A";
  }
  return `${value.toFixed(digits)}\u00d7`;
}

/** `23.6%` from an already-scaled percentage, or `N/A`. */
export function formatPercentValue(
  value: number | null | undefined,
  digits = 1,
): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return "N/A";
  }
  return `${value.toFixed(digits)}%`;
}

/**
 * `-11.0%` / `+19.1%` from an already-scaled signed percentage.
 *
 * The sign is always explicit: in the lease archive a negative value is a
 * premium relative to the band baseline, not a discount.
 */
export function formatSignedPercent(
  value: number | null | undefined,
  digits = 1,
): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return "N/A";
  }
  const sign = value < 0 ? "-" : "+";
  return `${sign}${Math.abs(value).toFixed(digits)}%`;
}
