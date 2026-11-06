/**
 * Shared presentation pieces for the decision-tools workspace.
 *
 * Kept tiny on purpose: field labels with units, a withheld/unavailable panel
 * and an evidence badge. Every caveat string still comes from
 * `lib/tool-evidence.ts`; these components only lay it out.
 */

import type { ReactNode } from "react";

export function EvidenceBadge({ children }: { children: ReactNode }) {
  return (
    <p className="inline-block rounded-sm bg-[hsl(var(--secondary))] px-2 py-1 text-xs font-bold text-foreground">
      {children}
    </p>
  );
}

export function WithheldPanel({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <div
      role="status"
      className="rounded-xl border border-border bg-muted/30 p-4 text-sm text-foreground"
    >
      <p className="font-bold">{title}</p>
      <div className="mt-2 space-y-2 text-muted-foreground">{children}</div>
    </div>
  );
}

export function FieldLabel({
  htmlFor,
  label,
  unit,
}: {
  htmlFor: string;
  label: string;
  unit?: string;
}) {
  return (
    <label
      htmlFor={htmlFor}
      className="block text-sm font-bold text-foreground"
    >
      {label}
      {unit ? (
        <span className="ml-1 font-normal text-muted-foreground">/ {unit}</span>
      ) : null}
    </label>
  );
}

export function ToolHeading({
  id,
  title,
  subtitle,
}: {
  id: string;
  title: string;
  subtitle: string;
}) {
  return (
    <div className="max-w-3xl">
      <h2 id={id} className="text-2xl font-bold text-foreground sm:text-3xl">
        {title}
      </h2>
      <p className="mt-2 text-sm text-muted-foreground sm:text-base">
        {subtitle}
      </p>
    </div>
  );
}
