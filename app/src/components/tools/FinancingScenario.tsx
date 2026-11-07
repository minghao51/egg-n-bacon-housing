/**
 * Financing scenario tool (slice S8).
 *
 * Explicit hypothetical inputs plus ordinary amortization. Output copy is
 * withheld whenever an input is blank or out of range, and the named reference
 * price is source-bound to one joint 2025 section of `map_metrics` (the table is
 * built at build time by `ToolsSurface.astro` through `lib/tool-reference.ts`).
 *
 * Nothing here is an eligibility check, a CPF/MSR/TDSR determination or a loan
 * recommendation. Income never leaves the workspace island's memory: the draft
 * is owned by `ToolsWorkspace` (S8-F1) so it survives a tool switch, and it is
 * never serialised to the URL, storage or telemetry.
 */

import { useMemo } from "react";
import {
  computeFinancingScenario,
  invalidFieldReason,
  FINANCING_LIMITS,
  type FinancingField,
  type FinancingInputs,
} from "./lib/tool-amortization";
import {
  formatMultiple,
  formatPercentValue,
  formatSgd,
} from "./lib/tool-format";
import {
  FINANCING_ILLUSTRATIVE_NOTE,
  FINANCING_LOCAL_NOTE,
  FINANCING_NOT_OFFER_NOTE,
  FINANCING_REFERENCE_NOTE,
} from "./lib/tool-evidence";
import type { FinancingDraft } from "./lib/financing-draft";
import {
  findReferenceEntry,
  referenceAreasFor,
  type ReferencePriceEntry,
  type ReferencePriceTable,
  type ReferenceSourceStatus,
} from "./lib/tool-reference";
import {
  TOOL_PROPERTIES,
  TOOL_PROPERTY_LABELS,
  type ToolProperty,
  type ToolReferenceSelection,
} from "./lib/tool-url-state";
import {
  EvidenceBadge,
  FieldLabel,
  ToolHeading,
  WithheldPanel,
} from "./ToolParts";

export interface ToolsReleaseInfo {
  generation: string;
  /** Published trailing month recorded by `dashboard-release.json`. */
  trailingMonth: string;
  /** Asset paths listed by the release manifest. */
  assets: string[];
}

interface FinancingScenarioProps {
  baseUrl: string;
  referenceTable: ReferencePriceTable;
  referenceSource: ReferenceSourceStatus;
  release: ToolsReleaseInfo;
  referenceSelection: ToolReferenceSelection | null;
  onReferenceChange: (selection: ToolReferenceSelection | null) => void;
  /** Resolved by the workspace, which also decides when to import its price. */
  referenceEntry: ReferencePriceEntry | null;
  referenceMissing: boolean;
  /** Draft owned by the workspace so it survives a tool switch. */
  draft: FinancingDraft;
  onDraftChange: (patch: Partial<FinancingDraft>) => void;
  onReset: () => void;
}

/** Empty → `null`; anything non-numeric → `NaN` (which every bound rejects). */
function parseNumber(text: string): number | null {
  const trimmed = text.trim().replace(/,/g, "");
  if (trimmed === "") return null;
  const value = Number(trimmed);
  return Number.isFinite(value) ? value : Number.NaN;
}

