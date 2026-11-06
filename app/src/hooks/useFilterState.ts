// app/src/hooks/useFilterState.ts
import { useState, useCallback, useMemo, useEffect, useRef } from "react";
import type { FilterState, Persona } from "@/types/segments";
import {
  INITIAL_FILTERS,
  PERSONA_PRESETS,
  presetFilters,
} from "@/components/dashboard/segments/lib/segment-presets";

interface UseFilterStateResult {
  filters: FilterState;
  debouncedFilters: FilterState;
  persona: Persona;
  setPersona: (persona: Persona) => void;
  updateFilter: <K extends keyof FilterState>(
    key: K,
    value: FilterState[K],
  ) => void;
  resetFilters: () => void;
  activeFilterCount: number;
}

interface UseFilterStateOptions {
  countVisibleFiltersOnly?: boolean;
  /**
   * Constraints read from the address bar (`fv=1&psf=…&types=…`). Applied on
   * top of the persona preset before the first commit, so a deep link is never
   * rendered with (and re-serialised from) the preset defaults.
   */
  initialFilters?: Partial<FilterState>;
}

export function useFilterState(
  initialPersona: Persona = "all",
  options: UseFilterStateOptions = {},
): UseFilterStateResult {
  const [persona, setPersona] = useState<Persona>(initialPersona);
  const [filters, setFilters] = useState<FilterState>(() => ({
    ...presetFilters(initialPersona),
    ...options.initialFilters,
  }));

  // Debounced filters for expensive operations (map rendering)
  const [debouncedFilters, setDebouncedFilters] =
    useState<FilterState>(filters);
  const debounceTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Debounce filter updates - wait 300ms after last change before updating expensive operations
  useEffect(() => {
    if (debounceTimeoutRef.current) {
      clearTimeout(debounceTimeoutRef.current);
    }
    debounceTimeoutRef.current = setTimeout(() => {
      setDebouncedFilters(filters);
    }, 300);

    return () => {
      if (debounceTimeoutRef.current) {
        clearTimeout(debounceTimeoutRef.current);
      }
    };
  }, [filters]);

  const updateFilter = useCallback(
    <K extends keyof FilterState>(key: K, value: FilterState[K]) => {
      setFilters((prev) => ({ ...prev, [key]: value }));
    },
    [],
  );

  const resetFilters = useCallback(() => {
    setFilters(presetFilters(persona));
  }, [persona]);

  const handleSetPersona = useCallback((newPersona: Persona) => {
    setPersona(newPersona);
    setFilters(presetFilters(newPersona));
  }, []);

  const activeFilterCount = useMemo(() => {
    let count = 0;
    if (!options.countVisibleFiltersOnly && filters.investmentGoal) count++;
    if (
      filters.budgetRange[0] !== INITIAL_FILTERS.budgetRange[0] ||
      filters.budgetRange[1] !== INITIAL_FILTERS.budgetRange[1]
    )
      count++;
    if (filters.propertyTypes.length < 3) count++;
    if (filters.locations.length < 3) count++;
    if (!options.countVisibleFiltersOnly && filters.timeHorizon) count++;
    if (filters.hotspotFilter !== "all") count++;
    return count;
  }, [filters, options.countVisibleFiltersOnly]);

  return {
    filters,
    debouncedFilters,
    persona,
    setPersona: handleSetPersona,
    updateFilter,
    resetFilters,
    activeFilterCount,
  };
}

export { INITIAL_FILTERS, PERSONA_PRESETS };
