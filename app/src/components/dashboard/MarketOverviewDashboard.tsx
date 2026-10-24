import React, { useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import ClientChart from "@/components/charts/ClientChart";
import PriceTrendsChart from "./PriceTrendsChart";
import TransactionVolumeChart from "./TransactionVolumeChart";
import DeltaBadge from "./DeltaBadge";

interface TrendRecord {
  date: string;
  [key: string]: number | string;
}

interface OverviewHighlights {
  recentPriceDelta?: {
    current: number;
    previous: number;
    change: number;
  } | null;
  recentPriceDeltaYoY?: {
    current: number;
    previous: number;
    change: number;
  } | null;
  recentVolumeDelta?: {
    current: number;
    previous: number;
    change: number;
  } | null;
  recentVolumeDeltaYoY?: {
    current: number;
    previous: number;
    change: number;
  } | null;
  strongestPropertyType?: [string, number] | null;
  strongestAreaTrend?: [string, { yoy_change_pct: number }] | null;
  weakestAreaTrend?: [string, { yoy_change_pct: number }] | null;
}

interface OverviewData {
  metadata: {
    generated_at: string;
    total_records: number;
    date_range: { start: string; end: string };
  };
  stats: {
    // Temporal periods
    whole: StatBlock;
    pre_covid: StatBlock;
    recent: StatBlock;
    year_2025: StatBlock;
    // Combined era + property type
    whole_hdb: StatBlock;
    whole_ec: StatBlock;
    whole_condo: StatBlock;
    pre_covid_hdb: StatBlock;
    pre_covid_ec: StatBlock;
    pre_covid_condo: StatBlock;
    recent_hdb: StatBlock;
    recent_ec: StatBlock;
    recent_condo: StatBlock;
    year_2025_hdb: StatBlock;
    year_2025_ec: StatBlock;
    year_2025_condo: StatBlock;
  };
  distributions: {
    property_type: Record<string, number>;
    planning_area: Record<string, number>;
  };
}

interface StatBlock {
  count: number;
  median_price: number;
  median_psf: number;
  volume: number;
}

const COLORS = ["#0088FE", "#00C49F", "#FFBB28", "#FF8042", "#8884d8"];

export default function MarketOverviewDashboard({
  data,
  trendsData,
  overviewHighlights,
}: {
  data: OverviewData;
  trendsData?: TrendRecord[];
  overviewHighlights?: OverviewHighlights;
}) {
  const [temporalFilter, setTemporalFilter] = useState<
    "whole" | "pre_covid" | "recent" | "year_2025"
  >("whole");
  const [propertyTypeFilter, setPropertyTypeFilter] = useState<
    "all" | "hdb" | "ec" | "condo"
  >("all");

  // Determine data key based on temporal and property type filters
  const dataKey =
    propertyTypeFilter === "all"
      ? temporalFilter
      : (`${temporalFilter}_${propertyTypeFilter}` as keyof typeof data.stats);
  const currentStats = data.stats[dataKey];

  // Trailing-12-month price delta badge, only for recent-period filters
  const showKpiDelta =
    temporalFilter === "recent" || temporalFilter === "year_2025";
  const priceSeriesKey =
    propertyTypeFilter === "all"
      ? "Overall Price"
      : propertyTypeFilter === "hdb"
        ? "HDB Price"
        : propertyTypeFilter === "ec"
          ? "EC Price"
          : "Condominium Price";
  const kpiDelta = showKpiDelta
    ? computeRolling12mDelta(trendsData, priceSeriesKey)
    : null;
  const kpiDeltaBadge =
    kpiDelta !== null ? (
      <DeltaBadge value={kpiDelta} size="sm" label="vs prior 12m" />
    ) : undefined;

  // Prepare chart data
  const propertyTypeData = Object.entries(data.distributions.property_type).map(
    ([name, value]) => ({ name, value }),
  );

  const planningAreaData = Object.entries(data.distributions.planning_area)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 10);

  return (
    <div className="space-y-8">
      <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <h2 className="text-xl font-bold text-foreground">
              What Changed Recently
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Read the current market shift first, then decide whether to
              explore areas, compare rankings, or move into segment discovery.
            </p>
          </div>
          <div className="rounded-xl bg-muted/40 px-4 py-3 text-sm text-muted-foreground">
            Best for: a quick market pulse before deeper analysis.
          </div>
        </div>
        <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
          <HighlightCard
            title="Median Price"
            value={
              <span className="flex flex-wrap items-center gap-2">
                <DeltaBadge
                  value={
                    overviewHighlights?.recentPriceDeltaYoY?.change ?? null
                  }
                  label="YoY"
                />
                <DeltaBadge
                  value={overviewHighlights?.recentPriceDelta?.change ?? null}
                  label="MoM"
                  size="sm"
                />
              </span>
            }
            description={
              overviewHighlights?.recentPriceDeltaYoY
                ? `From $${overviewHighlights.recentPriceDeltaYoY.previous.toLocaleString()} to $${overviewHighlights.recentPriceDeltaYoY.current.toLocaleString()} — monthly averages, latest month vs a year ago`
                : "Recent delta unavailable"
            }
          />
          <HighlightCard
            title="Transaction Volume"
            value={
              <span className="flex flex-wrap items-center gap-2">
                <DeltaBadge
                  value={
                    overviewHighlights?.recentVolumeDeltaYoY?.change ?? null
                  }
                  label="YoY"
                />
                <DeltaBadge
                  value={overviewHighlights?.recentVolumeDelta?.change ?? null}
                  label="MoM"
                  size="sm"
                />
              </span>
            }
            description={
              overviewHighlights?.recentVolumeDeltaYoY
                ? `From ${overviewHighlights.recentVolumeDeltaYoY.previous.toLocaleString()} to ${overviewHighlights.recentVolumeDeltaYoY.current.toLocaleString()} deals — monthly totals, latest month vs a year ago`
                : "Recent delta unavailable"
            }
          />
          <HighlightCard
            title="Largest Market Share"
            value={overviewHighlights?.strongestPropertyType?.[0] ?? "N/A"}
            description={
              overviewHighlights?.strongestPropertyType
                ? `${overviewHighlights.strongestPropertyType[1].toLocaleString()} records in the current dataset`
                : "Property share unavailable"
            }
          />
          <HighlightCard
            title="Strongest vs Weakest Area Move"
            value={
              overviewHighlights?.strongestAreaTrend &&
              overviewHighlights?.weakestAreaTrend
                ? `${overviewHighlights.strongestAreaTrend[0]} / ${overviewHighlights.weakestAreaTrend[0]}`
                : "N/A"
            }
            description={
              overviewHighlights?.strongestAreaTrend &&
              overviewHighlights?.weakestAreaTrend ? (
                <span className="flex flex-wrap items-center gap-2">
                  <DeltaBadge
                    value={
                      overviewHighlights.strongestAreaTrend[1].yoy_change_pct
                    }
                    label="YoY"
                  />
                  <DeltaBadge
                    value={
                      overviewHighlights.weakestAreaTrend[1].yoy_change_pct
                    }
                    label="YoY"
                  />
                </span>
              ) : (
                "Area momentum unavailable"
              )
            }
          />
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap justify-between items-center gap-4 bg-card p-4 rounded-lg border border-border">
        <h2 className="text-xl font-bold text-foreground">Market Snapshot</h2>
        <div className="flex flex-wrap gap-2">
          {/* Temporal Filter */}
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-muted-foreground">
              Period:
            </span>
            <div className="flex space-x-1 bg-muted p-1 rounded-md">
              {(["whole", "pre_covid", "recent", "year_2025"] as const).map(
                (key) => (
                  <button
                    key={key}
                    onClick={() => setTemporalFilter(key)}
                    className={`px-3 py-1.5 text-xs font-medium rounded-sm transition-all ${
                      temporalFilter === key
                        ? "bg-background text-foreground shadow-sm"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    {key === "whole"
                      ? "All Time"
                      : key === "pre_covid"
                        ? "Pre-COVID"
                        : key === "recent"
                          ? "Recent"
                          : "2025"}
                  </button>
                ),
              )}
            </div>
          </div>

          {/* Property Type Filter */}
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-muted-foreground">
              Type:
            </span>
            <div className="flex space-x-1 bg-muted p-1 rounded-md">
              {(["all", "hdb", "ec", "condo"] as const).map((key) => (
                <button
                  key={key}
                  onClick={() => setPropertyTypeFilter(key)}
                  className={`px-3 py-1.5 text-xs font-medium rounded-sm transition-all ${
                    propertyTypeFilter === key
                      ? "bg-background text-foreground shadow-sm"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {key === "all" ? "All" : key.toUpperCase()}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <KpiCard
          title="Total Transactions"
          value={currentStats.count.toLocaleString()}
          subtext={
            temporalFilter === "whole" && propertyTypeFilter === "all"
              ? "All records"
              : "In selected period"
          }
        />
        <KpiCard
          title="Median Price"
          value={`$${currentStats.median_price.toLocaleString()}`}
          subtext="SGD"
          delta={kpiDeltaBadge}
        />
        <KpiCard
          title="Median PSF"
          value={`$${currentStats.median_psf.toLocaleString()}`}
          subtext="Per Sq Ft"
          delta={kpiDeltaBadge}
        />
        <KpiCard
          title="Date Range"
          value={
            data.metadata.date_range.start.substring(0, 4) +
            " - " +
            data.metadata.date_range.end.substring(0, 4)
          }
          subtext="Full dataset range"
        />
      </div>

      {/* Charts Row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="bg-card p-6 rounded-lg border border-border">
          <h3 className="text-lg font-semibold mb-6 text-foreground">
            Property Type Distribution
          </h3>
          <ClientChart className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%" minWidth={100}>
              <PieChart>
                <Pie
                  data={propertyTypeData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) =>
                    `${name} ${((percent || 0) * 100).toFixed(0)}%`
                  }
                  outerRadius={100}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {propertyTypeData.map((entry, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={COLORS[index % COLORS.length]}
                    />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: "hsl(var(--card))",
                    borderColor: "hsl(var(--border))",
                  }}
                  itemStyle={{ color: "hsl(var(--foreground))" }}
                />
              </PieChart>
            </ResponsiveContainer>
          </ClientChart>
        </div>

        <div className="bg-card p-6 rounded-lg border border-border">
          <h3 className="text-lg font-semibold mb-6 text-foreground">
            Top 10 Planning Areas (Volume)
          </h3>
          <ClientChart className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%" minWidth={100}>
              <BarChart
                layout="vertical"
                data={planningAreaData}
                margin={{ top: 5, right: 30, left: 40, bottom: 5 }}
              >
                <CartesianGrid
                  strokeDasharray="3 3"
                  className="stroke-muted"
                  horizontal={false}
                />
                <XAxis
                  type="number"
                  className="text-xs"
                  tick={{ fill: "hsl(var(--foreground))" }}
                />
                <YAxis
                  dataKey="name"
                  type="category"
                  width={100}
                  className="text-xs"
                  tick={{ fill: "hsl(var(--foreground))" }}
                />
                <Tooltip
                  cursor={{ fill: "hsl(var(--muted)/0.2)" }}
                  contentStyle={{
                    backgroundColor: "hsl(var(--card))",
                    borderColor: "hsl(var(--border))",
                  }}
                  itemStyle={{ color: "hsl(var(--foreground))" }}
                />
                <Bar dataKey="value" fill="#3b82f6" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </ClientChart>
        </div>
      </div>

      {/* Charts Row 2 - Price Trends and Transaction Volume */}
      {trendsData && (
        <div className="space-y-8">
          <PriceTrendsChart data={trendsData} />
          <TransactionVolumeChart data={trendsData} />
        </div>
      )}

      <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
        <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <div>
            <h3 className="text-lg font-semibold text-foreground">
              Pick the Next Workspace
            </h3>
            <p className="text-sm text-muted-foreground">
              Move from the executive snapshot into the page built for your next
              decision.
            </p>
          </div>
        </div>
        <div className="mt-4 grid gap-4 md:grid-cols-3">
          <NextStepCard
            href={`${import.meta.env.BASE_URL}dashboard/map`}
            title="Explore on map"
            description="Open the geographic view to see hotspots, affordability pockets, and overlay presets."
          />
          <NextStepCard
            href={`${import.meta.env.BASE_URL}dashboard/leaderboard`}
            title="See ranked areas"
            description="Switch to a single-metric ranking workspace and narrow down a shortlist."
          />
          <NextStepCard
            href={`${import.meta.env.BASE_URL}dashboard/segments`}
            title="Find matching segments"
            description="Start a guided discovery flow to match segment archetypes to your goal."
          />
        </div>
      </div>
    </div>
  );
}

function computeRolling12mDelta(
  records: TrendRecord[] | undefined,
  key: string,
): number | null {
  if (!records || records.length < 24) return null;

  // Fail closed: every one of the last 24 monthly positions must hold a usable
  // value, so the trailing-12m windows stay position-contiguous (gaps in the
  // series yield no badge instead of a misleading delta).
  const values: number[] = [];
  for (let index = records.length - 24; index < records.length; index += 1) {
    const value = records[index]?.[key];
    if (typeof value !== "number" || Number.isNaN(value)) return null;
    values.push(value);
  }

  const average = (slice: number[]) =>
    slice.reduce((sum, entry) => sum + entry, 0) / slice.length;
  const recent = average(values.slice(12));
  const previous = average(values.slice(0, 12));
  if (previous === 0) return null;

  return ((recent - previous) / previous) * 100;
}

function HighlightCard({
  title,
  value,
  description,
}: {
  title: string;
  value: React.ReactNode;
  description: React.ReactNode;
}) {
  return (
    <div className="rounded-2xl border border-border bg-background p-4">
      <div className="text-xs uppercase tracking-wide text-muted-foreground">
        {title}
      </div>
      <div className="mt-2 text-lg font-bold text-foreground">{value}</div>
      <p className="mt-2 text-sm text-muted-foreground">{description}</p>
    </div>
  );
}

function NextStepCard({
  href,
  title,
  description,
}: {
  href: string;
  title: string;
  description: string;
}) {
  return (
    <a
      href={href}
      className="rounded-2xl border border-border bg-background p-4 transition-colors hover:bg-muted/40"
    >
      <div className="text-sm font-semibold text-foreground">{title}</div>
      <p className="mt-2 text-sm text-muted-foreground">{description}</p>
    </a>
  );
}

function KpiCard({
  title,
  value,
  subtext,
  delta,
}: {
  title: string;
  value: string;
  subtext?: string;
  delta?: React.ReactNode;
}) {
  return (
    <div className="bg-card p-6 rounded-2xl border border-border shadow-sm">
      <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wider mb-2">
        {title}
      </h3>
      <div className="text-3xl font-bold text-foreground mb-1">{value}</div>
      {(delta || subtext) && (
        <div className="flex flex-wrap items-center gap-2">
          {delta}
          {subtext && (
            <p className="text-xs text-muted-foreground">{subtext}</p>
          )}
        </div>
      )}
    </div>
  );
}
