import type {
  SegmentAreaRow,
  SegmentInvestigationMetric,
} from "@/types/segments";
import {
  formatSegmentMetric,
  segmentMetricEvidence,
} from "@/components/dashboard/segments/lib/segment-evidence";

interface SegmentAreaTableProps {
  rows: SegmentAreaRow[];
  selectedMetric: SegmentInvestigationMetric;
  highlightedArea: string | null;
  onRowHover: (area: string | null) => void;
  onRowClick: (area: string) => void;
  /** Areas the segment declares before the current constraints are applied. */
  declaredAreaCount: number;
}

export default function SegmentAreaTable({
  rows,
  selectedMetric,
  highlightedArea,
  onRowHover,
  onRowClick,
  declaredAreaCount,
}: SegmentAreaTableProps) {
  const selected = segmentMetricEvidence(selectedMetric);
  const showSelectedColumn = selectedMetric !== "avgPricePsf";

  if (rows.length === 0) {
    return (
      <div className="rounded-2xl bg-muted/20 py-12 text-center">
        <h3 className="mb-2 text-lg font-semibold text-foreground">
          No declared areas fit these constraints
        </h3>
        <p className="mb-2 text-muted-foreground">
          {declaredAreaCount} linked area
          {declaredAreaCount === 1 ? "" : "s"} are declared for this segment;
          none match the current PSF range, region and spatial-class filters.
        </p>
        <p className="text-sm text-muted-foreground">
          Widen the price, region, or hotspot filters to restore the shortlist.
          Nothing has been added or substituted.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-lg font-semibold text-foreground">Linked areas</h3>
        <p className="text-sm text-muted-foreground">
          Showing {rows.length} of {declaredAreaCount} &middot; sorted by{" "}
          {selected.label}
        </p>
      </div>

      <div className="overflow-x-auto rounded-2xl border border-border">
        <table className="min-w-full text-left text-sm">
          <caption className="sr-only">
            Declared planning areas for this research segment with stored
            archive averages. These are not observed 2025 transaction medians.
          </caption>
          <thead className="bg-muted/60 text-xs uppercase tracking-wide text-muted-foreground">
            <tr>
              <th scope="col" className="px-3 py-3 font-semibold">
                Planning area
              </th>
              <th scope="col" className="px-3 py-3 font-semibold">
                Market segment
              </th>
              <th scope="col" className="px-3 py-3 font-semibold">
                Stored avg PSF
              </th>
              {showSelectedColumn && (
                <th scope="col" className="px-3 py-3 font-semibold">
                  {selected.label}
                  {selected.gated ? " †" : ""}
                </th>
              )}
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {rows.map((row) => {
              const isHighlighted = highlightedArea === row.areaKey;

              return (
                <tr
                  key={row.areaKey}
                  className={`cursor-pointer transition-colors ${
                    isHighlighted
                      ? "bg-primary/10 ring-1 ring-inset ring-primary/20"
                      : "hover:bg-muted/40"
                  }`}
                  onMouseEnter={() => onRowHover(row.areaKey)}
                  onMouseLeave={() => onRowHover(null)}
                  onClick={() => onRowClick(row.areaKey)}
                >
                  <td className="px-3 py-3 font-medium text-foreground">
                    {row.planningArea}
                  </td>
                  <td className="px-3 py-3 text-muted-foreground">
                    {row.region}
                  </td>
                  <td className="px-3 py-3 text-foreground">
                    {formatSegmentMetric(row.avgPricePsf, "avgPricePsf")}
                  </td>
                  {showSelectedColumn && (
                    <td className="px-3 py-3 text-foreground">
                      {formatSegmentMetric(row[selectedMetric], selectedMetric)}
                    </td>
                  )}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <p className="text-xs text-muted-foreground">
        † Stored archive field: definition, units, sample and observation period
        are not supplied. Inspectable, not a current recommendation.
      </p>
    </div>
  );
}
