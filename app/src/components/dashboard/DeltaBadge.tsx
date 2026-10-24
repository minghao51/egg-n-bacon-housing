import { ArrowDownRight, ArrowUpRight } from "lucide-react";

interface DeltaBadgeProps {
  value?: number | null;
  label?: string;
  size?: "sm" | "md";
  invert?: boolean;
}

function ariaTextFor(label?: string): string {
  if (label === "YoY") return "year over year";
  if (label === "MoM") return "month over month";
  return label ?? "change";
}

export default function DeltaBadge({
  value,
  label,
  size = "md",
  invert = false,
}: DeltaBadgeProps) {
  const sizeClasses = size === "sm" ? "text-xs" : "text-sm font-semibold";
  const iconClasses = size === "sm" ? "h-3 w-3" : "h-3.5 w-3.5";

  if (
    value === null ||
    value === undefined ||
    Number.isNaN(value) ||
    value === 0
  ) {
    return (
      <span
        className={`inline-flex items-center gap-1 text-muted-foreground ${sizeClasses}`}
      >
        <span aria-hidden="true">—</span>
        {label && <span className="text-xs font-normal">{label}</span>}
      </span>
    );
  }

  const isUp = value > 0;
  const Icon = isUp ? ArrowUpRight : ArrowDownRight;
  const toneClass = (invert ? !isUp : isUp)
    ? "text-emerald-600"
    : "text-rose-600";
  const ariaLabel = `${isUp ? "up" : "down"} ${Math.abs(value).toFixed(1)} percent ${ariaTextFor(label)}`;

  return (
    <span
      className={`inline-flex items-center gap-1 ${sizeClasses} ${toneClass}`}
      aria-label={ariaLabel}
    >
      <Icon className={iconClasses} aria-hidden="true" />
      <span>
        {isUp ? "+" : "-"}
        {Math.abs(value).toFixed(1)}%
      </span>
      {label && <span className="text-xs font-normal">{label}</span>}
    </span>
  );
}
