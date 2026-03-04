// app/src/components/dashboard/segments/SegmentsDashboard.tsx
import { useEffect, useRef, useState } from 'react';
import { HelpCircle } from 'lucide-react';
import { useSegmentsData } from '@/hooks/useSegmentsData';
import { useFilterState } from '@/hooks/useFilterState';
import { useSegmentMatching } from '@/hooks/useSegmentMatching';
import type { Segment, Persona } from '@/types/segments';
import PersonaSelector from '@/components/dashboard/PersonaSelector';
import FilterPanel from './FilterPanel';
import TabNavigation from './TabNavigation';
import { DiscoverTab } from './discover/DiscoverTab';
import { CompareTab } from './compare/CompareTab';
import { InvestigateTab } from './investigate/InvestigateTab';
import SegmentMetricGuideModal from './investigate/SegmentMetricGuideModal';

type TabId = 'discover' | 'investigate' | 'compare';

function personaLabel(persona: Persona): string {
  switch (persona) {
    case 'all':
      return 'All Personas';
    case 'investor':
      return 'Investor';
    case 'first-time-buyer':
      return 'First-Time Buyer';
    case 'upgrader':
      return 'Upgrader';
    default:
      return persona;
  }
}

export default function SegmentsDashboard() {
  const { data, loading, error } = useSegmentsData();
  const { filters, debouncedFilters, persona, setPersona, updateFilter, resetFilters, activeFilterCount } =
    useFilterState('all', { countVisibleFiltersOnly: true });
  const [activeTab, setActiveTab] = useState<TabId>('discover');
  const [selectedSegment, setSelectedSegment] = useState<Segment | null>(null);
  const [comparisonSet, setComparisonSet] = useState<Set<string>>(new Set());
  const [selectedArea, setSelectedArea] = useState<string | null>(null);
  const [showMetricGuide, setShowMetricGuide] = useState(false);
  const hasHydratedFromUrl = useRef(false);

  const { matchedSegments, scoredSegments } = useSegmentMatching(data?.segments ?? [], debouncedFilters);

  useEffect(() => {
    if (typeof window === 'undefined' || hasHydratedFromUrl.current || !data) {
      return;
    }

    const params = new URLSearchParams(window.location.search);
    const personaParam = params.get('persona');
    const segmentParam = params.get('segment');
    const comparisonParam = params.get('segments');
    const areaParam = params.get('area');
    const tabParam = params.get('tab');

    if (personaParam === 'all' || personaParam === 'investor' || personaParam === 'first-time-buyer' || personaParam === 'upgrader') {
      setPersona(personaParam);
    }

    if (segmentParam) {
      const nextSegment = data.segments.find((segment) => segment.id === segmentParam);
      if (nextSegment) {
        setSelectedSegment(nextSegment);
      }
    }

    if (comparisonParam) {
      const nextSet = new Set(
        comparisonParam
          .split(',')
          .filter(Boolean)
          .slice(0, 4)
          .filter((segmentId) => data.segments.some((segment) => segment.id === segmentId))
      );
      setComparisonSet(nextSet);
    }

    if (areaParam) {
      setSelectedArea(areaParam.toUpperCase());
    }

    if (tabParam === 'discover' || tabParam === 'investigate' || tabParam === 'compare') {
      setActiveTab(tabParam);
    }

    hasHydratedFromUrl.current = true;
  }, [data, setPersona]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    const url = new URL(window.location.href);
    url.searchParams.set('persona', persona);

    if (activeTab !== 'discover') {
      url.searchParams.set('tab', activeTab);
    } else {
      url.searchParams.delete('tab');
    }

    if (selectedSegment) {
      url.searchParams.set('segment', selectedSegment.id);
    } else {
      url.searchParams.delete('segment');
    }

    if (comparisonSet.size > 0) {
      url.searchParams.set('segments', Array.from(comparisonSet).join(','));
    } else {
      url.searchParams.delete('segments');
    }

    if (selectedArea) {
      url.searchParams.set('area', selectedArea);
    } else {
      url.searchParams.delete('area');
    }

    window.history.replaceState({}, '', url.toString());
  }, [activeTab, comparisonSet, persona, selectedArea, selectedSegment]);

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="text-center">
          <div className="mx-auto mb-4 h-12 w-12 animate-spin rounded-full border-b-2 border-primary" />
          <p className="text-muted-foreground">Loading segments data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="max-w-md text-center">
          <div className="mb-4 text-6xl">⚠️</div>
          <h3 className="mb-2 text-lg font-semibold text-foreground">Failed to load data</h3>
          <p className="mb-4 text-muted-foreground">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="rounded-md bg-primary px-4 py-2 text-primary-foreground hover:bg-primary/90"
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

  const handleInvestigateSegment = (segment: Segment) => {
    setSelectedSegment(segment);
    setSelectedArea(null);
    setActiveTab('investigate');
  };

  const handleAddToCompare = (segment: Segment) => {
    setComparisonSet((prev) => {
      const next = new Set(prev);
      if (next.has(segment.id)) {
        next.delete(segment.id);
      } else if (next.size < 4) {
        next.add(segment.id);
      }
      return next;
    });
  };

  const comparisonSegments = data.segments.filter((segment) => comparisonSet.has(segment.id));
  const selectedSegmentArea = selectedArea ?? selectedSegment?.planningAreas?.[0]?.toUpperCase() ?? null;

  return (
    <div className="space-y-6">
      <div className="rounded-3xl border border-border bg-card p-6 shadow-sm">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
          <div>
            <h1 className="mb-2 text-3xl font-bold text-foreground">Discover Segments</h1>
            <p className="max-w-3xl text-muted-foreground">
              Use this page to match segment archetypes to your goal, then investigate where the strongest candidates are concentrated.
            </p>
          </div>
          <button
            onClick={() => setShowMetricGuide(true)}
            className="inline-flex items-center gap-2 rounded-full border border-border px-4 py-2 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
          >
            <HelpCircle className="h-4 w-4" />
            <span>Metrics Guide</span>
          </button>
        </div>

        <div className="mt-5 grid grid-cols-2 gap-3 xl:grid-cols-4">
          <StatusPill label="Persona" value={personaLabel(persona)} />
          <StatusPill label="Filters" value={`${activeFilterCount} active`} />
          <StatusPill label="Matched Segments" value={String(matchedSegments.length)} />
          <StatusPill label="Selected Segment" value={selectedSegment?.name ?? 'None'} />
        </div>

        <div className="mt-5">
          <PersonaSelector selected={persona} onChange={setPersona} compact />
        </div>
      </div>

      <TabNavigation
        activeTab={activeTab}
        onTabChange={setActiveTab}
        disabledTabs={[
          ...(selectedSegment ? [] : ['investigate' as const]),
          ...(comparisonSet.size < 2 ? ['compare' as const] : []),
        ]}
      />

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
        <WorkflowSteps activeTab={activeTab} selectedSegment={selectedSegment} comparisonCount={comparisonSet.size} />
        <ShortlistRail
          selectedSegment={selectedSegment}
          comparisonSegments={comparisonSegments}
          selectedArea={selectedSegmentArea}
        />
      </div>

      <div className="flex flex-col gap-6 lg:flex-row">
        <div className="lg:sticky lg:top-24 lg:self-start">
          <FilterPanel
            filters={filters}
            onFilterChange={updateFilter}
            onReset={resetFilters}
            activeFilterCount={activeFilterCount}
          />
        </div>

        <div className="flex-1">
          {activeTab === 'discover' && (
            <DiscoverTab
              scoredSegments={scoredSegments}
              insights={data.insights}
              persona={persona}
              selectedSegmentId={selectedSegment?.id ?? null}
              activeFilterCount={activeFilterCount}
              onResetFilters={resetFilters}
              onInvestigateSegment={handleInvestigateSegment}
              onAddToCompare={handleAddToCompare}
              comparisonSet={comparisonSet}
            />
          )}

          {activeTab === 'investigate' && selectedSegment && (
            <InvestigateTab
              segment={selectedSegment}
              planningAreas={data.planningAreas}
              filters={debouncedFilters}
              persona={persona}
              selectedArea={selectedArea}
              onAreaChange={setSelectedArea}
              onChangeSegment={() => setActiveTab('discover')}
              onOpenMetricGuide={() => setShowMetricGuide(true)}
            />
          )}

          {activeTab === 'compare' && (
            <CompareTab
              segments={comparisonSegments}
              allSegments={data.segments}
              persona={persona}
            />
          )}
        </div>
      </div>

      <SegmentMetricGuideModal isOpen={showMetricGuide} onClose={() => setShowMetricGuide(false)} />
    </div>
  );
}

