// app/src/components/dashboard/segments/discover/DiscoverTab.tsx
import { useState } from 'react';
import type { Segment, Insight, Persona } from '@/types/segments';
import { SegmentGrid } from './SegmentGrid';
import { InsightCard } from './InsightCard';

interface DiscoverTabProps {
  scoredSegments: Array<{ segment: Segment; matchScore: number }>;
  insights: Insight[];
  persona: Persona;
  selectedSegmentId: string | null;
  activeFilterCount: number;
  onResetFilters: () => void;
  onInvestigateSegment: (segment: Segment) => void;
  onAddToCompare: (segment: Segment) => void;
  comparisonSet: Set<string>;
}

type SortOption = 'relevance' | 'yield' | 'growth' | 'value';

const SORT_OPTIONS: { value: SortOption; label: string }[] = [
  { value: 'relevance', label: 'Relevance' },
  { value: 'yield', label: 'Yield' },
  { value: 'growth', label: 'Growth' },
  { value: 'value', label: 'Value' },
];

export function DiscoverTab({
  scoredSegments,
  insights,
  persona,
  selectedSegmentId,
  activeFilterCount,
  onResetFilters,
  onInvestigateSegment,
  onAddToCompare,
  comparisonSet,
}: DiscoverTabProps) {
  const [sortBy, setSortBy] = useState<SortOption>('relevance');
  const matchedCount = scoredSegments.length;

  const relevantInsights = insights.filter((insight) => {
    if (persona === 'all') return true;
    return insight.relevantFor.includes(persona);
  });

  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-border bg-card p-4">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h2 className="text-xl font-semibold text-foreground">
              {matchedCount} Segment{matchedCount !== 1 ? 's' : ''} Ready To Review
            </h2>
            <p className="text-sm text-muted-foreground">
              Choose a segment first, then move into the investigation workspace.
            </p>
          </div>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <div className="flex items-center gap-2">
              <label className="text-sm text-muted-foreground">Ranking Bias</label>
              <div className="flex flex-wrap gap-2">
                {SORT_OPTIONS.map((option) => (
                  <button
                    key={option.value}
                    onClick={() => setSortBy(option.value)}
                    className={`rounded-full px-3 py-1.5 text-sm font-medium transition-colors ${
                      sortBy === option.value
                        ? 'bg-primary text-primary-foreground'
                        : 'bg-muted text-muted-foreground hover:text-foreground'
                    }`}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </div>
            {activeFilterCount > 0 && (
              <button
                onClick={onResetFilters}
                className="rounded-full border border-border px-3 py-1.5 text-sm font-medium text-muted-foreground hover:text-foreground"
              >
                Clear Filters ({activeFilterCount})
              </button>
            )}
          </div>
        </div>
      </div>

      {relevantInsights.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {relevantInsights.slice(0, 2).map((insight) => (
            <InsightCard key={insight.id} insight={insight} />
          ))}
        </div>
      )}

      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h3 className="text-lg font-semibold text-foreground">Segment Selection Board</h3>
          <p className="text-sm text-muted-foreground">
            Investigate opens the area shortlist. Compare keeps a side-by-side cross-check set.
          </p>
        </div>
        {selectedSegmentId && (
          <div className="rounded-full bg-primary/10 px-3 py-1 text-sm font-medium text-primary">
            Active Segment Selected
          </div>
        )}
      </div>

      <SegmentGrid
        scoredSegments={scoredSegments}
        sortBy={sortBy}
        onInvestigate={onInvestigateSegment}
        onAddToCompare={onAddToCompare}
        selectedSegmentId={selectedSegmentId}
        comparisonSet={comparisonSet}
      />
    </div>
  );
}
