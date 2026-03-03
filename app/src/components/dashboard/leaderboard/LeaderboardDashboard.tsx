// app/src/components/dashboard/leaderboard/LeaderboardDashboard.tsx
import React, { useState } from 'react';
import { useFilterState } from '@/hooks/useFilterState';
import { useLeaderboardData } from '@/hooks/useLeaderboardData';
import type { LeaderboardEntry, LeaderboardMetric, MetricMeta } from '@/types/leaderboard';
import FilterPanel from '@/components/dashboard/segments/FilterPanel';
import LeaderboardMap from './LeaderboardMap';
import LeaderboardTable from './LeaderboardTable';
import MetricHelpModal, { METRICS } from './MetricHelpModal';
import { Loader2, HelpCircle } from 'lucide-react';

interface LeaderboardDashboardProps {
  initialData?: LeaderboardEntry[];
}

const DEFAULT_METRIC: LeaderboardMetric = 'yoy_growth_pct';

export default function LeaderboardDashboard({ initialData }: LeaderboardDashboardProps) {
  // Filter state management - use debounced filters for expensive operations
  const { filters, debouncedFilters, persona, setPersona, updateFilter, resetFilters, activeFilterCount } =
    useFilterState('all');

  // Metric selection state
  const [selectedMetric, setSelectedMetric] = useState<LeaderboardMetric>(DEFAULT_METRIC);

  // Help modal state
  const [showHelpModal, setShowHelpModal] = useState(false);

  // Highlight state for map/table sync
  const [highlightedArea, setHighlightedArea] = useState<string | null>(null);

  // Load and filter leaderboard data using debounced filters for smooth performance
  const { data, loading, error, reload } = useLeaderboardData(debouncedFilters, selectedMetric);

  // Get metric metadata
  const metricMeta = METRICS.find(m => m.key === selectedMetric) || METRICS[0];

  // Handle area hover from map
  const handleAreaHover = (area: string | null) => {
    setHighlightedArea(area);
  };

  // Handle area click from map
  const handleAreaClick = (area: string) => {
    setHighlightedArea(area);
    // Scroll to table row
    const rowElement = document.querySelector(`[data-area="${area}"]`);
    if (rowElement) {
      rowElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  };

  // Handle row hover from table
  const handleRowHover = (area: string | null) => {
    setHighlightedArea(area);
  };

  // Handle row click from table
  const handleRowClick = (area: string) => {
    setHighlightedArea(area);
  };

  // Handle metric change
  const handleMetricChange = (metric: LeaderboardMetric) => {
    setSelectedMetric(metric);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-muted-foreground">Loading leaderboard data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="max-w-md text-center space-y-4">
          <div className="text-red-500 text-6xl">⚠️</div>
          <h2 className="text-xl font-bold">Unable to Load Data</h2>
          <p className="text-muted-foreground">{error}</p>
          <button
            onClick={reload}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold">Area Rankings</h1>
              <p className="text-sm text-muted-foreground mt-1">
                Explore Singapore planning areas by performance metrics
              </p>
            </div>
            <button
              onClick={() => setShowHelpModal(true)}
              className="flex items-center gap-2 px-4 py-2 bg-muted hover:bg-muted/80 rounded-md transition-colors"
              aria-label="View metric definitions"
            >
              <HelpCircle className="h-4 w-4" />
              <span>Metrics Guide</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="container mx-auto px-4 py-6">
        {/* Metric Selector */}
        <div className="mb-6">
          <label className="text-sm font-medium text-muted-foreground mb-2 block">
            Display Metric
          </label>
          <div className="flex flex-wrap gap-2">
            {METRICS.map(metric => (
              <button
                key={metric.key}
                onClick={() => handleMetricChange(metric.key as LeaderboardMetric)}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  selectedMetric === metric.key
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-muted hover:bg-muted/80'
                }`}
              >
                {metric.label}
              </button>
            ))}
          </div>
        </div>

        {/* Active Filters Info */}
        {activeFilterCount > 0 && (
          <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-md flex items-center justify-between">
            <span className="text-sm text-blue-800">
              {activeFilterCount} filter{activeFilterCount > 1 ? 's' : ''} active • Showing {data.length} areas
            </span>
            <button
              onClick={resetFilters}
              className="text-sm text-blue-600 hover:text-blue-800 font-medium"
            >
              Reset Filters
            </button>
          </div>
        )}

        {/* Layout: Sidebar + Main Content */}
        <div className="flex gap-6">
          {/* Filter Sidebar */}
          <aside className="w-80 flex-shrink-0 hidden lg:block">
            <div className="sticky top-24">
              <FilterPanel
                filters={filters}
                persona={persona}
                onFilterChange={updateFilter}
                onPersonaChange={setPersona}
                onReset={resetFilters}
              />
            </div>
          </aside>

          {/* Main Content Area */}
          <main className="flex-1 min-w-0">
            {/* Mobile Filter Toggle */}
            <div className="lg:hidden mb-4">
              <button
                onClick={() => {/* TODO: Implement mobile filter drawer */}}
                className="w-full px-4 py-3 bg-muted hover:bg-muted/80 rounded-md font-medium flex items-center justify-center gap-2"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3" />
                </svg>
                Filters ({activeFilterCount} active)
              </button>
            </div>

            {/* Map View */}
            <div className="mb-6">
              <div className="bg-card border border-border rounded-lg overflow-hidden">
                <div className="p-4 border-b">
                  <h2 className="text-lg font-semibold">Geographic View</h2>
                  <p className="text-sm text-muted-foreground">
                    Color-coded by {metricMeta.label.toLowerCase()}
                  </p>
                </div>
                <div className="h-[500px]">
                  <LeaderboardMap
                    data={data}
                    selectedMetric={selectedMetric}
                    metricMeta={metricMeta}
                    filters={debouncedFilters}
                    highlightedArea={highlightedArea}
                    onAreaHover={handleAreaHover}
                    onAreaClick={handleAreaClick}
                  />
                </div>
              </div>
            </div>

            {/* Table View */}
            <div>
              <div className="bg-card border border-border rounded-lg overflow-hidden">
                <div className="p-4 border-b">
                  <h2 className="text-lg font-semibold">Detailed Rankings</h2>
                  <p className="text-sm text-muted-foreground">
                    Click column headers to sort • Hover rows to highlight on map
                  </p>
                </div>
                <div className="p-4">
                  <LeaderboardTable
                    data={data}
                    highlightedArea={highlightedArea}
                    onRowHover={handleRowHover}
                    onRowClick={handleRowClick}
                    sortBy={selectedMetric}
                    onSortChange={handleMetricChange}
                  />
                </div>
              </div>
            </div>
          </main>
        </div>
      </div>

      {/* Help Modal */}
      <MetricHelpModal isOpen={showHelpModal} onClose={() => setShowHelpModal(false)} />
    </div>
  );
}
