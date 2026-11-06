/**
 * Research-map archive inspector (slice S9, SVG 17).
 *
 * Shows the stored fields behind the selected area for the active archive
 * layers, plus data-driven warnings about uniform placeholder values and
 * historical forecast targets. It never renders a recommendation, a current
 * fill value or a portfolio allocation.
 */

import type { ArchiveInspection } from "@/utils/map-archive";

interface ArchiveInspectorProps {
  inspection: ArchiveInspection;
  activeLayerCount: number;
  baseUrl: string;
}

export default function ArchiveInspector({
  inspection,
  activeLayerCount,
  baseUrl,
}: ArchiveInspectorProps) {
  return (
    <section
      aria-labelledby="archive-inspector-heading"
      className="mt-4 rounded-2xl border border-border bg-card p-4 shadow-sm"
    >
      <h2
        id="archive-inspector-heading"
        className="text-lg font-bold text-foreground"
      >
        Archived field inspector
      </h2>

      <div className="mt-3 rounded border border-border bg-muted/30 p-3 text-sm">
        <p className="font-bold text-foreground">
          Output gate / not validated for current use
        </p>
        <p className="mt-1 text-muted-foreground">
          Archived layer data can be inspected per area; it is never shaded onto
          the map as a current quantity. Source failures are reported per layer.
        </p>
      </div>

      {inspection.areaId === null ? (
        <p className="mt-4 text-sm text-muted-foreground">
          Select a planning area on the map to inspect its stored archive
          fields. No value is shown until an area is selected.
        </p>
      ) : activeLayerCount === 0 ? (
        <p className="mt-4 text-sm text-muted-foreground">
          No archive layer is selected. The observed transaction fill remains
          the only evidence on the map.
        </p>
      ) : (
        <>
          <div className="mt-4">
            <div className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
              Selected archived area
            </div>
            <div className="mt-1 text-base font-bold text-foreground">
              {inspection.areaId}
            </div>
            {inspection.coverage ? (
              <p className="mt-1 text-xs text-muted-foreground">
                Coverage: {inspection.coverage.archivedAreas} archived areas
                against {inspection.coverage.mapFeatures} planning-area
                polygons. An absent area is shown as unavailable, never as a
                neutral value.
              </p>
            ) : null}
          </div>

          {inspection.warnings.length > 0 ? (
            <ul className="mt-4 space-y-2 rounded border border-amber-600 p-3 text-sm text-amber-900 dark:text-amber-200">
              {inspection.warnings.map((warning) => (
                <li key={warning}>{warning}</li>
              ))}
            </ul>
          ) : null}

          <div className="mt-4 space-y-4">
            {inspection.rows.map((row) => (
              <div key={row.layerId}>
                <h3 className="text-sm font-bold text-foreground">
                  {row.label}
                </h3>
                <dl className="mt-2 grid gap-2 sm:grid-cols-2">
                  {row.values.map((value) => (
                    <div
                      key={`${row.layerId}-${value.label}`}
                      className="rounded bg-muted/30 p-2"
                    >
                      <dt className="text-xs text-muted-foreground">
                        {value.label}
                      </dt>
                      <dd className="text-sm font-medium text-foreground">
                        {value.value}
                      </dd>
                    </div>
                  ))}
                </dl>
              </div>
            ))}
          </div>
        </>
      )}

      <details className="mt-4 rounded border border-border p-3 text-sm">
        <summary className="cursor-pointer font-bold text-foreground">
          Source metadata
        </summary>
        <dl className="mt-2 space-y-2 text-xs text-muted-foreground">
          {inspection.metadata.map((meta) => (
            <div key={meta.group}>
              <dt className="font-bold text-foreground">
                {meta.group} <code className="font-mono">{meta.asset}</code>
              </dt>
              <dd>
                Generated {meta.generatedAt ?? "not supplied"}
                {meta.dataVersion ? ` · ${meta.dataVersion}` : ""}
                {meta.extra ? ` · ${meta.extra}` : ""}
              </dd>
            </div>
          ))}
        </dl>
        <p className="mt-2 text-xs text-muted-foreground">
          Archive extraction dates are not observation periods and are not
          evidence of current model validity.
        </p>
      </details>

      <a
        href={`${baseUrl}explore`}
        className="mt-4 inline-block rounded border border-border px-3 py-2 text-sm font-bold text-foreground hover:bg-muted/40"
      >
        Return to observed map →
      </a>
    </section>
  );
}
