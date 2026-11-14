/**
 * Monthly history for an area fieldnote (RF10 slice 2b).
 *
 * The monthly payload is the largest asset in the release (up to ~233 KB per
 * property type), so nothing is fetched until the reader asks. The island then
 * verifies the payload against the published manifest before rendering a single
 * number: a tampered or missing payload is an error state, not a shorter series.
 *
 * Rules carried from RF09:
 * - A month inside the grid with zero sales is `no-sales` — a verified zero, not
 *   a gap and not "cold".
 * - A month outside the grid, or an area the release does not carry, is
 *   `missing-source` and never renders as 0.
 * - Already-verified rows survive a failed refresh; the error appears beside
 *   them with a retry rather than blanking the table.
 */

import { useCallback, useState } from "react";

import {
  buildAreaHistoryView,
  monthStatusLabel,
  type AreaHistoryView,
} from "@/utils/area-history";
import type { PropertyTypeId } from "@/utils/observed-monthly";
import {
  V2_MANIFEST_PATH,
  loadObservedHistory,
  parseV2Manifest,
  type V2Manifest,
} from "@/utils/observed-pack-loader";

export interface AreaHistoryPanelProps {
  areaName: string;
  /** Pack geography id (`"PUNGGOL"`), not the route slug. */
  areaId: string;
  property: PropertyTypeId;
  /** Deployment base without its trailing slash ("" at the root path). */
  base: string;
}

type PanelState =
  | { state: "idle" }
  | { state: "loading" }
  | { state: "ready"; view: AreaHistoryView }
  | { state: "error"; message: string };

const PROPERTY_LABELS: Record<PropertyTypeId, string> = {
  hdb: "HDB resale",
  ec: "executive condominium",
  condo: "private residential",
  all: "all residential",
};

function formatCount(value: number | null): string {
  return value === null ? "—" : value.toLocaleString("en-US");
}

function formatPrice(value: number | null): string {
  return value === null ? "—" : `S$${Math.round(value).toLocaleString("en-US")}`;
}

function formatPsf(value: number | null): string {
  return value === null ? "—" : `S$${Math.round(value).toLocaleString("en-US")}`;
}

/** Fetch the manifest only, then verify the one payload we need. */
async function fetchHistory(
  base: string,
  property: PropertyTypeId,
  areaId: string,
): Promise<{ ok: true; view: AreaHistoryView } | { ok: false; message: string }> {
  const baseUrl = base === "" ? "/" : `${base}/`;
  let manifest: V2Manifest;
  try {
    const response = await fetch(`${baseUrl}${V2_MANIFEST_PATH}`, {
      cache: "no-store",
    });
    if (!response.ok) {
      return {
        ok: false,
        message: `The published manifest could not be read (HTTP ${response.status}), so no monthly history is shown.`,
      };
    }
    const parsed = parseV2Manifest(await response.json());
    if (!parsed.ok) {
      return {
        ok: false,
        message: `The published manifest did not verify: ${parsed.errors.join("; ")}.`,
      };
    }
    manifest = parsed.manifest;
  } catch (error) {
    return {
      ok: false,
      message: `The published manifest could not be read: ${String(error)}.`,
    };
  }

  const loaded = await loadObservedHistory(manifest, property, { baseUrl });
  if (loaded.state !== "ready") {
    return {
      ok: false,
      message: `This release does not serve a verified monthly history for ${PROPERTY_LABELS[property]}: ${loaded.errors.join("; ")}.`,
    };
  }

  return { ok: true, view: buildAreaHistoryView(loaded.history, areaId) };
}

