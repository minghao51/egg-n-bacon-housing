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
