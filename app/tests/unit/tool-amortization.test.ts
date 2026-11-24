/**
 * Unit tests for the S8 financing arithmetic
 * (src/components/tools/lib/tool-amortization.ts).
 *
 * The pinned numbers are the slice's exit criteria: S$497,000 principal over
 * 25 years at 3% is S$2,356.830…, displayed as S$2,357; payment/income 23.6%;
 * price/annual income 5.92×; sensitivity 2,107 / 2,357 / 2,623 / 2,905 / 3,202.
 * The zero-interest branch and the withhold-on-invalid behaviour are pinned too,
 * because a default or a 0 would be worse than no output.
 */

import { describe, expect, test } from "bun:test";

import {
  computeFinancingScenario,
  invalidFieldReason,
  monthlyPayment,
  SENSITIVITY_RATES,
  type FinancingInputs,
  type FinancingScenario,
} from "../../src/components/tools/lib/tool-amortization";
import {
  formatPercentValue,
  formatSgd,
  formatSignedPercent,
} from "../../src/components/tools/lib/tool-format";

const SCENARIO: FinancingInputs = {
  price: 710_000,
  annualIncome: 120_000,
  downPaymentPercent: 30,
  termYears: 25,
  annualRatePercent: 3,
};

describe("standard amortization", () => {
  test("the documented scenario reproduces the exit values", () => {
    const result = computeFinancingScenario(SCENARIO);
    expect(result.ok).toBe(true);
    if (!result.ok) return;

    expect(result.scenario.downPaymentAmount).toBe(213_000);
    expect(result.scenario.principal).toBe(497_000);
    expect(result.scenario.monthlyPayment).toBeCloseTo(2356.8302, 4);
    expect(Math.round(result.scenario.monthlyPayment)).toBe(2357);
    expect(result.scenario.monthlyIncome).toBe(10_000);
    expect(formatPercentValue(result.scenario.paymentToIncomePercent)).toBe(
      "23.6%",
    );
    expect(result.scenario.priceToAnnualIncome.toFixed(2)).toBe("5.92");
  });

  test("sensitivity uses the same principal and term at 2–6%", () => {
    const result = computeFinancingScenario(SCENARIO);
    expect(result.ok).toBe(true);
    if (!result.ok) return;

    expect(result.scenario.sensitivity.map((row) => row.ratePercent)).toEqual([
      ...SENSITIVITY_RATES,
    ]);
    expect(
      result.scenario.sensitivity.map((row) =>
        row.monthlyPayment === null ? null : Math.round(row.monthlyPayment),
      ),
    ).toEqual([2107, 2357, 2623, 2905, 3202]);
  });

  test("a zero interest rate uses principal ÷ months, not a division by zero", () => {
    const result = computeFinancingScenario({
      ...SCENARIO,
      annualRatePercent: 0,
    });
    expect(result.ok).toBe(true);
    if (!result.ok) return;

    expect(result.scenario.monthlyPayment).toBeCloseTo(497_000 / 300, 9);
    expect(Math.round(result.scenario.monthlyPayment)).toBe(1657);
    expect(Number.isFinite(result.scenario.monthlyPayment)).toBe(true);
  });

  test("monthlyPayment rejects a non-positive principal or term", () => {
    expect(monthlyPayment(0, 3, 25)).toBeNull();
    expect(monthlyPayment(-1000, 3, 25)).toBeNull();
    expect(monthlyPayment(1000, 3, 0)).toBeNull();
    expect(monthlyPayment(1000, -1, 25)).toBeNull();
  });

  test("a tiny interest rate stays finite and approaches principal ÷ months", () => {
    const principal = 497_000;
    const months = 300;
    const unitPayment = principal / months;
    const payments = [1e-14, 1e-9, 1e-6].map((annualRatePercent) => {
      const payment = monthlyPayment(principal, annualRatePercent, 25);
      expect(payment).not.toBeNull();
      expect(Number.isFinite(payment as number)).toBe(true);
      return payment as number;
    });

    for (const payment of payments) {
      // Any positive rate costs a little more than the zero-rate payment, and
      // at these rates the difference is far below a cent.
      expect(payment).toBeGreaterThanOrEqual(unitPayment);
      expect(Math.abs(payment / unitPayment - 1)).toBeLessThan(1e-6);
    }
    // Raising the rate never lowers the payment.
    expect(payments[0]).toBeLessThanOrEqual(payments[1]);
    expect(payments[1]).toBeLessThanOrEqual(payments[2]);
  });

  test("a scenario with a tiny interest rate returns finite fields", () => {
    for (const annualRatePercent of [1e-14, 1e-9, 1e-6]) {
      const result = computeFinancingScenario({
        ...SCENARIO,
        annualRatePercent,
      });
      expect(result.ok).toBe(true);
      if (!result.ok) return;

      expect(Number.isFinite(result.scenario.monthlyPayment)).toBe(true);
      expect(Number.isFinite(result.scenario.paymentToIncomePercent)).toBe(
        true,
      );
      // A positive rate costs more than the zero-rate payment, but at these
      // rates the difference is well under a thousandth of a percent.
      expect(
        Math.abs(result.scenario.monthlyPayment / (497_000 / 300) - 1),
      ).toBeLessThan(1e-6);
      for (const row of result.scenario.sensitivity) {
        expect(Number.isFinite(row.monthlyPayment as number)).toBe(true);
      }
    }
  });

  test("a 100% down payment is a valid cash purchase, not an invalid price", () => {
    const result = computeFinancingScenario({
      ...SCENARIO,
      downPaymentPercent: 100,
    });
    expect(result.ok).toBe(true);
    if (!result.ok) return;

    expect(result.scenario.downPaymentAmount).toBe(710_000);
    expect(result.scenario.principal).toBe(0);
    expect(result.scenario.monthlyPayment).toBe(0);
    expect(result.scenario.monthlyIncome).toBe(10_000);
    expect(result.scenario.paymentToIncomePercent).toBe(0);
    expect(result.scenario.priceToAnnualIncome).toBeCloseTo(
      710_000 / 120_000,
      12,
    );
    expect(result.scenario.totalMonths).toBe(300);
    // No loan means no principal-and-interest at any rate.
    expect(
      result.scenario.sensitivity.map((row) => row.monthlyPayment),
    ).toEqual([0, 0, 0, 0, 0]);
  });

  test("a 100% down payment never names a valid price as invalid", () => {
    const result = computeFinancingScenario({
      ...SCENARIO,
      downPaymentPercent: 100,
    });
    expect(result.ok).toBe(true);
    if (result.ok) return;
    expect(result.invalidFields).not.toContain("price");
  });

  test("a cash purchase of a fractional price has an exactly zero principal", () => {
    const result = computeFinancingScenario({
      ...SCENARIO,
      price: 0.1,
      downPaymentPercent: 100,
    });
    expect(result.ok).toBe(true);
    if (!result.ok) return;

    expect(result.scenario.principal).toBe(0);
    expect(result.scenario.monthlyPayment).toBe(0);
  });

  test("a derived value that overflows fails closed and names its input", () => {
    // A finite, positive income can still be too small to carry the
    // payment/income ratio inside the double range; the module withholds every
    // output instead of returning Infinity.
    const result = computeFinancingScenario({
      ...SCENARIO,
      price: 1,
      annualIncome: 5e-324,
      downPaymentPercent: 0,
      annualRatePercent: 0,
    });
    expect(result.ok).toBe(false);
    if (result.ok) return;
    expect(result.invalidFields).toEqual(["annualIncome"]);
  });
});

