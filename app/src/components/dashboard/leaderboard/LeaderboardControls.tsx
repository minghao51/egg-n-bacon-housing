import React from 'react';
import type {
  LeaderboardControlsState,
  LeaderboardPropertyType,
  LeaderboardTimeBasis,
} from '@/types/leaderboard';
import type { Region } from '@/types/segments';

interface LeaderboardControlsProps {
  controls: LeaderboardControlsState;
  activeFilterCount: number;
  onChange: <K extends keyof LeaderboardControlsState>(
    key: K,
    value: LeaderboardControlsState[K]
  ) => void;
  onReset: () => void;
  compact?: boolean;
}

const REGION_OPTIONS: { value: Region; label: string }[] = [
  { value: 'CCR', label: 'Core Central Region' },
  { value: 'RCR', label: 'Rest of Central Region' },
  { value: 'OCR', label: 'Outside Central Region' },
];

const PROPERTY_TYPE_OPTIONS: { value: LeaderboardPropertyType; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'hdb', label: 'HDB' },
  { value: 'condo', label: 'Condo' },
  { value: 'ec', label: 'EC' },
];

const TIME_BASIS_OPTIONS: { value: LeaderboardTimeBasis; label: string }[] = [
  { value: 'recent', label: 'Recent' },
  { value: 'whole', label: 'All-time' },
  { value: 'year_2025', label: '2025' },
];

function formatCurrency(value: number): string {
  if (value >= 1000000) {
    return `$${(value / 1000000).toFixed(value % 1000000 === 0 ? 0 : 1)}M`;
  }
  return `$${Math.round(value / 1000)}k`;
}

export default function LeaderboardControls({
  controls,
  activeFilterCount,
  onChange,
  onReset,
  compact = false,
}: LeaderboardControlsProps) {
  const sectionGap = compact ? 'space-y-4' : 'space-y-6';

  return (
    <div className={`rounded-2xl border border-border bg-card p-4 shadow-sm ${sectionGap}`}>
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-foreground">Filters</h2>
          <p className="text-xs text-muted-foreground">Every control updates the map and rankings.</p>
        </div>
        <button
          type="button"
          onClick={onReset}
          className="rounded-md px-3 py-1.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
        >
          Reset {activeFilterCount > 0 ? `(${activeFilterCount})` : ''}
        </button>
      </div>

      <FilterSection title="Region">
        <div className="space-y-2">
          {REGION_OPTIONS.map((option) => {
            const checked = controls.region.includes(option.value);
            return (
              <label
                key={option.value}
                className={`flex items-center gap-3 rounded-xl border px-3 py-2 text-sm transition-colors ${
                  checked ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/40'
                }`}
              >
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={(event) => {
                    const next = event.target.checked
                      ? [...controls.region, option.value]
                      : controls.region.filter((region) => region !== option.value);
                    onChange('region', next);
                  }}
                />
                <span>{option.label}</span>
              </label>
            );
          })}
        </div>
      </FilterSection>

      <FilterSection title="Property Type">
        <SegmentedButtons
          options={PROPERTY_TYPE_OPTIONS}
          value={controls.propertyType}
          onChange={(value) => onChange('propertyType', value)}
        />
      </FilterSection>

      <FilterSection title="Time Basis">
        <SegmentedButtons
          options={TIME_BASIS_OPTIONS}
          value={controls.timeBasis}
          onChange={(value) => onChange('timeBasis', value)}
        />
      </FilterSection>

      <FilterSection title="Median Price Range">
        <div className="space-y-3">
          <RangeSlider
            label="Min"
            value={controls.priceRange[0]}
            min={300000}
            max={2500000}
            step={50000}
            displayValue={formatCurrency(controls.priceRange[0])}
            onChange={(value) => {
              if (value < controls.priceRange[1]) {
                onChange('priceRange', [value, controls.priceRange[1]]);
              }
            }}
          />
          <RangeSlider
            label="Max"
            value={controls.priceRange[1]}
            min={300000}
            max={2500000}
            step={50000}
            displayValue={formatCurrency(controls.priceRange[1])}
            onChange={(value) => {
              if (value > controls.priceRange[0]) {
                onChange('priceRange', [controls.priceRange[0], value]);
              }
            }}
          />
          <div className="rounded-xl bg-muted/50 px-3 py-2 text-xs text-muted-foreground">
            Showing areas between{' '}
            <span className="font-medium text-foreground">{formatCurrency(controls.priceRange[0])}</span>{' '}
            and <span className="font-medium text-foreground">{formatCurrency(controls.priceRange[1])}</span>.
          </div>
        </div>
      </FilterSection>
    </div>
  );
}

function FilterSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-3">
      <h3 className="text-sm font-semibold text-foreground">{title}</h3>
      {children}
    </section>
  );
}

function SegmentedButtons<T extends string>({
  options,
  value,
  onChange,
}: {
  options: { value: T; label: string }[];
  value: T;
  onChange: (value: T) => void;
}) {
  return (
    <div className="grid grid-cols-2 gap-2">
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          onClick={() => onChange(option.value)}
          className={`rounded-xl border px-3 py-2 text-sm font-medium transition-colors ${
            value === option.value
              ? 'border-primary bg-primary text-primary-foreground'
              : 'border-border bg-background hover:border-primary/40'
          }`}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

function RangeSlider({
  label,
  value,
  min,
  max,
  step,
  displayValue,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  displayValue: string;
  onChange: (value: number) => void;
}) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-xs">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-medium text-foreground">{displayValue}</span>
      </div>
      <input
        type="range"
        value={value}
        min={min}
        max={max}
        step={step}
        onChange={(event) => onChange(Number(event.target.value))}
        className="h-2 w-full cursor-pointer appearance-none rounded-lg bg-muted accent-primary"
      />
    </div>
  );
}
