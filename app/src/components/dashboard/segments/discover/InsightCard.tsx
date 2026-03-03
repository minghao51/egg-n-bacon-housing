// app/src/components/dashboard/segments/discover/InsightCard.tsx
import type { Insight } from '@/types/segments';

interface InsightCardProps {
  insight: Insight;
}

export function InsightCard({ insight }: InsightCardProps) {
  return (
    <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
      <div className="flex items-start gap-3">
        <span className="text-2xl flex-shrink-0">💡</span>
        <div className="flex-1 min-w-0">
          <h4 className="font-semibold text-foreground mb-1">{insight.title}</h4>
          <p className="text-sm text-muted-foreground mb-3">{insight.content}</p>
          {insight.learnMoreUrl && (
            <a
              href={insight.learnMoreUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-primary hover:underline"
            >
              Learn more →
            </a>
          )}
        </div>
      </div>
    </div>
  );
}
