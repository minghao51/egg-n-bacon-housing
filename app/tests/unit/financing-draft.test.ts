/**
 * Unit tests for the S8-F1 financing draft (`lib/financing-draft.ts`) and the
 * shared reference resolution it depends on (`lib/tool-reference.ts`).
 *
 * The behaviour that matters: the five inputs are ordinary local state, the
 * documented defaults are the ones the plan specifies, and a reference import
 * happens on a *reference change*, not on a remount — otherwise lifting the
 * state would silently wipe a manual price every time the tab is revisited.
 */

import { describe, expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import { gunzipSync } from "node:zlib";

import {
  applyReferenceToDraft,
  createFinancingDraftState,
  FINANCING_DEFAULT_DRAFT,
  mergeDraft,
  priceTextFor,
  type FinancingDraft,
} from "../../src/components/tools/lib/financing-draft";
import {
  buildReferencePriceTable,
  findReferenceEntry,
  referenceKey,
  resolveReference,
  type ReferencePriceTable,
} from "../../src/components/tools/lib/tool-reference";

const table: ReferencePriceTable = buildReferencePriceTable(
  JSON.parse(
    gunzipSync(
      readFileSync(
        new URL("../../public/data/map_metrics.json.gz", import.meta.url),
      ),
    ).toString("utf-8"),
  ),
);

const tampines = findReferenceEntry(table, "TAMPINES", "hdb");
const queenstown = findReferenceEntry(table, "QUEENSTOWN", "condo");
if (tampines === null || queenstown === null) {
  throw new Error(
    "published fixture is missing Tampines HDB / Queenstown condo",
  );
}

describe("financing draft defaults", () => {
  test("the documented defaults are the plan's assumptions", () => {
    expect(FINANCING_DEFAULT_DRAFT).toEqual({
      priceText: "",
      incomeText: "120000",
      downText: "30",
      termText: "25",
      rateText: "3.0",
    });
  });

  test("a resolved reference seeds the price and records its key", () => {
    const state = createFinancingDraftState(tampines);
    expect(state.draft.priceText).toBe("710000");
    expect(state.draft.incomeText).toBe("120000");
    expect(state.appliedReferenceKey).toBe("TAMPINES:hdb");
    expect(priceTextFor(null)).toBe("");
  });

  test("no reference at all still yields a usable default draft", () => {
    const state = createFinancingDraftState(null);
    expect(state.draft).toEqual(FINANCING_DEFAULT_DRAFT);
    expect(state.appliedReferenceKey).toBe("none");
  });
});

describe("financing draft merge", () => {
  const base = createFinancingDraftState(tampines).draft;

  test("a partial patch leaves the other fields alone", () => {
    const merged = mergeDraft(base, { incomeText: "137777" });
    expect(merged.incomeText).toBe("137777");
    expect(merged.priceText).toBe(base.priceText);
    expect(merged.downText).toBe(base.downText);
    expect(merged.termText).toBe(base.termText);
    expect(merged.rateText).toBe(base.rateText);
  });

  test("a blank or invalid string is preserved, never repaired", () => {
    const merged = mergeDraft(base, {
      priceText: "",
      termText: "abc",
      rateText: "0",
    });
    expect(merged.priceText).toBe("");
    expect(merged.termText).toBe("abc");
    expect(merged.rateText).toBe("0");
  });

  test("an explicit undefined patch value cannot blank a field", () => {
    const merged = mergeDraft(base, { incomeText: undefined });
    expect(merged.incomeText).toBe("120000");
  });

  test("merge is immutable", () => {
    const before: FinancingDraft = { ...base };
    mergeDraft(base, { priceText: "1", incomeText: "2" });
    expect(base).toEqual(before);
  });
});

describe("reference-key change detection", () => {
  test("keys identify the area and property type", () => {
    expect(referenceKey(tampines)).toBe("TAMPINES:hdb");
    expect(referenceKey(queenstown)).toBe("QUEENSTOWN:condo");
    expect(referenceKey(null)).toBe("none");
  });

  test("the same reference does not re-import, even as a new object", () => {
    const state = createFinancingDraftState(tampines);
    // Same key, different object identity: the guard is the key, not the object.
    expect(applyReferenceToDraft(state, { ...tampines })).toBe(state);
  });

  test("a manual price survives a tool switch (same key, new entry object)", () => {
    const initial = createFinancingDraftState(tampines);
    const edited = {
      ...initial,
      draft: mergeDraft(initial.draft, {
        priceText: "700000",
        incomeText: "137777",
        downText: "25",
        termText: "30",
        rateText: "2.5",
      }),
    };

    // Leaving and returning to the financing tab resolves the same reference.
    const afterSwitch = applyReferenceToDraft(edited, { ...tampines });
    expect(afterSwitch).toBe(edited);
    expect(afterSwitch.draft.priceText).toBe("700000");
    expect(afterSwitch.draft.incomeText).toBe("137777");
    expect(afterSwitch.appliedReferenceKey).toBe("TAMPINES:hdb");
  });

  test("a changed reference imports the new observed median", () => {
    const initial = createFinancingDraftState(tampines);
    const switched = applyReferenceToDraft(initial, queenstown);
    expect(switched.draft.priceText).toBe("2088000");
    expect(switched.appliedReferenceKey).toBe("QUEENSTOWN:condo");
    // The other four inputs are untouched by a reference change.
    expect(switched.draft.incomeText).toBe("120000");
    expect(switched.draft.downText).toBe("30");
  });

  test("a manual price is replaced only when the key actually changes", () => {
    const initial = createFinancingDraftState(tampines);
    const edited = {
      ...initial,
      draft: mergeDraft(initial.draft, { priceText: "700000" }),
    };
    expect(applyReferenceToDraft(edited, tampines).draft.priceText).toBe(
      "700000",
    );
    expect(applyReferenceToDraft(edited, queenstown).draft.priceText).toBe(
      "2088000",
    );
  });

  test("going back to no reference clears the imported price and keys to none", () => {
    const initial = createFinancingDraftState(tampines);
    const withoutReference = applyReferenceToDraft(initial, null);
    expect(withoutReference.draft.priceText).toBe("");
    expect(withoutReference.appliedReferenceKey).toBe("none");
  });
});

describe("reference resolution", () => {
  test("an explicit selection resolves to that entry", () => {
    const resolved = resolveReference(table, {
      area: "QUEENSTOWN",
      property: "condo",
    });
    expect(resolved.entry?.areaId).toBe("QUEENSTOWN");
    expect(resolved.entry?.medianPrice).toBe(2_088_000);
    expect(resolved.missingRequested).toBe(false);
  });

  test("no selection resolves to the documented default", () => {
    const resolved = resolveReference(table, null);
    expect(resolved.entry?.areaId).toBe("TAMPINES");
    expect(resolved.missingRequested).toBe(false);
  });

  test("an unpublished selection falls back and says so", () => {
    const resolved = resolveReference(table, {
      area: "NOT A REAL AREA",
      property: "condo",
    });
    expect(resolved.entry?.areaId).toBe("TAMPINES");
    expect(resolved.missingRequested).toBe(true);
  });

  test("the same selection resolves to the same key across calls", () => {
    const first = resolveReference(table, {
      area: "QUEENSTOWN",
      property: "condo",
    });
    const second = resolveReference(table, {
      area: "QUEENSTOWN",
      property: "condo",
    });
    expect(referenceKey(first.entry)).toBe(referenceKey(second.entry));
  });
});
