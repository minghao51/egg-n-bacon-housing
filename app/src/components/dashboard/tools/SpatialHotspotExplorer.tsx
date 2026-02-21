import { useState, useMemo } from 'react';
import type { Persona } from '../PersonaSelector';

interface Cluster {
  cluster_type: 'HH' | 'LH' | 'HL' | 'LL';
  towns: string[];
  avg_appreciation_5y: number;
  avg_price_psf: number;
  persistence_probability: number;
  risk_level: 'Low' | 'Medium' | 'High';
}

interface SpatialData {
  clusters: Cluster[];
  analysis_date: string;
  methodology: string;
}

interface SpatialHotspotExplorerProps {
  data: SpatialData;
  persona: Persona;
}

const CLUSTER_CONFIG = {
  HH: {
    label: 'High-High',
    color: 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800',
    textColor: 'text-green-700 dark:text-green-300',
    badgeColor: 'bg-green-100 dark:bg-green-800 text-green-800 dark:text-green-200',
    description: 'Hotspots with high appreciation surrounded by high-appreciation areas',
    icon: '🔥',
  },
  LH: {
    label: 'Low-High',
    color: 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800',
    textColor: 'text-blue-700 dark:text-blue-300',
    badgeColor: 'bg-blue-100 dark:bg-blue-800 text-blue-800 dark:text-blue-200',
    description: 'Coldspots surrounded by hotspots - potential transition zones',
    icon: '❄️',
  },
  HL: {
    label: 'High-Low',
    color: 'bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800',
    textColor: 'text-yellow-700 dark:text-yellow-300',
    badgeColor: 'bg-yellow-100 dark:bg-yellow-800 text-yellow-800 dark:text-yellow-200',
    description: 'Hotspots surrounded by coldspots - emerging pioneers',
    icon: '⭐',
  },
  LL: {
    label: 'Low-Low',
    color: 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800',
    textColor: 'text-red-700 dark:text-red-300',
    badgeColor: 'bg-red-100 dark:bg-red-800 text-red-800 dark:text-red-200',
    description: 'Coldspots with low appreciation surrounded by low-appreciation areas',
    icon: '🥶',
  },
};

const INVESTMENT_HORIZONS = {
  short: { label: 'Short Term (1-3 years)', years: 2 },
  medium: { label: 'Medium Term (3-7 years)', years: 5 },
  long: { label: 'Long Term (7-15 years)', years: 10 },
};

const RISK_TOLERANCE = {
  low: { label: 'Low', adjustFactor: 0.7 },
  medium: { label: 'Medium', adjustFactor: 1.0 },
  high: { label: 'High', adjustFactor: 1.3 },
};

