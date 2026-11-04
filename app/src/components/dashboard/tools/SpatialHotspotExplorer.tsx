import { useMemo, useState } from "react";
import type { Persona } from "../PersonaSelector";
import TrendsMap from "../TrendsMap";
import type {
  HotspotClusterType,
  HotspotPortfolioPersona,
  SpatialHotspotsData,
  SpatialHotspotTown,
} from "../../../types/spatial-hotspots";

interface SpatialHotspotExplorerProps {
  data: SpatialHotspotsData;
  persona: Persona;
}

const NOT_AVAILABLE = "Not available in this published snapshot";

const CLUSTER_TYPES: HotspotClusterType[] = ["HH", "HL", "LH", "LL"];

const PORTFOLIO_PERSONAS: HotspotPortfolioPersona[] = [
  "investor",
  "first-time-buyer",
  "upgrader",
];

interface ClusterConfig {
  label: string;
  color: string;
  textColor: string;
  badgeColor: string;
  description: string;
  icon: string;
}

const CLUSTER_CONFIG: Record<HotspotClusterType, ClusterConfig> = {
  HH: {
    label: "High-High",
    color:
      "bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800",
    textColor: "text-green-700 dark:text-green-300",
    badgeColor:
      "bg-green-100 dark:bg-green-800 text-green-800 dark:text-green-200",
    description:
      "Hotspots with high appreciation surrounded by high-appreciation areas",
    icon: "🔥",
  },
  LH: {
    label: "Low-High",
    color:
      "bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800",
    textColor: "text-blue-700 dark:text-blue-300",
    badgeColor: "bg-blue-100 dark:bg-blue-800 text-blue-800 dark:text-blue-200",
    description:
      "Coldspots surrounded by hotspots - potential transition zones",
    icon: "❄️",
  },
  HL: {
    label: "High-Low",
    color:
      "bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800",
    textColor: "text-yellow-700 dark:text-yellow-300",
    badgeColor:
      "bg-yellow-100 dark:bg-yellow-800 text-yellow-800 dark:text-yellow-200",
    description: "Hotspots surrounded by coldspots - emerging pioneers",
    icon: "⭐",
  },
  LL: {
    label: "Low-Low",
    color: "bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800",
    textColor: "text-red-700 dark:text-red-300",
    badgeColor: "bg-red-100 dark:bg-red-800 text-red-800 dark:text-red-200",
    description:
      "Coldspots with low appreciation surrounded by low-appreciation areas",
    icon: "🥶",
  },
};

const INVESTMENT_HORIZONS = {
  short: { label: "Short Term (1-3 years)", years: 2 },
  medium: { label: "Medium Term (3-7 years)", years: 5 },
  long: { label: "Long Term (7-15 years)", years: 10 },
};

const RISK_TOLERANCE = {
  low: { label: "Low", adjustFactor: 0.7 },
  medium: { label: "Medium", adjustFactor: 1.0 },
  high: { label: "High", adjustFactor: 1.3 },
};

function isClusterType(value: unknown): value is HotspotClusterType {
  return CLUSTER_TYPES.some((type) => type === value);
}

function isPortfolioPersona(value: string): value is HotspotPortfolioPersona {
  return PORTFOLIO_PERSONAS.some((persona) => persona === value);
}

function isHorizon(value: string): value is keyof typeof INVESTMENT_HORIZONS {
  return Object.prototype.hasOwnProperty.call(INVESTMENT_HORIZONS, value);
}

function isRiskTolerance(value: string): value is keyof typeof RISK_TOLERANCE {
  return Object.prototype.hasOwnProperty.call(RISK_TOLERANCE, value);
}

/** Read a town's cluster from `town_clusters`, falling back to its town record. */
function clusterTypeForTown(
  data: SpatialHotspotsData,
  town: string,
): HotspotClusterType | null {
  const fromMap = data.town_clusters[town];
  if (isClusterType(fromMap)) {
    return fromMap;
  }
  const record = data.towns.find((entry) => entry.town === town);
  if (record && isClusterType(record.cluster)) {
    return record.cluster;
  }
  return null;
}

