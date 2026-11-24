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
 * - A 100% down payment is a **valid cash purchase**, not a validation
 *   failure: the principal is 0 and the monthly payment is 0 at every rate.
 *   `price` is never blamed for a principal that is legitimately zero.
 * - The payment is evaluated as `P × r / −expm1(−n × log1p(r))`, the
 *   cancellation-free form of `P × r / (1 − (1 + r)^−n)`, so an arbitrarily
 *   small positive rate still yields a finite payment approaching `P / n`.
 * - A derived value that is not finite (reachable only by overflowing the
 *   double range) fails closed and names the input whose magnitude drives it:
 *   `price` for the loan figures, `annualIncome` for the ratios, `termYears`
 *   for the term.
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
 * `P × r / (1 − (1 + r)^−n)` with `r = annualRate/12` and `n = years × 12`,
 * evaluated as `P × r / −expm1(−n × log1p(r))`. At `r = 0` the payment is
 * `P / n`.
 *
 * Returns `null` for a non-positive principal/term or a negative rate.
 * A non-positive principal is not a payment failure at the scenario level —
 * `computeFinancingScenario` treats a 100% down payment as a cash purchase.
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
  // `-expm1(-n·log1p(r))` is `1 − (1 + r)^−n` without catastrophic
  // cancellation: once `1 + r` rounds to 1 the naive form divides by zero and
  // reports `Infinity` for a perfectly ordinary payment.
  return (
    (principal * monthlyRate) / -Math.expm1(-months * Math.log1p(monthlyRate))
  );
}

/** Every field whose value is blank, non-finite or outside its UI bound. */
function collectInvalidFields(inputs: FinancingInputs): FinancingField[] {
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

  return invalidFields;
}

/** Validate every field and, only when all are valid, compute the scenario. */
export function computeFinancingScenario(
  inputs: FinancingInputs,
): FinancingResult {
  const invalidFields = collectInvalidFields(inputs);
  if (invalidFields.length > 0) {
    return { ok: false, invalidFields };
  }

  const {
    price,
    annualIncome,
    downPaymentPercent,
    termYears,
    annualRatePercent,
  } = inputs;

  // Every field is a finite number beyond this point; the assertions keep the
  // arithmetic readable for the compiler without changing behaviour.
  const validPrice = price as number;
  const validIncome = annualIncome as number;
  const validDown = downPaymentPercent as number;
  const validYears = termYears as number;
  const validRate = annualRatePercent as number;

  const downPaymentAmount = (validPrice * validDown) / 100;
  // `downPaymentPercent` is bounded at 100, so the principal cannot be
  // negative; clamping only removes the float residue of `price × 100 / 100`
  // so that a 100% down payment is exactly a cash purchase, not a loan of
  // −1e−17.
  const principal = Math.max(0, validPrice - downPaymentAmount);
  const monthlyIncome = validIncome / 12;
  const totalMonths = validYears * 12;

  // A cash purchase has no loan, so its payment is 0 at every rate. This is a
  // valid scenario, not a validation failure: the price was valid all along.
  const paymentFor = (ratePercent: number): number | null =>
    principal === 0 ? 0 : monthlyPayment(principal, ratePercent, validYears);

  const payment = paymentFor(validRate);
  const sensitivity = SENSITIVITY_RATES.map((ratePercent) => ({
    ratePercent,
    monthlyPayment: paymentFor(ratePercent),
  }));

  // Defence in depth. The bounds above keep these finite for every realistic
  // input; a magnitude that overflows the double range fails closed with the
  // input whose magnitude drives the offending value named, rather than
  // rendering `Infinity` or `NaN`.
  if (
    !Number.isFinite(downPaymentAmount) ||
    !Number.isFinite(principal) ||
    payment === null ||
    !Number.isFinite(payment) ||
    sensitivity.some(
      (row) =>
        row.monthlyPayment === null || !Number.isFinite(row.monthlyPayment),
    )
  ) {
    return { ok: false, invalidFields: ["price"] };
  }

  const paymentToIncomePercent = (payment / monthlyIncome) * 100;
  const priceToAnnualIncome = validPrice / validIncome;

  if (
    !Number.isFinite(monthlyIncome) ||
    !Number.isFinite(paymentToIncomePercent) ||
    !Number.isFinite(priceToAnnualIncome)
  ) {
    return { ok: false, invalidFields: ["annualIncome"] };
  }
  if (!Number.isFinite(totalMonths)) {
    return { ok: false, invalidFields: ["termYears"] };
  }

  return {
    ok: true,
    scenario: {
      downPaymentAmount,
      principal,
      monthlyPayment: payment,
      monthlyIncome,
      paymentToIncomePercent,
      priceToAnnualIncome,
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