export default function FinancingScenario({
  baseUrl,
  referenceTable,
  referenceSource,
  release,
  referenceSelection,
  onReferenceChange,
  referenceEntry: entry,
  referenceMissing: missingRequested,
  draft,
  onDraftChange,
  onReset,
}: FinancingScenarioProps) {
  const { priceText, incomeText, downText, termText, rateText } = draft;

  const inputs: FinancingInputs = useMemo(
    () => ({
      price: parseNumber(draft.priceText),
      annualIncome: parseNumber(draft.incomeText),
      downPaymentPercent: parseNumber(draft.downText),
      termYears: parseNumber(draft.termText),
      annualRatePercent: parseNumber(draft.rateText),
    }),
    [draft],
  );

  const result = useMemo(() => computeFinancingScenario(inputs), [inputs]);

  const invalidFields = result.ok ? [] : result.invalidFields;
  const isInvalid = (field: FinancingField) => invalidFields.includes(field);
  const fieldErrorId = (field: FinancingField) => `financing-${field}-error`;

  const priceApplied =
    entry !== null &&
    inputs.price !== null &&
    Number.isFinite(inputs.price) &&
    inputs.price === entry.medianPrice;

  const currentProperty: ToolProperty =
    referenceSelection?.property ?? entry?.property ?? "hdb";
  const propertyAreas = useMemo(
    () => referenceAreasFor(referenceTable, currentProperty),
    [referenceTable, currentProperty],
  );
  const currentAreaId = entry?.areaId ?? "";

  const selectProperty = (property: ToolProperty) => {
    const keepArea = findReferenceEntry(
      referenceTable,
      currentAreaId,
      property,
    );
    const next = keepArea ?? referenceAreasFor(referenceTable, property)[0];
    if (next === undefined) return;
    onReferenceChange({ area: next.areaId, property });
  };

  const selectArea = (areaId: string) => {
    onReferenceChange({ area: areaId, property: currentProperty });
  };

  // The workspace owns the draft, so a reset also resets the defaults there and
  // cannot race the reference import.
  const resetScenario = () => onReset();

  const generationLabel =
    release.generation.length > 12
      ? `${release.generation.slice(0, 12)}\u2026`
      : release.generation;

  return (
    <section aria-labelledby="financing-heading" className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <ToolHeading
          id="financing-heading"
          title="Financing scenario"
          subtitle="Explicit hypothetical assumptions, standard amortization, and the same principal across every sensitivity row."
        />
        <button
          type="button"
          onClick={resetScenario}
          className="rounded border border-input px-3 py-2 text-sm font-bold text-foreground transition-colors hover:bg-muted"
        >
          Reset scenario
        </button>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <EvidenceBadge>Illustrative arithmetic</EvidenceBadge>
        <p className="max-w-2xl text-sm text-muted-foreground">
          {FINANCING_ILLUSTRATIVE_NOTE}
        </p>
      </div>

      <div className="rounded-xl border border-border bg-card p-4 sm:p-5">
        <h3 className="text-sm font-bold uppercase tracking-wider text-muted-foreground">
          Reference price import
        </h3>
        <div className="mt-3 grid gap-4 sm:grid-cols-2 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto] lg:items-end">
          <div>
            <FieldLabel htmlFor="reference-property" label="Property type" />
            <select
              id="reference-property"
              value={currentProperty}
              onChange={(event) =>
                selectProperty(event.target.value as ToolProperty)
              }
              className="mt-1 w-full rounded border border-input bg-background px-3 py-2 text-sm text-foreground"
            >
              {TOOL_PROPERTIES.map((property) => (
                <option key={property} value={property}>
                  {TOOL_PROPERTY_LABELS[property]}
                </option>
              ))}
            </select>
          </div>
          <div>
            <FieldLabel htmlFor="reference-area" label="Planning area" />
            <select
              id="reference-area"
              value={currentAreaId}
              onChange={(event) => selectArea(event.target.value)}
              className="mt-1 w-full rounded border border-input bg-background px-3 py-2 text-sm text-foreground"
            >
              {propertyAreas.map((area) => (
                <option key={area.areaId} value={area.areaId}>
                  {area.areaName}
                </option>
              ))}
            </select>
          </div>
          <button
            type="button"
            onClick={() => {
              if (entry !== null)
                onDraftChange({ priceText: String(entry.medianPrice) });
            }}
            disabled={entry === null}
            className="rounded border border-input px-3 py-2 text-sm font-bold text-foreground transition-colors hover:bg-muted disabled:cursor-not-allowed disabled:opacity-50"
          >
            Import observed 2025 median
          </button>
        </div>

        {missingRequested && referenceSelection !== null ? (
          <p
            role="status"
            className="mt-3 rounded border border-border bg-muted/30 p-3 text-sm text-foreground"
          >
            The linked reference ({referenceSelection.area}{" "}
            {TOOL_PROPERTY_LABELS[referenceSelection.property]}) is not
            published in this snapshot, so the documented default is shown
            instead. No value is substituted for the missing combination.
          </p>
        ) : null}

        <p
          id="financing-reference-status"
          className="mt-3 text-sm text-muted-foreground"
        >
          {referenceSource === "unavailable" ? (
            <>
              The published reference table could not be read, so no observed
              2025 reference price is available. Enter a hypothetical price
              instead; the financing arithmetic still runs on your inputs.
            </>
          ) : entry === null ? (
            <>
              No 2025 observation is published for the selected planning area
              and property type, so there is no reference price to import. Enter
              a hypothetical price instead.
            </>
          ) : priceApplied ? (
            <>
              Imported from{" "}
              <code className="font-mono">map_metrics.{entry.section}</code>{" "}
              &middot; {entry.areaName} &middot; observed median{" "}
              {formatSgd(entry.medianPrice)}
              {entry.volume === null
                ? " · sales count not available"
                : ` · ${entry.volume.toLocaleString("en-SG")} sales`}{" "}
              &middot; release {generationLabel} (published through{" "}
              {release.trailingMonth}).
            </>
          ) : (
            <>
              Price entered manually &mdash; the named reference{" "}
              {entry.areaName} {TOOL_PROPERTY_LABELS[entry.property]} (
              {formatSgd(entry.medianPrice)}) is no longer applied. Select{" "}
              <em>Import observed 2025 median</em> to use it again.
            </>
          )}
        </p>
        <p className="mt-2 text-xs text-muted-foreground">
          {FINANCING_REFERENCE_NOTE}
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <div>
          <FieldLabel htmlFor="financing-price" label="Price" unit="SGD" />
          <input
            id="financing-price"
            type="text"
            inputMode="decimal"
            autoComplete="off"
            value={priceText}
            onChange={(event) =>
              onDraftChange({ priceText: event.target.value })
            }
            aria-invalid={isInvalid("price")}
            aria-describedby={
              isInvalid("price") ? fieldErrorId("price") : undefined
            }
            className="mt-1 w-full rounded border border-input bg-background px-3 py-2 text-sm text-foreground"
          />
          <p className="mt-1 text-xs text-muted-foreground">
            Observed 2025 median or a hypothetical price. Valid when greater
            than 0.
          </p>
          {isInvalid("price") ? (
            <p
              id={fieldErrorId("price")}
              className="mt-1 text-xs text-red-700 dark:text-red-300"
            >
              {invalidFieldReason("price")}
            </p>
          ) : null}
        </div>

        <div>
          <FieldLabel
            htmlFor="financing-income"
            label="Annual household income"
            unit="SGD"
          />
          <input
            id="financing-income"
            type="text"
            inputMode="decimal"
            autoComplete="off"
            value={incomeText}
            onChange={(event) =>
              onDraftChange({ incomeText: event.target.value })
            }
            aria-invalid={isInvalid("annualIncome")}
            aria-describedby={
              isInvalid("annualIncome")
                ? fieldErrorId("annualIncome")
                : undefined
            }
            className="mt-1 w-full rounded border border-input bg-background px-3 py-2 text-sm text-foreground"
          />
          <p className="mt-1 text-xs text-muted-foreground">
            Illustrative and kept in this tab. Valid when greater than 0.
          </p>
          {isInvalid("annualIncome") ? (
            <p
              id={fieldErrorId("annualIncome")}
              className="mt-1 text-xs text-red-700 dark:text-red-300"
            >
              {invalidFieldReason("annualIncome")}
            </p>
          ) : null}
        </div>

        <div>
          <FieldLabel
            htmlFor="financing-down"
            label="Down payment"
            unit="percent"
          />
          <input
            id="financing-down"
            type="text"
            inputMode="decimal"
            autoComplete="off"
            value={downText}
            onChange={(event) =>
              onDraftChange({ downText: event.target.value })
            }
            aria-invalid={isInvalid("downPaymentPercent")}
            aria-describedby={
              isInvalid("downPaymentPercent")
                ? fieldErrorId("downPaymentPercent")
                : undefined
            }
            className="mt-1 w-full rounded border border-input bg-background px-3 py-2 text-sm text-foreground"
          />
          <p className="mt-1 text-xs text-muted-foreground">
            {FINANCING_LIMITS.downPaymentPercent.min}&ndash;
            {FINANCING_LIMITS.downPaymentPercent.max}% of the price.
          </p>
          {isInvalid("downPaymentPercent") ? (
            <p
              id={fieldErrorId("downPaymentPercent")}
              className="mt-1 text-xs text-red-700 dark:text-red-300"
            >
              {invalidFieldReason("downPaymentPercent")}
            </p>
          ) : null}
        </div>

        <div>
          <FieldLabel htmlFor="financing-term" label="Loan term" unit="years" />
          <input
            id="financing-term"
            type="text"
            inputMode="numeric"
            autoComplete="off"
            value={termText}
            onChange={(event) =>
              onDraftChange({ termText: event.target.value })
            }
            aria-invalid={isInvalid("termYears")}
            aria-describedby={
              isInvalid("termYears") ? fieldErrorId("termYears") : undefined
            }
            className="mt-1 w-full rounded border border-input bg-background px-3 py-2 text-sm text-foreground"
          />
          <p className="mt-1 text-xs text-muted-foreground">
            {FINANCING_LIMITS.termYears.min}&ndash;
            {FINANCING_LIMITS.termYears.max} years. A UI bound, not a lender
            limit.
          </p>
          {isInvalid("termYears") ? (
            <p
              id={fieldErrorId("termYears")}
              className="mt-1 text-xs text-red-700 dark:text-red-300"
            >
              {invalidFieldReason("termYears")}
            </p>
          ) : null}
        </div>

        <div>
          <FieldLabel
            htmlFor="financing-rate"
            label="Annual interest rate"
            unit="percent"
          />
          <input
            id="financing-rate"
            type="text"
            inputMode="decimal"
            autoComplete="off"
            value={rateText}
            onChange={(event) =>
              onDraftChange({ rateText: event.target.value })
            }
            aria-invalid={isInvalid("annualRatePercent")}
            aria-describedby={
              isInvalid("annualRatePercent")
                ? fieldErrorId("annualRatePercent")
                : undefined
            }
            className="mt-1 w-full rounded border border-input bg-background px-3 py-2 text-sm text-foreground"
          />
          <p className="mt-1 text-xs text-muted-foreground">
            Nominal annual rate; 0% is allowed and uses principal &divide;
            months.
          </p>
          {isInvalid("annualRatePercent") ? (
            <p
              id={fieldErrorId("annualRatePercent")}
              className="mt-1 text-xs text-red-700 dark:text-red-300"
            >
              {invalidFieldReason("annualRatePercent")}
            </p>
          ) : null}
        </div>
      </div>

      {result.ok ? (
        <>
          <div className="rounded-2xl border border-border bg-card p-5 sm:p-6">
            <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
              Illustrative principal + interest
            </p>
            <p className="mt-2 text-4xl font-bold text-foreground">
              {formatSgd(Math.round(result.scenario.monthlyPayment))}
              <span className="ml-2 text-base font-normal text-muted-foreground">
                / month
              </span>
            </p>
            <dl className="mt-5 grid gap-4 text-sm sm:grid-cols-2 lg:grid-cols-4">
              <div>
                <dt className="text-muted-foreground">Down payment</dt>
                <dd className="font-bold text-foreground">
                  {formatSgd(Math.round(result.scenario.downPaymentAmount))}
                </dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Loan principal</dt>
                <dd className="font-bold text-foreground">
                  {formatSgd(Math.round(result.scenario.principal))}
                </dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Monthly income</dt>
                <dd className="font-bold text-foreground">
                  {formatSgd(Math.round(result.scenario.monthlyIncome))}
                </dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Payment / income</dt>
                <dd className="font-bold text-foreground">
                  {formatPercentValue(result.scenario.paymentToIncomePercent)}
                </dd>
              </div>
            </dl>
            <p className="mt-4 text-sm text-muted-foreground">
              Price / annual income:{" "}
              <span className="font-bold text-foreground">
                {formatMultiple(result.scenario.priceToAnnualIncome)}
              </span>
            </p>
          </div>

          <div className="rounded-xl border border-border bg-card p-4 sm:p-5">
            <h3 className="text-sm font-bold uppercase tracking-wider text-muted-foreground">
              Interest-rate sensitivity
            </h3>
            <p className="mt-1 text-sm text-muted-foreground">
              Monthly payment with the same principal and{" "}
              {result.scenario.totalMonths / 12}
              -year term. Rounded to the nearest dollar.
            </p>
            <div className="mt-3 overflow-x-auto">
              <table className="w-full min-w-[320px] border-collapse text-sm">
                <caption className="sr-only">
                  Monthly payment by annual interest rate, same principal and
                  term
                </caption>
                <thead>
                  <tr className="border-b border-border text-left">
                    <th
                      scope="col"
                      className="py-2 pr-4 font-bold text-foreground"
                    >
                      Annual rate
                    </th>
                    <th scope="col" className="py-2 font-bold text-foreground">
                      Monthly payment
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {result.scenario.sensitivity.map((row) => (
                    <tr
                      key={row.ratePercent}
                      className="border-b border-border/60"
                    >
                      <th
                        scope="row"
                        className="py-2 pr-4 font-normal text-foreground"
                      >
                        {row.ratePercent}%
                      </th>
                      <td className="py-2 text-foreground">
                        {row.monthlyPayment === null
                          ? "N/A"
                          : formatSgd(Math.round(row.monthlyPayment))}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      ) : (
        <WithheldPanel title="Monthly payment withheld">
          <p>
            The scenario is not shown until every assumption is valid, so an
            incomplete field cannot look like a real payment.
          </p>
          <ul className="list-disc space-y-1 pl-5">
            {invalidFields.map((field) => (
              <li key={field}>
                <span className="font-bold text-foreground">
                  {FINANCING_LIMITS[field].label}:
                </span>{" "}
                {invalidFieldReason(field)}
              </li>
            ))}
          </ul>
        </WithheldPanel>
      )}

      <div className="rounded-xl border border-border bg-muted/20 p-4 text-sm text-muted-foreground">
        <p className="font-bold text-foreground">{FINANCING_NOT_OFFER_NOTE}</p>
        <p className="mt-2">{FINANCING_LOCAL_NOTE}</p>
        <p className="mt-3 flex flex-wrap gap-4">
          <a
            className="font-bold text-foreground underline"
            href={`${baseUrl}explore`}
          >
            Open observed explorer
          </a>
          <a
            className="font-bold text-foreground underline"
            href={`${baseUrl}catalog/`}
          >
            Data catalogue
          </a>
        </p>
      </div>
    </section>
  );
}