function WorkflowSteps({
  activeTab,
  selectedSegment,
  comparisonCount,
}: {
  activeTab: TabId;
  selectedSegment: Segment | null;
  comparisonCount: number;
}) {
  const steps = [
    {
      id: 'discover',
      title: 'Discover',
      description: 'Find segment archetypes that match your current filters and persona.',
      status: activeTab === 'discover' ? 'active' : selectedSegment ? 'complete' : 'open',
    },
    {
      id: 'investigate',
      title: 'Investigate',
      description: 'Open the selected segment and inspect which planning areas are strongest.',
      status: activeTab === 'investigate' ? 'active' : selectedSegment ? 'open' : 'locked',
    },
    {
      id: 'compare',
      title: 'Compare',
      description: 'Cross-check the shortlisted segments once at least two candidates are saved.',
      status: activeTab === 'compare' ? 'active' : comparisonCount >= 2 ? 'open' : 'locked',
    },
  ] as const;

  return (
    <div className="grid gap-4 md:grid-cols-3">
      {steps.map((step) => (
        <div
          key={step.id}
          className={`rounded-2xl border p-4 ${
            step.status === 'active'
              ? 'border-primary bg-primary/5'
              : step.status === 'complete'
                ? 'border-emerald-200 bg-emerald-50'
                : step.status === 'locked'
                  ? 'border-border bg-muted/20'
                  : 'border-border bg-card'
          }`}
        >
          <div className="text-sm font-semibold text-foreground">{step.title}</div>
          <p className="mt-2 text-sm text-muted-foreground">{step.description}</p>
        </div>
      ))}
    </div>
  );
}

