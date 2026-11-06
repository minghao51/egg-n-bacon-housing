// app/src/components/dashboard/segments/discover/InsightCard.tsx
/**
 * Stored archive note.
 *
 * The archive's insight strings restate model claims (for example MRT
 * sensitivity) whose definitions are not supplied. They are labelled as archive
 * notes here instead of being presented as verified findings.
 */
import type { Insight } from "@/types/segments";

interface InsightCardProps {
  insight: Insight;
  /** Deployment base path, resolved once by the Astro shell. */
  baseUrl: string;
}

export function InsightCard({ insight, baseUrl }: InsightCardProps) {
  return (
    <div className="rounded-lg border border-border bg-muted/30 p-4">
      <div className="flex items-start gap-3">
        <span aria-hidden="true" className="text-2xl flex-shrink-0">
          🗒️
        </span>
        <div className="flex-1 min-w-0">
          <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Archive note &middot; model definition not verified
          </p>
          <h4 className="font-semibold text-foreground mb-1">
            {insight.title}
          </h4>
          <p className="text-sm text-muted-foreground mb-3">
            {insight.content}
          </p>
          {insight.source && (
            <p className="text-xs text-muted-foreground">
              Archive source: {insight.source}
            </p>
          )}
          {insight.learnMoreUrl && (
            <a
              href={`${baseUrl}${insight.learnMoreUrl.replace(/^\//, "")}`}
              className="mt-2 inline-block text-sm text-primary hover:underline"
            >
              Read the study →
            </a>
          )}
        </div>
      </div>
    </div>
  );
}
