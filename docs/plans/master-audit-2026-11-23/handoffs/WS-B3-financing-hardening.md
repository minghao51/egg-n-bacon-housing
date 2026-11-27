# WS-B3 — Financing boundary hardening (UI-4)

**Severity:** MEDIUM (2×3 = 6). **Effort:** S. **Wave:** 0.

## Problem

`app/src/components/tools/lib/tool-amortization.ts` accepts inputs its own arithmetic then contradicts:

- `:37` allows `downPaymentPercent` up to 100 %.
- `:156` computes `principal = price - downPaymentAmount`, which is 0 at 100 %.
- `:92-94` `monthlyPayment` correctly returns `null` for a non-positive principal.
- `:161-163` maps that `null` to `{ok:false, invalidFields:["price"]}` — blaming the price, which was valid.
- `:96` uses `(principal * r) / (1 - Math.pow(1 + r, -months))`, which cancels when `1 + r` rounds to 1; a tiny positive rate yields `Infinity`.

Reproduced (`../evidence/financing-poc.log`, default S$710,000 scenario):

```
{"downPaymentPercent":100} -> {"ok":false,"invalidFields":["price"]}
{"annualRatePercent":1e-14} -> {"ok":true, monthlyPayment:"Infinity", paymentToIncomePercent:"Infinity"}
```

## Required change

1. Handle the zero-principal case explicitly: a cash purchase is a valid scenario with `monthlyPayment = 0`, not a validation failure, **or** reject 100 % down with an explicit `downPaymentPercent` reason. Choose one, document it in the module header, and keep the UI copy consistent. Do not report `price` as invalid when the price is valid.
2. Use a numerically stable form for the payment (`log1p`/`expm1`), e.g. `principal * r / -expm1(-months * log1p(r))`, with the zero-rate branch preserved.
3. Reject non-finite derived outputs after computing them (defence in depth): if `monthlyPayment`, `paymentToIncomePercent` or `principal` is not finite, fail closed with the offending field named.
4. Keep the module's stated contract: pure, no DOM/fetch/URL, unrounded values, blank/invalid input withholds every output and names the field.
5. Do not add eligibility, CPF/MSR/TDSR or recommendation semantics — the tool is illustrative arithmetic by contract (`app/src/components/tools/ToolsSurface.astro:160`).

## Tests (`app/tests/unit/tool-amortization.test.ts`)

- 100 % down: whichever contract you chose, assert the exact result and the named field.
- `annualRatePercent` values `1e-14`, `1e-9`, `1e-6`: finite outputs, and the payment approaches `principal / months`.
- Property test: for all in-bounds inputs, every returned numeric field is finite.
- Existing default-scenario and zero-rate cases stay green.

## Verification

```bash
cd app && PATH="$HOME/.bun/bin:$PATH" bun run test:unit
cd app && PATH="$HOME/.bun/bin:$PATH" bun run astro check
```

## Owns

`app/src/components/tools/lib/tool-amortization.ts`, `app/tests/unit/tool-amortization.test.ts`, and the financing copy in `app/src/components/tools/` only if the chosen contract changes user-visible text.

## Do not touch

Other tools, release loaders, workflows, Python.

## Done when

No accepted input can produce a non-finite output, a valid price is never blamed for an invalid principal, and the frontend gate is green.
