import { useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';
import type { Persona } from '../PersonaSelector';

interface LeaseBand {
  lease_age_band: string;
  min_lease_years: number;
  max_lease_years: number;
  discount_percent: number;
  annual_decay_rate: number;
  volume_category: string;
  risk_zone: string;
}

interface LeaseDecayData {
  bands: LeaseBand[];
  insights: {
    maturity_cliff: { band: string; discount: number; annual_rate: number; description: string };
    best_value: { band: string; discount: number; annual_rate: number; description: string };
    safe_zone: { band: string; discount: number; annual_rate: number; description: string };
  };
}

interface LeaseDecayAnalyzerProps {
  data: LeaseDecayData;
  persona: Persona;
}

export default function LeaseDecayAnalyzer({ data, persona }: LeaseDecayAnalyzerProps) {
  const [remainingLease, setRemainingLease] = useState(75);

  // Find applicable band
  const currentBand = data.bands.find(band =>
    remainingLease >= band.min_lease_years && remainingLease <= band.max_lease_years
  ) || data.bands[0];

  // Risk zone styling
  const riskZoneConfig = {
    'safe': { color: 'green', label: '🟢 Safe Zone', bg: 'bg-green-50 dark:bg-green-900/20', border: 'border-green-200 dark:border-green-800' },
    'moderate': { color: 'yellow', label: '🟡 Moderate', bg: 'bg-yellow-50 dark:bg-yellow-900/20', border: 'border-yellow-200 dark:border-yellow-800' },
    'approaching-cliff': { color: 'orange', label: '🟠 Approaching Cliff', bg: 'bg-orange-50 dark:bg-orange-900/20', border: 'border-orange-200 dark:border-orange-800' },
    'cliff': { color: 'red', label: '🔴 Maturity Cliff', bg: 'bg-red-50 dark:bg-red-900/20', border: 'border-red-200 dark:border-red-800' }
  };

  const riskConfig = riskZoneConfig[currentBand.risk_zone as keyof typeof riskZoneConfig] || riskZoneConfig.safe;

  // Chart data
  const chartData = data.bands.map(band => ({
    age: band.min_lease_years,
    discount: band.discount_percent,
    riskZone: band.risk_zone
  }));

  // Persona recommendation
  const getRecommendation = () => {
    if (persona === 'investor') {
      return remainingLease < 70
        ? `Exit strategy: Sell before cliff accelerates. Target ${data.insights.safe_zone.band} for rental stability.`
        : remainingLease < 80
        ? `Consider ${data.insights.best_value.band} for arbitrage opportunities (25-32% below theoretical value).`
        : `Safe zone for long-term holds or rental income.`;
    } else if (persona === 'first-time-buyer') {
      return remainingLease < 80
        ? `⚠️ Avoid: ${data.insights.maturity_cliff.band} has ${data.insights.maturity_cliff.discount}% discount accelerating at ${data.insights.maturity_cliff.annual_rate}%/year.`
        : remainingLease < 90
        ? `Moderate risk. Consider ${data.insights.safe_zone.band} for maximum loan tenure and CPF usage.`
        : `✅ Optimal: ${data.insights.safe_zone.band} for long-term security and minimal decay (${data.insights.safe_zone.annual_rate}%/year).`;
    } else {
      return remainingLease < 70
        ? `Sell current property before cliff. Upgrade target should have ${data.insights.safe_zone.band} lease.`
        : `Good position. Upgrade to ${data.insights.best_value.band} for 23.8% discount with high liquidity.`;
    }
  };

  return (
    <div className="space-y-6">
      {/* Quick Summary */}
      <div className="bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-lg p-4">
        <h3 className="font-semibold text-orange-900 dark:text-orange-100 mb-2">⚠️ The Maturity Cliff</h3>
        <ul className="text-sm text-orange-800 dark:text-orange-200 space-y-1">
          <li>• <strong>70-80 years remaining:</strong> {data.insights.maturity_cliff.discount}% discount, {data.insights.maturity_cliff.annual_rate}% annual decay</li>
          <li>• <strong>Best value:</strong> {data.insights.best_value.band} at {data.insights.best_value.discount}% discount with high liquidity</li>
          <li>• <strong>Safe zone:</strong> {data.insights.safe_zone.band} for long-term holds</li>
        </ul>
      </div>

      {/* Input */}
      <div>
        <label className="block text-sm font-medium mb-2">
          Remaining Lease: {remainingLease} years
        </label>
        <input
          type="range"
          min="40"
          max="99"
          value={remainingLease}
          onChange={(e) => setRemainingLease(Number(e.target.value))}
          className="w-full"
        />
        <div className="flex justify-between text-xs text-gray-500 mt-1">
          <span>40 years</span>
          <span>99 years</span>
        </div>
      </div>

      {/* Results */}
      <div className={`border rounded-lg p-4 ${riskConfig.bg} ${riskConfig.border}`}>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <div className="text-sm text-gray-600 dark:text-gray-400">Current Band</div>
            <div className="font-semibold">{currentBand.lease_age_band}</div>
          </div>
          <div>
            <div className="text-sm text-gray-600 dark:text-gray-400">Discount</div>
            <div className="font-semibold">{currentBand.discount_percent}%</div>
          </div>
          <div>
            <div className="text-sm text-gray-600 dark:text-gray-400">Annual Decay</div>
            <div className="font-semibold">{currentBand.annual_decay_rate}%</div>
          </div>
          <div>
            <div className="text-sm text-gray-600 dark:text-gray-400">Risk Zone</div>
            <div className="font-semibold">{riskConfig.label}</div>
          </div>
        </div>
      </div>

      {/* Persona Recommendation */}
      <div className="bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
        <div className="text-sm text-gray-600 dark:text-gray-400">
          <span className="font-medium">Recommendation for {persona === 'investor' ? 'Investors' : persona === 'first-time-buyer' ? 'First-Time Buyers' : 'Upgraders'}:</span>
          <span className="ml-2">{getRecommendation()}</span>
        </div>
      </div>

      {/* Visualization */}
      <div>
        <h4 className="font-medium mb-3">Lease Decay Curve</h4>
        <ResponsiveContainer width="100%" height={250}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="age" label={{ value: 'Remaining Lease (years)', position: 'insideBottom', offset: -5 }} />
            <YAxis label={{ value: 'Discount (%)', angle: -90, position: 'insideLeft' }} />
            <Tooltip />
            <Line type="monotone" dataKey="discount" stroke="#f97316" strokeWidth={2} dot={{ r: 3 }} />
            <ReferenceLine x={remainingLease} stroke="#3b82f6" strokeDasharray="5 5" label="Your Position" />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
