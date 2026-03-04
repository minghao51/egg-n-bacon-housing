import { useState } from 'react';

export type Persona = 'all' | 'investor' | 'first-time-buyer' | 'upgrader';

interface PersonaConfig {
  id: Persona;
  name: string;
  icon: string;
  description: string;
}

const PERSONAS: PersonaConfig[] = [
  {
    id: 'all',
    name: 'All Personas',
    icon: '👥',
    description: 'Explore freely without preset filters'
  },
  {
    id: 'investor',
    name: 'Investor',
    icon: '🏠',
    description: 'ROI-focused, portfolio optimization'
  },
  {
    id: 'first-time-buyer',
    name: 'First-Time Buyer',
    icon: '👤',
    description: 'Affordability, loan approval, stability'
  },
  {
    id: 'upgrader',
    name: 'Upgrader',
    icon: '🏡',
    description: 'More space, better location, trade-up'
  }
];

interface PersonaSelectorProps {
  selected: Persona;
  onChange: (persona: Persona) => void;
  compact?: boolean;
}

export default function PersonaSelector({
  selected,
  onChange,
  compact = false,
}: PersonaSelectorProps) {
  return (
    <div className="mb-6">
      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
        I'm a:
      </label>
      <div className="flex flex-wrap gap-3">
        {PERSONAS.map((persona) => (
          <button
            key={persona.id}
            onClick={() => onChange(persona.id)}
            className={`
              rounded-lg border-2 transition-all flex-1 min-w-[140px]
              ${compact ? 'px-3 py-2' : 'px-4 py-3'}
              ${selected === persona.id
                ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300'
                : 'border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500'
              }
            `}
          >
            <div className={`${compact ? 'text-lg mb-0.5' : 'text-2xl mb-1'}`}>{persona.icon}</div>
            <div className="font-medium text-sm">{persona.name}</div>
            {!compact && (
              <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                {persona.description}
              </div>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}
