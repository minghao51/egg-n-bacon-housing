// app/src/components/dashboard/segments/details/SegmentOverview.tsx
import type { Segment } from '@/types/segments';

interface SegmentOverviewProps {
  segment: Segment;
  persona: string;
}

const RISK_COLORS = {
  low: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
  medium: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
  high: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300',
  very_high: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
};

const HOTSPOT_INFO: Record<string, { icon: string; label: string; description: string; className: string }> = {
  HH: { icon: '🔥', label: 'Hotspot', description: 'High prices surrounded by high prices', className: 'text-red-700 bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800' },
  LL: { icon: '❄️', label: 'Coldspot', description: 'Low prices surrounded by low prices', className: 'text-blue-700 bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800' },
  HL: { icon: '⚡', label: 'High-Low Pioneer', description: 'High prices in lower-priced area', className: 'text-orange-700 bg-orange-50 dark:bg-orange-900/20 border-orange-200 dark:border-orange-800' },
  LH: { icon: '🔄', label: 'Low-High Transition', description: 'Low prices near higher-priced areas', className: 'text-purple-700 bg-purple-50 dark:bg-purple-900/20 border-purple-200 dark:border-purple-800' },
};

export function SegmentOverview({ segment, persona }: SegmentOverviewProps) {
  const riskColor = RISK_COLORS[segment.characteristics.riskLevel];

  const getImplication = () => {
    switch (persona) {
      case 'investor':
        return segment.implications.investor;
      case 'first-time-buyer':
        return segment.implications.firstTimeBuyer;
      case 'upgrader':
        return segment.implications.upgrader;
      default:
        return segment.implications.investor;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-3 mb-2">
          <span className="text-4xl">📊</span>
          <div>
            <h2 className="text-2xl font-bold text-foreground">{segment.name}</h2>
            <p className="text-muted-foreground">{segment.description}</p>
          </div>
        </div>
        <div className="flex items-center gap-2 mt-3">
          <span className={`px-3 py-1 text-sm font-medium rounded-full ${riskColor}`}>
            {segment.characteristics.riskLevel.replace('_', ' ').toUpperCase()} RISK
          </span>
          <span className="px-3 py-1 text-sm font-medium rounded-full bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300">
            {segment.investmentType.toUpperCase()}
          </span>
        </div>
      </div>

      {/* Key Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label="Price PSF" value={`$${segment.metrics.avgPricePsf.toFixed(0)}`} />
        <StatCard label="Yield" value={`${segment.metrics.avgYield.toFixed(1)}%`} />
        <StatCard label="YoY Growth" value={`+${segment.metrics.yoyGrowth.toFixed(1)}%`} />
        <StatCard label="Market Share" value={`${(segment.metrics.marketShare * 100).toFixed(1)}%`} />
      </div>

      {/* Hotspot Information */}
      {segment.spatialClassification && HOTSPOT_INFO[segment.spatialClassification] && (
        <div className={`border p-4 rounded-lg ${HOTSPOT_INFO[segment.spatialClassification].className}`}>
          <div className="flex items-center gap-2 mb-2">
            <span className="text-2xl">{HOTSPOT_INFO[segment.spatialClassification].icon}</span>
            <div>
              <h3 className="font-semibold">{HOTSPOT_INFO[segment.spatialClassification].label} Area</h3>
              <p className="text-sm opacity-80">{HOTSPOT_INFO[segment.spatialClassification].description}</p>
            </div>
          </div>
          {segment.persistenceProbability > 0 && (
            <p className="text-sm mt-2">
              <strong>Persistence Probability:</strong> {(segment.persistenceProbability * 100).toFixed(0)}%
              {segment.spatialClassification === 'HH' && ' - Hotspots tend to remain hot year-over-year'}
              {segment.spatialClassification === 'LL' && ' - Coldspots show persistent price discounts'}
            </p>
          )}
        </div>
      )}

      {/* Characteristics */}
      <div className="bg-muted/50 p-4 rounded-lg">
        <h3 className="font-semibold text-foreground mb-3">Characteristics</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-sm">
          <div>
            <span className="text-muted-foreground">Price Tier:</span>{' '}
            <span className="font-medium">{segment.characteristics.priceTier}</span>
          </div>
          <div>
            <span className="text-muted-foreground">Volatility:</span>{' '}
            <span className="font-medium">{segment.characteristics.volatility}</span>
          </div>
          <div>
            <span className="text-muted-foreground">Appreciation:</span>{' '}
            <span className="font-medium">{segment.characteristics.appreciationPotential}</span>
          </div>
          <div>
            <span className="text-muted-foreground">Spatial:</span>{' '}
            <span className="font-medium">{segment.spatialClassification}</span>
          </div>
          <div>
            <span className="text-muted-foreground">MRT Sensitivity:</span>{' '}
            <span className="font-medium">{segment.mrtSensitivity}</span>
          </div>
          <div>
            <span className="text-muted-foreground">School Quality:</span>{' '}
            <span className="font-medium">{segment.schoolQuality}</span>
          </div>
        </div>
      </div>

      {/* Persona-Specific Implication */}
      <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 p-4 rounded-lg">
        <h3 className="font-semibold text-foreground mb-2">
          For {persona === 'all' ? 'Investors' : persona.replace('-', ' ')}:
        </h3>
        <p className="text-sm text-muted-foreground">{getImplication()}</p>
      </div>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-card border border-border p-3 rounded-lg">
      <div className="text-xs text-muted-foreground mb-1">{label}</div>
      <div className="text-xl font-bold text-foreground">{value}</div>
    </div>
  );
}
