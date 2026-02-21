import React, { useState } from 'react';
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
} from 'recharts';
import PriceTrendsChart from './PriceTrendsChart';
import TransactionVolumeChart from './TransactionVolumeChart';

interface TrendRecord {
  date: string;
  [key: string]: number | string;
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

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8'];

export default function MarketOverviewDashboard({
  data,
  trendsData
}: {
  data: OverviewData;
  trendsData?: TrendRecord[];
}) {
  const [temporalFilter, setTemporalFilter] = useState<'whole' | 'pre_covid' | 'recent' | 'year_2025'>('whole');
  const [propertyTypeFilter, setPropertyTypeFilter] = useState<'all' | 'hdb' | 'ec' | 'condo'>('all');

  // Determine data key based on temporal and property type filters
  const dataKey = propertyTypeFilter === 'all'
    ? temporalFilter
    : `${temporalFilter}_${propertyTypeFilter}` as keyof typeof data.stats;
  const currentStats = data.stats[dataKey];

  // Prepare chart data
  const propertyTypeData = Object.entries(data.distributions.property_type).map(
    ([name, value]) => ({ name, value })
  );

  const planningAreaData = Object.entries(data.distributions.planning_area)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 10);

  return (
    <div className="space-y-8">
      {/* Filters */}
      <div className="flex flex-wrap justify-between items-center gap-4 bg-card p-4 rounded-lg border border-border">
        <h2 className="text-xl font-bold text-foreground">Market Snapshot</h2>
        <div className="flex flex-wrap gap-2">
          {/* Temporal Filter */}
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-muted-foreground">Period:</span>
            <div className="flex space-x-1 bg-muted p-1 rounded-md">
              {(['whole', 'pre_covid', 'recent', 'year_2025'] as const).map((key) => (
                <button
                  key={key}
                  onClick={() => setTemporalFilter(key)}
                  className={`px-3 py-1.5 text-xs font-medium rounded-sm transition-all ${temporalFilter === key
                    ? 'bg-background text-foreground shadow-sm'
                    : 'text-muted-foreground hover:text-foreground'
                    }`}
                >
                  {key === 'whole'
                    ? 'All Time'
                    : key === 'pre_covid'
                      ? 'Pre-COVID'
                      : key === 'recent'
                        ? 'Recent'
                        : '2025'}
                </button>
              ))}
            </div>
          </div>

          {/* Property Type Filter */}
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-muted-foreground">Type:</span>
            <div className="flex space-x-1 bg-muted p-1 rounded-md">
              {(['all', 'hdb', 'ec', 'condo'] as const).map((key) => (
                <button
                  key={key}
                  onClick={() => setPropertyTypeFilter(key)}
                  className={`px-3 py-1.5 text-xs font-medium rounded-sm transition-all ${propertyTypeFilter === key
                    ? 'bg-background text-foreground shadow-sm'
                    : 'text-muted-foreground hover:text-foreground'
                    }`}
                >
                  {key === 'all' ? 'All' : key.toUpperCase()}
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
          subtext={temporalFilter === 'whole' && propertyTypeFilter === 'all' ? 'All records' : 'In selected period'}
        />
        <KpiCard
          title="Median Price"
          value={`$${currentStats.median_price.toLocaleString()}`}
          subtext="SGD"
        />
        <KpiCard
          title="Median PSF"
          value={`$${currentStats.median_psf.toLocaleString()}`}
          subtext="Per Sq Ft"
        />
        <KpiCard
          title="Date Range"
          value={data.metadata.date_range.start.substring(0, 4) + ' - ' + data.metadata.date_range.end.substring(0, 4)}
          subtext="Full dataset range"
        />
      </div>

      {/* Charts Row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="bg-card p-6 rounded-lg border border-border">
          <h3 className="text-lg font-semibold mb-6 text-foreground">
            Property Type Distribution
          </h3>
          <div className="h-[300px]">
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
                  contentStyle={{ backgroundColor: 'hsl(var(--card))', borderColor: 'hsl(var(--border))' }}
                  itemStyle={{ color: 'hsl(var(--foreground))' }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-card p-6 rounded-lg border border-border">
          <h3 className="text-lg font-semibold mb-6 text-foreground">
            Top 10 Planning Areas (Volume)
          </h3>
          <div className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%" minWidth={100}>
              <BarChart
                layout="vertical"
                data={planningAreaData}
                margin={{ top: 5, right: 30, left: 40, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" horizontal={false} />
                <XAxis type="number" className="text-xs" tick={{ fill: 'hsl(var(--foreground))' }} />
                <YAxis
                  dataKey="name"
                  type="category"
                  width={100}
                  className="text-xs"
                  tick={{ fill: 'hsl(var(--foreground))' }}
                />
                <Tooltip
                  cursor={{ fill: 'hsl(var(--muted)/0.2)' }}
                  contentStyle={{ backgroundColor: 'hsl(var(--card))', borderColor: 'hsl(var(--border))' }}
                  itemStyle={{ color: 'hsl(var(--foreground))' }}
                />
                <Bar dataKey="value" fill="#3b82f6" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Charts Row 2 - Price Trends and Transaction Volume */}
      {trendsData && (
        <div className="space-y-8">
          <PriceTrendsChart data={trendsData} />
          <TransactionVolumeChart data={trendsData} />
        </div>
      )}
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
    <div className="bg-card p-6 rounded-lg border border-border shadow-sm">
      <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wider mb-2">
        {title}
      </h3>
      <div className="text-3xl font-bold text-foreground mb-1">{value}</div>
      {subtext && <p className="text-xs text-muted-foreground">{subtext}</p>}
    </div>
  );
}
