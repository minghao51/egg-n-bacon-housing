import { useState, useMemo } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import type { Persona } from '../PersonaSelector';

interface TownMetric {
  town: string;
  property_type: string;
  median_price: number;
  affordability_ratio: number;
  category: string;
  estimated_monthly_mortgage: number;
}

interface AffordabilityData {
  median_household_income: number;
  town_metrics: TownMetric[];
}

interface AffordabilityCalculatorProps {
  data: AffordabilityData;
  persona: Persona;
}

const CATEGORIES = {
  affordable: {
    label: 'Affordable',
    color: 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800',
    textColor: 'text-green-700 dark:text-green-300',
    barColor: '#10b981',
    description: 'Price-to-income ratio ≤ 2.5x. Excellent affordability.',
  },
  moderate: {
    label: 'Moderate',
    color: 'bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800',
    textColor: 'text-yellow-700 dark:text-yellow-300',
    barColor: '#f59e0b',
    description: 'Price-to-income ratio 2.5-3.5x. Manageable with careful budgeting.',
  },
  stretched: {
    label: 'Stretched',
    color: 'bg-orange-50 dark:bg-orange-900/20 border-orange-200 dark:border-orange-800',
    textColor: 'text-orange-700 dark:text-orange-300',
    barColor: '#f97316',
    description: 'Price-to-income ratio 3.5-5.0x. Consider smaller units or longer tenure.',
  },
  severe: {
    label: 'Severe',
    color: 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800',
    textColor: 'text-red-700 dark:text-red-300',
    barColor: '#ef4444',
    description: 'Price-to-income ratio > 5.0x. High financial burden. Explore alternatives.',
  },
};

