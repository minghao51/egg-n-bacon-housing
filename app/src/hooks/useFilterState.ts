// app/src/hooks/useFilterState.ts
import { useState, useCallback, useMemo, useEffect, useRef } from 'react';
import type {
  FilterState,
  Persona,
  InvestmentGoal,
  PropertyType,
  Region,
  TimeHorizon,
  PersonaPreset,
} from '@/types/segments';

const INITIAL_FILTERS: FilterState = {
  investmentGoal: null,
  budgetRange: [400, 1000],
  propertyTypes: ['HDB', 'Condominium', 'EC'],
  locations: ['CCR', 'RCR', 'OCR'],
  timeHorizon: null,
  hotspotFilter: 'all',
};

const PERSONA_PRESETS: Record<Persona, PersonaPreset> = {
  all: {
    filters: {
      investmentGoal: null,
      budgetRange: [400, 1000],
      propertyTypes: ['HDB', 'Condominium', 'EC'],
      locations: ['CCR', 'RCR', 'OCR'],
      timeHorizon: null,
      hotspotFilter: 'all',
    },
    priorityMetrics: [],
    defaultInsights: [],
  },
  investor: {
    filters: {
      investmentGoal: 'yield',
      budgetRange: [500, 1000],
      propertyTypes: ['Condominium', 'HDB'],
      locations: ['CCR', 'RCR', 'OCR'],
      timeHorizon: 'medium',
      hotspotFilter: 'HH',
    },
    priorityMetrics: ['rental_yield', 'mrt_proximity', 'appreciation'],
    defaultInsights: ['condo_mrt_sensitivity', 'hotspot_persistence'],
  },
  'first-time-buyer': {
    filters: {
      investmentGoal: 'value',
      budgetRange: [400, 600],
      propertyTypes: ['HDB'],
      locations: ['OCR', 'RCR'],
      timeHorizon: 'long',
      hotspotFilter: 'all',
    },
    priorityMetrics: ['affordability', 'school_quality', 'lease_remaining'],
    defaultInsights: ['school_premiums_by_region', 'cbd_vs_mrt'],
  },
  upgrader: {
    filters: {
      investmentGoal: 'balanced',
      budgetRange: [500, 800],
      propertyTypes: ['HDB', 'Condominium'],
      locations: ['RCR', 'OCR'],
      timeHorizon: 'long',
      hotspotFilter: 'all',
    },
    priorityMetrics: ['space_value', 'neighborhood', 'amenities'],
    defaultInsights: ['cbd_vs_mrt', 'school_premiums_by_region'],
  },
};

interface UseFilterStateResult {
  filters: FilterState;
  debouncedFilters: FilterState;
  persona: Persona;
  setPersona: (persona: Persona) => void;
  updateFilter: <K extends keyof FilterState>(key: K, value: FilterState[K]) => void;
  resetFilters: () => void;
  activeFilterCount: number;
}

interface UseFilterStateOptions {
  countVisibleFiltersOnly?: boolean;
}

export function useFilterState(
  initialPersona: Persona = 'all',
  options: UseFilterStateOptions = {}
): UseFilterStateResult {
  const [persona, setPersona] = useState<Persona>(initialPersona);
  const [filters, setFilters] = useState<FilterState>(() => {
    const preset = PERSONA_PRESETS[initialPersona];
    return { ...INITIAL_FILTERS, ...preset.filters };
  });

  // Debounced filters for expensive operations (map rendering)
  const [debouncedFilters, setDebouncedFilters] = useState<FilterState>(filters);
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

  const updateFilter = useCallback(<K extends keyof FilterState>(
    key: K,
    value: FilterState[K]
  ) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  }, []);

  const resetFilters = useCallback(() => {
    const preset = PERSONA_PRESETS[persona];
    setFilters({ ...INITIAL_FILTERS, ...preset.filters });
  }, [persona]);

  const handleSetPersona = useCallback((newPersona: Persona) => {
    setPersona(newPersona);
    const preset = PERSONA_PRESETS[newPersona];
    setFilters({ ...INITIAL_FILTERS, ...preset.filters });
  }, []);

  const activeFilterCount = useMemo(() => {
    let count = 0;
    if (!options.countVisibleFiltersOnly && filters.investmentGoal) count++;
    if (filters.budgetRange[0] !== INITIAL_FILTERS.budgetRange[0] ||
        filters.budgetRange[1] !== INITIAL_FILTERS.budgetRange[1]) count++;
    if (filters.propertyTypes.length < 3) count++;
    if (filters.locations.length < 3) count++;
    if (!options.countVisibleFiltersOnly && filters.timeHorizon) count++;
    if (filters.hotspotFilter !== 'all') count++;
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

export { PERSONA_PRESETS };
