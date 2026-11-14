// app/src/components/dashboard/leaderboard/MetricHelpModal.tsx
import { useModalDialog } from "@/hooks/useModalDialog";
import type { MetricMeta } from "@/types/leaderboard";

interface MetricHelpModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const METRICS: MetricMeta[] = [
  {
    key: "median_price",
    label: "Median Price",
    description:
      "Middle transaction price for the selected property type and period in that planning area.",
    formula: "median(transaction prices)",
    unit: "SGD",
    colorScale: "sequential",
  },
  {
    key: "median_psf",
    label: "Median Price per Square Foot",
    description:
      "Middle price per square foot across eligible transactions for the selected property type and period.",
    formula: "median(price ÷ floor area in sqft)",
    unit: "S$/sqft",
    colorScale: "sequential",
  },
  {
    key: "volume",
    label: "Sales",
    description:
      "Number of included transactions for the selected property type and period.",
    formula: "count(transactions)",
    unit: "count",
    colorScale: "sequential",
  },
];

export default function MetricHelpModal({
  isOpen,
  onClose,
}: MetricHelpModalProps) {
  const panelRef = useModalDialog(isOpen, onClose);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="metric-help-title"
        tabIndex={-1}
        className="bg-background rounded-lg shadow-xl max-w-2xl w-full max-h-[80vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <h2 id="metric-help-title" className="text-2xl font-bold">
            Metric Definitions
          </h2>
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
              <h3 className="text-lg font-semibold mb-3 text-blue-600">
                Price Metrics
              </h3>
              <div className="space-y-4">
                {METRICS.filter((m) => m.key === "median_price").map(
                  (metric) => (
                    <div
                      key={metric.key}
                      className="border-l-2 border-blue-500 pl-4"
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <h4 className="font-semibold">{metric.label}</h4>
                        <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded">
                          {metric.unit}
                        </span>
                      </div>
                      <p className="text-sm text-muted-foreground mb-2">
                        {metric.description}
                      </p>
                      <code className="text-xs bg-muted px-2 py-1 rounded block font-mono">
                        {metric.formula}
                      </code>
                    </div>
                  ),
                )}
              </div>
            </section>

            <section>
              <h3 className="text-lg font-semibold mb-3 text-orange-600">
                Not published for this selection
              </h3>
              <p className="mb-3 text-sm text-muted-foreground">
                Growth, momentum, yield and affordability are published only
                across all property types or all periods at once. Ranking areas
                on them would compare different populations, so this page
                reports them as unavailable instead of substituting a number.
              </p>
              <p className="text-sm text-muted-foreground">
                An older link that requests one of them opens this notice; pick
                a supported metric to rank again.
              </p>
            </section>

            <section>
              <h3 className="text-lg font-semibold mb-3 text-purple-600">
                Market Activity
              </h3>
              <div className="space-y-4">
                {METRICS.filter((m) => m.key === "volume").map((metric) => (
                  <div
                    key={metric.key}
                    className="border-l-2 border-purple-500 pl-4"
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <h4 className="font-semibold">{metric.label}</h4>
                      <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded">
                        {metric.unit}
                      </span>
                    </div>
                    <p className="text-sm text-muted-foreground mb-2">
                      {metric.description}
                    </p>
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
              <strong>Data Source:</strong> Published dashboard release
              (observed transactions, coverage through 2026-10).
            </p>
            <p>
              <strong>Scope:</strong> Every value is the planning area ×
              property type × period section of the released data. Property-only
              and period-only totals are never used as substitutes.
            </p>
            <p className="mt-2">
              <strong>Ranking:</strong> Areas with fewer than 150 sales in the
              selected window stay visible but are not ranked.
            </p>
            <p className="mt-2 text-xs">
              <strong>Note:</strong> A missing value means the release does not
              publish that area for the selected scope. It is not zero.
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
