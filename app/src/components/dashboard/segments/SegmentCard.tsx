// app/src/components/dashboard/segments/SegmentCard.tsx
/**
 * Segment card for the discover board.
 *
 * Only the stored average PSF, the declared cohorts and the weighted fit are
 * shown. Yield, growth, forecast and persistence stay out of the card because
 * their definitions, periods and samples are not supplied by the archive (see
 * `lib/segment-evidence.ts`).
 */
import type { Segment } from "@/types/segments";
import { clsx } from "clsx";

interface SegmentCardProps {
  segment: Segment;
  matchScore: number;
  onInvestigate: (segment: Segment) => void;
  onAddToCompare: (segment: Segment) => void;
  isActive?: boolean;
  isSelectedForCompare?: boolean;
  /** True when the comparison set is full and this card is not in it. */
  compareDisabled?: boolean;
}

export default function SegmentCard({
  segment,
  matchScore,
  onInvestigate,
  onAddToCompare,
  isActive = false,
  isSelectedForCompare = false,
  compareDisabled = false,
}: SegmentCardProps) {
  const linkedAreas = segment.planningAreas.length;

  return (
    <div
      className={clsx(
        "rounded-2xl border bg-card p-4 transition-all hover:shadow-md",
        isActive && "border-primary ring-2 ring-primary/20 shadow-md",
        !isActive && isSelectedForCompare && "border-primary/60",
        !isActive && !isSelectedForCompare && "border-border",
      )}
    >
      <div className="mb-3 flex items-start justify-between gap-3">
        <h3 className="font-semibold text-foreground">{segment.name}</h3>
        <div className="text-right">
          <div className="text-xs uppercase tracking-wide text-muted-foreground">
            Weighted fit
          </div>
          <div className="text-xl font-bold text-primary">{matchScore}%</div>
          <div className="text-[11px] text-muted-foreground">
            not a return probability
          </div>
        </div>
      </div>

      <dl className="mb-3 space-y-1 text-sm">
        <div className="flex items-baseline justify-between gap-3">
          <dt className="text-muted-foreground">Stored avg PSF</dt>
          <dd className="font-semibold text-foreground">
            {Number.isFinite(segment.metrics.avgPricePsf)
              ? `S$${segment.metrics.avgPricePsf.toFixed(0)}`
              : "N/A"}
          </dd>
        </div>
        <div className="flex items-baseline justify-between gap-3">
          <dt className="text-muted-foreground">Linked areas</dt>
          <dd className="font-medium text-foreground">
            {linkedAreas} &middot; {segment.propertyTypes.join(", ")}
          </dd>
        </div>
      </dl>

      <p className="mb-4 rounded-lg bg-muted/40 px-3 py-2 text-xs text-muted-foreground">
        Period / yield provenance require review. Stored average, not a 2025
        transaction median.
      </p>

      <div className="flex gap-2">
        <button
          onClick={() => onInvestigate(segment)}
          className="flex-1 rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
          aria-label={`Investigate ${segment.name}`}
        >
          {isActive ? "Investigating" : "Investigate"}
        </button>
        <button
          onClick={() => onAddToCompare(segment)}
          disabled={compareDisabled && !isSelectedForCompare}
          aria-pressed={isSelectedForCompare}
          aria-label={
            isSelectedForCompare
              ? `Remove ${segment.name} from comparison`
              : `Add ${segment.name} to comparison`
          }
          className={clsx(
            "rounded-md border px-3 py-2 text-sm font-medium transition-colors",
            isSelectedForCompare
              ? "border-primary bg-primary/10 text-primary"
              : "border-border hover:border-primary hover:text-primary",
            compareDisabled &&
              !isSelectedForCompare &&
              "cursor-not-allowed opacity-50 hover:border-border hover:text-foreground",
          )}
        >
          {isSelectedForCompare ? "✓ In comparison" : "Add to comparison"}
        </button>
      </div>
    </div>
  );
}
