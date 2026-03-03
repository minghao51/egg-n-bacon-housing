// app/src/components/dashboard/segments/discover/SegmentGrid.tsx
import { useMemo } from 'react';
import type { Segment } from '@/types/segments';
import SegmentCard from '../SegmentCard';

interface SegmentGridProps {
  segments: Segment[];
  sortBy?: 'relevance' | 'price' | 'yield' | 'growth';
  onViewDetails: (segment: Segment) => void;
  onAddToCompare: (segment: Segment) => void;
  comparisonSet: Set<string>;
}

type SortOption = 'relevance' | 'price' | 'yield' | 'growth';

export function SegmentGrid({
  segments,
  sortBy = 'relevance',
  onViewDetails,
  onAddToCompare,
  comparisonSet,
}: SegmentGridProps) {
  const sortedSegments = useMemo(() => {
    const sorted = [...segments];

    switch (sortBy) {
      case 'price':
        return sorted.sort((a, b) => a.metrics.avgPricePsf - b.metrics.avgPricePsf);
      case 'yield':
        return sorted.sort((a, b) => b.metrics.avgYield - a.metrics.avgYield);
      case 'growth':
        return sorted.sort((a, b) => b.metrics.yoyGrowth - a.metrics.yoyGrowth);
      case 'relevance':
      default:
        return sorted; // Already sorted by match score
    }
  }, [segments, sortBy]);

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
      {sortedSegments.map((segment) => (
        <SegmentCard
          key={segment.id}
          segment={segment}
          onViewDetails={onViewDetails}
          onAddToCompare={onAddToCompare}
          isSelectedForCompare={comparisonSet.has(segment.id)}
        />
      ))}
    </div>
  );
}
