// app/src/components/dashboard/leaderboard/MetricHelpModal.tsx
import React, { useEffect } from 'react';
import type { LeaderboardMetric, MetricMeta } from '@/types/leaderboard';

interface MetricHelpModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const METRICS: MetricMeta[] = [
  {
    key: 'median_price',
    label: 'Median Price',
    description: 'The middle value of all property transaction prices in the area.',
    formula: 'median(all transaction prices)',
    unit: 'SGD',
    colorScale: 'sequential',
  },
  {
    key: 'yoy_growth_pct',
    label: 'Year-over-Year Growth',
    description: 'Percentage change in median price compared to the previous year.',
    formula: '((price_this_year - price_last_year) ÷ price_last_year) × 100',
    unit: '%',
    colorScale: 'diverging',
  },
  {
    key: 'volume',
    label: 'Transaction Volume',
    description: 'Total number of property transactions in the period.',
    formula: 'count(all transactions)',
    unit: 'count',
    colorScale: 'sequential',
  },
];

export default function MetricHelpModal({ isOpen, onClose }: MetricHelpModalProps) {
  // Handle ESC key press
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  // Prevent body scroll when modal is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }

    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="bg-background rounded-lg shadow-xl max-w-2xl w-full max-h-[80vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-2xl font-bold">Metric Definitions</h2>
          <button
            onClick={onClose}
            className="text-muted-foreground hover:text-foreground transition-colors p-2 rounded-md hover:bg-muted"
            aria-label="Close"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          <div className="space-y-6">
            <section>
              <h3 className="text-lg font-semibold mb-3 text-blue-600">Price Metrics</h3>
              <div className="space-y-4">
                {METRICS.filter(m => m.key === 'median_price').map(metric => (
                  <div key={metric.key} className="border-l-2 border-blue-500 pl-4">
                    <div className="flex items-center gap-2 mb-1">
                      <h4 className="font-semibold">{metric.label}</h4>
                      <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded">
                        {metric.unit}
                      </span>
                    </div>
                    <p className="text-sm text-muted-foreground mb-2">{metric.description}</p>
                    <code className="text-xs bg-muted px-2 py-1 rounded block font-mono">
                      {metric.formula}
                    </code>
                  </div>
                ))}
              </div>
            </section>

            <section>
              <h3 className="text-lg font-semibold mb-3 text-orange-600">Growth Metrics</h3>
              <div className="space-y-4">
                {METRICS.filter(m => m.key === 'yoy_growth_pct').map(metric => (
                  <div key={metric.key} className="border-l-2 border-orange-500 pl-4">
                    <div className="flex items-center gap-2 mb-1">
                      <h4 className="font-semibold">{metric.label}</h4>
                      <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded">
                        {metric.unit}
                      </span>
                    </div>
                    <p className="text-sm text-muted-foreground mb-2">{metric.description}</p>
                    <code className="text-xs bg-muted px-2 py-1 rounded block font-mono">
                      {metric.formula}
                    </code>
                  </div>
                ))}
              </div>
            </section>

            <section>
              <h3 className="text-lg font-semibold mb-3 text-purple-600">Market Activity</h3>
              <div className="space-y-4">
                {METRICS.filter(m => m.key === 'volume').map(metric => (
                  <div key={metric.key} className="border-l-2 border-purple-500 pl-4">
                    <div className="flex items-center gap-2 mb-1">
                      <h4 className="font-semibold">{metric.label}</h4>
                      <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded">
                        {metric.unit}
                      </span>
                    </div>
                    <p className="text-sm text-muted-foreground mb-2">{metric.description}</p>
                    <code className="text-xs bg-muted px-2 py-1 rounded block font-mono">
                      {metric.formula}
                    </code>
                  </div>
                ))}
              </div>
            </section>

          </div>

          {/* Data Source Note */}
          <div className="mt-6 pt-4 border-t text-sm text-muted-foreground">
            <p className="mb-2">
              <strong>Data Source:</strong> L3 unified dataset with processed analytics.
            </p>
            <p>
              <strong>Time Period:</strong> Default metrics are based on recent transactions (2022+).
              Time-based filters allow you to compare recent, all-time, and 2025 views.
            </p>
            <p className="mt-2 text-xs">
              <strong>Note:</strong> Some metrics may be unavailable for certain planning areas or
              time periods due to insufficient transaction data. These are displayed as "—" in the table.
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t bg-muted/20">
          <button
            onClick={onClose}
            className="w-full py-2 px-4 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors font-medium"
          >
            Got it, thanks!
          </button>
        </div>
      </div>
    </div>
  );
}

// Export metrics for use in other components
export { METRICS };
