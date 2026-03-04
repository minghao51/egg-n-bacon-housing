// app/src/components/dashboard/segments/discover/SegmentGrid.tsx
import { useMemo } from 'react';
import type { Segment } from '@/types/segments';
import SegmentCard from '../SegmentCard';

interface SegmentGridProps {
  scoredSegments: Array<{ segment: Segment; matchScore: number }>;
  sortBy?: 'relevance' | 'yield' | 'growth' | 'value';
  onInvestigate: (segment: Segment) => void;
  onAddToCompare: (segment: Segment) => void;
  selectedSegmentId?: string | null;
  comparisonSet: Set<string>;
}

type SortOption = 'relevance' | 'yield' | 'growth' | 'value';

export function SegmentGrid({
  scoredSegments,
  sortBy = 'relevance',
  onInvestigate,
  onAddToCompare,
  selectedSegmentId,
  comparisonSet,
}: SegmentGridProps) {
  const sortedSegments = useMemo(() => {
    const sorted = [...scoredSegments];

    switch (sortBy) {
      case 'yield':
        return sorted.sort((a, b) => b.segment.metrics.avgYield - a.segment.metrics.avgYield);
      case 'growth':
        return sorted.sort((a, b) => b.segment.metrics.yoyGrowth - a.segment.metrics.yoyGrowth);
      case 'value':
        return sorted.sort((a, b) => a.segment.metrics.avgPricePsf - b.segment.metrics.avgPricePsf);
      case 'relevance':
      default:
        return sorted;
    }
  }, [scoredSegments, sortBy]);

  if (sortedSegments.length === 0) {
    return (
      <div className="text-center py-12">
        <div className="text-6xl mb-4">🔍</div>
        <h3 className="text-lg font-semibold text-foreground mb-2">No segments found</h3>
        <p className="text-muted-foreground mb-4">
          Try adjusting your filters to see more results
        </p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      {sortedSegments.map(({ segment, matchScore }) => (
        <SegmentCard
          key={segment.id}
          segment={segment}
          matchScore={matchScore}
          onInvestigate={onInvestigate}
          onAddToCompare={onAddToCompare}
          isActive={selectedSegmentId === segment.id}
          isSelectedForCompare={comparisonSet.has(segment.id)}
        />
      ))}
    </div>
  );
}
