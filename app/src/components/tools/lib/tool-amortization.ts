/**
 * Illustrative financing arithmetic (slice S8).
 *
 * This is ordinary amortization over user-supplied assumptions. It is **not**
 * an eligibility engine, a loan recommendation, a CPF/MSR/TDSR assessment or a
 * predictive income model (decision register, implementation-plan §6 and
 * feature-specifications "Financing").
 *
 * Contract:
 * - Pure: no React, DOM, fetch or URL access.
 * - Unrounded values are returned; rounding is a display concern.
 * - A blank, non-finite or out-of-range input withholds **every** output and
 *   names the field, rather than substituting a default or a zero.
 * - The zero-interest branch is `principal / months`, not a division by zero.
 */

export interface FinancingInputs {
  /** Observed reference price or a user-specified hypothetical, in SGD. */
  price: number | null;
  annualIncome: number | null;
  /** Percent of price paid up front, 0–100. */
  downPaymentPercent: number | null;
  termYears: number | null;
  /** Nominal annual interest rate as a percentage, e.g. `3` for 3%. */
  annualRatePercent: number | null;
}

export type FinancingField = keyof FinancingInputs;

/**
 * UI bounds. They are documented arithmetic limits that keep the formula
 * finite and readable — they are not lender limits and imply no eligibility.
 */
export const FINANCING_LIMITS = {
  price: { minExclusive: 0, label: "Price" },
  annualIncome: { minExclusive: 0, label: "Annual household income" },
  downPaymentPercent: { min: 0, max: 100, label: "Down payment" },
  termYears: { min: 1, max: 50, label: "Loan term" },
  annualRatePercent: { min: 0, max: 20, label: "Annual interest rate" },
} as const;

/** The reference rates the sensitivity table reports, as percentages. */
export const SENSITIVITY_RATES: readonly number[] = [2, 3, 4, 5, 6];

export interface FinancingSensitivityRow {
  ratePercent: number;
  monthlyPayment: number | null;
}

export interface FinancingScenario {
  downPaymentAmount: number;
  principal: number;
  monthlyPayment: number;
  monthlyIncome: number;
  /** Monthly payment as a percentage of monthly income. */
  paymentToIncomePercent: number;
  /** Price divided by annual household income. */
  priceToAnnualIncome: number;
  totalMonths: number;
  sensitivity: FinancingSensitivityRow[];
}

export type FinancingResult =
  | { ok: true; scenario: FinancingScenario }
  | { ok: false; invalidFields: FinancingField[] };

function isFiniteNumber(value: number | null): value is number {
  return value !== null && Number.isFinite(value);
}

/**
 * Standard amortizing payment:
 * `P × r / (1 − (1 + r)^−n)` with `r = annualRate/12` and `n = years × 12`.
 * At `r = 0` the payment is `P / n`.
 *
 * Returns `null` for a non-positive principal/term or a negative rate.
 */
export function monthlyPayment(
  principal: number,
  annualRatePercent: number,
  termYears: number,
): number | null {
  if (!Number.isFinite(principal) || principal <= 0) return null;
  if (!Number.isFinite(termYears) || termYears <= 0) return null;
  if (!Number.isFinite(annualRatePercent) || annualRatePercent < 0) {
    return null;
  }

  const months = termYears * 12;
  if (!Number.isFinite(months) || months <= 0) return null;

  const monthlyRate = annualRatePercent / 100 / 12;
  if (monthlyRate === 0) {
    return principal / months;
  }
  return (principal * monthlyRate) / (1 - Math.pow(1 + monthlyRate, -months));
}

/** Validate every field and, only when all are valid, compute the scenario. */
export function computeFinancingScenario(
  inputs: FinancingInputs,
): FinancingResult {
  const invalidFields: FinancingField[] = [];
  const {
    price,
    annualIncome,
    downPaymentPercent,
    termYears,
    annualRatePercent,
  } = inputs;

  if (!isFiniteNumber(price) || price <= FINANCING_LIMITS.price.minExclusive) {
    invalidFields.push("price");
  }
  if (
    !isFiniteNumber(annualIncome) ||
    annualIncome <= FINANCING_LIMITS.annualIncome.minExclusive
  ) {
    invalidFields.push("annualIncome");
  }
  if (
    !isFiniteNumber(downPaymentPercent) ||
    downPaymentPercent < FINANCING_LIMITS.downPaymentPercent.min ||
    downPaymentPercent > FINANCING_LIMITS.downPaymentPercent.max
  ) {
    invalidFields.push("downPaymentPercent");
  }
  if (
    !isFiniteNumber(termYears) ||
    termYears < FINANCING_LIMITS.termYears.min ||
    termYears > FINANCING_LIMITS.termYears.max
  ) {
    invalidFields.push("termYears");
  }
  if (
    !isFiniteNumber(annualRatePercent) ||
    annualRatePercent < FINANCING_LIMITS.annualRatePercent.min ||
    annualRatePercent > FINANCING_LIMITS.annualRatePercent.max
  ) {
    invalidFields.push("annualRatePercent");
  }

  if (invalidFields.length > 0) {
    return { ok: false, invalidFields };
  }

  // Every field is a finite number beyond this point; the assertions keep the
  // arithmetic readable for the compiler without changing behaviour.
  const validPrice = price as number;
  const validIncome = annualIncome as number;
  const validDown = downPaymentPercent as number;
  const validYears = termYears as number;
  const validRate = annualRatePercent as number;

  const downPaymentAmount = (validPrice * validDown) / 100;
  const principal = validPrice - downPaymentAmount;
  const monthlyIncome = validIncome / 12;
  const totalMonths = validYears * 12;

  const payment = monthlyPayment(principal, validRate, validYears);
  if (payment === null) {
    // Unreachable with the bounds above; fail closed rather than render 0.
    return { ok: false, invalidFields: ["price"] };
  }

  const sensitivity = SENSITIVITY_RATES.map((ratePercent) => ({
    ratePercent,
    monthlyPayment: monthlyPayment(principal, ratePercent, validYears),
  }));

  return {
    ok: true,
    scenario: {
      downPaymentAmount,
      principal,
      monthlyPayment: payment,
      monthlyIncome,
      paymentToIncomePercent: (payment / monthlyIncome) * 100,
      priceToAnnualIncome: validPrice / validIncome,
      totalMonths,
      sensitivity,
    },
  };
}

/** Human-readable reason a field is withheld, for the validation summary. */
export function invalidFieldReason(field: FinancingField): string {
  switch (field) {
    case "price":
      return "Enter a price greater than 0.";
    case "annualIncome":
      return "Enter an annual household income greater than 0.";
    case "downPaymentPercent":
      return "Enter a down payment between 0% and 100%.";
    case "termYears":
      return `Enter a loan term between ${FINANCING_LIMITS.termYears.min} and ${FINANCING_LIMITS.termYears.max} years.`;
    case "annualRatePercent":
      return `Enter an annual interest rate between ${FINANCING_LIMITS.annualRatePercent.min}% and ${FINANCING_LIMITS.annualRatePercent.max}%.`;
    default:
      return "Enter a valid value.";
  }
}
