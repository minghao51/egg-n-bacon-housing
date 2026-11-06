// app/src/hooks/useSegmentMatching.ts
import { useMemo } from "react";
import type { Segment, FilterState } from "@/types/segments";

/**
 * Scoring weights, unchanged since before S7.
 *
 * Exported so the UI can *explain* the fit without restating (and drifting
 * from) the implementation. Changing a weight is an owner decision on the
 * segment model, not a UI change — see the decision register in
 * `assets/svg/implementation-plan.md` §6.
 */
export const SEGMENT_MATCH_WEIGHTS = {
  investmentGoal: 30,
  budget: 25,
  propertyType: 20,
  location: 15,
  timeHorizon: 10,
} as const;

export const SEGMENT_MATCH_RULE_NOTES = {
  hardFilter:
    "The spatial-class filter is hard: a segment in a different class is dropped before scoring.",
  optional:
    "Investment goal and time horizon are only part of the denominator when they are set; this is why a partial match can still score highly.",
  rounding:
    "The score is score ÷ applicable weights, rounded to a whole percent. It is a weighted fit, not a return probability.",
} as const;

export function useSegmentMatching(segments: Segment[], filters: FilterState) {
  const scoredSegments = useMemo(() => {
    return segments
      .map((segment) => ({
        segment,
        matchScore: calculateMatchScore(segment, filters),
      }))
      .filter(({ matchScore }) => matchScore > 0)
      .sort((a, b) => b.matchScore - a.matchScore);
  }, [segments, filters]);

  const matchedSegments = useMemo(
    () => scoredSegments.map(({ segment }) => segment),
    [scoredSegments],
  );

  return { matchedSegments, scoredSegments };
}

function calculateMatchScore(segment: Segment, filters: FilterState): number {
  let score = 0;
  let maxScore = 0;

  // Hotspot filter - hard filter (must match to pass)
  if (
    filters.hotspotFilter !== "all" &&
    segment.spatialClassification !== filters.hotspotFilter
  ) {
    return 0;
  }

  // Investment goal
  if (filters.investmentGoal) {
    if (
      (filters.investmentGoal === "yield" && segment.metrics.avgYield >= 4) ||
      (filters.investmentGoal === "growth" &&
        segment.metrics.yoyGrowth >= 12) ||
      (filters.investmentGoal === "value" &&
        segment.characteristics.priceTier === "affordable") ||
      (filters.investmentGoal === "balanced" &&
        segment.investmentType === "balanced")
    ) {
      score += SEGMENT_MATCH_WEIGHTS.investmentGoal;
    }
    maxScore += SEGMENT_MATCH_WEIGHTS.investmentGoal;
  }

  // Budget fit
  if (
    segment.metrics.avgPricePsf >= filters.budgetRange[0] &&
    segment.metrics.avgPricePsf <= filters.budgetRange[1]
  ) {
    score += SEGMENT_MATCH_WEIGHTS.budget;
  }
  maxScore += SEGMENT_MATCH_WEIGHTS.budget;

  // Property type match
  if (filters.propertyTypes.some((t) => segment.propertyTypes.includes(t))) {
    score += SEGMENT_MATCH_WEIGHTS.propertyType;
  }
  maxScore += SEGMENT_MATCH_WEIGHTS.propertyType;

  // Location match
  if (filters.locations.some((loc) => segment.regions.includes(loc))) {
    score += SEGMENT_MATCH_WEIGHTS.location;
  }
  maxScore += SEGMENT_MATCH_WEIGHTS.location;

  // Time horizon fit
  if (filters.timeHorizon) {
    if (
      (filters.timeHorizon === "short" &&
        segment.characteristics.volatility === "high") ||
      (filters.timeHorizon === "long" &&
        segment.characteristics.volatility === "low")
    ) {
      score += SEGMENT_MATCH_WEIGHTS.timeHorizon;
    }
    maxScore += SEGMENT_MATCH_WEIGHTS.timeHorizon;
  }

  return maxScore > 0 ? Math.round((score / maxScore) * 100) : 0;
}
