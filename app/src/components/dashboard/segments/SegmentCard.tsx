// app/src/components/dashboard/segments/SegmentCard.tsx
import type { Segment } from '@/types/segments';
import clsx from 'clsx';

interface SegmentCardProps {
  segment: Segment;
  matchScore?: number;
  onViewDetails: (segment: Segment) => void;
  onAddToCompare: (segment: Segment) => void;
  isSelectedForCompare?: boolean;
}

const SEGMENT_ICONS: Record<string, string> = {
  large_size_stable: '🏢',
  high_growth_recent: '🔥',
  speculator_hotspots: '⚡',
  declining_areas: '📉',
  mid_tier_value: '💎',
  premium_new_units: '🌟',
};

const RISK_COLORS = {
  low: 'text-green-600 bg-green-50 dark:bg-green-900/20',
  medium: 'text-yellow-600 bg-yellow-50 dark:bg-yellow-900/20',
  high: 'text-orange-600 bg-orange-50 dark:bg-orange-900/20',
  very_high: 'text-red-600 bg-red-50 dark:bg-red-900/20',
};

const HOTSPOT_BADGES: Record<string, { icon: string; label: string; className: string }> = {
  HH: { icon: '🔥', label: 'Hotspot', className: 'text-red-700 bg-red-50 dark:bg-red-900/30 border-red-200 dark:border-red-800' },
  LL: { icon: '❄️', label: 'Coldspot', className: 'text-blue-700 bg-blue-50 dark:bg-blue-900/30 border-blue-200 dark:border-blue-800' },
  HL: { icon: '⚡', label: 'Pioneer', className: 'text-orange-700 bg-orange-50 dark:bg-orange-900/30 border-orange-200 dark:border-orange-800' },
  LH: { icon: '🔄', label: 'Transition', className: 'text-purple-700 bg-purple-50 dark:bg-purple-900/30 border-purple-200 dark:border-purple-800' },
};

export default function SegmentCard({
  segment,
  matchScore,
  onViewDetails,
  onAddToCompare,
  isSelectedForCompare = false,
}: SegmentCardProps) {
  const icon = SEGMENT_ICONS[segment.id] || '📊';
  const riskColor = RISK_COLORS[segment.characteristics.riskLevel];

  return (
    <div
      className={clsx(
        'bg-card border rounded-lg p-4 transition-all hover:shadow-md',
        isSelectedForCompare ? 'border-primary' : 'border-border'
      )}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-2xl">{icon}</span>
          <div>
            <h3 className="font-semibold text-foreground">{segment.name}</h3>
            <p className="text-xs text-muted-foreground line-clamp-2">{segment.description}</p>
          </div>
        </div>
        {matchScore !== undefined && (
          <div className="text-right">
            <div className="text-xs text-muted-foreground">Match</div>
            <div className="text-lg font-bold text-primary">{matchScore}%</div>
          </div>
        )}
      </div>

      {/* Risk and Hotspot Badges */}
      <div className="mb-3 flex items-center gap-2 flex-wrap">
        <span className={clsx('inline-block px-2 py-1 text-xs font-medium rounded-full', riskColor)}>
          {segment.characteristics.riskLevel.replace('_', ' ').toUpperCase()} RISK
        </span>
        {segment.spatialClassification && HOTSPOT_BADGES[segment.spatialClassification] && (
          <span className={clsx('inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-full border', HOTSPOT_BADGES[segment.spatialClassification].className)}>
            {HOTSPOT_BADGES[segment.spatialClassification].icon} {HOTSPOT_BADGES[segment.spatialClassification].label}
          </span>
        )}
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        <MetricItem label="Price PSF" value={`$${segment.metrics.avgPricePsf.toFixed(0)}`} />
        <MetricItem label="Yield" value={`${segment.metrics.avgYield.toFixed(1)}%`} />
        <MetricItem label="YoY Growth" value={`+${segment.metrics.yoyGrowth.toFixed(1)}%`} />
        <MetricItem label="Share" value={`${(segment.metrics.marketShare * 100).toFixed(0)}%`} />
      </div>

      {/* Persistence */}
      {segment.persistenceProbability > 0 && (
        <div className="mb-4 p-2 bg-muted/50 rounded text-xs">
          <span className="text-muted-foreground">Persistence: </span>
          <span className="font-medium">{(segment.persistenceProbability * 100).toFixed(0)}%</span>
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-2">
        <button
          onClick={() => onViewDetails(segment)}
          className="flex-1 px-3 py-2 text-sm font-medium text-center rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
        >
          Details
        </button>
        <button
          onClick={() => onAddToCompare(segment)}
          className={clsx(
            'px-3 py-2 text-sm font-medium rounded-md border transition-colors',
            isSelectedForCompare
              ? 'border-primary bg-primary/10 text-primary'
              : 'border-border hover:border-primary hover:text-primary'
          )}
        >
          {isSelectedForCompare ? '✓' : '+'}
        </button>
      </div>
    </div>
  );
}

function MetricItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="text-sm font-semibold text-foreground">{value}</div>
    </div>
  );
}