function ShortlistRail({
  selectedSegment,
  comparisonSegments,
  selectedArea,
}: {
  selectedSegment: Segment | null;
  comparisonSegments: Segment[];
  selectedArea: string | null;
}) {
  const mapHref = `${import.meta.env.BASE_URL}dashboard/map${selectedArea ? `?area=${encodeURIComponent(selectedArea)}` : ''}`;
  const leaderboardHref = `${import.meta.env.BASE_URL}dashboard/leaderboard${
    selectedArea ? `?area=${encodeURIComponent(selectedArea)}` : ''
  }`;

  return (
    <aside className="rounded-2xl border border-border bg-card p-4 shadow-sm">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">Shortlist Rail</h2>
      <div className="mt-4 space-y-4">
        <div>
          <div className="text-xs uppercase tracking-wide text-muted-foreground">Selected Segment</div>
          <div className="mt-1 text-sm font-semibold text-foreground">{selectedSegment?.name ?? 'None yet'}</div>
        </div>
        <div>
          <div className="text-xs uppercase tracking-wide text-muted-foreground">Comparison Set</div>
          {comparisonSegments.length > 0 ? (
            <div className="mt-2 flex flex-wrap gap-2">
              {comparisonSegments.map((segment) => (
                <span key={segment.id} className="rounded-full bg-muted px-3 py-1 text-xs font-medium text-foreground">
                  {segment.name}
                </span>
              ))}
            </div>
          ) : (
            <p className="mt-1 text-sm text-muted-foreground">Add at least two segments to unlock side-by-side comparison.</p>
          )}
        </div>
        <div>
          <div className="text-xs uppercase tracking-wide text-muted-foreground">Next Handoff</div>
          <div className="mt-2 grid gap-2">
            <a
              href={leaderboardHref}
              className="rounded-xl border border-border px-3 py-2 text-sm font-medium text-foreground transition-colors hover:bg-muted/40"
            >
              Open in compare areas
            </a>
            <a
              href={mapHref}
              className="rounded-xl border border-border px-3 py-2 text-sm font-medium text-foreground transition-colors hover:bg-muted/40"
            >
              Open in explore areas
            </a>
          </div>
        </div>
      </div>
    </aside>
  );
}

function StatusPill({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-border bg-background px-4 py-3">
      <div className="text-xs uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className="mt-1 text-sm font-semibold text-foreground">{value}</div>
    </div>
  );
}
