// app/src/components/dashboard/segments/details/DetailsTab.tsx
import type { Segment, Persona, PlanningArea } from '@/types/segments';
import { SegmentOverview } from './SegmentOverview';
import { GeographicDistribution } from './GeographicDistribution';
import { RiskFactors } from './RiskFactors';

interface DetailsTabProps {
  segment: Segment;
  planningAreas: Record<string, PlanningArea>;
  persona: Persona;
  onBack: () => void;
}

export function DetailsTab({ segment, planningAreas, persona, onBack }: DetailsTabProps) {
  return (
    <div className="space-y-6">
      {/* Back Button */}
      <button
        onClick={onBack}
        className="text-sm text-muted-foreground hover:text-foreground flex items-center gap-1"
      >
        ← Back to Discover
      </button>

      {/* Overview */}
      <SegmentOverview segment={segment} persona={persona} />

      {/* Geographic Distribution */}
      <GeographicDistribution segment={segment} planningAreas={planningAreas} />

      {/* Risk Factors */}
      <RiskFactors segment={segment} />
    </div>
  );
}
