// app/src/components/dashboard/segments/FilterPanel.tsx
import type { ReactNode } from 'react';
import type { FilterState, PropertyType, Region, SpatialCluster } from '@/types/segments';

interface FilterPanelProps {
  filters: FilterState;
  onFilterChange: <K extends keyof FilterState>(key: K, value: FilterState[K]) => void;
  onReset: () => void;
  activeFilterCount: number;
}

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

const HOTSPOT_OPTIONS: { value: SpatialCluster | 'all'; label: string; icon: string; description: string }[] = [
  { value: 'all', label: 'All Areas', icon: '🌐', description: 'Show all segments' },
  { value: 'HH', label: 'Hotspots Only', icon: '🔥', description: 'High-price clusters (58-62% persistence)' },
  { value: 'LL', label: 'Coldspots Only', icon: '❄️', description: 'Low-price clusters (value opportunities)' },
  { value: 'HL', label: 'Pioneers', icon: '⚡', description: 'High prices in low-price areas' },
  { value: 'LH', label: 'Transitions', icon: '🔄', description: 'Low prices near high-price areas' },
];

export default function FilterPanel({ filters, onFilterChange, onReset, activeFilterCount }: FilterPanelProps) {
  return (
    <div className="w-full lg:w-80 flex-shrink-0 space-y-5 rounded-2xl border border-border bg-card p-5">
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-foreground">Constraints</h3>
          <button
            onClick={onReset}
            className="text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            Reset {activeFilterCount > 0 && `(${activeFilterCount})`}
          </button>
        </div>
        <div className="rounded-xl border border-border bg-muted/30 px-3 py-2 text-sm text-muted-foreground">
          {activeFilterCount > 0
            ? `${activeFilterCount} active filter${activeFilterCount > 1 ? 's' : ''} shaping the shortlist`
            : 'No constraints applied. All compatible segments are shown.'}
        </div>
      </div>

      <FilterSection title="Budget Range (Price PSF)">
        <div className="space-y-3">
          <div className="space-y-1">
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Min PSF</span>
              <span className="text-foreground font-medium">${filters.budgetRange[0]}</span>
            </div>
            <input
              type="range"
              min="300"
              max="1500"
              step="50"
              value={filters.budgetRange[0]}
              onChange={(e) => {
                const newMin = parseInt(e.target.value);
                if (newMin < filters.budgetRange[1]) {
                  onFilterChange('budgetRange', [newMin, filters.budgetRange[1]]);
                }
              }}
              className="w-full h-2 bg-muted rounded-lg appearance-none cursor-pointer accent-primary"
            />
          </div>

          <div className="space-y-1">
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Max PSF</span>
              <span className="text-foreground font-medium">
                {filters.budgetRange[1] >= 1500 ? '$1500+' : `$${filters.budgetRange[1]}`}
              </span>
            </div>
            <input
              type="range"
              min="300"
              max="1500"
              step="50"
              value={filters.budgetRange[1]}
              onChange={(e) => {
                const newMax = parseInt(e.target.value);
                if (newMax > filters.budgetRange[0]) {
                  onFilterChange('budgetRange', [filters.budgetRange[0], newMax]);
                }
              }}
              className="w-full h-2 bg-muted rounded-lg appearance-none cursor-pointer accent-primary"
            />
          </div>

          <div className="pt-2 border-t border-border mt-2">
            <div className="text-xs text-center text-muted-foreground">
              Current range:{' '}
              <span className="text-foreground font-medium">
                ${filters.budgetRange[0]} - ${filters.budgetRange[1]}+ PSF
              </span>
            </div>
          </div>
        </div>
      </FilterSection>

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

      <FilterSection title="Spatial Hotspot">
        <div className="space-y-2">
          {HOTSPOT_OPTIONS.map((option) => (
            <label
              key={option.value}
              className={`
                flex items-start p-3 rounded-lg border cursor-pointer transition-all
                ${filters.hotspotFilter === option.value
                  ? 'border-primary bg-primary/5'
                  : 'border-border hover:border-primary/50'
                }
              `}
            >
              <input
                type="radio"
                name="hotspotFilter"
                value={option.value}
                checked={filters.hotspotFilter === option.value}
                onChange={(e) => onFilterChange('hotspotFilter', e.target.value as SpatialCluster | 'all')}
                className="mt-1 mr-3"
              />
              <div>
                <div className="flex items-center gap-1">
                  <span className="text-sm">{option.icon}</span>
                  <div className="font-medium text-sm">{option.label}</div>
                </div>
                <div className="text-xs text-muted-foreground">{option.description}</div>
              </div>
            </label>
          ))}
        </div>
      </FilterSection>
    </div>
  );
}

function FilterSection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div>
      <h4 className="text-sm font-medium text-foreground mb-3">{title}</h4>
      {children}
    </div>
  );
}
