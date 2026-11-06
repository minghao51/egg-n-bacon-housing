/**
 * Segment investigation tab.
 *
 * Shows the segment's declared planning areas and their stored archive values.
 * The observed market surface lives behind an explicit link, never a merge: the
 * archive is not part of the dashboard release generation (see
 * `lib/segment-evidence.ts`).
 */
import { useMemo, useState } from "react";
import type {
  FilterState,
  Persona,
  PlanningArea,
  Segment,
  SegmentAreaRow,
  SegmentInvestigationMetric,
} from "@/types/segments";
import { buildSegmentAreaRows } from "@/components/dashboard/segments/lib/buildSegmentAreaRows";
import {
  formatSegmentMetric,
  SEGMENT_GATED_NOTE,
  SEGMENT_INVESTIGATION_METRICS,
  segmentMetricEvidence,
} from "@/components/dashboard/segments/lib/segment-evidence";
import SegmentAreaMap from "./SegmentAreaMap";
import SegmentAreaTable from "./SegmentAreaTable";

interface InvestigateTabProps {
  segment: Segment;
  planningAreas: Record<string, PlanningArea>;
  filters: FilterState;
  persona: Persona;
  archiveLabel: string;
  baseUrl: string;
  selectedArea: string | null;
  onAreaChange: (area: string | null) => void;
  onChangeSegment: () => void;
  onOpenMetricGuide: () => void;
}

const BADGE_STYLES: Record<string, string> = {
  HH: "border-red-200 bg-red-50 text-red-700",
  LL: "border-blue-200 bg-blue-50 text-blue-700",
  HL: "border-orange-200 bg-orange-50 text-orange-700",
  LH: "border-violet-200 bg-violet-50 text-violet-700",
};

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

function personaImplication(segment: Segment, persona: Persona): string {
  switch (persona) {
    case "first-time-buyer":
      return segment.implications.firstTimeBuyer;
    case "upgrader":
      return segment.implications.upgrader;
    case "all":
    case "investor":
    default:
      return segment.implications.investor;
  }
}

