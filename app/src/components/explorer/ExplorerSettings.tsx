/**
 * Settings rail for the `/explore` observed-comparison workspace.
 *
 * Property type, period and sample size only. Every control is a real radio
 * group with a visible fieldset legend, so the labels, grouping and keyboard
 * behaviour (arrow keys within a group) are native. The value shown in the list
 * is chosen by the sort control in the list header, not here.
 */

import type { ReactNode } from "react";
import {
  THIN_SAMPLE_THRESHOLD,
  type ExplorerMetric,
  type ExplorerPeriod,
  type ExplorerProperty,
  type ExplorerSelection,
} from "@/utils/explorer-selection";
import { ERA_DEFINITIONS } from "@/utils/observed-data";

export interface ExplorerOption<T extends string> {
  value: T;
  label: string;
}

export const PROPERTY_OPTIONS: readonly ExplorerOption<ExplorerProperty>[] = [
  { value: "all", label: "All" },
  { value: "hdb", label: "HDB" },
  { value: "ec", label: "EC" },
  { value: "condo", label: "Condo" },
];

/**
 * Period options reuse the literal era labels and boundaries the exporter
 * writes (`ERA_DEFINITIONS`), so the control cannot drift from the published
 * `map_metrics[period_property]` sections.
 */
export const PERIOD_OPTIONS: readonly ExplorerOption<ExplorerPeriod>[] =
  ERA_DEFINITIONS.map((definition) => ({
    value: definition.id,
    label: definition.label,
  }));

export interface MetricOption extends ExplorerOption<ExplorerMetric> {
  /** Sentence noun, e.g. "median transaction price". */
  noun: string;
}

export const METRIC_OPTIONS: readonly MetricOption[] = [
  {
    value: "median_price",
    label: "Median transaction price",
    noun: "median transaction price",
  },
  {
    value: "median_psf",
    label: "Median price per square foot",
    noun: "median price per square foot",
  },
  {
    value: "volume",
    label: "Transaction volume",
    noun: "transaction volume",
  },
];

/** Display label for a property type inside prose, e.g. "HDB" or "all types". */
export function propertyNoun(property: ExplorerProperty): string {
  if (property === "all") return "all property types";
  const option = PROPERTY_OPTIONS.find((entry) => entry.value === property);
  return option === undefined ? property : option.label;
}

export function periodLabel(period: ExplorerPeriod): string {
  const option = PERIOD_OPTIONS.find((entry) => entry.value === period);
  return option === undefined ? period : option.label;
}

export function metricNoun(metric: ExplorerMetric): string {
  const option = METRIC_OPTIONS.find((entry) => entry.value === metric);
  return option === undefined ? metric : option.noun;
}

interface ChoiceProps {
  /** Radio group name — every option of one fieldset shares it. */
  name: string;
  value: string;
  checked: boolean;
  onSelect: () => void;
  className?: string;
  children: ReactNode;
}

/**
 * One radio rendered as a selectable chip.
 *
 * The input itself is stretched over the chip instead of being visually hidden,
 * so the page-wide teal `:focus-visible` ring has a real boundary to draw and
 * the click target is the whole chip.
 */
function Choice({
  name,
  value,
  checked,
  onSelect,
  className = "",
  children,
}: ChoiceProps) {
  return (
    <label
      className={`relative flex cursor-pointer items-stretch ${className}`}
    >
      <input
        type="radio"
        name={name}
        value={value}
        checked={checked}
        onChange={onSelect}
        className="peer absolute inset-0 m-0 h-full w-full cursor-pointer appearance-none rounded border border-input bg-card checked:border-[hsl(var(--teal))] checked:bg-accent"
      />
      <span className="pointer-events-none relative flex w-full items-center justify-center px-3 py-2 text-sm font-medium text-foreground peer-checked:font-bold peer-checked:text-[hsl(var(--teal))]">
        {children}
      </span>
    </label>
  );
}

export interface ExplorerSettingsProps {
  selection: ExplorerSelection;
  summary: { shown: number; total: number; thin: number };
  onChange: (patch: Partial<ExplorerSelection>) => void;
  onReset: () => void;
}

export default function ExplorerSettings({
  selection,
  summary,
  onChange,
  onReset,
}: ExplorerSettingsProps) {
  const atLeast = selection.minSales ?? THIN_SAMPLE_THRESHOLD;

  return (
    <section
      aria-labelledby="explorer-settings-heading"
      className="rounded-lg border border-border bg-card p-5"
    >
      <h2
        id="explorer-settings-heading"
        className="text-lg font-bold text-foreground"
      >
        Comparison settings
      </h2>

      <fieldset className="mt-5">
        <legend className="text-sm font-bold text-foreground">
          Property type
        </legend>
        <div className="mt-2 flex flex-wrap gap-2">
          {PROPERTY_OPTIONS.map((option) => (
            <Choice
              key={option.value}
              name="explorer-property"
              value={option.value}
              checked={selection.property === option.value}
              onSelect={() => onChange({ property: option.value })}
              className="min-w-[3.5rem] flex-1"
            >
              {option.label}
            </Choice>
          ))}
        </div>
      </fieldset>

      <fieldset className="mt-6">
        <legend className="text-sm font-bold text-foreground">Period</legend>
        <div className="mt-2 flex flex-col gap-2">
          {PERIOD_OPTIONS.map((option) => (
            <Choice
              key={option.value}
              name="explorer-period"
              value={option.value}
              checked={selection.period === option.value}
              onSelect={() => onChange({ period: option.value })}
            >
              {option.label}
            </Choice>
          ))}
        </div>
      </fieldset>

      <fieldset className="mt-6">
        <legend className="text-sm font-bold text-foreground">
          Sample size
        </legend>
        <div className="mt-2 flex flex-col gap-2">
          <Choice
            name="explorer-min-sales"
            value="threshold"
            checked={selection.minSales !== null}
            onSelect={() => onChange({ minSales: THIN_SAMPLE_THRESHOLD })}
          >
            At least {atLeast} sales
          </Choice>
          <Choice
            name="explorer-min-sales"
            value="all"
            checked={selection.minSales === null}
            onSelect={() => onChange({ minSales: null })}
          >
            Show thin samples
          </Choice>
        </div>
        <p className="mt-3 text-xs text-muted-foreground">
          The {THIN_SAMPLE_THRESHOLD}-sale rule is a caution threshold chosen
          for this view, not a significance test. It applies to the selected
          period and property type, so the same area can be hidden in one
          comparison and shown in another.
        </p>
      </fieldset>

      <p className="mt-4 text-sm text-muted-foreground" role="status">
        {summary.shown} of {summary.total} areas shown.
        {summary.thin > 0
          ? ` ${summary.thin} ${summary.thin === 1 ? "area is" : "areas are"} below the ${THIN_SAMPLE_THRESHOLD}-sale threshold.`
          : null}
      </p>

      <div className="mt-6 border-t border-border pt-4 text-xs text-muted-foreground">
        <p>Price is per transaction, not an asking price or a valuation.</p>
        <p className="mt-2">
          PSF adjusts for floor area. It does not adjust for age, remaining
          lease or location.
        </p>
      </div>

      <button
        type="button"
        onClick={onReset}
        className="mt-4 text-sm font-bold text-[hsl(var(--teal))] underline underline-offset-4 hover:no-underline"
      >
        Reset settings
      </button>
    </section>
  );
}
