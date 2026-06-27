import type { CatalogLayer } from "@/types/catalog";
import { humanSize } from "@/types/catalog";

const LAYER_COLOR_CLASSES: Record<
  string,
  { bg: string; border: string; text: string; dot: string }
> = {
  bronze: {
    bg: "bg-amber-950/30",
    border: "border-amber-800/50",
    text: "text-amber-300",
    dot: "bg-amber-500",
  },
  silver: {
    bg: "bg-slate-800/30",
    border: "border-slate-700/50",
    text: "text-slate-300",
    dot: "bg-slate-400",
  },
  gold: {
    bg: "bg-yellow-950/30",
    border: "border-yellow-800/50",
    text: "text-yellow-300",
    dot: "bg-yellow-500",
  },
  platinum: {
    bg: "bg-purple-950/30",
    border: "border-purple-800/50",
    text: "text-purple-300",
    dot: "bg-purple-400",
  },
};

interface LayerCardProps {
  layer: CatalogLayer;
  baseUrl: string;
}

export default function LayerCard({ layer, baseUrl }: LayerCardProps) {
  const colors = LAYER_COLOR_CLASSES[layer.id] || LAYER_COLOR_CLASSES.bronze;

  return (
    <a
      href={`${baseUrl}${layer.id}`}
      className={`block p-6 rounded-lg border ${colors.border} ${colors.bg} hover:ring-2 hover:ring-primary/50 transition-all`}
    >
      <div className="flex items-center gap-2 mb-3">
        <div className={`h-3 w-3 rounded-full ${colors.dot}`} />
        <h2 className={`text-lg font-bold ${colors.text}`}>{layer.label}</h2>
      </div>
      <p className="text-sm text-muted-foreground mb-4">{layer.description}</p>
      <div className="grid grid-cols-3 gap-4">
        <div>
          <div className="text-2xl font-bold text-foreground tabular-nums">
            {layer.dataset_count}
          </div>
          <div className="text-xs text-muted-foreground">datasets</div>
        </div>
        <div>
          <div className="text-2xl font-bold text-foreground tabular-nums">
            {layer.total_rows.toLocaleString()}
          </div>
          <div className="text-xs text-muted-foreground">total rows</div>
        </div>
        <div>
          <div className="text-2xl font-bold text-foreground tabular-nums">
            {humanSize(layer.total_size_bytes)}
          </div>
          <div className="text-xs text-muted-foreground">total size</div>
        </div>
      </div>
    </a>
  );
}
