// app/src/components/dashboard/segments/details/GeographicDistribution.tsx
import type { Segment, PlanningArea } from '@/types/segments';

interface GeographicDistributionProps {
  segment: Segment;
  planningAreas: Record<string, PlanningArea>;
}

export function GeographicDistribution({ segment, planningAreas }: GeographicDistributionProps) {
  const segmentAreas = segment.planningAreas
    .map((name) => planningAreas[name])
    .filter(Boolean);

  const regionCounts = segmentAreas.reduce((acc, area) => {
    acc[area.region] = (acc[area.region] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-foreground">Geographic Distribution</h3>

      {/* Region Breakdown */}
      <div className="grid grid-cols-3 gap-3">
        {(['CCR', 'RCR', 'OCR'] as const).map((region) => (
          <div
            key={region}
            className={`p-3 rounded-lg border text-center ${
              segment.regions.includes(region)
                ? 'border-primary bg-primary/5'
                : 'border-border opacity-50'
            }`}
          >
            <div className="text-2xl font-bold text-foreground">{regionCounts[region] || 0}</div>
            <div className="text-xs text-muted-foreground">{region} Areas</div>
          </div>
        ))}
      </div>

      {/* Planning Areas List */}
      <div>
        <h4 className="font-medium text-foreground mb-2">
          Planning Areas ({segmentAreas.length})
        </h4>
        <div className="flex flex-wrap gap-2">
          {segmentAreas.map((area) => (
            <span
              key={area.name}
              className="px-3 py-1 bg-muted text-foreground text-sm rounded-full"
            >
              {area.name}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
