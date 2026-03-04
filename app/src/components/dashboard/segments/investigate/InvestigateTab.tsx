import { useMemo, useState } from 'react';
import type {
  FilterState,
  Persona,
  PlanningArea,
  Segment,
  SegmentAreaRow,
  SegmentInvestigationMetric,
} from '@/types/segments';
import { buildSegmentAreaRows } from '@/components/dashboard/segments/lib/buildSegmentAreaRows';
import SegmentAreaMap from './SegmentAreaMap';
import SegmentAreaTable from './SegmentAreaTable';

interface InvestigateTabProps {
  segment: Segment;
  planningAreas: Record<string, PlanningArea>;
  filters: FilterState;
  persona: Persona;
  selectedArea: string | null;
  onAreaChange: (area: string | null) => void;
  onChangeSegment: () => void;
  onOpenMetricGuide: () => void;
}

const INVESTIGATION_METRICS: Array<{ key: SegmentInvestigationMetric; label: string }> = [
  { key: 'avgPricePsf', label: 'Avg PSF' },
  { key: 'avgYield', label: 'Avg Yield' },
  { key: 'forecast6m', label: '6M Forecast' },
  { key: 'mrtPremium', label: 'MRT Premium' },
  { key: 'persistenceProbability', label: 'Persistence' },
];

const BADGE_STYLES: Record<string, string> = {
  HH: 'border-red-200 bg-red-50 text-red-700',
  LL: 'border-blue-200 bg-blue-50 text-blue-700',
  HL: 'border-orange-200 bg-orange-50 text-orange-700',
  LH: 'border-violet-200 bg-violet-50 text-violet-700',
};

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

function personaImplication(segment: Segment, persona: Persona): string {
  switch (persona) {
    case 'first-time-buyer':
      return segment.implications.firstTimeBuyer;
    case 'upgrader':
      return segment.implications.upgrader;
    case 'all':
    case 'investor':
    default:
      return segment.implications.investor;
  }
}