export default function AreaHistoryPanel({
  areaName,
  areaId,
  property,
  base,
}: AreaHistoryPanelProps) {
  const [panel, setPanel] = useState<PanelState>({ state: "idle" });

  const load = useCallback(async () => {
    setPanel((current) =>
      current.state === "ready" ? current : { state: "loading" },
    );
    const result = await fetchHistory(base, property, areaId);
    setPanel(
      result.ok
        ? { state: "ready", view: result.view }
        : { state: "error", message: result.message },
    );
  }, [base, property, areaId]);

  return (
    <section aria-labelledby="area-history-heading" className="mt-8 min-w-0">
      <h2 id="area-history-heading" className="text-2xl font-bold text-foreground">
        Monthly history
      </h2>
      <p className="mt-2 text-sm text-muted-foreground">
        Month-by-month observed sales and medians for {areaName} (
        {PROPERTY_LABELS[property]}). This reads the published monthly payload,
        so it is loaded only when you ask for it. Nothing here is fetched on page
        load.
      </p>

      {panel.state === "idle" ? (
        <button
          type="button"
          onClick={load}
          className="mt-4 rounded border border-input bg-card px-4 py-2 text-sm font-bold text-foreground"
          data-history-load
        >
          Load monthly history
        </button>
      ) : null}

      {panel.state === "loading" ? (
        <p
          role="status"
          className="mt-4 rounded border border-border bg-muted px-3 py-2 text-sm text-muted-foreground"
        >
          Verifying the monthly payload against the published manifest…
        </p>
      ) : null}

      {panel.state === "error" ? (
        <div className="mt-4 rounded border border-border bg-muted px-3 py-2 text-sm">
          <p className="font-bold text-foreground">
            Monthly history unavailable
          </p>
          <p className="mt-1 text-muted-foreground" data-history-error>
            {panel.message}
          </p>
          <button
            type="button"
            onClick={load}
            className="mt-2 rounded border border-input px-3 py-1 text-sm font-bold text-foreground"
            data-history-retry
          >
            Retry
          </button>
        </div>
      ) : null}

      {panel.state === "ready" ? (
        <HistoryTable view={panel.view} areaName={areaName} onRetry={load} />
      ) : null}
    </section>
  );
}

function HistoryTable({
  view,
  areaName,
  onRetry,
}: {
  view: AreaHistoryView;
  areaName: string;
  onRetry: () => void;
}) {
  if (view.rows.length === 0) {
    return (
      <p
        className="mt-4 rounded border border-border bg-muted px-3 py-2 text-sm text-foreground"
        data-history-empty
      >
        This release carries no monthly series for {areaName} in this property
        type. Nothing is shown rather than a column of zeros.
      </p>
    );
  }

  return (
    <div className="mt-4">
      <p className="text-sm text-muted-foreground">
        Last {view.rows.length} months of the published grid, ending{" "}
        {view.cutoffMonth}. {view.coverageRule}
        {view.noSalesMonths > 0 ? (
          <>
            {" "}
            {view.noSalesMonths} of these months have no observed sales — a
            verified zero for this population, not missing data.
          </>
        ) : null}
      </p>
      {!view.hasObservations ? (
        <p className="mt-2 rounded border border-border bg-muted px-3 py-2 text-sm text-foreground">
          Every month in this window is a verified zero for {areaName}. That
          usually means the area has little or no stock of this property type,
          not a quiet market.
        </p>
      ) : null}
      <div className="mt-3 overflow-x-auto">
        <table
          className="w-full min-w-[34rem] border-collapse text-sm"
          data-history-table
        >
          <caption className="sr-only">
            Monthly observed sales and medians for {areaName}
          </caption>
          <thead>
            <tr className="border-b border-border text-left">
              <th scope="col" className="py-2 pr-4 font-bold">
                Month
              </th>
              <th scope="col" className="py-2 pr-4 font-bold">
                Observed sales
              </th>
              <th scope="col" className="py-2 pr-4 font-bold">
                Median price
              </th>
              <th scope="col" className="py-2 font-bold">
                Median psf
              </th>
            </tr>
          </thead>
          <tbody>
            {view.rows.map((row) => (
              <tr
                key={row.month}
                className="border-b border-border"
                data-history-row={row.month}
                data-history-status={row.status}
              >
                <th scope="row" className="py-2 pr-4 text-left font-mono text-xs">
                  {row.month}
                </th>
                <td className="py-2 pr-4" data-numeric>
                  {row.status === "available"
                    ? formatCount(row.transactionCount)
                    : monthStatusLabel(row)}
                </td>
                <td className="py-2 pr-4" data-numeric>
                  {formatPrice(row.medianPrice)}
                </td>
                <td className="py-2" data-numeric>
                  {formatPsf(row.medianPsf)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-3 text-sm">
        <button
          type="button"
          onClick={onRetry}
          className="font-bold text-[hsl(var(--teal))] underline underline-offset-4 hover:no-underline"
          data-history-refresh
        >
          Re-verify this payload
        </button>
      </p>
    </div>
  );
}
