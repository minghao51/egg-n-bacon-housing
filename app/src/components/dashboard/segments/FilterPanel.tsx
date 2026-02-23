// app/src/components/dashboard/segments/FilterPanel.tsx
import { FilterState, InvestmentGoal, PropertyType, Region, TimeHorizon } from '@/types/segments';

interface FilterPanelProps {
  filters: FilterState;
  onFilterChange: <K extends keyof FilterState>(key: K, value: FilterState[K]) => void;
  onReset: () => void;
  activeFilterCount: number;
}

const INVESTMENT_GOALS: { value: InvestmentGoal; label: string; description: string }[] = [
  { value: 'yield', label: 'Yield Focus', description: '4%+ target yield' },
  { value: 'growth', label: 'Growth Focus', description: '12%+ YoY growth' },
  { value: 'value', label: 'Value Play', description: 'Below market price' },
  { value: 'balanced', label: 'Balanced', description: 'Growth + yield mix' },
];

const PROPERTY_TYPES: { value: PropertyType; label: string; note: string }[] = [
  { value: 'HDB', label: 'HDB', note: 'MRT impact minimal ~$5/100m' },
  { value: 'Condominium', label: 'Condominium', note: '15x MRT sensitive' },
  { value: 'EC', label: 'EC', note: 'Volatile post-COVID' },
];

const REGIONS: { value: Region; label: string }[] = [
  { value: 'CCR', label: 'Core Central Region' },
  { value: 'RCR', label: 'Rest of Central Region' },
  { value: 'OCR', label: 'Outside Central Region' },
];

const TIME_HORIZONS: { value: TimeHorizon; label: string; description: string }[] = [
  { value: 'short', label: 'Short-term', description: '1-3 years' },
  { value: 'medium', label: 'Medium-term', description: '3-7 years' },
  { value: 'long', label: 'Long-term', description: '7+ years' },
];

export default function FilterPanel({ filters, onFilterChange, onReset, activeFilterCount }: FilterPanelProps) {
  return (
    <div className="w-full lg:w-80 flex-shrink-0 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-foreground">Filters</h3>
        <button
          onClick={onReset}
          className="text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          Reset {activeFilterCount > 0 && `(${activeFilterCount})`}
        </button>
      </div>

      {/* Investment Goal */}
      <FilterSection title="Investment Goal">
        <div className="space-y-2">
          {INVESTMENT_GOALS.map((goal) => (
            <label
              key={goal.value}
              className={`
                flex items-start p-3 rounded-lg border cursor-pointer transition-all
                ${filters.investmentGoal === goal.value
                  ? 'border-primary bg-primary/5'
                  : 'border-border hover:border-primary/50'
                }
              `}
            >
              <input
                type="radio"
                name="investmentGoal"
                value={goal.value}
                checked={filters.investmentGoal === goal.value}
                onChange={(e) => onFilterChange('investmentGoal', e.target.value as InvestmentGoal)}
                className="mt-1 mr-3"
              />
              <div>
                <div className="font-medium text-sm">{goal.label}</div>
                <div className="text-xs text-muted-foreground">{goal.description}</div>
              </div>
            </label>
          ))}
        </div>
      </FilterSection>

      {/* Budget Range */}
      <FilterSection title="Budget Range (Price PSF)">
        <div className="space-y-4">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">${filters.budgetRange[0]}</span>
            <span className="text-foreground font-medium">${filters.budgetRange[1]}+</span>
          </div>
          <input
            type="range"
            min="300"
            max="1500"
            step="50"
            value={filters.budgetRange[0]}
            onChange={(e) => onFilterChange('budgetRange', [parseInt(e.target.value), filters.budgetRange[1]])}
            className="w-full"
          />
          <input
            type="range"
            min="300"
            max="1500"
            step="50"
            value={filters.budgetRange[1]}
            onChange={(e) => onFilterChange('budgetRange', [filters.budgetRange[0], parseInt(e.target.value)])}
            className="w-full"
          />
        </div>
      </FilterSection>

      {/* Property Type */}
      <FilterSection title="Property Type">
        <div className="space-y-2">
          {PROPERTY_TYPES.map((type) => (
            <label
              key={type.value}
              className={`
                flex items-start p-3 rounded-lg border cursor-pointer transition-all
                ${filters.propertyTypes.includes(type.value)
                  ? 'border-primary bg-primary/5'
                  : 'border-border hover:border-primary/50'
                }
              `}
            >
              <input
                type="checkbox"
                checked={filters.propertyTypes.includes(type.value)}
                onChange={(e) => {
                  const updated = e.target.checked
                    ? [...filters.propertyTypes, type.value]
                    : filters.propertyTypes.filter((t) => t !== type.value);
                  onFilterChange('propertyTypes', updated);
                }}
                className="mt-1 mr-3"
              />
              <div>
                <div className="font-medium text-sm">{type.label}</div>
                <div className="text-xs text-muted-foreground">{type.note}</div>
              </div>
            </label>
          ))}
        </div>
      </FilterSection>

      {/* Location */}
      <FilterSection title="Location">
        <div className="space-y-2">
          {REGIONS.map((region) => (
            <label
              key={region.value}
              className={`
                flex items-center p-3 rounded-lg border cursor-pointer transition-all
                ${filters.locations.includes(region.value)
                  ? 'border-primary bg-primary/5'
                  : 'border-border hover:border-primary/50'
                }
              `}
            >
              <input
                type="checkbox"
                checked={filters.locations.includes(region.value)}
                onChange={(e) => {
                  const updated = e.target.checked
                    ? [...filters.locations, region.value]
                    : filters.locations.filter((r) => r !== region.value);
                  onFilterChange('locations', updated);
                }}
                className="mr-3"
              />
              <span className="text-sm font-medium">{region.label}</span>
            </label>
          ))}
        </div>
      </FilterSection>

      {/* Time Horizon */}
      <FilterSection title="Time Horizon">
        <div className="space-y-2">
          {TIME_HORIZONS.map((horizon) => (
            <label
              key={horizon.value}
              className={`
                flex items-start p-3 rounded-lg border cursor-pointer transition-all
                ${filters.timeHorizon === horizon.value
                  ? 'border-primary bg-primary/5'
                  : 'border-border hover:border-primary/50'
                }
              `}
            >
              <input
                type="radio"
                name="timeHorizon"
                value={horizon.value}
                checked={filters.timeHorizon === horizon.value}
                onChange={(e) => onFilterChange('timeHorizon', e.target.value as TimeHorizon)}
                className="mt-1 mr-3"
              />
              <div>
                <div className="font-medium text-sm">{horizon.label}</div>
                <div className="text-xs text-muted-foreground">{horizon.description}</div>
              </div>
            </label>
          ))}
        </div>
      </FilterSection>
    </div>
  );
}

function FilterSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h4 className="text-sm font-medium text-foreground mb-3">{title}</h4>
      {children}
    </div>
  );
}
