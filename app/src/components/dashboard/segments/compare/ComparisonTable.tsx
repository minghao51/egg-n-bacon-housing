// app/src/components/dashboard/segments/compare/ComparisonTable.tsx
/**
 * Stored-field comparison for the segment shortlist.
 *
 * No "best" highlighting: the archive fields are not a ranking, the cohorts may
 * overlap, and per-segment counts are not additive.
 */
import type { Segment } from "@/types/segments";

interface ComparisonTableProps {
  segments: Segment[];
}

function formatStoredPsf(value: number): string {
  return Number.isFinite(value) ? `S$${value.toFixed(0)}` : "N/A";
}

export function ComparisonTable({ segments }: ComparisonTableProps) {
  if (segments.length === 0) {
    return (
      <div className="py-8 text-center text-muted-foreground">
        Select 2-4 segments to compare
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-2xl border border-border">
      <table className="w-full border-collapse text-sm">
        <caption className="sr-only">
          Stored research fields for the shortlisted segments. Cohort counts are
          per segment and are not additive.
        </caption>
        <thead>
          <tr className="border-b border-border bg-muted/40">
            <th
              scope="col"
              className="p-3 text-left font-semibold text-foreground"
            >
              Stored field
            </th>
            {segments.map((segment) => (
              <th
                key={segment.id}
                scope="col"
                className="min-w-[150px] p-3 text-center font-semibold text-foreground"
              >
                {segment.name}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          <tr className="border-b border-border">
            <th
              scope="row"
              className="p-3 text-left font-normal text-muted-foreground"
            >
              Average PSF (stored)
            </th>
            {segments.map((segment) => (
              <td
                key={segment.id}
                className="p-3 text-center font-medium text-foreground"
              >
                {formatStoredPsf(segment.metrics.avgPricePsf)}
              </td>
            ))}
          </tr>
          <tr className="border-b border-border">
            <th
              scope="row"
              className="p-3 text-left font-normal text-muted-foreground"
            >
              Linked planning areas
            </th>
            {segments.map((segment) => (
              <td
                key={segment.id}
                className="p-3 text-center font-medium text-foreground"
              >
                {segment.planningAreas.length}
              </td>
            ))}
          </tr>
          <tr className="border-b border-border">
            <th
              scope="row"
              className="p-3 text-left font-normal text-muted-foreground"
            >
              Property types
            </th>
            {segments.map((segment) => (
              <td
                key={segment.id}
                className="p-3 text-center font-medium text-foreground"
              >
                {segment.propertyTypes.join(" / ")}
              </td>
            ))}
          </tr>
          <tr className="border-b border-border">
            <th
              scope="row"
              className="p-3 text-left font-normal text-muted-foreground"
            >
              Reported cohort count
            </th>
            {segments.map((segment) => (
              <td
                key={segment.id}
                className="p-3 text-center font-medium text-foreground"
              >
                {Number.isFinite(segment.metrics.transactionCount)
                  ? segment.metrics.transactionCount.toLocaleString()
                  : "N/A"}
              </td>
            ))}
          </tr>
          <tr className="border-b border-border">
            <th
              scope="row"
              className="p-3 text-left font-normal text-muted-foreground"
            >
              Observation period
            </th>
            {segments.map((segment) => (
              <td
                key={segment.id}
                className="p-3 text-center font-medium text-muted-foreground"
              >
                Not supplied
              </td>
            ))}
          </tr>
          <tr className="border-b border-border">
            <th
              scope="row"
              className="p-3 text-left font-normal text-muted-foreground"
            >
              Stored risk label
            </th>
            {segments.map((segment) => (
              <td
                key={segment.id}
                className="p-3 text-center font-medium text-foreground"
              >
                {segment.characteristics.riskLevel.replace("_", " ")}
              </td>
            ))}
          </tr>
          <tr>
            <th
              scope="row"
              className="p-3 text-left font-normal text-muted-foreground"
            >
              Stored volatility label
            </th>
            {segments.map((segment) => (
              <td
                key={segment.id}
                className="p-3 text-center font-medium text-foreground"
              >
                {segment.characteristics.volatility}
              </td>
            ))}
          </tr>
        </tbody>
      </table>
      <p className="border-t border-border bg-muted/20 px-3 py-2 text-xs text-muted-foreground">
        Cohort counts are per segment and may overlap between segments; they are
        not additive and do not measure market coverage.
      </p>
    </div>
  );
}