export function InvestigateTab({
  segment,
  planningAreas,
  filters,
  persona,
  selectedArea,
  onAreaChange,
  onChangeSegment,
  onOpenMetricGuide,
}: InvestigateTabProps) {
  const [selectedMetric, setSelectedMetric] =
    useState<SegmentInvestigationMetric>('avgPricePsf');
  const riskFactors = segment.riskFactors ?? [];
  const opportunities = segment.opportunities ?? [];

  const rows = useMemo(
    () => buildSegmentAreaRows(segment, planningAreas, filters, selectedMetric),
    [filters, planningAreas, segment, selectedMetric]
  );

  const activeArea = useMemo(
    () => rows.find((row) => row.areaKey === selectedArea) ?? rows[0] ?? null,
    [rows, selectedArea]
  );

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-border bg-card p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-full bg-primary/10 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-primary">
                {segment.investmentType}
              </span>
              <span
                className={`rounded-full border px-3 py-1 text-xs font-semibold ${BADGE_STYLES[segment.spatialClassification] ?? 'border-border'}`}
              >
                {segment.spatialClassification} cluster
              </span>
            </div>
            <div>
              <h2 className="text-2xl font-bold text-foreground">{segment.name}</h2>
              <p className="mt-1 text-muted-foreground">{segment.description}</p>
            </div>
            <p className="max-w-3xl rounded-xl bg-muted/40 px-4 py-3 text-sm text-muted-foreground">
              <span className="font-semibold text-foreground">{personaLabel(persona)} takeaway:</span>{' '}
              {personaImplication(segment, persona)}
            </p>
          </div>
          <button
            onClick={onChangeSegment}
            className="rounded-full border border-border px-4 py-2 text-sm font-medium text-muted-foreground hover:text-foreground"
          >
            Change Segment
          </button>
        </div>

        <div className="mt-5 grid grid-cols-2 gap-3 xl:grid-cols-5">
          <StatCard label="Avg PSF" value={`$${segment.metrics.avgPricePsf.toFixed(0)}`} />
          <StatCard label="Yield" value={`${segment.metrics.avgYield.toFixed(1)}%`} />
          <StatCard label="YoY Growth" value={`+${segment.metrics.yoyGrowth.toFixed(1)}%`} />
          <StatCard label="Transactions" value={segment.metrics.transactionCount.toLocaleString()} />
          <StatCard label="Persistence" value={`${(segment.persistenceProbability * 100).toFixed(0)}%`} />
        </div>
      </section>

      <section className="rounded-2xl border border-border bg-card p-4">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h3 className="text-lg font-semibold text-foreground">Investigation Lens</h3>
            <p className="text-sm text-muted-foreground">
              Re-rank the segment&apos;s matching areas by the metric most relevant to the next step.
            </p>
          </div>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <div className="flex flex-wrap gap-2">
              {INVESTIGATION_METRICS.map((metric) => (
                <button
                  key={metric.key}
                  onClick={() => setSelectedMetric(metric.key)}
                  className={`rounded-full px-3 py-1.5 text-sm font-medium transition-colors ${
                    selectedMetric === metric.key
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-muted text-muted-foreground hover:text-foreground'
                  }`}
                >
                  {metric.label}
                </button>
              ))}
            </div>
            <button
              onClick={onOpenMetricGuide}
              className="rounded-full border border-border px-3 py-1.5 text-sm font-medium text-muted-foreground hover:text-foreground"
            >
              Metrics Guide
            </button>
          </div>
        </div>
      </section>

      <section className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)]">
        <div className="overflow-hidden rounded-2xl border border-border bg-card">
          <div className="border-b p-4">
            <h3 className="text-lg font-semibold">Geographic Match Map</h3>
            <p className="text-sm text-muted-foreground">
              Only areas inside this segment are emphasized; everything else is muted.
            </p>
          </div>
          <div className="h-[500px]">
            <SegmentAreaMap
              rows={rows}
              selectedMetric={selectedMetric}
              highlightedArea={activeArea?.areaKey ?? null}
              onAreaHover={onAreaChange}
              onAreaClick={onAreaChange}
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
            />
          </div>
          {activeArea && (
            <AreaEvidencePanel area={activeArea} />
          )}
        </div>
      </section>

      <section className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="rounded-2xl border border-border bg-card p-4 lg:col-span-1">
          <h3 className="mb-4 text-lg font-semibold text-foreground">Geographic Distribution</h3>
          <div className="grid grid-cols-3 gap-3">
            {(['CCR', 'RCR', 'OCR'] as const).map((region) => {
              const count = rows.filter((row) => row.region === region).length;
              return (
                <div key={region} className="rounded-xl border border-border bg-muted/30 p-3 text-center">
                  <div className="text-2xl font-bold text-foreground">{count}</div>
                  <div className="text-xs text-muted-foreground">{region} Areas</div>
                </div>
              );
            })}
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            {rows.map((row) => (
              <span key={row.areaKey} className="rounded-full bg-muted px-3 py-1 text-sm text-foreground">
                {row.planningArea}
              </span>
            ))}
          </div>
        </div>

        <div className="rounded-2xl border border-border bg-card p-4">
          <h3 className="mb-3 text-lg font-semibold text-foreground">Risk Signals</h3>
          {riskFactors.length > 0 ? (
            <ul className="space-y-2">
              {riskFactors.map((risk) => (
                <li key={risk} className="flex items-start gap-2 text-sm text-muted-foreground">
                  <span className="mt-0.5 text-rose-500">•</span>
                  <span>{risk}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted-foreground">No major risk flags supplied for this segment.</p>
          )}
        </div>

        <div className="rounded-2xl border border-border bg-card p-4">
          <h3 className="mb-3 text-lg font-semibold text-foreground">Opportunity Signals</h3>
          {opportunities.length > 0 ? (
            <ul className="space-y-2">
              {opportunities.map((opportunity) => (
                <li key={opportunity} className="flex items-start gap-2 text-sm text-muted-foreground">
                  <span className="mt-0.5 text-emerald-500">•</span>
                  <span>{opportunity}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted-foreground">No distinct opportunity notes supplied for this segment.</p>
          )}
        </div>
      </section>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-border bg-background p-3">
      <div className="text-xs uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className="mt-1 text-lg font-bold text-foreground">{value}</div>
    </div>
  );
}

function AreaEvidencePanel({ area }: { area: SegmentAreaRow }) {
  return (
    <div className="rounded-2xl border border-border bg-card p-4">
      <h3 className="text-lg font-semibold text-foreground">Area Evidence</h3>
      <p className="mt-1 text-sm text-muted-foreground">
        {area.planningArea} is currently selected for closer investigation.
      </p>
      <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
        <EvidenceItem label="Hotspot Confidence" value={area.hotspotConfidence} />
        <EvidenceItem label="Spatial Cluster" value={area.spatialCluster} />
        <EvidenceItem label="MRT Sensitivity" value={area.mrtSensitivity} />
        <EvidenceItem label="School Tier" value={area.schoolTier} />
      </div>
    </div>
  );
}

function EvidenceItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-muted/30 p-3">
      <div className="text-xs uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className="mt-1 font-medium text-foreground">{value}</div>
    </div>
  );
}