function formatRiskLevel(level: string): string {
  return level.length > 0 ? level.charAt(0).toUpperCase() + level.slice(1) : "";
}

function NotAvailable() {
  return (
    <span className="text-xs text-gray-500 dark:text-gray-400">
      {NOT_AVAILABLE}
    </span>
  );
}

export default function SpatialHotspotExplorer({
  data,
  persona,
}: SpatialHotspotExplorerProps) {
  const [selectedTown, setSelectedTown] = useState<string>("All Towns");
  const [horizon, setHorizon] =
    useState<keyof typeof INVESTMENT_HORIZONS>("medium");
  const [riskTolerance, setRiskTolerance] =
    useState<keyof typeof RISK_TOLERANCE>("medium");

  // Get all towns from the published `towns` records
  const towns = useMemo(() => {
    const allTowns = data.towns
      .map((record) => record.town)
      .filter((town) => town.trim().length > 0);
    const uniqueTowns = Array.from(new Set(allTowns)).sort();
    return ["All Towns", ...uniqueTowns];
  }, [data.towns]);

  const selectedTownRecord = useMemo<SpatialHotspotTown | null>(() => {
    if (selectedTown === "All Towns") return null;
    return data.towns.find((record) => record.town === selectedTown) ?? null;
  }, [data.towns, selectedTown]);

  // Get selected town's cluster
  const selectedClusterType = useMemo<HotspotClusterType | null>(() => {
    if (selectedTown === "All Towns") return null;
    return clusterTypeForTown(data, selectedTown);
  }, [data, selectedTown]);

  // Cluster membership, grouped from the published town records
  const clusterSummaries = useMemo(() => {
    return CLUSTER_TYPES.map((type) => ({
      type,
      townCount: data.towns.filter((record) => record.cluster === type).length,
    })).filter((summary) => summary.townCount > 0);
  }, [data.towns]);

  const visibleClusterSummaries = useMemo(() => {
    if (selectedTown === "All Towns") return clusterSummaries;
    if (!selectedClusterType) return [];
    return clusterSummaries.filter(
      (summary) => summary.type === selectedClusterType,
    );
  }, [clusterSummaries, selectedClusterType, selectedTown]);

  // Calculate expected returns from the published appreciation rate
  const calculateExpectedReturn = (
    appreciationRate: number,
    years: number,
    riskFactor: number,
  ) => {
    const adjustedRate = appreciationRate * riskFactor;
    const totalReturn = Math.pow(1 + adjustedRate / 100, years) - 1;
    return { adjustedRate, totalReturn };
  };

  // Get portfolio allocation by persona from the published asset
  const portfolioAllocation = useMemo(() => {
    if (!isPortfolioPersona(persona)) {
      return null;
    }
    const allocation = data.portfolio_allocation[persona];
    if (!allocation) {
      return null;
    }
    const entries = CLUSTER_TYPES.map((type) => ({
      type,
      value: allocation[type],
    })).filter(
      (entry): entry is { type: HotspotClusterType; value: number } =>
        typeof entry.value === "number",
    );
    return entries.length > 0 ? entries : null;
  }, [data.portfolio_allocation, persona]);

  return (
    <div className="flex flex-col gap-6">
      {/* Map Section */}
      <div className="h-[60vh] min-h-[400px] max-h-[600px] w-full">
        <h4 className="font-medium mb-3">Spatial Clusters by Town</h4>
        <div className="h-[calc(100%-2rem)] border border-border rounded-lg overflow-hidden">
          <TrendsMap
            metricData={data.town_clusters}
            metricLabel="Cluster Type"
            colorScale="diverging"
            showLegend={true}
          />
        </div>
      </div>

      {/* Details Section */}
      <div className="space-y-6">
        {/* Quick Summary */}
        <div className="bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800 rounded-lg p-4">
          <h3 className="font-semibold text-purple-900 dark:text-purple-100 mb-2">
            🗺️ Spatial Clustering Insights
          </h3>
          <ul className="text-sm text-purple-800 dark:text-purple-200 space-y-1">
            <li>
              • {clusterSummaries.length} cluster types across{" "}
              {data.towns.length} published town records (Moran's I
              classification)
            </li>
            <li>
              • HH = Hotspots (high appreciation), LL = Coldspots (low
              appreciation)
            </li>
            <li>• LH/HL = Transition zones with reversal potential</li>
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
            <label className="block text-sm font-medium mb-2">
              Investment Horizon
            </label>
            <select
              value={horizon}
              onChange={(e) => {
                if (isHorizon(e.target.value)) setHorizon(e.target.value);
              }}
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
            <label className="block text-sm font-medium mb-2">
              Risk Tolerance
            </label>
            <select
              value={riskTolerance}
              onChange={(e) => {
                if (isRiskTolerance(e.target.value))
                  setRiskTolerance(e.target.value);
              }}
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
        {selectedTownRecord && selectedClusterType && (
          <div
            className={`border rounded-lg p-4 ${
              CLUSTER_CONFIG[selectedClusterType].color
            }`}
          >
            <div className="flex items-start justify-between mb-3">
              <div>
                <div className="text-sm font-medium mb-1">
                  {selectedTownRecord.town} -{" "}
                  {CLUSTER_CONFIG[selectedClusterType].label} Cluster
                </div>
                <div className="text-xs text-gray-600 dark:text-gray-400">
                  {selectedTownRecord.cluster_description ??
                    CLUSTER_CONFIG[selectedClusterType].description}
                </div>
              </div>
              <div className="text-3xl">
                {CLUSTER_CONFIG[selectedClusterType].icon}
              </div>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <div className="text-xs text-gray-600 dark:text-gray-400 mb-1">
                  Appreciation Rate
                </div>
                <div
                  className={`text-xl font-bold ${
                    CLUSTER_CONFIG[selectedClusterType].textColor
                  }`}
                >
                  {selectedTownRecord.appreciation_rate.toFixed(1)}%
                </div>
              </div>

              <div>
                <div className="text-xs text-gray-600 dark:text-gray-400 mb-1">
                  Median Price
                </div>
                <div className="text-xl font-bold text-gray-900 dark:text-gray-100">
                  ${selectedTownRecord.median_price.toLocaleString()}
                </div>
              </div>

              <div>
                <div className="text-xs text-gray-600 dark:text-gray-400 mb-1">
                  Persistence Probability
                </div>
                <div className="text-xl font-bold text-gray-900 dark:text-gray-100">
                  {(selectedTownRecord.persistence_probability * 100).toFixed(
                    0,
                  )}
                  %
                </div>
              </div>

              <div>
                <div className="text-xs text-gray-600 dark:text-gray-400 mb-1">
                  Risk Level
                </div>
                <div className="text-xl font-bold text-gray-900 dark:text-gray-100">
                  {formatRiskLevel(selectedTownRecord.risk_level)}
                </div>
              </div>
            </div>

            {/* Expected Returns */}
            <div className="mt-4 pt-4 border-t border-gray-300 dark:border-gray-600">
              <div className="text-xs text-gray-600 dark:text-gray-400 mb-2">
                Expected Return ({INVESTMENT_HORIZONS[horizon].label}, Risk{" "}
                {RISK_TOLERANCE[riskTolerance].label})
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="text-xs text-gray-600 dark:text-gray-400 mb-1">
                    Adjusted Rate
                  </div>
                  <div className="text-lg font-bold text-gray-900 dark:text-gray-100">
                    {calculateExpectedReturn(
                      selectedTownRecord.appreciation_rate,
                      INVESTMENT_HORIZONS[horizon].years,
                      RISK_TOLERANCE[riskTolerance].adjustFactor,
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
                        selectedTownRecord.appreciation_rate,
                        INVESTMENT_HORIZONS[horizon].years,
                        RISK_TOLERANCE[riskTolerance].adjustFactor,
                      ).totalReturn * 100
                    ).toFixed(1)}
                    %
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Selected town without a published cluster assignment */}
        {selectedTown !== "All Towns" && !selectedClusterType && (
          <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
            <div className="text-sm font-medium mb-1">{selectedTown}</div>
            <div className="text-xs text-gray-600 dark:text-gray-400">
              This town has no cluster assignment in the published snapshot.
            </div>
          </div>
        )}

        {/* Portfolio Allocation */}
        <div className="bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
          <h4 className="font-medium mb-3">
            {persona === "all"
              ? "Neutral Cluster Mix"
              : `Portfolio Allocation for ${
                  persona === "investor"
                    ? "Investors"
                    : persona === "first-time-buyer"
                      ? "First-Time Buyers"
                      : "Upgraders"
                }`}
          </h4>
          {portfolioAllocation ? (
            <>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
                {portfolioAllocation.map(({ type, value }) => (
                  <div
                    key={type}
                    className={`p-3 rounded-lg border-2 ${
                      type === "HH"
                        ? "border-green-300 dark:border-green-700 bg-green-50 dark:bg-green-900/10"
                        : type === "HL"
                          ? "border-yellow-300 dark:border-yellow-700 bg-yellow-50 dark:bg-yellow-900/10"
                          : type === "LH"
                            ? "border-blue-300 dark:border-blue-700 bg-blue-50 dark:bg-blue-900/10"
                            : "border-red-300 dark:border-red-700 bg-red-50 dark:bg-red-900/10"
                    }`}
                  >
                    <div className="text-xs text-gray-600 dark:text-gray-400 mb-1">
                      {type} {CLUSTER_CONFIG[type].label}
                    </div>
                    <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                      {value}%
                    </div>
                  </div>
                ))}
              </div>
              <p className="text-sm text-gray-700 dark:text-gray-300">
                <span className="font-medium">Allocation:</span> published for
                this persona in the current snapshot. The snapshot does not
                publish a rationale for these weights, so none is shown.
              </p>
            </>
          ) : (
            <p className="text-sm text-gray-700 dark:text-gray-300">
              <span className="font-medium">Strategy:</span> {NOT_AVAILABLE}.
              This snapshot publishes cluster allocations for the investor,
              first-time-buyer and upgrader personas only, so no neutral mix is
              shown here.
            </p>
          )}
        </div>

        {/* Cluster Summary Table */}
        <div>
          <h4 className="font-medium mb-3">Cluster Summary</h4>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 dark:border-gray-700">
                  <th className="text-left py-2 px-3 font-medium">
                    Cluster Type
                  </th>
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
                  <th className="text-right py-2 px-3 font-medium">
                    Persistence
                  </th>
                  <th className="text-right py-2 px-3 font-medium">Risk</th>
                </tr>
              </thead>
              <tbody>
                {visibleClusterSummaries.map((summary) => (
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
                      {data.cluster_descriptions[summary.type] ? (
                        <div className="text-xs text-gray-600 dark:text-gray-400">
                          {data.cluster_descriptions[summary.type]}
                        </div>
                      ) : null}
                    </td>
                    <td className="text-right py-2 px-3">
                      {summary.townCount}
                    </td>
                    <td className="text-right py-2 px-3">
                      <NotAvailable />
                    </td>
                    <td className="text-right py-2 px-3">
                      <NotAvailable />
                    </td>
                    <td className="text-right py-2 px-3">
                      <NotAvailable />
                    </td>
                    <td className="text-right py-2 px-3">
                      <NotAvailable />
                    </td>
                    <td className="text-right py-2 px-3">
                      <NotAvailable />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
            This snapshot publishes town-level cluster assignments only. Cluster
            averages for appreciation, persistence and risk are{" "}
            {NOT_AVAILABLE.toLowerCase()}.
          </p>
        </div>

        {/* Methodology Note */}
        <div className="bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
          <h4 className="font-medium mb-2">📊 Methodology</h4>
          <p className="text-sm text-gray-700 dark:text-gray-300">
            Methodology notes are not available in this published snapshot.
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
            Analysis date: not available in this published snapshot.
          </p>
        </div>
      </div>
    </div>
  );
}
