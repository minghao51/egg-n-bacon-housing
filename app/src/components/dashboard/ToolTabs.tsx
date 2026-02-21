export type ToolTab = 'mrt-cbd' | 'lease-decay' | 'affordability' | 'hotspots';

interface ToolConfig {
  id: ToolTab;
  label: string;
  icon: string;
  description: string;
}

const TOOLS: ToolConfig[] = [
  {
    id: 'mrt-cbd',
    label: 'MRT/CBD Impact',
    icon: '🚇',
    description: 'Transportation proximity effects on prices'
  },
  {
    id: 'lease-decay',
    label: 'Lease Decay',
    icon: '📉',
    description: 'How remaining lease affects property value'
  },
  {
    id: 'affordability',
    label: 'Affordability',
    icon: '💰',
    description: 'Income-based property affordability analysis'
  },
  {
    id: 'hotspots',
    label: 'Spatial Hotspots',
    icon: '🗺️',
    description: 'Neighborhood appreciation clusters'
  }
];

interface ToolTabsProps {
  active: ToolTab;
  onChange: (tab: ToolTab) => void;
}

export default function ToolTabs({ active, onChange }: ToolTabsProps) {
  return (
    <div className="border-b border-gray-200 dark:border-gray-700 mb-6">
      <nav className="flex space-x-1 overflow-x-auto" aria-label="Tabs">
        {TOOLS.map((tool) => (
          <button
            key={tool.id}
            onClick={() => onChange(tool.id)}
            className={`
              whitespace-nowrap py-3 px-4 border-b-2 font-medium text-sm flex items-center gap-2 transition-colors
              ${active === tool.id
                ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
              }
            `}
            aria-current={active === tool.id ? 'page' : undefined}
          >
            <span className="text-lg">{tool.icon}</span>
            <span>{tool.label}</span>
          </button>
        ))}
      </nav>
    </div>
  );
}

export { TOOLS };
export type { ToolConfig };
