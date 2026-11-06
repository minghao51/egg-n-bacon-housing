/**
 * Segment comparison tab.
 *
 * Compares the same stored archive fields for two-to-four shortlisted
 * segments. Cohorts may overlap, so counts are never summed and nothing here is
 * market coverage or a best-investment score.
 */
import { useState } from "react";
import type { Segment } from "@/types/segments";
import { ComparisonTable } from "./ComparisonTable";
import {
  SEGMENT_COMPARISON_MAX,
  SEGMENT_COMPARISON_MIN,
} from "@/components/dashboard/segments/lib/segment-url-state";

interface CompareTabProps {
  segments: Segment[];
  allSegments: Segment[];
  onRemoveSegment: (segmentId: string) => void;
  onAddSegment: (segmentId: string) => void;
}

export function CompareTab({
  segments,
  allSegments,
  onRemoveSegment,
  onAddSegment,
}: CompareTabProps) {
  const [candidateId, setCandidateId] = useState("");
  const available = allSegments.filter(
    (segment) => !segments.some((selected) => selected.id === segment.id),
  );
  const slotsAvailable = SEGMENT_COMPARISON_MAX - segments.length;

  if (segments.length < SEGMENT_COMPARISON_MIN) {
    return (
      <div className="rounded-2xl border border-border bg-card p-8 text-center">
        <h2 className="mb-2 text-xl font-semibold text-foreground">
          Comparison needs {SEGMENT_COMPARISON_MIN}-{SEGMENT_COMPARISON_MAX}{" "}
          segments
        </h2>
        <p className="text-muted-foreground">
          {segments.length === 1
            ? "One segment is shortlisted. Removing it would leave nothing to compare, so the minimum is two - the other selection is kept."
            : "No segments are shortlisted yet."}{" "}
          Add another from the discover board (or with the control below) to
          cross-check their stored fields.
        </p>
        {segments.length === 1 && (
          <div className="mt-6 flex flex-col items-center gap-3 sm:flex-row sm:justify-center">
            <h3 className="text-sm font-semibold text-foreground">
              {segments[0].name}
            </h3>
            <button
              onClick={() => onRemoveSegment(segments[0].id)}
              className="rounded-full border border-border px-3 py-1.5 text-sm font-medium text-muted-foreground hover:text-foreground"
            >
              Remove {segments[0].name}
            </button>
          </div>
        )}
        {available.length > 0 && (
          <div className="mt-6 flex flex-col items-center gap-2 sm:flex-row sm:justify-center">
            <label
              htmlFor="compare-add-segment-empty"
              className="text-sm text-muted-foreground"
            >
              Add a segment
            </label>
            <select
              id="compare-add-segment-empty"
              value={candidateId}
              onChange={(event) => setCandidateId(event.target.value)}
              className="rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground"
            >
              <option value="">Select a segment</option>
              {available.map((segment) => (
                <option key={segment.id} value={segment.id}>
                  {segment.name}
                </option>
              ))}
            </select>
            <button
              onClick={() => {
                onAddSegment(candidateId);
                setCandidateId("");
              }}
              disabled={candidateId === ""}
              className="rounded-full bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:cursor-not-allowed disabled:opacity-50"
            >
              Add
            </button>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-foreground">
          Two segments, one research vocabulary
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Different segment cohorts may overlap. Counts are reported per
          segment; they are not additive and are not market coverage.
        </p>
      </div>

      <ComparisonTable segments={segments} />

      <div className="rounded-2xl border border-border bg-card p-4">
        <h3 className="text-sm font-semibold text-foreground">Shortlist</h3>
        <ul className="mt-3 space-y-2">
          {segments.map((segment) => (
            <li
              key={segment.id}
              className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-border px-3 py-2"
            >
              <span className="text-sm font-medium text-foreground">
                {segment.name}
              </span>
              <button
                onClick={() => onRemoveSegment(segment.id)}
                className="rounded-full border border-border px-3 py-1 text-xs font-medium text-muted-foreground hover:text-foreground"
              >
                Remove {segment.name}
              </button>
            </li>
          ))}
        </ul>

        {slotsAvailable > 0 ? (
          <div className="mt-4 flex flex-col gap-2 sm:flex-row sm:items-center">
            <label
              htmlFor="compare-add-segment"
              className="text-sm text-muted-foreground"
            >
              Add another segment &middot; {slotsAvailable} slot
              {slotsAvailable === 1 ? "" : "s"} available
            </label>
            <select
              id="compare-add-segment"
              value={candidateId}
              onChange={(event) => setCandidateId(event.target.value)}
              className="rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground"
            >
              <option value="">Select a segment</option>
              {available.map((segment) => (
                <option key={segment.id} value={segment.id}>
                  {segment.name}
                </option>
              ))}
            </select>
            <button
              onClick={() => {
                onAddSegment(candidateId);
                setCandidateId("");
              }}
              disabled={candidateId === ""}
              className="rounded-full bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:cursor-not-allowed disabled:opacity-50"
            >
              Add
            </button>
          </div>
        ) : (
          <p className="mt-4 text-sm text-muted-foreground">
            Comparison set is full ({SEGMENT_COMPARISON_MAX} of{" "}
            {SEGMENT_COMPARISON_MAX}). Remove a segment before adding another.
          </p>
        )}

        <p className="mt-3 text-xs text-muted-foreground">
          Minimum {SEGMENT_COMPARISON_MIN} / maximum {SEGMENT_COMPARISON_MAX}.
          Removing a segment keeps the remaining selection and explains when the
          two-segment minimum is not met.
        </p>
      </div>
    </div>
  );
}
