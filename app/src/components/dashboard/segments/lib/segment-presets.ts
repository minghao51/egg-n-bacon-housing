/**
 * Persona presets for the segment workspace.
 *
 * Pure data (no React) so the URL parser, the hook and the tests can share one
 * definition of "reset to persona settings". Values are unchanged from the
 * pre-S7 hook; the scoring itself lives in `useSegmentMatching.ts` and is not
 * redefined here.
 */

import type { FilterState, Persona, PersonaPreset } from "@/types/segments";

export const INITIAL_FILTERS: FilterState = {
  investmentGoal: null,
  budgetRange: [400, 1000],
  propertyTypes: ["HDB", "Condominium", "EC"],
  locations: ["CCR", "RCR", "OCR"],
  timeHorizon: null,
  hotspotFilter: "all",
};

export const PERSONA_PRESETS: Record<Persona, PersonaPreset> = {
  all: {
    filters: {
      investmentGoal: null,
      budgetRange: [400, 1000],
      propertyTypes: ["HDB", "Condominium", "EC"],
      locations: ["CCR", "RCR", "OCR"],
      timeHorizon: null,
      hotspotFilter: "all",
    },
    priorityMetrics: [],
    defaultInsights: [],
  },
  investor: {
    filters: {
      investmentGoal: "yield",
      budgetRange: [500, 1000],
      propertyTypes: ["Condominium", "HDB"],
      locations: ["CCR", "RCR", "OCR"],
      timeHorizon: "medium",
      hotspotFilter: "HH",
    },
    priorityMetrics: ["rental_yield", "mrt_proximity", "appreciation"],
    defaultInsights: ["condo_mrt_sensitivity", "hotspot_persistence"],
  },
  "first-time-buyer": {
    filters: {
      investmentGoal: "value",
      budgetRange: [400, 600],
      propertyTypes: ["HDB"],
      locations: ["OCR", "RCR"],
      timeHorizon: "long",
      hotspotFilter: "all",
    },
    priorityMetrics: ["affordability", "school_quality", "lease_remaining"],
    defaultInsights: ["school_premiums_by_region", "cbd_vs_mrt"],
  },
  upgrader: {
    filters: {
      investmentGoal: "balanced",
      budgetRange: [500, 800],
      propertyTypes: ["HDB", "Condominium"],
      locations: ["RCR", "OCR"],
      timeHorizon: "long",
      hotspotFilter: "all",
    },
    priorityMetrics: ["space_value", "neighborhood", "amenities"],
    defaultInsights: ["cbd_vs_mrt", "school_premiums_by_region"],
  },
};

/** Persona preset filters with the shared initial values filled in. */
export function presetFilters(persona: Persona): FilterState {
  return { ...INITIAL_FILTERS, ...PERSONA_PRESETS[persona].filters };
}

/** Whether the given filters still differ from their persona preset. */
export function filtersDifferFromPreset(
  filters: FilterState,
  persona: Persona,
): boolean {
  const preset = presetFilters(persona);
  return (
    filters.investmentGoal !== preset.investmentGoal ||
    filters.budgetRange[0] !== preset.budgetRange[0] ||
    filters.budgetRange[1] !== preset.budgetRange[1] ||
    filters.propertyTypes.length !== preset.propertyTypes.length ||
    filters.propertyTypes.some(
      (type) => !preset.propertyTypes.includes(type),
    ) ||
    filters.locations.length !== preset.locations.length ||
    filters.locations.some((region) => !preset.locations.includes(region)) ||
    filters.timeHorizon !== preset.timeHorizon ||
    filters.hotspotFilter !== preset.hotspotFilter
  );
}
