import React, { useEffect, useMemo, useState } from 'react';
import { Loader2, HelpCircle, Search, SlidersHorizontal, X } from 'lucide-react';
import type {
  LeaderboardControlsState,
  LeaderboardEntry,
  LeaderboardMetric,
} from '@/types/leaderboard';
import type { Region } from '@/types/segments';
import { useLeaderboardData } from '@/hooks/useLeaderboardData';
import LeaderboardControls from './LeaderboardControls';
import LeaderboardMap from './LeaderboardMap';
import LeaderboardTable from './LeaderboardTable';
import MetricHelpModal, { METRICS } from './MetricHelpModal';

interface LeaderboardDashboardProps {
  initialData?: LeaderboardEntry[];
}

const DEFAULT_CONTROLS: LeaderboardControlsState = {
  region: ['CCR', 'RCR', 'OCR'],
  propertyType: 'all',
  timeBasis: 'recent',
  priceRange: [300000, 2500000],
  search: '',
  rankMetric: 'yoy_growth_pct',
};

const REGION_LABELS: Record<Region, string> = {
  CCR: 'CCR',
  RCR: 'RCR',
  OCR: 'OCR',
};

const TIME_BASIS_LABELS: Record<LeaderboardControlsState['timeBasis'], string> = {
  recent: 'Recent',
  whole: 'All-time',
  year_2025: '2025',
};

function formatCurrency(value: number): string {
  return `$${value.toLocaleString()}`;
}

