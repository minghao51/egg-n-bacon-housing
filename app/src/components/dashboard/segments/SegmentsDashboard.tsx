// app/src/components/dashboard/segments/SegmentsDashboard.tsx
/**
 * Segment workspace island (shared by `/research/segments` and the legacy
 * `/dashboard/segments` wrapper).
 *
 * Evidence boundary: this surface reads `segments_enhanced.json.gz` only. That
 * asset is not part of `dashboard-release.json`, so no number here is compared
 * with a dashboard median or count — see `lib/segment-evidence.ts`.
 *
 * State: the address bar is read once, before the first commit (the island is
 * client-only), and written back with `replaceState`. Only the query keys this
 * workspace owns are touched, so parameters owned by other surfaces survive.
 */
import { useEffect, useState } from "react";
import { HelpCircle } from "lucide-react";
import { useSegmentsData } from "@/hooks/useSegmentsData";
import { useFilterState } from "@/hooks/useFilterState";
import { useSegmentMatching } from "@/hooks/useSegmentMatching";
import type { Segment, Persona } from "@/types/segments";
import PersonaSelector from "@/components/dashboard/PersonaSelector";
import FilterPanel from "./FilterPanel";
import TabNavigation from "./TabNavigation";
import { DiscoverTab } from "./discover/DiscoverTab";
import { CompareTab } from "./compare/CompareTab";
import { InvestigateTab } from "./investigate/InvestigateTab";
import SegmentMetricGuideModal from "./investigate/SegmentMetricGuideModal";
import {
  SEGMENT_ARCHIVE_NOTE,
  SEGMENT_NOT_COMPARABLE_NOTE,
} from "./lib/segment-evidence";
import {
  applySegmentQuery,
  parseSegmentQuery,
  SEGMENT_COMPARISON_MAX,
  SEGMENT_COMPARISON_MIN,
  type SegmentQueryState,
  type SegmentTab,
} from "./lib/segment-url-state";

/** Read the selection once, before the first commit. */
function readInitialQueryState(): SegmentQueryState {
  if (typeof window === "undefined") {
    // The island is client-only; this branch only guards a stray server render.
    return parseSegmentQuery("");
  }
  return parseSegmentQuery(window.location.search);
}

function personaLabel(persona: Persona): string {
  switch (persona) {
    case "all":
      return "All Personas";
    case "investor":
      return "Investor";
    case "first-time-buyer":
      return "First-Time Buyer";
    case "upgrader":
      return "Upgrader";
    default:
      return persona;
  }
}

/** "2026-04-19T23:23:07.52Z" → "19 Apr 2026" (extraction, not observation). */
export function archiveExtractionLabel(
  lastUpdated: string | undefined,
): string {
  if (!lastUpdated) {
    return "not supplied";
  }
  const parsed = new Date(lastUpdated);
  if (Number.isNaN(parsed.getTime())) {
    return "not supplied";
  }
  return parsed.toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  });
}

interface SegmentsDashboardProps {
  /** Deployment base path, resolved once by the Astro shell. */
  baseUrl: string;
}

