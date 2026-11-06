// app/src/components/dashboard/segments/FilterPanel.tsx
/**
 * Visible constraints for the segment workspace.
 *
 * Copy only: ranges are PSF (not total budget), the spatial class is a hard
 * filter, and the weighted fit is explained from the real weights in
 * `useSegmentMatching`. No archive model claim is repeated as fact here.
 */
import type { ReactNode } from "react";
import type {
  FilterState,
  PropertyType,
  Region,
  SpatialCluster,
} from "@/types/segments";
import {
  SEGMENT_MATCH_RULE_NOTES,
  SEGMENT_MATCH_WEIGHTS,
} from "@/hooks/useSegmentMatching";

interface FilterPanelProps {
  filters: FilterState;
  onFilterChange: <K extends keyof FilterState>(
    key: K,
    value: FilterState[K],
  ) => void;
  onReset: () => void;
  activeFilterCount: number;
}

const PROPERTY_TYPES: { value: PropertyType; label: string }[] = [
  { value: "HDB", label: "HDB" },
  { value: "Condominium", label: "Condominium" },
  { value: "EC", label: "EC" },
];

const REGIONS: { value: Region; label: string }[] = [
  { value: "CCR", label: "Core Central Region" },
  { value: "RCR", label: "Rest of Central Region" },
  { value: "OCR", label: "Outside Central Region" },
];

const SPATIAL_OPTIONS: {
  value: SpatialCluster | "all";
  label: string;
  description: string;
}[] = [
  {
    value: "all",
    label: "All classes",
    description: "Every segment whose other criteria fit",
  },
  {
    value: "HH",
    label: "HH",
    description: "Stored high-price / high-growth label",
  },
  {
    value: "LL",
    label: "LL",
    description: "Stored low-price / low-growth label",
  },
  {
    value: "HL",
    label: "HL",
    description: "Stored high-price / low-growth label",
  },
  {
    value: "LH",
    label: "LH",
    description: "Stored low-price / high-growth label",
  },
];

