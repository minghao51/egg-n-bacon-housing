// app/src/hooks/useSegmentMatching.ts
import { useMemo } from 'react';
import { Segment, FilterState } from '@/types/segments';

export function useSegmentMatching(
  segments: Segment[],
  filters: FilterState
) {
  const matchedSegments = useMemo(() => {
    return segments
      .map((segment) => ({
        segment,
        matchScore: calculateMatchScore(segment, filters),
      }))
      .filter(({ matchScore }) => matchScore > 0)
      .sort((a, b) => b.matchScore - a.matchScore)
      .map(({ segment }) => segment);
  }, [segments, filters]);

  return { matchedSegments };
}

function calculateMatchScore(segment: Segment, filters: FilterState): number {
  let score = 0;
  let maxScore = 0;

  // Investment goal (30% weight)
  if (filters.investmentGoal) {
    if (
      (filters.investmentGoal === 'yield' && segment.metrics.avgYield >= 4) ||
      (filters.investmentGoal === 'growth' && segment.metrics.yoyGrowth >= 12) ||
      (filters.investmentGoal === 'value' && segment.characteristics.priceTier === 'affordable') ||
      (filters.investmentGoal === 'balanced' && segment.investmentType === 'balanced')
    ) {
      score += 30;
    }
    maxScore += 30;
  }

  // Budget fit (25% weight)
  if (
    segment.metrics.avgPricePsf >= filters.budgetRange[0] &&
    segment.metrics.avgPricePsf <= filters.budgetRange[1]
  ) {
    score += 25;
  }
  maxScore += 25;

  // Property type match (20% weight)
  if (filters.propertyTypes.some((t) => segment.propertyTypes.includes(t))) {
    score += 20;
  }
  maxScore += 20;

  // Location match (15% weight)
  if (filters.locations.some((loc) => segment.regions.includes(loc))) {
    score += 15;
  }
  maxScore += 15;

  // Time horizon fit (10% weight)
  if (filters.timeHorizon) {
    if (
      (filters.timeHorizon === 'short' && segment.characteristics.volatility === 'high') ||
      (filters.timeHorizon === 'long' && segment.characteristics.volatility === 'low')
    ) {
      score += 10;
    }
    maxScore += 10;
  }

  return maxScore > 0 ? Math.round((score / maxScore) * 100) : 0;
}
