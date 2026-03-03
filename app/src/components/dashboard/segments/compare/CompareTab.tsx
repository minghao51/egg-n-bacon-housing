// app/src/components/dashboard/segments/compare/CompareTab.tsx
import type { Segment, Persona } from '@/types/segments';
import { ComparisonTable } from './ComparisonTable';
import { ComparisonCharts } from './ComparisonCharts';
import { InvestmentImplications } from './InvestmentImplications';

interface CompareTabProps {
  segments: Segment[];
  allSegments: Segment[];
  persona: Persona;
}

export function CompareTab({ segments, allSegments, persona }: CompareTabProps) {
  if (segments.length < 2) {
    return (
      <div className="text-center py-16">
        <div className="text-6xl mb-4">⚖️</div>
        <h3 className="text-xl font-semibold text-foreground mb-2">Select Segments to Compare</h3>
        <p className="text-muted-foreground mb-6">
          Choose 2-4 segments from the Discover tab to compare them side-by-side
        </p>
        <p className="text-sm text-muted-foreground">
          {segments.length === 1 ? '1 segment selected' : '0 segments selected'} (need 2-4)
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Comparison Table */}
      <div>
        <h2 className="text-xl font-semibold text-foreground mb-4">Metrics Comparison</h2>
        <ComparisonTable segments={segments} persona={persona} />
      </div>

      {/* Charts */}
      <div>
        <h2 className="text-xl font-semibold text-foreground mb-4">Visual Comparison</h2>
        <ComparisonCharts segments={segments} />
      </div>

      {/* Investment Implications */}
      <InvestmentImplications segments={segments} persona={persona} />
    </div>
  );
}