export default function SpatialHotspotExplorer({
  data,
  persona,
}: SpatialHotspotExplorerProps) {
  const [selectedTown, setSelectedTown] = useState<string>('All Towns');
  const [horizon, setHorizon] = useState<keyof typeof INVESTMENT_HORIZONS>('medium');
  const [riskTolerance, setRiskTolerance] = useState<keyof typeof RISK_TOLERANCE>('medium');

  // Get all towns
  const towns = useMemo(() => {
    const allTowns = data.clusters.flatMap((c) => c.towns);
    const uniqueTowns = Array.from(new Set(allTowns)).sort();
    return ['All Towns', ...uniqueTowns];
  }, [data.clusters]);

  // Filter clusters by town
  const filteredClusters = useMemo(() => {
    if (selectedTown === 'All Towns') {
      return data.clusters;
    }
    return data.clusters.filter((c) => c.towns.includes(selectedTown));
  }, [data.clusters, selectedTown]);

  // Get selected town's cluster
  const selectedCluster = useMemo(() => {
    if (selectedTown === 'All Towns') return null;
    return data.clusters.find((c) => c.towns.includes(selectedTown)) || null;
  }, [data.clusters, selectedTown]);

  // Calculate expected returns
  const calculateExpectedReturn = (
    cluster: Cluster,
    years: number,
    riskFactor: number
  ) => {
    const adjustedRate = cluster.avg_appreciation_5y * riskFactor;
    const totalReturn = Math.pow(1 + adjustedRate / 100, years) - 1;
    return { adjustedRate, totalReturn };
  };

  // Get portfolio allocation by persona
  const getPortfolioAllocation = () => {
    const riskFactor = RISK_TOLERANCE[riskTolerance].adjustFactor;
    const years = INVESTMENT_HORIZONS[horizon].years;

    if (persona === 'investor') {
      return {
        HH: 50,
        HL: 30,
        LH: 15,
        LL: 5,
        reasoning:
          'Focus on HH hotspots for growth, HL pioneers for upside potential. Minimize LL exposure.',
      };
    } else if (persona === 'first-time-buyer') {
      return {
        HH: 30,
        HL: 20,
        LH: 35,
        LL: 15,
        reasoning:
          'Balanced approach: LH coldspots near hotspots offer affordability with future upside. Prioritize stability over maximum growth.',
      };
    } else {
      return {
        HH: 40,
        HL: 25,
        LH: 25,
        LL: 10,
        reasoning:
          'Upgrade strategy: Target HH for appreciation, HL for value-add opportunities. Limited LL exposure for diversification.',
      };
    }
  };

  const portfolio = getPortfolioAllocation();

  // Calculate cluster summary stats
  const clusterSummary = useMemo(() => {
    return filteredClusters.map((cluster) => {
      const { adjustedRate, totalReturn } = calculateExpectedReturn(
        cluster,
        INVESTMENT_HORIZONS[horizon].years,
        RISK_TOLERANCE[riskTolerance].adjustFactor
      );
      return {
        type: cluster.cluster_type,
        avgAppreciation: cluster.avg_appreciation_5y,
        townCount: cluster.towns.length,
        adjustedRate,
        totalReturn,
        persistence: cluster.persistence_probability,
        risk: cluster.risk_level,
      };
    });
  }, [filteredClusters, horizon, riskTolerance]);

  return (
    <div className="space-y-6">
      {/* Quick Summary */}
      <div className="bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800 rounded-lg p-4">
        <h3 className="font-semibold text-purple-900 dark:text-purple-100 mb-2">
          🗺️ Spatial Clustering Insights
        </h3>
        <ul className="text-sm text-purple-800 dark:text-purple-200 space-y-1">
          <li>
            • {data.clusters.length} clusters identified using Moran's I spatial
            autocorrelation
          </li>
          <li>
            • HH = Hotspots (high appreciation), LL = Coldspots (low appreciation)
          </li>
          <li>
            • LH/HL = Transition zones with reversal potential
          </li>
        </ul>
      </div>

      {/* Controls */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <label className="block text-sm font-medium mb-2">Town</label>
          <select
            value={selectedTown}
            onChange={(e) => setSelectedTown(e.target.value)}
            className="w-full px-3 py-2 border rounded-lg dark:bg-gray-800 dark:border-gray-600"
            disabled={towns.length <= 1}
          >
            {towns.map((town) => (
              <option key={town} value={town}>
                {town}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">Investment Horizon</label>
          <select
            value={horizon}
            onChange={(e) => setHorizon(e.target.value as any)}
            className="w-full px-3 py-2 border rounded-lg dark:bg-gray-800 dark:border-gray-600"
          >
            {Object.entries(INVESTMENT_HORIZONS).map(([key, { label }]) => (
              <option key={key} value={key}>
                {label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">Risk Tolerance</label>
          <select
            value={riskTolerance}
            onChange={(e) => setRiskTolerance(e.target.value as any)}
            className="w-full px-3 py-2 border rounded-lg dark:bg-gray-800 dark:border-gray-600"
          >
            {Object.entries(RISK_TOLERANCE).map(([key, { label }]) => (
              <option key={key} value={key}>
                {label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Selected Town Details */}
      {selectedCluster && (
        <div
          className={`border rounded-lg p-4 ${
            CLUSTER_CONFIG[selectedCluster.cluster_type].color
          }`}
        >
          <div className="flex items-start justify-between mb-3">
            <div>
              <div className="text-sm font-medium mb-1">
                {selectedTown} - {CLUSTER_CONFIG[selectedCluster.cluster_type].label}{' '}
                Cluster
              </div>
              <div className="text-xs text-gray-600 dark:text-gray-400">
                {CLUSTER_CONFIG[selectedCluster.cluster_type].description}
              </div>
            </div>
            <div className="text-3xl">
              {CLUSTER_CONFIG[selectedCluster.cluster_type].icon}
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <div className="text-xs text-gray-600 dark:text-gray-400 mb-1">
                5-Year Appreciation
              </div>
              <div
                className={`text-xl font-bold ${
                  CLUSTER_CONFIG[selectedCluster.cluster_type].textColor
                }`}
              >
                {selectedCluster.avg_appreciation_5y.toFixed(1)}%
              </div>
            </div>

            <div>
              <div className="text-xs text-gray-600 dark:text-gray-400 mb-1">
                Avg Price PSF
              </div>
              <div className="text-xl font-bold text-gray-900 dark:text-gray-100">
                ${selectedCluster.avg_price_psf.toLocaleString()}
              </div>
            </div>

            <div>
              <div className="text-xs text-gray-600 dark:text-gray-400 mb-1">
                Persistence Probability
              </div>
              <div className="text-xl font-bold text-gray-900 dark:text-gray-100">
                {(selectedCluster.persistence_probability * 100).toFixed(0)}%
              </div>
            </div>

            <div>
              <div className="text-xs text-gray-600 dark:text-gray-400 mb-1">
                Risk Level
              </div>
              <div className="text-xl font-bold text-gray-900 dark:text-gray-100">
                {selectedCluster.risk_level}
              </div>
            </div>
          </div>

          {/* Expected Returns */}
          <div className="mt-4 pt-4 border-t border-gray-300 dark:border-gray-600">
            <div className="text-xs text-gray-600 dark:text-gray-400 mb-2">
              Expected Return ({INVESTMENT_HORIZONS[horizon].label}, Risk{' '}
              {RISK_TOLERANCE[riskTolerance].label})
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="text-xs text-gray-600 dark:text-gray-400 mb-1">
                  Adjusted Rate
                </div>
                <div className="text-lg font-bold text-gray-900 dark:text-gray-100">
                  {calculateExpectedReturn(
                    selectedCluster,
                    INVESTMENT_HORIZONS[horizon].years,
                    RISK_TOLERANCE[riskTolerance].adjustFactor
                  ).adjustedRate.toFixed(2)}
                  %/year
                </div>
              </div>
              <div>
                <div className="text-xs text-gray-600 dark:text-gray-400 mb-1">
                  Total Return
                </div>
                <div className="text-lg font-bold text-gray-900 dark:text-gray-100">
                  {(
                    calculateExpectedReturn(
                      selectedCluster,
                      INVESTMENT_HORIZONS[horizon].years,
                      RISK_TOLERANCE[riskTolerance].adjustFactor
                    ).totalReturn * 100
                  ).toFixed(1)}
                  %
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Portfolio Allocation */}
      <div className="bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
        <h4 className="font-medium mb-3">
          Portfolio Allocation for{' '}
          {persona === 'investor'
            ? 'Investors'
            : persona === 'first-time-buyer'
            ? 'First-Time Buyers'
            : 'Upgraders'}
        </h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
          {Object.entries(portfolio).map(([key, value]) =>
            typeof value === 'number' ? (
              <div
                key={key}
                className={`p-3 rounded-lg border-2 ${
                  key === 'HH'
                    ? 'border-green-300 dark:border-green-700 bg-green-50 dark:bg-green-900/10'
                    : key === 'HL'
                    ? 'border-yellow-300 dark:border-yellow-700 bg-yellow-50 dark:bg-yellow-900/10'
                    : key === 'LH'
                    ? 'border-blue-300 dark:border-blue-700 bg-blue-50 dark:bg-blue-900/10'
                    : 'border-red-300 dark:border-red-700 bg-red-50 dark:bg-red-900/10'
                }`}
              >
                <div className="text-xs text-gray-600 dark:text-gray-400 mb-1">
                  {key} {CLUSTER_CONFIG[key as keyof typeof CLUSTER_CONFIG].label}
                </div>
                <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                  {value}%
                </div>
              </div>
            ) : null
          )}
        </div>
        <p className="text-sm text-gray-700 dark:text-gray-300">
          <span className="font-medium">Strategy:</span> {portfolio.reasoning}
        </p>
      </div>

      {/* Cluster Summary Table */}
      <div>
        <h4 className="font-medium mb-3">Cluster Summary</h4>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-700">
                <th className="text-left py-2 px-3 font-medium">Cluster Type</th>
                <th className="text-right py-2 px-3 font-medium">Towns</th>
                <th className="text-right py-2 px-3 font-medium">
                  5-Year Appreciation
                </th>
                <th className="text-right py-2 px-3 font-medium">
                  Adjusted Rate ({riskTolerance} risk)
                </th>
                <th className="text-right py-2 px-3 font-medium">
                  Total Return ({INVESTMENT_HORIZONS[horizon].label})
                </th>
                <th className="text-right py-2 px-3 font-medium">Persistence</th>
                <th className="text-right py-2 px-3 font-medium">Risk</th>
              </tr>
            </thead>
            <tbody>
              {clusterSummary.map((summary) => (
                <tr
                  key={summary.type}
                  className={`border-b border-gray-100 dark:border-gray-800 ${
                    CLUSTER_CONFIG[summary.type].color
                  }`}
                >
                  <td className="py-2 px-3">
                    <div className="flex items-center gap-2">
                      <span>{CLUSTER_CONFIG[summary.type].icon}</span>
                      <span className="font-medium">
                        {summary.type} {CLUSTER_CONFIG[summary.type].label}
                      </span>
                    </div>
                  </td>
                  <td className="text-right py-2 px-3">{summary.townCount}</td>
                  <td className="text-right py-2 px-3">
                    {summary.avgAppreciation.toFixed(1)}%
                  </td>
                  <td className="text-right py-2 px-3">
                    {summary.adjustedRate.toFixed(2)}%
                  </td>
                  <td className="text-right py-2 px-3 font-medium">
                    {(summary.totalReturn * 100).toFixed(1)}%
                  </td>
                  <td className="text-right py-2 px-3">
                    {(summary.persistence * 100).toFixed(0)}%
                  </td>
                  <td className="text-right py-2 px-3">{summary.risk}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Methodology Note */}
      <div className="bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
        <h4 className="font-medium mb-2">📊 Methodology</h4>
        <p className="text-sm text-gray-700 dark:text-gray-300">{data.methodology}</p>
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
          Analysis date: {data.analysis_date}
        </p>
      </div>
    </div>
  );
}
