// app/src/components/dashboard/segments/compare/InvestmentImplications.tsx
import type { Segment, Persona } from '@/types/segments';

interface InvestmentImplicationsProps {
  segments: Segment[];
  persona: Persona;
}

export function InvestmentImplications({ segments, persona }: InvestmentImplicationsProps) {
  const getImplications = () => {
    switch (persona) {
      case 'investor':
        return {
          title: 'For Property Investors',
          getComparison: (s: Segment) => s.implications.investor,
        };
      case 'first-time-buyer':
        return {
          title: 'For First-Time Buyers',
          getComparison: (s: Segment) => s.implications.firstTimeBuyer,
        };
      case 'upgrader':
        return {
          title: 'For Upsizers',
          getComparison: (s: Segment) => s.implications.upgrader,
        };
      default:
        return {
          title: 'Investment Implications',
          getComparison: (s: Segment) => s.implications.investor,
        };
    }
  };

  const { title, getComparison } = getImplications();

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-foreground">{title}</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {segments.map((segment) => (
          <div key={segment.id} className="bg-muted/50 p-4 rounded-lg">
            <h4 className="font-semibold text-foreground mb-2">{segment.name}</h4>
            <p className="text-sm text-muted-foreground">{getComparison(segment)}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