export function InvestigateTab({
  segment,
  planningAreas,
  filters,
  persona,
  archiveLabel,
  baseUrl,
  selectedArea,
  onAreaChange,
  onChangeSegment,
  onOpenMetricGuide,
}: InvestigateTabProps) {
  const [selectedMetric, setSelectedMetric] =
    useState<SegmentInvestigationMetric>("avgPricePsf");

  const rows = useMemo(
    () => buildSegmentAreaRows(segment, planningAreas, filters, selectedMetric),
    [filters, planningAreas, segment, selectedMetric],
  );
  const declaredAreas = segment.planningAreas.length;
  const activeArea = useMemo(
    () => rows.find((row) => row.areaKey === selectedArea) ?? rows[0] ?? null,
    [rows, selectedArea],
  );
  const activeMetric = segmentMetricEvidence(selectedMetric);
  const observedHref = `${baseUrl}explore${
    activeArea ? `?area=${encodeURIComponent(activeArea.areaKey)}` : ""
  }`;

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-border bg-card p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-full bg-muted px-3 py-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Selected: {segment.name}
              </span>
              <span
                className={`rounded-full border px-3 py-1 text-xs font-semibold ${BADGE_STYLES[segment.spatialClassification] ?? "border-border"}`}
              >
                {segment.spatialClassification} cluster label
              </span>
            </div>
            <p className="text-sm text-muted-foreground">
              Research extract updated {archiveLabel} &middot; observation
              period unspecified.
            </p>
            <p className="max-w-3xl rounded-xl bg-muted/40 px-4 py-3 text-sm text-muted-foreground">
              <span className="font-semibold text-foreground">
                {personaLabel(persona)} archive note:
              </span>{" "}
              {personaImplication(segment, persona)}
            </p>
          </div>
          <button
            onClick={onChangeSegment}
            className="rounded-full border border-border px-4 py-2 text-sm font-medium text-muted-foreground hover:text-foreground"
          >
            ← Discover
          </button>
        </div>

        <div className="mt-5 grid grid-cols-2 gap-3 xl:grid-cols-4">
          <StatCard
            label="Stored avg PSF"
            value={
              Number.isFinite(segment.metrics.avgPricePsf)
                ? `S$${segment.metrics.avgPricePsf.toFixed(0)}`
                : "N/A"
            }
          />
          <StatCard
            label="Declared linked areas"
            value={String(declaredAreas)}
          />
          <StatCard
            label="Property types"
            value={segment.propertyTypes.join(", ")}
          />
          <StatCard label="Regions" value={segment.regions.join(", ")} />
        </div>
      </section>

      <section className="rounded-2xl border border-border bg-card p-4">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h3 className="text-lg font-semibold text-foreground">
              Investigation lens
            </h3>
            <p className="text-sm text-muted-foreground">
              Re-rank the segment&apos;s declared areas by a stored archive
              field. This does not recompute any value.
            </p>
          </div>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <div className="flex flex-wrap gap-2">
              {SEGMENT_INVESTIGATION_METRICS.map((metric) => {
                const evidence = segmentMetricEvidence(metric);
                return (
                  <button
                    key={metric}
                    onClick={() => setSelectedMetric(metric)}
                    aria-pressed={selectedMetric === metric}
                    className={`rounded-full px-3 py-1.5 text-sm font-medium transition-colors ${
                      selectedMetric === metric
                        ? "bg-primary text-primary-foreground"
                        : "bg-muted text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    {evidence.label}
                    {evidence.gated ? " †" : ""}
                  </button>
                );
              })}
            </div>
            <button
              onClick={onOpenMetricGuide}
              className="rounded-full border border-border px-3 py-1.5 text-sm font-medium text-muted-foreground hover:text-foreground"
            >
              Metrics guide
            </button>
          </div>
        </div>

        <div className="mt-4 rounded-xl border border-border bg-muted/30 px-4 py-3 text-sm text-muted-foreground">
          <p className="font-semibold text-foreground">
            Sorting by {activeMetric.label}
          </p>
          <p className="mt-1">{activeMetric.caveat}</p>
          {activeMetric.gated && <p className="mt-2">{SEGMENT_GATED_NOTE}</p>}
        </div>
      </section>

      <section className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)]">
        <div className="overflow-hidden rounded-2xl border border-border bg-card">
          <div className="border-b p-4">
            <h3 className="text-lg font-semibold">
              Declared areas on the planning-area map
            </h3>
            <p className="text-sm text-muted-foreground">
              Only areas the archive declares for this segment are emphasized;
              the rest is muted. Fill colours come from stored archive values,
              not from observed transactions.
            </p>
          </div>
          <div className="h-[500px]">
            <SegmentAreaMap
              rows={rows}
              selectedMetric={selectedMetric}
              highlightedArea={activeArea?.areaKey ?? null}
              onAreaHover={onAreaChange}
              onAreaClick={onAreaChange}
              baseUrl={baseUrl}
            />
          </div>
        </div>

        <div className="space-y-4">
          <div className="rounded-2xl border border-border bg-card p-4">
            <SegmentAreaTable
              rows={rows}
              selectedMetric={selectedMetric}
              highlightedArea={activeArea?.areaKey ?? null}
              onRowHover={onAreaChange}
              onRowClick={onAreaChange}
              declaredAreaCount={declaredAreas}
            />
          </div>
          {activeArea && (
            <AreaEvidencePanel area={activeArea} observedHref={observedHref} />
          )}
        </div>
      </section>

      <section className="rounded-2xl border border-border bg-card p-4">
        <h3 className="text-lg font-semibold text-foreground">
          Stored archive notes
        </h3>
        <p className="mt-1 text-sm text-muted-foreground">
          Risk and opportunity strings come from the same archive. They are not
          current advice and are not a recommendation.
        </p>
        <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
          <div>
            <h4 className="mb-2 text-sm font-semibold text-foreground">
              Risk signals
            </h4>
            <ul className="space-y-2">
              {(segment.riskFactors ?? []).map((risk) => (
                <li
                  key={risk}
                  className="flex items-start gap-2 text-sm text-muted-foreground"
                >
                  <span aria-hidden="true" className="mt-0.5 text-rose-500">
                    •
                  </span>
                  <span>{risk}</span>
                </li>
              ))}
              {(segment.riskFactors ?? []).length === 0 && (
                <li className="text-sm text-muted-foreground">
                  No risk notes supplied in the archive for this segment.
                </li>
              )}
            </ul>
          </div>
          <div>
            <h4 className="mb-2 text-sm font-semibold text-foreground">
              Opportunity signals
            </h4>
            <ul className="space-y-2">
              {(segment.opportunities ?? []).map((opportunity) => (
                <li
                  key={opportunity}
                  className="flex items-start gap-2 text-sm text-muted-foreground"
                >
                  <span aria-hidden="true" className="mt-0.5 text-emerald-500">
                    •
                  </span>
                  <span>{opportunity}</span>
                </li>
              ))}
              {(segment.opportunities ?? []).length === 0 && (
                <li className="text-sm text-muted-foreground">
                  No opportunity notes supplied in the archive for this segment.
                </li>
              )}
            </ul>
          </div>
        </div>
      </section>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-border bg-background p-3">
      <div className="text-xs uppercase tracking-wide text-muted-foreground">
        {label}
      </div>
      <div className="mt-1 text-lg font-bold text-foreground">{value}</div>
    </div>
  );
}

function AreaEvidencePanel({
  area,
  observedHref,
}: {
  area: SegmentAreaRow;
  observedHref: string;
}) {
  return (
    <div className="rounded-2xl border border-border bg-card p-4">
      <h3 className="text-lg font-semibold text-foreground">
        {area.planningArea} / selected research area
      </h3>
      <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
        <EvidenceItem
          label="Stored avg PSF"
          value={formatSegmentMetric(area.avgPricePsf, "avgPricePsf")}
        />
        <EvidenceItem label="Region" value={area.region} />
        <EvidenceItem
          label="Cluster label"
          value={`${area.spatialCluster} · stored confidence label ${area.hotspotConfidence}`}
        />
        <EvidenceItem label="School tier" value={area.schoolTier} />
      </div>
      <div className="mt-4 rounded-xl border border-border bg-muted/30 px-4 py-3 text-sm text-muted-foreground">
        <p>
          No sample count or observation period is supplied for{" "}
          {area.planningArea}. Forecast, yield, MRT-premium and persistence
          values are not shown as current recommendations; validate their
          definitions and reproducibility before activating those metrics.
        </p>
        <a
          href={observedHref}
          className="mt-3 inline-block rounded-xl border border-border bg-card px-3 py-2 font-medium text-foreground transition-colors hover:bg-muted/40"
        >
          Open observed comparison →
        </a>
        <p className="mt-2 text-xs">
          This switches to observed transactions (2025 HDB by default). It does
          not reinterpret the stored{" "}
          {formatSegmentMetric(area.avgPricePsf, "avgPricePsf")} as that median.
        </p>
      </div>
    </div>
  );
}

function EvidenceItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-muted/30 p-3">
      <div className="text-xs uppercase tracking-wide text-muted-foreground">
        {label}
      </div>
      <div className="mt-1 font-medium text-foreground">{value}</div>
    </div>
  );
}