export default function AffordabilityCalculator({
  data,
  persona,
}: AffordabilityCalculatorProps) {
  const [annualIncome, setAnnualIncome] = useState(120000);
  const [propertyType, setPropertyType] = useState<'HDB' | 'Condominium' | 'EC'>(
    'HDB'
  );
  const [selectedTown, setSelectedTown] = useState<string>('All Towns');

  // Filter metrics by property type
  const filteredMetrics = useMemo(() => {
    return data.town_metrics.filter((m) => m.property_type === propertyType);
  }, [data.town_metrics, propertyType]);

  // Get unique towns
  const towns = useMemo(() => {
    const uniqueTowns = Array.from(
      new Set(filteredMetrics.map((m) => m.town))
    ).sort();
    return ['All Towns', ...uniqueTowns];
  }, [filteredMetrics]);

  // Calculate user's affordability ratio for selected town
  const userAffordability = useMemo(() => {
    if (selectedTown === 'All Towns') {
      // Calculate national average ratio for this property type
      const avgPrice =
        filteredMetrics.reduce((sum, m) => sum + m.median_price, 0) /
        filteredMetrics.length;
      return avgPrice / annualIncome;
    } else {
      const townData = filteredMetrics.find((m) => m.town === selectedTown);
      return townData ? townData.median_price / annualIncome : 0;
    }
  }, [filteredMetrics, selectedTown, annualIncome]);

  // Determine category
  const getCategory = (ratio: number) => {
    if (ratio <= 2.5) return 'affordable';
    if (ratio <= 3.5) return 'moderate';
    if (ratio <= 5.0) return 'stretched';
    return 'severe';
  };

  const userCategory = getCategory(userAffordability);

  // Estimate monthly mortgage (assuming 30% downpayment, 25-year loan at 3%)
  const estimateMonthlyMortgage = (price: number) => {
    const loanAmount = price * 0.7;
    const monthlyRate = 0.03 / 12;
    const months = 25 * 12;
    return (
      (loanAmount * monthlyRate * Math.pow(1 + monthlyRate, months)) /
      (Math.pow(1 + monthlyRate, months) - 1)
    );
  };

  const userMonthlyMortgage = estimateMonthlyMortgage(
    userAffordability * annualIncome
  );

  // Count affordable towns
  const affordableCount = useMemo(() => {
    return filteredMetrics.filter((m) => m.category === 'affordable').length;
  }, [filteredMetrics]);

  // Get top 10 and bottom 10 towns for chart
  const chartData = useMemo(() => {
    const sorted = [...filteredMetrics].sort(
      (a, b) => a.affordability_ratio - b.affordability_ratio
    );
    const top10 = sorted.slice(0, 10);
    const bottom10 = sorted.slice(-10).reverse();
    return [...top10, ...bottom10];
  }, [filteredMetrics]);

  // Persona recommendation
  const getRecommendation = () => {
    if (persona === 'investor') {
      return `Focus on rental yield potential rather than affordability. Properties in "stretched" areas often command higher rents, improving ROI.`;
    } else if (persona === 'first-time-buyer') {
      return `Target "affordable" towns with good transport links. Keep your ratio below 3.0x for better loan approval chances and financial buffer.`;
    } else {
      return `Consider your current equity + sale proceeds. For upgraders, a ratio up to 4.0x is manageable if you're selling an existing property.`;
    }
  };

  return (
    <div className="space-y-6">
      {/* Quick Summary */}
      <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
        <h3 className="font-semibold text-blue-900 dark:text-blue-100 mb-2">
          💡 Affordability Insights
        </h3>
        <ul className="text-sm text-blue-800 dark:text-blue-200 space-y-1">
          <li>
            • National median household income: ${data.median_household_income.toLocaleString()}
          </li>
          <li>
            • {affordableCount} of {towns.length - 1} towns are "affordable" for{' '}
            {propertyType}
          </li>
          <li>
            • Target ratio ≤ 3.0x for easier loan approval (MSR 30% limit for HDB)
          </li>
        </ul>
      </div>

      {/* Inputs */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <label className="block text-sm font-medium mb-2">
            Annual Household Income: ${annualIncome.toLocaleString()}
          </label>
          <input
            type="range"
            min="30000"
            max="500000"
            step="10000"
            value={annualIncome}
            onChange={(e) => setAnnualIncome(Number(e.target.value))}
            className="w-full"
          />
          <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400 mt-1">
            <span>$30k</span>
            <span>$500k</span>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">Property Type</label>
          <select
            value={propertyType}
            onChange={(e) => setPropertyType(e.target.value as any)}
            className="w-full px-3 py-2 border rounded-lg dark:bg-gray-800 dark:border-gray-600"
          >
            <option value="HDB">HDB</option>
            <option value="Condominium">Condominium</option>
            <option value="EC">EC (Executive Condo)</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">Town</label>
          <select
            value={selectedTown}
            onChange={(e) => setSelectedTown(e.target.value)}
            className="w-full px-3 py-2 border rounded-lg dark:bg-gray-800 dark:border-gray-600"
          >
            {towns.map((town) => (
              <option key={town} value={town}>
                {town}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Results */}
      <div
        className={`border rounded-lg p-4 ${CATEGORIES[userCategory as keyof typeof CATEGORIES].color}`}
      >
        <div className="text-sm font-medium mb-1">
          {selectedTown === 'All Towns'
            ? `National Average (${propertyType})`
            : selectedTown}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <div className="text-xs text-gray-600 dark:text-gray-400 mb-1">
              Price-to-Income Ratio
            </div>
            <div
              className={`text-3xl font-bold ${CATEGORIES[userCategory as keyof typeof CATEGORIES].textColor}`}
            >
              {userAffordability.toFixed(2)}x
            </div>
            <div className="text-xs text-gray-600 dark:text-gray-400 mt-1">
              {CATEGORIES[userCategory as keyof typeof CATEGORIES].label}
            </div>
          </div>
          <div>
            <div className="text-xs text-gray-600 dark:text-gray-400 mb-1">
              Estimated Property Price
            </div>
            <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
              ${(userAffordability * annualIncome).toLocaleString()}
            </div>
          </div>
          <div>
            <div className="text-xs text-gray-600 dark:text-gray-400 mb-1">
              Est. Monthly Mortgage
            </div>
            <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
              ${Math.round(userMonthlyMortgage).toLocaleString()}
            </div>
            <div className="text-xs text-gray-600 dark:text-gray-400 mt-1">
              {(userMonthlyMortgage / (annualIncome / 12) * 100).toFixed(1)}% of
              income
            </div>
          </div>
        </div>
        <div className="mt-3 pt-3 border-t border-gray-300 dark:border-gray-600">
          <p className="text-sm text-gray-700 dark:text-gray-300">
            {CATEGORIES[userCategory as keyof typeof CATEGORIES].description}
          </p>
        </div>
      </div>

      {/* Persona Recommendation */}
      <div className="bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
        <div className="text-sm text-gray-600 dark:text-gray-400">
          <span className="font-medium">
            Recommendation for{' '}
            {persona === 'investor'
              ? 'Investors'
              : persona === 'first-time-buyer'
              ? 'First-Time Buyers'
              : 'Upgraders'}
            :
          </span>{' '}
          <span className="ml-1">{getRecommendation()}</span>
        </div>
      </div>

      {/* Visualization */}
      <div>
        <h4 className="font-medium mb-3">
          Affordability Ratio by Town ({propertyType})
        </h4>
        <ResponsiveContainer width="100%" height={400}>
          <BarChart data={chartData} layout="vertical">
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis type="number" domain={[0, 'dataMax + 1']} />
            <YAxis dataKey="town" type="category" width={120} />
            <Tooltip
              formatter={(value: number, name: string) => {
                if (name === 'affordability_ratio') {
                  return [`${value.toFixed(2)}x`, 'Affordability Ratio'];
                }
                return [value, name];
              }}
            />
            <ReferenceLine x={3.0} stroke="#ef4444" strokeWidth={2} />
            <Bar
              dataKey="affordability_ratio"
              fill={(entry: any) =>
                CATEGORIES[getCategory(entry.affordability_ratio) as keyof typeof CATEGORIES]
                  .barColor
              }
            />
          </BarChart>
        </ResponsiveContainer>
        <div className="text-center mt-2">
          <span className="inline-flex items-center gap-2 text-xs text-gray-600 dark:text-gray-400">
            <span className="w-3 h-3 bg-red-500 rounded"></span>
            <span>3.0x = Target for loan approval</span>
          </span>
        </div>
      </div>
    </div>
  );
}
