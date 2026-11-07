/**
 * Financing draft state for the decision-tools workspace (S8-F1).
 *
 * The five inputs used to live in `FinancingScenario`, so selecting another
 * tool unmounted the component and reset them. They now live in
 * `ToolsWorkspace`, which stays mounted across tabs, and this module holds the
 * pure part: the draft shape, the documented defaults, an immutable merge and
 * the "apply the reference price only when the reference actually changed"
 * rule.
 *
 * Privacy invariant: the draft is ordinary React memory inside the island. It
 * is never serialised to the URL, storage, telemetry or the console, and a
 * reload starts again from the defaults.
 */

import { referenceKey, type ReferencePriceEntry } from "./tool-reference";

/** The five editable financing inputs, kept as the raw input strings. */
export interface FinancingDraft {
  priceText: string;
  incomeText: string;
  downText: string;
  termText: string;
  rateText: string;
}

export const FINANCING_DRAFT_FIELDS = [
  "priceText",
  "incomeText",
  "downText",
  "termText",
  "rateText",
] as const satisfies readonly (keyof FinancingDraft)[];

/**
 * Documented defaults for the four hypothetical assumptions. The price starts
 * empty only when no observed reference exists; otherwise it is the named
 * reference median (see {@link createFinancingDraftState}).
 */
export const FINANCING_DEFAULT_DRAFT: FinancingDraft = {
  priceText: "",
  incomeText: "120000",
  downText: "30",
  termText: "25",
  rateText: "3.0",
};

/** The price input value an entry imports; `null` entry means no import. */
export function priceTextFor(entry: ReferencePriceEntry | null): string {
  return entry === null ? "" : String(entry.medianPrice);
}

/**
 * Immutable partial merge. Only string patch values are applied, so an
 * explicit `undefined` from a caller can never blank a field, and a blank
 * string stays blank (the tool withholds output rather than guessing).
 */
export function mergeDraft(
  draft: FinancingDraft,
  patch: Partial<FinancingDraft>,
): FinancingDraft {
  const next: FinancingDraft = { ...draft };
  for (const field of FINANCING_DRAFT_FIELDS) {
    const value = patch[field];
    if (typeof value === "string") next[field] = value;
  }
  return next;
}

export interface FinancingDraftState {
  draft: FinancingDraft;
  /** Reference key whose published median is currently in `draft.priceText`. */
  appliedReferenceKey: string;
}

/** Fresh state: defaults plus the resolved reference price. */
export function createFinancingDraftState(
  entry: ReferencePriceEntry | null,
): FinancingDraftState {
  return {
    draft: { ...FINANCING_DEFAULT_DRAFT, priceText: priceTextFor(entry) },
    appliedReferenceKey: referenceKey(entry),
  };
}

/**
 * Apply an imported price only when the resolved reference key changed.
 *
 * Returns the *same* state object otherwise, which both documents the intent
 * and lets React bail out. This is what keeps a manual price manual: switching
 * tools and coming back resolves to the same key, so nothing is re-imported,
 * while a deep link or a back/forward to a different area does change the key
 * and imports the new observed median.
 */
export function applyReferenceToDraft(
  state: FinancingDraftState,
  entry: ReferencePriceEntry | null,
): FinancingDraftState {
  const key = referenceKey(entry);
  if (key === state.appliedReferenceKey) return state;
  return {
    draft: mergeDraft(state.draft, { priceText: priceTextFor(entry) }),
    appliedReferenceKey: key,
  };
}