export default function FilterPanel({
  filters,
  onFilterChange,
  onReset,
  activeFilterCount,
}: FilterPanelProps) {
  return (
    <div className="w-full lg:w-80 flex-shrink-0 space-y-5 rounded-2xl border border-border bg-card p-5">
      <div className="space-y-3">
        <div className="flex items-center justify-between gap-2">
          <h3 className="text-lg font-semibold text-foreground">Constraints</h3>
          <button
            onClick={onReset}
            className="text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            Reset to persona settings
            {activeFilterCount > 0 && ` (${activeFilterCount})`}
          </button>
        </div>
        <div className="rounded-xl border border-border bg-muted/30 px-3 py-2 text-sm text-muted-foreground">
          {activeFilterCount > 0
            ? `${activeFilterCount} active filter${activeFilterCount > 1 ? "s" : ""} shaping the shortlist.`
            : "No constraints applied. All compatible segments are shown."}{" "}
          Ranges are PSF, not total budget.
        </div>
        <p className="text-sm text-muted-foreground">
          Current matching is weighted: a partial match may remain. The
          spatial-class filter is hard.
        </p>
        <details className="rounded-xl border border-border bg-background px-3 py-2 text-sm text-muted-foreground">
          <summary className="cursor-pointer font-medium text-foreground">
            Explain match calculation
          </summary>
          <ul className="mt-2 space-y-1">
            <li>
              Investment goal &middot; {SEGMENT_MATCH_WEIGHTS.investmentGoal}{" "}
              points (only when a goal is set)
            </li>
            <li>PSF range &middot; {SEGMENT_MATCH_WEIGHTS.budget} points</li>
            <li>
              Property type &middot; {SEGMENT_MATCH_WEIGHTS.propertyType} points
            </li>
            <li>Region &middot; {SEGMENT_MATCH_WEIGHTS.location} points</li>
            <li>
              Time horizon &middot; {SEGMENT_MATCH_WEIGHTS.timeHorizon} points
              (only when set)
            </li>
          </ul>
          <p className="mt-2">{SEGMENT_MATCH_RULE_NOTES.hardFilter}</p>
          <p className="mt-1">{SEGMENT_MATCH_RULE_NOTES.optional}</p>
          <p className="mt-1">{SEGMENT_MATCH_RULE_NOTES.rounding}</p>
        </details>
      </div>

      <FilterSection title="Price PSF range">
        <div className="space-y-3">
          <div className="space-y-1">
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Min PSF</span>
              <span className="text-foreground font-medium">
                S${filters.budgetRange[0]}
              </span>
            </div>
            <input
              type="range"
              min="300"
              max="1500"
              step="50"
              value={filters.budgetRange[0]}
              aria-label="Minimum price per square foot"
              onChange={(e) => {
                const newMin = parseInt(e.target.value);
                if (newMin < filters.budgetRange[1]) {
                  onFilterChange("budgetRange", [
                    newMin,
                    filters.budgetRange[1],
                  ]);
                }
              }}
              className="w-full h-2 bg-muted rounded-lg appearance-none cursor-pointer accent-primary"
            />
          </div>

          <div className="space-y-1">
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Max PSF</span>
              <span className="text-foreground font-medium">
                {filters.budgetRange[1] >= 1500
                  ? "S$1500+"
                  : `S$${filters.budgetRange[1]}`}
              </span>
            </div>
            <input
              type="range"
              min="300"
              max="1500"
              step="50"
              value={filters.budgetRange[1]}
              aria-label="Maximum price per square foot"
              onChange={(e) => {
                const newMax = parseInt(e.target.value);
                if (newMax > filters.budgetRange[0]) {
                  onFilterChange("budgetRange", [
                    filters.budgetRange[0],
                    newMax,
                  ]);
                }
              }}
              className="w-full h-2 bg-muted rounded-lg appearance-none cursor-pointer accent-primary"
            />
          </div>

          <div className="pt-2 border-t border-border mt-2">
            <div className="text-xs text-center text-muted-foreground">
              Current range:{" "}
              <span className="text-foreground font-medium">
                S${filters.budgetRange[0]} to S${filters.budgetRange[1]}+ PSF
              </span>
            </div>
          </div>
        </div>
      </FilterSection>

      <FilterSection title="Property type">
        <div className="space-y-2">
          {PROPERTY_TYPES.map((type) => (
            <label
              key={type.value}
              className={`
                flex items-start p-3 rounded-lg border cursor-pointer transition-all
                ${
                  filters.propertyTypes.includes(type.value)
                    ? "border-primary bg-primary/5"
                    : "border-border hover:border-primary/50"
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
                  onFilterChange("propertyTypes", updated);
                }}
                className="mt-1 mr-3"
              />
              <div>
                <div className="font-medium text-sm">{type.label}</div>
              </div>
            </label>
          ))}
        </div>
      </FilterSection>

      <FilterSection title="Region">
        <div className="space-y-2">
          {REGIONS.map((region) => (
            <label
              key={region.value}
              className={`
                flex items-center p-3 rounded-lg border cursor-pointer transition-all
                ${
                  filters.locations.includes(region.value)
                    ? "border-primary bg-primary/5"
                    : "border-border hover:border-primary/50"
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
                  onFilterChange("locations", updated);
                }}
                className="mr-3"
              />
              <span className="text-sm font-medium">{region.label}</span>
            </label>
          ))}
        </div>
      </FilterSection>

      <FilterSection title="Spatial class">
        <div className="space-y-2">
          {SPATIAL_OPTIONS.map((option) => (
            <label
              key={option.value}
              className={`
                flex items-start p-3 rounded-lg border cursor-pointer transition-all
                ${
                  filters.hotspotFilter === option.value
                    ? "border-primary bg-primary/5"
                    : "border-border hover:border-primary/50"
                }
              `}
            >
              <input
                type="radio"
                name="hotspotFilter"
                value={option.value}
                checked={filters.hotspotFilter === option.value}
                onChange={(e) =>
                  onFilterChange(
                    "hotspotFilter",
                    e.target.value as SpatialCluster | "all",
                  )
                }
                className="mt-1 mr-3"
              />
              <div>
                <div className="font-medium text-sm">{option.label}</div>
                <div className="text-xs text-muted-foreground">
                  {option.description}
                </div>
              </div>
            </label>
          ))}
          <p className="text-xs text-muted-foreground">
            Class labels are stored archive labels, not verified hotspot
            probabilities.
          </p>
        </div>
      </FilterSection>
    </div>
  );
}

function FilterSection({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <div>
      <h4 className="text-sm font-medium text-foreground mb-3">{title}</h4>
      {children}
    </div>
  );
}
