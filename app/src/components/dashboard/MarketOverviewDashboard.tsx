import { useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import ClientChart from "@/components/charts/ClientChart";
import PriceTrendsChart from "./PriceTrendsChart";
import TransactionVolumeChart from "./TransactionVolumeChart";
import {
  DASHBOARD_NAV_ITEMS,
  type DashboardNavItem,
} from "@/constants/dashboard-nav";
import {
  ERA_DEFINITIONS,
  readNationalBaseline,
  sectionKey,
  type EraId,
  type ObservedMetric,
  type ObservedObservation,
  type PropertyTypeId,
} from "@/utils/observed-data";

interface TrendRecord {
  date: string;
  [key: string]: number | string;
}

/**
 * The parts of the published `dashboard_overview.json.gz` payload this page
 * reads. Every field is optional because the payload is parsed JSON: a missing
 * block must render as "not published", never as a zero or a stale fallback.
 */
export interface MarketOverviewDashboardData {
  metadata?: {
    generated_at?: string;
    total_records?: number;
    date_range?: { start?: string; end?: string };
  };
  distributions?: {
    property_type?: Record<string, number>;
    planning_area?: Record<string, number>;
  };
}

const COLORS = ["#0088FE", "#00C49F", "#FFBB28", "#FF8042", "#8884d8"];

const PROPERTY_TYPE_LABELS: Record<PropertyTypeId, string> = {
  all: "All property types",
  hdb: "HDB",
  ec: "EC",
  condo: "Condominium",
};

/** Compact labels for the period buttons; the scope line prints the full era label. */
const ERA_FILTERS: readonly { id: EraId; buttonLabel: string }[] = [
  { id: "whole", buttonLabel: "All history" },
  { id: "pre_covid", buttonLabel: "Through 2021" },
  { id: "recent", buttonLabel: "2022 onward" },
  { id: "year_2025", buttonLabel: "2025" },
];

const PROPERTY_TYPE_FILTERS: readonly {
  id: PropertyTypeId;
  buttonLabel: string;
}[] = [
  { id: "all", buttonLabel: "All" },
  { id: "hdb", buttonLabel: "HDB" },
  { id: "ec", buttonLabel: "EC" },
  { id: "condo", buttonLabel: "Condominium" },
];

/**
 * One card per property type, each bound to its own matching
 * `dashboard_overview.stats.year_2025_*` block. No figure here is derived from
 * another one, and no national median is averaged out of area values.
 */
const SCOPED_2025_TYPES: readonly {
  propertyType: Exclude<PropertyTypeId, "all">;
  label: string;
  detail: string;
}[] = [
  { propertyType: "hdb", label: "HDB", detail: "HDB resale flats" },
  {
    propertyType: "ec",
    label: "EC",
    detail: "Executive condominium",
  },
  {
    propertyType: "condo",
    label: "Condominium",
    detail: "Private condominium sales",
  },
];

const MONTH_NAMES = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
];

function formatSgd(value: number): string {
  return `S$${Math.round(value).toLocaleString("en-US")}`;
}

function formatSgdPerSqFt(value: number): string {
  return `${formatSgd(value)} psf`;
}

function formatSales(value: number): string {
  return `${Math.round(value).toLocaleString("en-US")} transactions`;
}

/**
 * Render one observation, or say that it is not published. `null` value with
 * the exporter's all-zero block is a separate state from a missing field, and
 * neither may become a real-looking number.
 */
function publishedValue(
  observation: ObservedObservation | null,
  format: (value: number) => string,
): string {
  if (observation === null) return "Not published";
  if (observation.value === null) {
    return observation.status === "empty"
      ? "No sales published"
      : "Not published";
  }
  return format(observation.value);
}

function observationFor(
  observations: ObservedObservation[] | null,
  metric: ObservedMetric,
): ObservedObservation | null {
  return observations?.find((entry) => entry.metric === metric) ?? null;
}

function eraLabel(era: EraId): string {
  return ERA_DEFINITIONS.find((entry) => entry.id === era)?.label ?? era;
}

function navItem(key: DashboardNavItem["key"]): DashboardNavItem | undefined {
  return DASHBOARD_NAV_ITEMS.find((item) => item.key === key);
}

function navLabel(key: DashboardNavItem["key"], fallback: string): string {
  return navItem(key)?.label ?? fallback;
}

function navPath(key: DashboardNavItem["key"], fallback: string): string {
  return navItem(key)?.path ?? fallback;
}

