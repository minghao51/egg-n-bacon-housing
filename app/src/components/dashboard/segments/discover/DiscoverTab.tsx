// app/src/components/dashboard/segments/discover/DiscoverTab.tsx
import { useState } from 'react';
import { Segment, Insight, Persona } from '@/types/segments';
import { SegmentGrid } from './SegmentGrid';
import { InsightCard } from './InsightCard';

interface DiscoverTabProps {
  segments: Segment[];
  insights: Insight[];
  persona: Persona;
  onViewDetails: (segment: Segment) => void;
  onAddToCompare: (segment: Segment) => void;
  comparisonSet: Set<string>;
}

type SortOption = 'relevance' | 'price' | 'yield' | 'growth';

const SORT_OPTIONS: { value: SortOption; label: string }[] = [
  { value: 'relevance', label: 'Relevance' },
  { value: 'price', label: 'Price (Low to High)' },
  { value: 'yield', label: 'Yield (High to Low)' },
  { value: 'growth', label: 'Growth (High to Low)' },
];

export function DiscoverTab({
  segments,
  insights,
  persona,
  onViewDetails,
  onAddToCompare,
  comparisonSet,
}: DiscoverTabProps) {
  const [sortBy, setSortBy] = useState<SortOption>('relevance');

  // Get relevant insights for persona
  const relevantInsights = insights.filter((insight) => {
    if (persona === 'all') return true;
    return insight.relevantFor.includes(persona);
  });

  return (
    <div className="space-y-6">
      {/* Header with Sort */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold text-foreground">
            {segments.length} Segment{segments.length !== 1 ? 's' : ''} Found
          </h2>
          <p className="text-sm text-muted-foreground">
            Click on a segment to view details or add to comparison
          </p>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-sm text-muted-foreground">Sort by:</label>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as SortOption)}
            className="px-3 py-2 border border-border rounded-md bg-background text-foreground text-sm"
          >
            {SORT_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Insight Cards */}
      {relevantInsights.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {relevantInsights.slice(0, 2).map((insight) => (
            <InsightCard key={insight.id} insight={insight} />
          ))}
        </div>
      )}

      {/* Segment Grid */}
      <SegmentGrid
        segments={segments}
        sortBy={sortBy}
        onViewDetails={onViewDetails}
        onAddToCompare={onAddToCompare}
        comparisonSet={comparisonSet}
      />
    </div>
  );
}