export default function SegmentsDashboard({ baseUrl }: SegmentsDashboardProps) {
  const { data, loading, error, reload } = useSegmentsData();
  const [initialState] = useState<SegmentQueryState>(readInitialQueryState);
  const {
    filters,
    debouncedFilters,
    persona,
    setPersona,
    updateFilter,
    resetFilters,
    activeFilterCount,
  } = useFilterState(initialState.persona, {
    countVisibleFiltersOnly: true,
    initialFilters: initialState.filters,
  });
  const [activeTab, setActiveTab] = useState<SegmentTab>(initialState.tab);
  const [selectedSegmentId, setSelectedSegmentId] = useState<string | null>(
    initialState.segmentId,
  );
  const [comparisonIds, setComparisonIds] = useState<string[]>(
    initialState.comparisonIds,
  );
  const [selectedArea, setSelectedArea] = useState<string | null>(
    initialState.area,
  );
  const [showMetricGuide, setShowMetricGuide] = useState(false);

  const segments = data?.segments ?? [];
  const { matchedSegments, scoredSegments } = useSegmentMatching(
    segments,
    debouncedFilters,
  );

  // IDs — not objects — are the state, so an unknown or stale ID simply falls
  // back to "nothing selected" instead of holding a stale segment.
  const selectedSegment =
    segments.find((segment) => segment.id === selectedSegmentId) ?? null;
  const comparisonSegments = comparisonIds
    .map((id) => segments.find((segment) => segment.id === id))
    .filter((segment): segment is Segment => Boolean(segment));
  const comparisonLimitReached =
    comparisonSegments.length >= SEGMENT_COMPARISON_MAX;
  // A stable key for the effect below: `comparisonSegments` is re-derived on
  // every render, but the IDs only change when the selection does.
  const comparisonKey = comparisonSegments
    .map((segment) => segment.id)
    .join(",");

  // Write the address bar back. Runs after the first commit, when the state
  // above is already the parsed selection, so no deep link is overwritten. It
  // waits for the archive before writing: until then an incoming segment ID
  // cannot be validated, and serialising would prune it out of the URL and then
  // restore it, which is exactly the kind of transient rewrite S7 removed.
  useEffect(() => {
    if (typeof window === "undefined" || !data) {
      return;
    }
    const next = applySegmentQuery(window.location.href, {
      persona,
      tab: activeTab,
      segmentId: selectedSegment?.id ?? null,
      comparisonIds: comparisonKey === "" ? [] : comparisonKey.split(","),
      area: selectedArea,
      filters,
    });
    if (next !== window.location.href) {
      window.history.replaceState({}, "", next);
    }
  }, [
    activeTab,
    comparisonKey,
    data,
    filters,
    persona,
    selectedArea,
    selectedSegment,
  ]);

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
          <h2 className="mb-2 text-lg font-semibold text-foreground">
            Failed to load the segment archive
          </h2>
          <p className="mb-4 text-muted-foreground">{error}</p>
          <p className="mb-4 text-sm text-muted-foreground">
            No segment numbers are shown while the archive is unavailable.
          </p>
          <button
            onClick={() => void reload()}
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
    setSelectedSegmentId(segment.id);
    setSelectedArea(null);
    setActiveTab("investigate");
  };

  const handleAddToCompare = (segment: Segment) => {
    setComparisonIds((prev) => {
      if (prev.includes(segment.id)) {
        return prev.filter((id) => id !== segment.id);
      }
      if (prev.length >= SEGMENT_COMPARISON_MAX) {
        return prev;
      }
      return [...prev, segment.id];
    });
  };

  const handleRemoveFromCompare = (segmentId: string) => {
    setComparisonIds((prev) => prev.filter((id) => id !== segmentId));
  };

  const handleAddFromCompare = (segmentId: string) => {
    if (segmentId === "") return;
    setComparisonIds((prev) =>
      prev.includes(segmentId) || prev.length >= SEGMENT_COMPARISON_MAX
        ? prev
        : [...prev, segmentId],
    );
  };

  const archiveLabel = archiveExtractionLabel(data.lastUpdated);
  const selectedSegmentArea =
    selectedArea ?? selectedSegment?.planningAreas?.[0]?.toUpperCase() ?? null;

  return (
    <div className="space-y-6">
      <div className="rounded-3xl border border-border bg-card p-6 shadow-sm">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
          <div>
            <h2 className="mb-2 text-2xl font-bold text-foreground">
              Six stored research segments
            </h2>
            <p className="max-w-3xl text-muted-foreground">
              Weighted fit ranks the archive against your constraints; it is not
              a return probability and not a current investment recommendation.
            </p>
            <p className="mt-3 max-w-3xl text-sm text-muted-foreground">
              <span className="font-semibold text-foreground">
                Archive: {archiveLabel}
              </span>{" "}
              &middot; {SEGMENT_ARCHIVE_NOTE}
            </p>
          </div>
          <button
            onClick={() => setShowMetricGuide(true)}
            className="inline-flex items-center gap-2 rounded-full border border-border px-4 py-2 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
          >
            <HelpCircle className="h-4 w-4" />
            <span>Metrics guide</span>
          </button>
        </div>

        <div className="mt-5 grid grid-cols-2 gap-3 xl:grid-cols-4">
          <StatusPill label="Persona" value={personaLabel(persona)} />
          <StatusPill label="Filters" value={`${activeFilterCount} active`} />
          <StatusPill
            label="Matched Segments"
            value={`${matchedSegments.length} of ${segments.length}`}
          />
          <StatusPill
            label="Selected Segment"
            value={selectedSegment?.name ?? "None"}
          />
        </div>

        <div className="mt-5">
          <PersonaSelector selected={persona} onChange={setPersona} compact />
        </div>
      </div>

      <TabNavigation
        activeTab={activeTab}
        onTabChange={setActiveTab}
        comparisonCount={comparisonSegments.length}
        disabledTabs={[
          ...(selectedSegment ? [] : ["investigate" as const]),
          ...(comparisonSegments.length < SEGMENT_COMPARISON_MIN
            ? ["compare" as const]
            : []),
        ]}
      />

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
        <WorkflowSteps
          activeTab={activeTab}
          selectedSegment={selectedSegment}
          comparisonCount={comparisonSegments.length}
        />
        <ShortlistRail
          selectedSegment={selectedSegment}
          comparisonSegments={comparisonSegments}
          selectedArea={selectedSegmentArea}
          baseUrl={baseUrl}
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
          {activeTab === "investigate" && selectedSegment ? (
            <InvestigateTab
              segment={selectedSegment}
              planningAreas={data.planningAreas}
              filters={debouncedFilters}
              persona={persona}
              archiveLabel={archiveLabel}
              baseUrl={baseUrl}
              selectedArea={selectedArea}
              onAreaChange={setSelectedArea}
              onChangeSegment={() => setActiveTab("discover")}
              onOpenMetricGuide={() => setShowMetricGuide(true)}
            />
          ) : activeTab === "compare" ? (
            <CompareTab
              segments={comparisonSegments}
              allSegments={segments}
              onRemoveSegment={handleRemoveFromCompare}
              onAddSegment={handleAddFromCompare}
            />
          ) : (
            <DiscoverTab
              scoredSegments={scoredSegments}
              insights={data.insights}
              persona={persona}
              selectedSegmentId={selectedSegment?.id ?? null}
              activeFilterCount={activeFilterCount}
              onResetFilters={resetFilters}
              onInvestigateSegment={handleInvestigateSegment}
              onAddToCompare={handleAddToCompare}
              comparisonSet={new Set(comparisonSegments.map((s) => s.id))}
              comparisonLimitReached={comparisonLimitReached}
              baseUrl={baseUrl}
            />
          )}
        </div>
      </div>

      <section
        aria-label="Source and status"
        className="rounded-2xl border border-border bg-muted/20 p-5 text-sm text-muted-foreground"
      >
        <p className="font-semibold text-foreground">Source and status</p>
        <p className="mt-2">{SEGMENT_ARCHIVE_NOTE}</p>
        <p className="mt-2">{SEGMENT_NOT_COMPARABLE_NOTE}</p>
        <p className="mt-2">
          Scores, cohort counts and stored averages are archive fields. Changing
          them requires an owner decision on the segment model, not a UI change.
        </p>
      </section>

      <SegmentMetricGuideModal
        isOpen={showMetricGuide}
        onClose={() => setShowMetricGuide(false)}
      />
    </div>
  );
}