/** Every numeric field of a returned scenario must be a finite number. */
function expectFiniteScenario(scenario: FinancingScenario): void {
  for (const [key, value] of Object.entries(scenario)) {
    if (key === "sensitivity") continue;
    expect(Number.isFinite(value as number)).toBe(true);
  }
  expect(scenario.sensitivity.length).toBe(SENSITIVITY_RATES.length);
  for (const row of scenario.sensitivity) {
    expect(Number.isFinite(row.ratePercent)).toBe(true);
    expect(row.monthlyPayment).not.toBeNull();
    expect(Number.isFinite(row.monthlyPayment as number)).toBe(true);
  }
}

describe("no accepted input produces a non-finite output", () => {
  const prices = [0.01, 1, 1_000, 710_000, 1e12];
  const incomes = [1e-300, 1, 5_000, 120_000, 1e300];
  const downs = [0, 0.5, 30, 99.9, 100];
  const terms = [1, 25, 50];
  const rates = [0, 1e-14, 1e-9, 1e-6, 3, 20];
  const fields: Array<keyof FinancingInputs> = [
    "price",
    "annualIncome",
    "downPaymentPercent",
    "termYears",
    "annualRatePercent",
  ];

  test("every in-bounds combination returns finite numbers or names a field", () => {
    let accepted = 0;
    for (const price of prices) {
      for (const annualIncome of incomes) {
        for (const downPaymentPercent of downs) {
          for (const termYears of terms) {
            for (const annualRatePercent of rates) {
              const result = computeFinancingScenario({
                price,
                annualIncome,
                downPaymentPercent,
                termYears,
                annualRatePercent,
              });

              if (result.ok) {
                accepted += 1;
                expectFiniteScenario(result.scenario);
              } else {
                // Fail closed, never silently substitute a value.
                expect(result.invalidFields.length).toBeGreaterThan(0);
                for (const field of result.invalidFields) {
                  expect(fields).toContain(field);
                }
              }
            }
          }
        }
      }
    }
    // The grid is mostly ordinary, so the success path is genuinely exercised.
    expect(accepted).toBeGreaterThan(500);
  });
});

