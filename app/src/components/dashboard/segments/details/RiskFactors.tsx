// app/src/components/dashboard/segments/details/RiskFactors.tsx
import type { Segment } from '@/types/segments';

interface RiskFactorsProps {
  segment: Segment;
}

export function RiskFactors({ segment }: RiskFactorsProps) {
  if (segment.riskFactors.length === 0 && segment.opportunities.length === 0) {
    return null;
  }

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-foreground">Risk & Opportunities</h3>

      {/* Risk Factors */}
      {segment.riskFactors.length > 0 && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 p-4 rounded-lg">
          <h4 className="font-semibold text-foreground mb-2 flex items-center gap-2">
            <span>⚠️</span> Risk Factors
          </h4>
          <ul className="space-y-1">
            {segment.riskFactors.map((risk, index) => (
              <li key={index} className="text-sm text-muted-foreground flex items-start gap-2">
                <span className="text-red-500 mt-0.5">•</span>
                <span>{risk}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Opportunities */}
      {segment.opportunities.length > 0 && (
        <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 p-4 rounded-lg">
          <h4 className="font-semibold text-foreground mb-2 flex items-center gap-2">
            <span>✨</span> Opportunities
          </h4>
          <ul className="space-y-1">
            {segment.opportunities.map((opportunity, index) => (
              <li key={index} className="text-sm text-muted-foreground flex items-start gap-2">
                <span className="text-green-500 mt-0.5">•</span>
                <span>{opportunity}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