function WorkflowSteps({
  activeTab,
  selectedSegment,
  comparisonCount,
}: {
  activeTab: SegmentTab;
  selectedSegment: Segment | null;
  comparisonCount: number;
}) {
  const steps = [
    {
      id: "discover",
      title: "Discover",
      description:
        "Find segment archetypes that match your current filters and persona.",
      status:
        activeTab === "discover"
          ? "active"
          : selectedSegment
            ? "complete"
            : "open",
    },
    {
      id: "investigate",
      title: "Investigate",
      description:
        "Open the selected segment and inspect which planning areas it declares.",
      status:
        activeTab === "investigate"
          ? "active"
          : selectedSegment
            ? "open"
            : "locked",
    },
    {
      id: "compare",
      title: "Compare",
      description: `Cross-check ${SEGMENT_COMPARISON_MIN}-${SEGMENT_COMPARISON_MAX} shortlisted segments side by side.`,
      status:
        activeTab === "compare"
          ? "active"
          : comparisonCount >= SEGMENT_COMPARISON_MIN
            ? "open"
            : "locked",
    },
  ] as const;

  return (
    <div className="grid gap-4 md:grid-cols-3">
      {steps.map((step) => (
        <div
          key={step.id}
          className={`rounded-2xl border p-4 ${
            step.status === "active"
              ? "border-primary bg-primary/5"
              : step.status === "complete"
                ? "border-emerald-200 bg-emerald-50"
                : step.status === "locked"
                  ? "border-border bg-muted/20"
                  : "border-border bg-card"
          }`}
        >
          <div className="text-sm font-semibold text-foreground">
            {step.title}
          </div>
          <p className="mt-2 text-sm text-muted-foreground">
            {step.description}
          </p>
        </div>
      ))}
    </div>
  );
}

