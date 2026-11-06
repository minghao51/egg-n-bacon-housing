/**
 * Segment evidence and matching guide.
 *
 * Replaces the pre-S7 metric guide, which restated invented formulas
 * ("forecasted six month appreciation", "mean(area avg_yield)") as if the
 * archive published them. This version states the real weighted-fit rules and
 * the evidence status of every field the workspace displays.
 */
import { useModalDialog } from "@/hooks/useModalDialog";
import {
  SEGMENT_ARCHIVE_NOTE,
  SEGMENT_GATED_NOTE,
  SEGMENT_INVESTIGATION_METRICS,
  SEGMENT_NOT_COMPARABLE_NOTE,
  segmentMetricEvidence,
} from "@/components/dashboard/segments/lib/segment-evidence";
import {
  SEGMENT_MATCH_RULE_NOTES,
  SEGMENT_MATCH_WEIGHTS,
} from "@/hooks/useSegmentMatching";

interface SegmentMetricGuideModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function SegmentMetricGuideModal({
  isOpen,
  onClose,
}: SegmentMetricGuideModalProps) {
  const panelRef = useModalDialog(isOpen, onClose);

  if (!isOpen) {
    return null;
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="segment-guide-title"
        tabIndex={-1}
        className="flex max-h-[80vh] w-full max-w-3xl flex-col overflow-hidden rounded-2xl bg-background shadow-xl"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b p-6">
          <div>
            <h2 id="segment-guide-title" className="text-2xl font-bold">
              Segment evidence guide
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">
              What the weighted fit means, and what the archive does and does
              not supply.
            </p>
          </div>
          <button
            onClick={onClose}
            className="rounded-md p-2 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            aria-label="Close segment evidence guide"
          >
            ✕
          </button>
        </div>

        <div className="flex-1 space-y-6 overflow-y-auto p-6">
          <section>
            <h3 className="mb-2 text-lg font-semibold">
              How the fit is scored
            </h3>
            <ul className="space-y-1 text-sm text-muted-foreground">
              <li>
                Investment goal &middot; {SEGMENT_MATCH_WEIGHTS.investmentGoal}{" "}
                points (only when set)
              </li>
              <li>PSF range &middot; {SEGMENT_MATCH_WEIGHTS.budget} points</li>
              <li>
                Property type &middot; {SEGMENT_MATCH_WEIGHTS.propertyType}{" "}
                points
              </li>
              <li>Region &middot; {SEGMENT_MATCH_WEIGHTS.location} points</li>
              <li>
                Time horizon &middot; {SEGMENT_MATCH_WEIGHTS.timeHorizon} points
                (only when set)
              </li>
            </ul>
            <p className="mt-3 text-sm text-muted-foreground">
              {SEGMENT_MATCH_RULE_NOTES.hardFilter}
            </p>
            <p className="mt-1 text-sm text-muted-foreground">
              {SEGMENT_MATCH_RULE_NOTES.optional}
            </p>
            <p className="mt-1 text-sm text-muted-foreground">
              {SEGMENT_MATCH_RULE_NOTES.rounding}
            </p>
          </section>

          <section>
            <h3 className="mb-2 text-lg font-semibold">
              Field status in this archive
            </h3>
            <ul className="space-y-3">
              {SEGMENT_INVESTIGATION_METRICS.map((metric) => {
                const evidence = segmentMetricEvidence(metric);
                return (
                  <li
                    key={metric}
                    className="rounded-xl border border-border p-3"
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-semibold">{evidence.label}</span>
                      {evidence.unit && (
                        <span className="rounded bg-muted px-2 py-0.5 text-xs text-muted-foreground">
                          {evidence.unit}
                        </span>
                      )}
                      <span className="rounded bg-muted px-2 py-0.5 text-xs text-muted-foreground">
                        {evidence.status === "stored-average"
                          ? "stored average"
                          : "definition unverified"}
                      </span>
                    </div>
                    <p className="mt-2 text-sm text-muted-foreground">
                      {evidence.caveat}
                    </p>
                  </li>
                );
              })}
            </ul>
          </section>

          <section className="rounded-xl border border-border bg-muted/30 p-4 text-sm text-muted-foreground">
            <h3 className="mb-2 text-base font-semibold text-foreground">
              Source and limits
            </h3>
            <p>{SEGMENT_ARCHIVE_NOTE}</p>
            <p className="mt-2">{SEGMENT_GATED_NOTE}</p>
            <p className="mt-2">{SEGMENT_NOT_COMPARABLE_NOTE}</p>
            <p className="mt-2">
              No formula is reproduced here because the archive does not publish
              one.
            </p>
          </section>
        </div>

        <div className="border-t bg-muted/20 p-4">
          <button
            onClick={onClose}
            className="w-full rounded-md bg-primary px-4 py-2 font-medium text-primary-foreground transition-colors hover:bg-primary/90"
          >
            Close guide
          </button>
        </div>
      </div>
    </div>
  );
}
