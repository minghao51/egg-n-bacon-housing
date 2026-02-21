import { useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts';
import type { Persona } from '../PersonaSelector';

interface MrtCbdData {
  property_type_multipliers: {
    [key: string]: { premium_per_100m: number; cbd_per_km: number };
  };
  town_multipliers: { [key: string]: number };
  town_premiums: Array<{
    town: string;
    multiplier: number;
    hdb_premium_per_100m: number;
    condo_premium_per_100m: number;
  }>;
}

interface MrtCbdCalculatorProps {
  data: MrtCbdData;
  persona: Persona;
}

export default function MrtCbdCalculator({ data, persona }: MrtCbdCalculatorProps) {
  const [propertyType, setPropertyType] = useState<'HDB' | 'Condominium' | 'EC'>('HDB');
  const [mrtDistance, setMrtDistance] = useState(500);
  const [cbdDistance, setCbdDistance] = useState(10);
  const [selectedTown, setSelectedTown] = useState('Bishan');

  // Calculate MRT premium
  const basePremium = data.property_type_multipliers[propertyType]?.premium_per_100m || 5;
  const townMultiplier = data.town_multipliers[selectedTown] || 1.0;
  const effectiveDistance = Math.min(mrtDistance, 500);
  const premiumPer100m = basePremium * townMultiplier;
  const totalMrtPremium = (effectiveDistance / 100) * premiumPer100m * 1000; // Convert to dollars

  // Calculate CBD discount
  const cbdPerKm = data.property_type_multipliers[propertyType]?.cbd_per_km || 15000;
  const totalCbdDiscount = cbdDistance * cbdPerKm;

  const netEffect = totalMrtPremium - totalCbdDiscount;

  // Decay curve data
  const decayData = Array.from({ length: 6 }, (_, i) => ({
    distance: i * 100,
    premium: (i * 100) / 100 * premiumPer100m * 1000
  }));

  // Top and bottom towns
  const topTowns = data.town_premiums.slice(0, 5);
  const bottomTowns = data.town_premiums.slice(-5).reverse();

  // Persona recommendation
  const getRecommendation = () => {
    if (persona === 'investor') {
      return `For ${propertyType}, focus on town multiplier (currently ${townMultiplier}x) rather than pure MRT distance. Consider towns with multipliers >1.5x for better appreciation.`;
    } else if (persona === 'first-time-buyer') {
      return `HDB MRT premium is minimal ($${premiumPer100m}/100m). Prioritize lease remaining and affordability over MRT proximity.`;
    } else {
      return `Compare current town (${data.town_multipliers[selectedTown]}x) vs target. Condos are 15x more MRT-sensitive than HDB.`;
    }
  };

  return (
    <div className="space-y-6">
      {/* Quick Summary */}
      <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
        <h3 className="font-semibold text-blue-900 dark:text-blue-100 mb-2">💡 Key Insight</h3>
        <ul className="text-sm text-blue-800 dark:text-blue-200 space-y-1">
          <li>• MRT premium: ${premiumPer100m}/100m for {propertyType}</li>
          <li>• CBD distance explains 22.6% of price variation vs 0.78% for MRT</li>
          <li>• Condos are 7x more MRT-sensitive than HDB</li>
        </ul>
      </div>

      {/* Inputs */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div>
          <label className="block text-sm font-medium mb-2">Property Type</label>
          <select
            value={propertyType}
            onChange={(e) => setPropertyType(e.target.value as any)}
            className="w-full px-3 py-2 border rounded-lg dark:bg-gray-800 dark:border-gray-600"
          >
            <option value="HDB">HDB</option>
            <option value="Condominium">Condominium</option>
            <option value="EC">EC</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">
            Distance to MRT: {mrtDistance}m
          </label>
          <input
            type="range"
            min="0"
            max="2000"
            step="50"
            value={mrtDistance}
            onChange={(e) => setMrtDistance(Number(e.target.value))}
            className="w-full"
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">
            Distance to CBD: {cbdDistance}km
          </label>
          <input
            type="range"
            min="0"
            max="15"
            step="0.5"
            value={cbdDistance}
            onChange={(e) => setCbdDistance(Number(e.target.value))}
            className="w-full"
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">Town</label>
          <select
            value={selectedTown}
            onChange={(e) => setSelectedTown(e.target.value)}
            className="w-full px-3 py-2 border rounded-lg dark:bg-gray-800 dark:border-gray-600"
          >
            {Object.entries(data.town_multipliers).map(([town]) => (
              <option key={town} value={town}>{town}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Results */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4">
          <div className="text-sm text-green-600 dark:text-green-400 font-medium">MRT Premium</div>
          <div className="text-2xl font-bold text-green-700 dark:text-green-300">
            +${totalMrtPremium.toLocaleString()}
          </div>
        </div>
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <div className="text-sm text-red-600 dark:text-red-400 font-medium">CBD Discount</div>
          <div className="text-2xl font-bold text-red-700 dark:text-red-300">
            -${totalCbdDiscount.toLocaleString()}
          </div>
        </div>
        <div className={`border rounded-lg p-4 ${netEffect >= 0 ? 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800' : 'bg-orange-50 dark:bg-orange-900/20 border-orange-200 dark:border-orange-800'}`}>
          <div className={`text-sm font-medium ${netEffect >= 0 ? 'text-green-600 dark:text-green-400' : 'text-orange-600 dark:text-orange-400'}`}>Net Effect</div>
          <div className={`text-2xl font-bold ${netEffect >= 0 ? 'text-green-700 dark:text-green-300' : 'text-orange-700 dark:text-orange-300'}`}>
            {netEffect >= 0 ? '+' : ''}${netEffect.toLocaleString()}
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

      {/* Visualizations */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div>
          <h4 className="font-medium mb-3">MRT Premium Decay Curve</h4>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={decayData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="distance" label={{ value: 'Distance (m)', position: 'insideBottom', offset: -5 }} />
              <YAxis label={{ value: 'Premium ($)', angle: -90, position: 'insideLeft' }} />
              <Tooltip formatter={(value: number) => `$${value.toLocaleString()}`} />
              <Line type="monotone" dataKey="premium" stroke="#3b82f6" strokeWidth={2} dot={{ r: 4 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div>
          <h4 className="font-medium mb-3">Top vs Bottom Towns (MRT Multiplier)</h4>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={[...topTowns, ...bottomTowns]} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" />
              <YAxis dataKey="town" type="category" width={100} />
              <Tooltip />
              <Bar dataKey="multiplier" fill={(entry: any) => entry.multiplier >= 1 ? '#10b981' : '#ef4444'} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