/** `2026-10-24T21:26:26.831603` -> `24 Oct 2026`; no timezone shifting. */
function formatPublishedDate(iso: string | undefined): string | null {
  const match = iso === undefined ? null : /^(\d{4})-(\d{2})-(\d{2})/.exec(iso);
  if (match === null) return null;
  const monthName = MONTH_NAMES[Number(match[2]) - 1];
  const day = Number(match[3]);
  if (monthName === undefined || !Number.isFinite(day) || day < 1) {
    return null;
  }
  return `${day} ${monthName} ${match[1]}`;
}

function yearOf(value: string | undefined): string | null {
  const match = value === undefined ? null : /^(\d{4})/.exec(value);
  return match === null ? null : match[1];
}

export default function MarketOverviewDashboard({
  initialData,
  trendsData,
  baseUrl,
}: {
  initialData: MarketOverviewDashboardData;
  trendsData?: TrendRecord[];
  /** Deployment base path, resolved once by the Astro page. */
  baseUrl: string;
}) {
  const [era, setEra] = useState<EraId>("whole");
  const [propertyType, setPropertyType] = useState<PropertyTypeId>("all");

  const base = baseUrl;

  // Every snapshot figure comes from the joint `era_property` stats block of
  // the loaded asset, so the period and the type can never drift apart.
  const scopeSection = sectionKey(era, propertyType);
  const snapshot = readNationalBaseline(initialData, era, propertyType);
  const snapshotVolume = observationFor(snapshot, "volume");
  const snapshotCount = publishedValue(snapshotVolume, formatSales);

  const propertyTypeData = Object.entries(
    initialData.distributions?.property_type ?? {},
  ).map(([name, value]) => ({ name, value }));

  const planningAreaData = Object.entries(
    initialData.distributions?.planning_area ?? {},
  )
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 10);

  const coverageStart = yearOf(initialData.metadata?.date_range?.start);
  const coverageEnd = yearOf(initialData.metadata?.date_range?.end);
  const coverageLabel =
    coverageStart !== null && coverageEnd !== null
      ? `${coverageStart} - ${coverageEnd}`
      : "Not published";
  const coverageDetail =
    initialData.metadata?.date_range?.start !== undefined &&
    initialData.metadata?.date_range?.end !== undefined
      ? `${initialData.metadata.date_range.start} to ${initialData.metadata.date_range.end}`
      : null;

  const exportDate = formatPublishedDate(initialData.metadata?.generated_at);

  const allTypes2025 = readNationalBaseline(initialData, "year_2025", "all");
  const allTypes2025Summary = `${publishedValue(
    observationFor(allTypes2025, "volume"),
    formatSales,
  )} at a median of ${publishedValue(
    observationFor(allTypes2025, "median_price"),
    formatSgd,
  )}`;

  const capabilityLinks: readonly {
    href: string;
    label: string;
    description: string;
  }[] = [
    {
      href: `${base}${navPath("explore", "explore")}`,
      label: navLabel("explore", "Observed explorer"),
      description:
        "Compare planning areas on the same year and property type, with sales counts beside every price.",
    },
    {
      href: `${base}research/trends`,
      label: "Monthly trends",
      description:
        "Monthly price and volume series with the sales behind them, for the type and range you choose.",
    },
    {
      href: `${base}areas/tampines`,
      label: "Tampines fieldnote",
      description:
        "An example area fieldnote: observed medians, sales counts and what the snapshot does not say.",
    },
    {
      href: `${base}${navPath("leaderboard", "dashboard/leaderboard")}`,
      label: navLabel("leaderboard", "Compare Areas"),
      description:
        "Rank planning areas on a single metric and narrow down a shortlist.",
    },
    {
      href: `${base}${navPath("tools", "dashboard/trends")}`,
      label: navLabel("tools", "Decision Tools"),
      description:
        "Financing, lease, commute and spatial scenario tools, with their inputs and limits shown.",
    },
    {
      href: `${base}${navPath("segments", "dashboard/segments")}`,
      label: navLabel("segments", "Discover Segments"),
      description:
        "Guided segment discovery that links an archetype to the areas that match it.",
    },
  ];

  return (
    <div className="space-y-8">
      <section
        aria-labelledby="overview-medians-heading"
        className="rounded-2xl border border-border bg-card p-5 shadow-sm"
      >
        <h2
          id="overview-medians-heading"
          className="text-xl font-bold text-foreground"
        >
          One market. Very different price tags.
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Median transaction price and transaction count by property type, 2025
          complete year, read from the one published overview asset.
        </p>

        <ul
          aria-label="2025 medians by property type"
          className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-3"
        >
          {SCOPED_2025_TYPES.map((card) => {
            const observations = readNationalBaseline(
              initialData,
              "year_2025",
              card.propertyType,
            );
            const section =
              observations?.[0]?.source.section ??
              sectionKey("year_2025", card.propertyType);
            return (
              <li
                key={card.propertyType}
                className="rounded-2xl border border-border bg-background p-4"
              >
                <h3 className="text-lg font-bold text-foreground">
                  {card.label}
                </h3>
                <p className="mt-0.5 text-xs uppercase tracking-wide text-muted-foreground">
                  {card.detail} · 2025 complete year
                </p>
                <p className="mt-3 text-2xl font-bold text-foreground">
                  {publishedValue(
                    observationFor(observations, "median_price"),
                    formatSgd,
                  )}
                </p>
                <p className="mt-1 text-sm text-muted-foreground">
                  {publishedValue(
                    observationFor(observations, "volume"),
                    formatSales,
                  )}
                </p>
                <p className="mt-2 text-xs text-muted-foreground">
                  Source:{" "}
                  <code className="font-mono">
                    dashboard_overview.stats.{section}
                  </code>
                </p>
              </li>
            );
          })}
        </ul>

        <p className="mt-4 text-sm text-foreground">
          <span className="font-bold">
            All property types, 2025 complete year:
          </span>{" "}
          {allTypes2025Summary}{" "}
          <span className="text-muted-foreground">
            &middot; from{" "}
            <code className="font-mono">
              dashboard_overview.stats.{sectionKey("year_2025", "all")}
            </code>
          </span>
        </p>

        <p className="mt-3 text-sm text-muted-foreground">
          These are 2025 medians of observed sales &mdash; not an index and not
          a forecast. Size, age and location differ between the property types,
          so the three prices are not a like-for-like comparison.
        </p>
      </section>

      <section
        aria-labelledby="overview-snapshot-heading"
        className="rounded-2xl border border-border bg-card p-5 shadow-sm"
      >
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="max-w-xl">
            <h2
              id="overview-snapshot-heading"
              className="text-xl font-bold text-foreground"
            >
              Market Snapshot
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Every figure below is filtered by both controls. Change either one
              and the count, the medians and the source section change with it.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-muted-foreground">
                Period:
              </span>
              <div className="flex space-x-1 rounded-md bg-muted p-1">
                {ERA_FILTERS.map((filter) => (
                  <button
                    key={filter.id}
                    type="button"
                    aria-pressed={era === filter.id}
                    onClick={() => setEra(filter.id)}
                    className={`rounded-sm px-3 py-1.5 text-xs font-medium transition-all ${
                      era === filter.id
                        ? "bg-background text-foreground shadow-sm"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    {filter.buttonLabel}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-muted-foreground">
                Type:
              </span>
              <div className="flex space-x-1 rounded-md bg-muted p-1">
                {PROPERTY_TYPE_FILTERS.map((filter) => (
                  <button
                    key={filter.id}
                    type="button"
                    aria-pressed={propertyType === filter.id}
                    onClick={() => setPropertyType(filter.id)}
                    className={`rounded-sm px-3 py-1.5 text-xs font-medium transition-all ${
                      propertyType === filter.id
                        ? "bg-background text-foreground shadow-sm"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    {filter.buttonLabel}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        <p
          data-overview-scope="true"
          className="mt-4 rounded border border-border bg-muted/40 px-3 py-2 text-sm text-foreground"
        >
          <span className="font-bold">Scope:</span> {eraLabel(era)} &middot;{" "}
          {PROPERTY_TYPE_LABELS[propertyType]} &middot; {snapshotCount} &middot;
          from{" "}
          <code className="font-mono">
            dashboard_overview.stats.{scopeSection}
          </code>
        </p>

        <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-4">
          <KpiCard
            title="Total Transactions"
            value={snapshotCount}
            subtext="Observed sales in this scope"
          />
          <KpiCard
            title="Median Price"
            value={publishedValue(
              observationFor(snapshot, "median_price"),
              formatSgd,
            )}
            subtext="Nominal SGD, observed sales"
          />
          <KpiCard
            title="Median PSF"
            value={publishedValue(
              observationFor(snapshot, "median_psf"),
              formatSgdPerSqFt,
            )}
            subtext="Per square foot"
          />
          <KpiCard
            title="Coverage"
            value={coverageLabel}
            subtext={
              coverageDetail === null
                ? "Observation range not published"
                : `${coverageDetail} · whole published dataset, not the filter above`
            }
          />
        </div>

        <p className="mt-4 text-xs text-muted-foreground">
          <span className="font-bold uppercase tracking-wide">Data note:</span>{" "}
          <code className="font-mono">dashboard_overview.json.gz</code>
          {exportDate === null
            ? " has no published export date"
            : ` was exported ${exportDate}`}
          {coverageDetail === null
            ? "; observed coverage is not published."
            : `; observed transactions span ${coverageDetail}.`}{" "}
          Export time is not source freshness, and nothing on this page is live
          listings or a valuation.
        </p>
      </section>

      {/* Charts Row 1 */}
      <div className="grid grid-cols-1 gap-8 lg:grid-cols-2">
        <div className="rounded-lg border border-border bg-card p-6">
          <h3 className="text-lg font-semibold text-foreground">
            Transactions by property type
          </h3>
          <p className="mt-1 mb-4 text-sm text-muted-foreground">
            Record counts across all history in the published asset, from{" "}
            <code className="font-mono">dashboard_overview.distributions</code>.
          </p>
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
                      key={`cell-${entry.name}`}
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
          {/* The chart is decorative; these are the numbers it encodes. */}
          <details className="mt-4 text-sm">
            <summary className="cursor-pointer font-bold text-foreground">
              View as a table
            </summary>
            <table className="mt-2 w-full text-sm">
              <caption className="sr-only">
                Published record counts by property type, all history
              </caption>
              <thead className="sr-only">
                <tr>
                  <th scope="col">Property type</th>
                  <th scope="col">Records</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {propertyTypeData.map((entry) => (
                  <tr key={entry.name}>
                    <th
                      scope="row"
                      className="py-2 text-left font-normal text-foreground"
                    >
                      {entry.name}
                    </th>
                    <td
                      className="py-2 text-right text-foreground"
                      data-numeric
                    >
                      {entry.value.toLocaleString("en-US")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </details>
        </div>

        <div className="rounded-lg border border-border bg-card p-6">
          <h3 className="text-lg font-semibold text-foreground">
            Top 10 planning areas by transactions
          </h3>
          <p className="mt-1 mb-4 text-sm text-muted-foreground">
            The same all-history record counts, by planning area.
          </p>
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
          {/* Accessible equivalent of the plotted counts. */}
          <details className="mt-4 text-sm">
            <summary className="cursor-pointer font-bold text-foreground">
              View as a table
            </summary>
            <table className="mt-2 w-full text-sm">
              <caption className="sr-only">
                Published record counts for the ten planning areas with the most
                transactions, all history
              </caption>
              <thead className="sr-only">
                <tr>
                  <th scope="col">Planning area</th>
                  <th scope="col">Records</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {planningAreaData.map((entry) => (
                  <tr key={entry.name}>
                    <th
                      scope="row"
                      className="py-2 text-left font-normal text-foreground"
                    >
                      {entry.name}
                    </th>
                    <td
                      className="py-2 text-right text-foreground"
                      data-numeric
                    >
                      {entry.value.toLocaleString("en-US")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </details>
        </div>
      </div>

      {/* Monthly series */}
      {trendsData && (
        <section
          aria-labelledby="overview-monthly-heading"
          className="space-y-6"
        >
          <div>
            <h2
              id="overview-monthly-heading"
              className="text-xl font-bold text-foreground"
            >
              Monthly series
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Monthly medians and volumes from the companion asset{" "}
              <code className="font-mono">dashboard_trends</code> &mdash;
              monthly figures, not the annual medians above. The price chart
              plots 2022 onward; the volume chart plots the whole published
              series.
            </p>
          </div>
          <PriceTrendsChart data={trendsData} />
          <TransactionVolumeChart data={trendsData} />
        </section>
      )}

      <nav
        aria-labelledby="overview-capabilities-heading"
        className="rounded-2xl border border-border bg-card p-5 shadow-sm"
      >
        <h2
          id="overview-capabilities-heading"
          className="text-xl font-bold text-foreground"
        >
          Keep exploring
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Each destination carries its own property type and period controls.
          None of them is a live feed.
        </p>
        <ul className="mt-4 grid gap-4 md:grid-cols-3">
          {capabilityLinks.map((link) => (
            <li key={link.href}>
              <a
                href={link.href}
                className="block h-full rounded-2xl border border-border bg-background p-4 transition-colors hover:bg-muted/40"
              >
                <span className="block text-sm font-semibold text-foreground">
                  {link.label}
                </span>
                <span className="mt-2 block text-sm text-muted-foreground">
                  {link.description}
                </span>
              </a>
            </li>
          ))}
        </ul>
      </nav>
    </div>
  );
}

function KpiCard({
  title,
  value,
  subtext,
}: {
  title: string;
  value: string;
  subtext?: string;
}) {
  return (
    <div className="rounded-2xl border border-border bg-background p-4 shadow-sm">
      <h3 className="mb-2 text-sm font-medium uppercase tracking-wider text-muted-foreground">
        {title}
      </h3>
      <div className="mb-1 text-2xl font-bold text-foreground">{value}</div>
      {subtext && <p className="text-xs text-muted-foreground">{subtext}</p>}
    </div>
  );
}
