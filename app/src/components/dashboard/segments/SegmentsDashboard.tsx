// app/src/components/dashboard/segments/SegmentsDashboard.tsx
import { useState } from 'react';
import { useSegmentsData } from '@/hooks/useSegmentsData';
import { useFilterState } from '@/hooks/useFilterState';
import { useSegmentMatching } from '@/hooks/useSegmentMatching';
import { Segment, Persona } from '@/types/segments';
import PersonaSelector from '@/components/dashboard/PersonaSelector';
import FilterPanel from './FilterPanel';
import TabNavigation from './TabNavigation';
import { DiscoverTab } from './discover/DiscoverTab';
import { CompareTab } from './compare/CompareTab';
import { DetailsTab } from './details/DetailsTab';

type TabId = 'discover' | 'compare' | 'details';

export default function SegmentsDashboard() {
  const { data, loading, error } = useSegmentsData();
  const { filters, persona, setPersona, updateFilter, resetFilters, activeFilterCount } =
    useFilterState();
  const [activeTab, setActiveTab] = useState<TabId>('discover');
  const [selectedSegment, setSelectedSegment] = useState<Segment | null>(null);
  const [comparisonSet, setComparisonSet] = useState<Set<string>>(new Set());

  // Handle loading state
  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4" />
          <p className="text-muted-foreground">Loading segments data...</p>
        </div>
      </div>
    );
  }

  // Handle error state
  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center max-w-md">
          <div className="text-6xl mb-4">⚠️</div>
          <h3 className="text-lg font-semibold text-foreground mb-2">Failed to load data</h3>
          <p className="text-muted-foreground mb-4">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!data) {
    return null;
  }

  // Get matched segments
  const { matchedSegments } = useSegmentMatching(data.segments, filters);

  // Handlers
  const handleViewDetails = (segment: Segment) => {
    setSelectedSegment(segment);
    setActiveTab('details');
  };

  const handleAddToCompare = (segment: Segment) => {
    setComparisonSet((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(segment.id)) {
        newSet.delete(segment.id);
      } else if (newSet.size < 4) {
        newSet.add(segment.id);
      }
      return newSet;
    });
  };

  const comparisonSegments = data.segments.filter((s) => comparisonSet.has(s.id));

  return (
    <div className="space-y-6">
      {/* Header with Persona Selector */}
      <div>
        <h1 className="text-3xl font-bold text-foreground mb-2">Market Segments</h1>
        <p className="text-muted-foreground mb-6">
          Explore property market segments with interactive filters and persona-based insights
        </p>
        <PersonaSelector selected={persona} onChange={setPersona} />
      </div>

      {/* Tab Navigation */}
      <TabNavigation
        activeTab={activeTab}
        onTabChange={setActiveTab}
        disabledTabs={comparisonSet.size < 2 ? ['compare'] : []}
      />

      {/* Main Content */}
      <div className="flex flex-col lg:flex-row gap-6">
        {/* Filter Sidebar */}
        <FilterPanel
          filters={filters}
          onFilterChange={updateFilter}
          onReset={resetFilters}
          activeFilterCount={activeFilterCount}
        />

        {/* Content Area */}
        <div className="flex-1">
          {activeTab === 'discover' && (
            <DiscoverTab
              segments={matchedSegments}
              insights={data.insights}
              persona={persona}
              onViewDetails={handleViewDetails}
              onAddToCompare={handleAddToCompare}
              comparisonSet={comparisonSet}
            />
          )}

          {activeTab === 'compare' && (
            <CompareTab
              segments={comparisonSegments}
              allSegments={data.segments}
              persona={persona}
            />
          )}

          {activeTab === 'details' && selectedSegment && (
            <DetailsTab
              segment={selectedSegment}
              planningAreas={data.planningAreas}
              persona={persona}
              onBack={() => setActiveTab('discover')}
            />
          )}
        </div>
      </div>
    </div>
  );
}