function ShortlistRail({
  selectedSegment,
  comparisonSegments,
  selectedArea,
  baseUrl,
}: {
  selectedSegment: Segment | null;
  comparisonSegments: Segment[];
  selectedArea: string | null;
  baseUrl: string;
}) {
  const exploreHref = `${baseUrl}explore${
    selectedArea ? `?area=${encodeURIComponent(selectedArea)}` : ""
  }`;
  const mapHref = `${baseUrl}dashboard/map${
    selectedArea ? `?area=${encodeURIComponent(selectedArea)}` : ""
  }`;

  return (
    <aside className="rounded-2xl border border-border bg-card p-4 shadow-sm">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
        Shortlist rail
      </h2>
      <div className="mt-4 space-y-4">
        <div>
          <div className="text-xs uppercase tracking-wide text-muted-foreground">
            Selected segment
          </div>
          <div className="mt-1 text-sm font-semibold text-foreground">
            {selectedSegment?.name ?? "None yet"}
          </div>
        </div>
        <div>
          <div className="text-xs uppercase tracking-wide text-muted-foreground">
            Comparison set: {comparisonSegments.length} of{" "}
            {SEGMENT_COMPARISON_MAX}
          </div>
          {comparisonSegments.length > 0 ? (
            <div className="mt-2 flex flex-wrap gap-2">
              {comparisonSegments.map((segment) => (
                <span
                  key={segment.id}
                  className="rounded-full bg-muted px-3 py-1 text-xs font-medium text-foreground"
                >
                  {segment.name}
                </span>
              ))}
            </div>
          ) : (
            <p className="mt-1 text-sm text-muted-foreground">
              Add at least {SEGMENT_COMPARISON_MIN} segments to unlock
              side-by-side comparison.
            </p>
          )}
          {comparisonSegments.length === 1 && (
            <p className="mt-2 text-xs text-muted-foreground">
              One segment shortlisted. The comparison needs{" "}
              {SEGMENT_COMPARISON_MIN}-{SEGMENT_COMPARISON_MAX}.
            </p>
          )}
        </div>
        <div>
          <div className="text-xs uppercase tracking-wide text-muted-foreground">
            Switch evidence context
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            These links leave the archive; they do not reinterpret a stored
            average as a 2025 transaction median.
          </p>
          <div className="mt-2 grid gap-2">
            <a
              href={exploreHref}
              className="rounded-xl border border-border px-3 py-2 text-sm font-medium text-foreground transition-colors hover:bg-muted/40"
            >
              Open observed comparison
            </a>
            <a
              href={mapHref}
              className="rounded-xl border border-border px-3 py-2 text-sm font-medium text-foreground transition-colors hover:bg-muted/40"
            >
              Open research map
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
      <div className="text-xs uppercase tracking-wide text-muted-foreground">
        {label}
      </div>
      <div className="mt-1 text-sm font-semibold text-foreground">{value}</div>
    </div>
  );
}