export default function LeaderboardDashboard({ initialData }: LeaderboardDashboardProps) {
  const [controls, setControls] = useState<LeaderboardControlsState>(DEFAULT_CONTROLS);
  const [showHelpModal, setShowHelpModal] = useState(false);
  const [highlightedArea, setHighlightedArea] = useState<string | null>(null);
  const [isMobileFiltersOpen, setIsMobileFiltersOpen] = useState(false);
  const [mobileView, setMobileView] = useState<'map' | 'rankings'>('map');
  const [isInteractiveReady, setIsInteractiveReady] = useState(false);

  const { data, loading, error, reload } = useLeaderboardData(controls, initialData);
  const metricMeta = METRICS.find((metric) => metric.key === controls.rankMetric) || METRICS[0];

  useEffect(() => {
    setIsInteractiveReady(true);
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    const params = new URLSearchParams(window.location.search);
    const areaParam = params.get('area');
    const metricParam = params.get('metric');
    const propertyTypeParam = params.get('propertyType');
    const timeBasisParam = params.get('timeBasis');

    if (areaParam) {
      setHighlightedArea(areaParam.toUpperCase());
    }

    if (metricParam && METRICS.some((metric) => metric.key === metricParam)) {
      setControls((current) => ({ ...current, rankMetric: metricParam as LeaderboardMetric }));
    }

    if (propertyTypeParam && ['all', 'hdb', 'ec', 'condo'].includes(propertyTypeParam)) {
      setControls((current) => ({ ...current, propertyType: propertyTypeParam as LeaderboardControlsState['propertyType'] }));
    }

    if (timeBasisParam && ['recent', 'whole', 'year_2025'].includes(timeBasisParam)) {
      setControls((current) => ({ ...current, timeBasis: timeBasisParam as LeaderboardControlsState['timeBasis'] }));
    }
  }, []);

  const activeFilterCount = useMemo(() => {
    let count = 0;
    if (controls.region.length !== DEFAULT_CONTROLS.region.length) count += 1;
    if (controls.propertyType !== DEFAULT_CONTROLS.propertyType) count += 1;
    if (controls.timeBasis !== DEFAULT_CONTROLS.timeBasis) count += 1;
    if (
      controls.priceRange[0] !== DEFAULT_CONTROLS.priceRange[0] ||
      controls.priceRange[1] !== DEFAULT_CONTROLS.priceRange[1]
    ) {
      count += 1;
    }
    if (controls.search.trim()) count += 1;
    return count;
  }, [controls]);

  const activeChips = useMemo(() => {
    const chips: string[] = [];

    if (controls.region.length !== DEFAULT_CONTROLS.region.length) {
      chips.push(`Region: ${controls.region.map((region) => REGION_LABELS[region]).join(', ') || 'None'}`);
    }

    if (controls.propertyType !== DEFAULT_CONTROLS.propertyType) {
      chips.push(`Type: ${controls.propertyType.toUpperCase()}`);
    }

    if (controls.timeBasis !== DEFAULT_CONTROLS.timeBasis) {
      chips.push(`Time: ${TIME_BASIS_LABELS[controls.timeBasis]}`);
    }

    if (
      controls.priceRange[0] !== DEFAULT_CONTROLS.priceRange[0] ||
      controls.priceRange[1] !== DEFAULT_CONTROLS.priceRange[1]
    ) {
      chips.push(`Price: ${formatCurrency(controls.priceRange[0])} - ${formatCurrency(controls.priceRange[1])}`);
    }

    if (controls.search.trim()) {
      chips.push(`Search: ${controls.search.trim()}`);
    }

    return chips;
  }, [controls]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    const url = new URL(window.location.href);
    url.searchParams.set('metric', controls.rankMetric);
    url.searchParams.set('propertyType', controls.propertyType);
    url.searchParams.set('timeBasis', controls.timeBasis);

    if (highlightedArea) {
      url.searchParams.set('area', highlightedArea);
    } else {
      url.searchParams.delete('area');
    }

    window.history.replaceState({}, '', url.toString());
  }, [controls.propertyType, controls.rankMetric, controls.timeBasis, highlightedArea]);

  const updateControl = <K extends keyof LeaderboardControlsState>(
    key: K,
    value: LeaderboardControlsState[K]
  ) => {
    setControls((current) => ({ ...current, [key]: value }));
  };

  const resetControls = () => {
    setControls(DEFAULT_CONTROLS);
    setHighlightedArea(null);
  };

  const handleAreaClick = (area: string) => {
    setHighlightedArea(area);
    const rowElement = document.querySelector(`[data-area="${area.toUpperCase()}"]`);
    if (rowElement) {
      rowElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  };

  const selectedAreaRow = useMemo(
    () => data.find((row) => row.areaKey === highlightedArea) ?? null,
    [data, highlightedArea]
  );
  const quickSummary = useMemo(() => {
    const topFive = data.slice(0, 5);
    const topLabel =
      controls.rankMetric === 'rental_yield_mean' || controls.rankMetric === 'rental_yield_median'
        ? 'Top 5 by yield'
        : controls.rankMetric === 'yoy_growth_pct'
          ? 'Top movers by recent growth'
          : controls.rankMetric === 'affordability_ratio'
            ? 'Best value under current budget'
            : 'Top 5 under current metric';

    return {
      label: topLabel,
      areas: topFive.map((row) => row.planningArea).join(', '),
    };
  }, [controls.rankMetric, data]);

  if (loading && !initialData?.length) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-muted-foreground">Loading leaderboard data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="max-w-md space-y-4 text-center">
          <div className="text-6xl text-red-500">⚠️</div>
          <h2 className="text-xl font-bold">Unable to Load Data</h2>
          <p className="text-muted-foreground">{error}</p>
          <button
            onClick={reload}
            className="rounded-md bg-primary px-4 py-2 text-primary-foreground hover:bg-primary/90"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background" data-interactive-ready={isInteractiveReady ? 'true' : 'false'}>
      <header className="sticky top-0 z-40 border-b border-border bg-background/95 backdrop-blur">
        <div className="container mx-auto space-y-4 px-4 py-4">
          <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
            <div className="space-y-1">
              <h1 className="text-3xl font-bold tracking-tight">Compare Areas</h1>
              <p className="text-sm text-muted-foreground">
                Use this page to rank planning areas on one metric, shortlist the strongest options, and hand them into the map or segment flow.
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <label className="flex items-center gap-2 rounded-xl border border-border bg-card px-3 py-2 text-sm shadow-sm">
                <span className="font-medium text-muted-foreground">Rank by</span>
                <select
                  aria-label="Rank by"
                  value={controls.rankMetric}
                  onChange={(event) => updateControl('rankMetric', event.target.value as LeaderboardMetric)}
                  className="bg-transparent font-medium text-foreground focus:outline-none"
                >
                  {METRICS.map((metric) => (
                    <option key={metric.key} value={metric.key}>
                      {metric.label}
                    </option>
                  ))}
                </select>
              </label>
              <button
                onClick={() => setShowHelpModal(true)}
                className="flex items-center gap-2 rounded-xl border border-border bg-card px-4 py-2 text-sm font-medium shadow-sm transition-colors hover:bg-muted"
                aria-label="View metric definitions"
              >
                <HelpCircle className="h-4 w-4" />
                <span>Metrics Guide</span>
              </button>
            </div>
          </div>

          <div className="flex flex-col gap-3 rounded-2xl border border-border bg-card px-4 py-3 shadow-sm lg:flex-row lg:items-center lg:justify-between">
            <div className="flex flex-col gap-2">
              <div className="text-sm font-medium text-foreground">
                Showing {data.length} areas ranked by {metricMeta.label.toLowerCase()} using {TIME_BASIS_LABELS[controls.timeBasis].toLowerCase()} data.
              </div>
              <div className="text-sm text-muted-foreground">
                {quickSummary.label}: <span className="font-medium text-foreground">{quickSummary.areas || 'No areas available'}</span>
              </div>
              {activeChips.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {activeChips.map((chip) => (
                    <span
                      key={chip}
                      className="rounded-full border border-border bg-muted px-3 py-1 text-xs font-medium text-muted-foreground"
                    >
                      {chip}
                    </span>
                  ))}
                </div>
              )}
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setIsMobileFiltersOpen(true)}
                className="flex items-center gap-2 rounded-xl border border-border px-3 py-2 text-sm font-medium lg:hidden"
              >
                <SlidersHorizontal className="h-4 w-4" />
                Filters ({activeFilterCount})
              </button>
              {activeFilterCount > 0 && (
                <button
                  type="button"
                  onClick={resetControls}
                  className="rounded-xl bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
                >
                  Reset
                </button>
              )}
            </div>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-6">
        <div className="grid gap-6 lg:grid-cols-[320px_minmax(0,1fr)]">
          <aside className="hidden lg:block">
            <div className="sticky top-36">
              <LeaderboardControls
                controls={controls}
                activeFilterCount={activeFilterCount}
                onChange={updateControl}
                onReset={resetControls}
              />
            </div>
          </aside>

          <main className="min-w-0 space-y-6">
            {selectedAreaRow && (
              <section className="rounded-2xl border border-border bg-card p-4 shadow-sm">
                <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                  <div>
                    <h2 className="text-lg font-semibold text-foreground">Selected Area</h2>
                    <p className="mt-1 text-sm text-muted-foreground">
                      {selectedAreaRow.planningArea} is currently highlighted at rank #{selectedAreaRow.rank} for {metricMeta.label.toLowerCase()}.
                    </p>
                  </div>
                  <div className="grid gap-2 sm:grid-cols-2">
                    <a
                      href={`${import.meta.env.BASE_URL}dashboard/map?area=${encodeURIComponent(selectedAreaRow.areaKey)}&metric=${encodeURIComponent(controls.rankMetric)}&propertyType=${encodeURIComponent(controls.propertyType)}&timeBasis=${encodeURIComponent(controls.timeBasis)}`}
                      className="rounded-xl border border-border px-3 py-2 text-sm font-medium text-foreground transition-colors hover:bg-muted/40"
                    >
                      Open in explore areas
                    </a>
                    <a
                      href={`${import.meta.env.BASE_URL}dashboard/segments?area=${encodeURIComponent(selectedAreaRow.areaKey)}`}
                      className="rounded-xl border border-border px-3 py-2 text-sm font-medium text-foreground transition-colors hover:bg-muted/40"
                    >
                      Open in discover segments
                    </a>
                  </div>
                </div>
              </section>
            )}

            <section className="lg:hidden">
              <div className="grid grid-cols-2 gap-2 rounded-2xl border border-border bg-card p-2 shadow-sm">
                <button
                  type="button"
                  onClick={() => setMobileView('map')}
                  className={`rounded-xl px-3 py-2 text-sm font-medium ${
                    mobileView === 'map' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground'
                  }`}
                >
                  Map
                </button>
                <button
                  type="button"
                  onClick={() => setMobileView('rankings')}
                  className={`rounded-xl px-3 py-2 text-sm font-medium ${
                    mobileView === 'rankings' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground'
                  }`}
                >
                  Rankings
                </button>
              </div>
            </section>

            <section className={`${mobileView === 'rankings' ? 'hidden lg:block' : 'block'}`}>
              <div className="overflow-hidden rounded-2xl border border-border bg-card shadow-sm">
                <div className="border-b border-border px-5 py-4">
                  <h2 className="text-lg font-semibold">Geographic View</h2>
                  <p className="text-sm text-muted-foreground">
                    Color-coded by {metricMeta.label.toLowerCase()} using {TIME_BASIS_LABELS[controls.timeBasis].toLowerCase()} values.
                  </p>
                </div>
                <div className="h-[420px] md:h-[520px]">
                  <LeaderboardMap
                    data={data}
                    selectedMetric={controls.rankMetric}
                    metricMeta={metricMeta}
                    highlightedArea={highlightedArea}
                    onAreaHover={setHighlightedArea}
                    onAreaClick={handleAreaClick}
                  />
                </div>
              </div>
            </section>

            <section className={`${mobileView === 'map' ? 'hidden lg:block' : 'block'}`}>
              <div className="overflow-hidden rounded-2xl border border-border bg-card shadow-sm">
                <div className="border-b border-border px-5 py-4">
                  <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                    <div>
                      <h2 className="text-lg font-semibold">Detailed Rankings</h2>
                      <p className="text-sm text-muted-foreground">
                        Rows stay sorted by the selected ranking metric. Hover to sync with the map.
                      </p>
                    </div>
                    <label className="flex items-center gap-2 rounded-xl border border-border bg-background px-3 py-2 text-sm">
                      <Search className="h-4 w-4 text-muted-foreground" />
                      <input
                        type="text"
                        aria-label="Search planning areas"
                        value={controls.search}
                        onChange={(event) => updateControl('search', event.target.value)}
                        placeholder="Search planning areas..."
                        className="w-full bg-transparent outline-none md:w-64"
                      />
                    </label>
                  </div>
                </div>
                <div className="p-4">
                  <LeaderboardTable
                    data={data}
                    selectedMetric={controls.rankMetric}
                    highlightedArea={highlightedArea}
                    onRowHover={setHighlightedArea}
                    onRowClick={handleAreaClick}
                  />
                </div>
              </div>
            </section>
          </main>
        </div>
      </div>

      {isMobileFiltersOpen && (
        <div className="fixed inset-0 z-50 flex items-end bg-black/50 lg:hidden">
          <div className="max-h-[85vh] w-full overflow-y-auto rounded-t-3xl bg-background p-4">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold">Leaderboard Filters</h2>
                <p className="text-sm text-muted-foreground">Adjust filters, then close to return to the page.</p>
              </div>
              <button
                type="button"
                onClick={() => setIsMobileFiltersOpen(false)}
                className="rounded-xl border border-border p-2"
                aria-label="Close filters"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <LeaderboardControls
              controls={controls}
              activeFilterCount={activeFilterCount}
              onChange={updateControl}
              onReset={resetControls}
              compact
            />
          </div>
        </div>
      )}

      <MetricHelpModal isOpen={showHelpModal} onClose={() => setShowHelpModal(false)} />
    </div>
  );
}