describe("invalid inputs withhold every output", () => {
  const invalidCases: Array<{
    name: string;
    patch: Partial<FinancingInputs>;
    field: string;
  }> = [
    {
      name: "blank income",
      patch: { annualIncome: null },
      field: "annualIncome",
    },
    { name: "zero income", patch: { annualIncome: 0 }, field: "annualIncome" },
    { name: "blank price", patch: { price: null }, field: "price" },
    { name: "zero price", patch: { price: 0 }, field: "price" },
    {
      name: "down payment above 100%",
      patch: { downPaymentPercent: 101 },
      field: "downPaymentPercent",
    },
    {
      name: "negative down payment",
      patch: { downPaymentPercent: -1 },
      field: "downPaymentPercent",
    },
    { name: "zero term", patch: { termYears: 0 }, field: "termYears" },
    {
      name: "term beyond the UI bound",
      patch: { termYears: 51 },
      field: "termYears",
    },
    {
      name: "non-numeric ratio parse",
      patch: { annualRatePercent: Number.NaN },
      field: "annualRatePercent",
    },
    {
      name: "negative rate",
      patch: { annualRatePercent: -0.5 },
      field: "annualRatePercent",
    },
  ];

  for (const invalidCase of invalidCases) {
    test(invalidCase.name, () => {
      const result = computeFinancingScenario({
        ...SCENARIO,
        ...invalidCase.patch,
      });
      expect(result.ok).toBe(false);
      if (result.ok) return;
      expect(result.invalidFields).toContain(invalidCase.field);
      expect(invalidFieldReason(result.invalidFields[0])).not.toBe("");
    });
  }

  test("all invalid fields are named, not just the first", () => {
    const result = computeFinancingScenario({
      price: null,
      annualIncome: 0,
      downPaymentPercent: 50,
      termYears: 25,
      annualRatePercent: 3,
    });
    expect(result.ok).toBe(false);
    if (result.ok) return;
    expect(result.invalidFields).toEqual(["price", "annualIncome"]);
  });
});

describe("display formatting", () => {
  test("missing values stay N/A and a real zero is a number", () => {
    expect(formatSgd(null)).toBe("N/A");
    expect(formatSgd(undefined)).toBe("N/A");
    expect(formatSgd(0)).toBe("S$0");
    expect(formatSgd(2_356.8302, 1)).toBe("S$2,356.8");
  });

  test("signed lease statistics always state their sign", () => {
    expect(formatSignedPercent(19.1)).toBe("+19.1%");
    expect(formatSignedPercent(-11.02)).toBe("-11.0%");
    expect(formatSignedPercent(null)).toBe("N/A");
  });
});
