import { useEffect } from 'react';

interface SegmentMetricGuideModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const SEGMENT_METRICS = [
  {
    key: 'avgPricePsf',
    label: 'Average Price PSF',
    description: 'Average price per square foot for planning areas in the selected segment.',
    formula: 'mean(area avg_price_psf)',
    group: 'Pricing',
    unit: 'SGD/sqft',
  },
  {
    key: 'avgYield',
    label: 'Average Yield',
    description: 'Average rental yield across matching planning areas.',
    formula: 'mean(area avg_yield)',
    group: 'Yield & Growth',
    unit: '%',
  },
  {
    key: 'yoyGrowth',
    label: 'YoY Growth',
    description: 'Segment-level year-over-year growth used for selection and comparison.',
    formula: 'segment yoy_growth',
    group: 'Yield & Growth',
    unit: '%',
  },
  {
    key: 'transactionCount',
    label: 'Transaction Count',
    description: 'Segment-wide transaction volume used as a liquidity signal.',
    formula: 'count(segment transactions)',
    group: 'Liquidity',
    unit: 'count',
  },
  {
    key: 'marketShare',
    label: 'Market Share',
    description: 'Segment share of tracked market activity.',
    formula: 'segment transactions ÷ all transactions',
    group: 'Liquidity',
    unit: '%',
  },
  {
    key: 'persistenceProbability',
    label: 'Persistence Probability',
    description: 'Likelihood the area keeps its current hotspot pattern.',
    formula: 'spatial persistence probability',
    group: 'Area Evidence',
    unit: '%',
  },
  {
    key: 'forecast6m',
    label: '6M Forecast',
    description: 'Projected six-month price change for the planning area.',
    formula: 'forecasted six month appreciation',
    group: 'Area Evidence',
    unit: '%',
  },
  {
    key: 'mrtPremium',
    label: 'MRT Premium',
    description: 'Estimated price premium linked to MRT proximity.',
    formula: 'modeled MRT price premium',
    group: 'Area Evidence',
    unit: 'SGD',
  },
];

const GROUP_COLORS: Record<string, string> = {
  Pricing: 'border-sky-500',
  'Yield & Growth': 'border-emerald-500',
  Liquidity: 'border-amber-500',
  'Area Evidence': 'border-violet-500',
};

export default function SegmentMetricGuideModal({
  isOpen,
  onClose,
}: SegmentMetricGuideModalProps) {
  useEffect(() => {
    if (!isOpen) {
      return undefined;
    }

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose();
      }
    };

    document.body.style.overflow = 'hidden';
    document.addEventListener('keydown', handleEscape);

    return () => {
      document.body.style.overflow = '';
      document.removeEventListener('keydown', handleEscape);
    };
  }, [isOpen, onClose]);

  if (!isOpen) {
    return null;
  }

  const groups = ['Pricing', 'Yield & Growth', 'Liquidity', 'Area Evidence'] as const;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="flex max-h-[80vh] w-full max-w-3xl flex-col overflow-hidden rounded-2xl bg-background shadow-xl"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b p-6">
          <div>
            <h2 className="text-2xl font-bold">Segment Metrics Guide</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Definitions for the metrics used to rank segments and shortlist planning areas.
            </p>
          </div>
          <button
            onClick={onClose}
            className="rounded-md p-2 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        <div className="flex-1 space-y-6 overflow-y-auto p-6">
          {groups.map((group) => (
            <section key={group}>
              <h3 className="mb-3 text-lg font-semibold">{group}</h3>
              <div className="space-y-4">
                {SEGMENT_METRICS.filter((metric) => metric.group === group).map((metric) => (
                  <div
                    key={metric.key}
                    className={`border-l-4 pl-4 ${GROUP_COLORS[group] ?? 'border-border'}`}
                  >
                    <div className="mb-1 flex items-center gap-2">
                      <h4 className="font-semibold">{metric.label}</h4>
                      <span className="rounded bg-muted px-2 py-0.5 text-xs text-muted-foreground">
                        {metric.unit}
                      </span>
                    </div>
                    <p className="mb-2 text-sm text-muted-foreground">{metric.description}</p>
                    <code className="block rounded bg-muted px-2 py-1 text-xs">{metric.formula}</code>
                  </div>
                ))}
              </div>
            </section>
          ))}
        </div>

        <div className="border-t bg-muted/20 p-4">
          <button
            onClick={onClose}
            className="w-full rounded-md bg-primary px-4 py-2 font-medium text-primary-foreground transition-colors hover:bg-primary/90"
          >
            Close Guide
          </button>
        </div>
      </div>
    </div>
  );
}
