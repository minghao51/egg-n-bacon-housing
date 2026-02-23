import type { Persona } from './PersonaSelector';

interface Segment {
  id: string;
  name: string;
  description: string;
  implications: {
    investor?: string;
    firstTimeBuyer?: string;
    upgrader?: string;
  };
}

interface PersonaHeaderProps {
  persona: Persona;
  segments: Segment[];
}

const PERSONA_LABELS: Record<Persona, string> = {
  all: 'All Personas',
  investor: 'Investors',
  'first-time-buyer': 'First-Time Buyers',
  upgrader: 'Upgraders',
};

export default function PersonaHeader({ persona, segments }: PersonaHeaderProps) {
  // Map persona to the key used in segments data
  const key = persona === 'first-time-buyer' ? 'firstTimeBuyer' : persona;

  // Get segments with relevant implications for this persona
  const relevantSegments = segments
    .filter((s) => s.implications[key])
    .slice(0, 3);

  return (
    <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4 mb-6">
      <h3 className="font-semibold text-blue-900 dark:text-blue-100">
        📊 Insights for {PERSONA_LABELS[persona]}
      </h3>
      {relevantSegments.length > 0 ? (
        <ul className="mt-3 space-y-2">
          {relevantSegments.map((segment) => (
            <li
              key={segment.id}
              className="text-sm text-blue-800 dark:text-blue-200"
            >
              <strong>{segment.name}:</strong> {segment.implications[key]}
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-blue-700 dark:text-blue-300 mt-2">
          Select a persona to see personalized insights.
        </p>
      )}
    </div>
  );
}
