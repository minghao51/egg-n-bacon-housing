/**
 * Lease-band tool (slice S8, SVG 18).
 *
 * A stored-band lookup, not a decay model. The archive's own
 * inclusive/first-match endpoint rule is preserved and its ambiguity is named;
 * signed statistics are shown as stored, and no safe/cliff recommendation or
 * projected loss is produced.
 */

import { useMemo, useState } from "react";
import {
  leaseCoverageGaps,
  leaseLabelConflicts,
  LEASE_ENDPOINT_POLICY_NOTE,
  LEASE_LOOKUP_NOTE,
  LEASE_RISK_LABEL_NOTE,
  LEASE_SIGNED_NOTE,
  LEASE_WITHHELD_NOTE,
  selectLeaseBand,
  TOOL_ARCHIVE_LABEL,
  TOOL_ARCHIVE_NOTE,
} from "./lib/tool-evidence";
import { readLeaseAsset } from "./lib/tool-assets";
import { formatSignedPercent } from "./lib/tool-format";
import LeaseBandChart from "./LeaseBandChart";
import {
  EvidenceBadge,
  FieldLabel,
  ToolHeading,
  WithheldPanel,
} from "./ToolParts";

const LEASE_INPUT_MIN = 40;
const LEASE_INPUT_MAX = 99;

function parseLeaseInput(text: string): number | null {
  const trimmed = text.trim();
  if (trimmed === "") return null;
  const value = Number(trimmed);
  return Number.isFinite(value) ? value : null;
}

export default function LeaseBands({
  data,
  baseUrl,
}: {
  data: unknown;
  baseUrl: string;
}) {
  const read = useMemo(() => readLeaseAsset(data), [data]);
  const [leaseText, setLeaseText] = useState("75");

  if (!read.ok) {
    return (
      <section aria-labelledby="lease-heading" className="space-y-6">
        <ToolHeading
          id="lease-heading"
          title="Lease bands"
          subtitle="Stored band statistics with a stored-band lookup, not a forecast."
        />
        <WithheldPanel title="Lease bands are unavailable">
          <p>{read.reason}</p>
          <p>
            The tool shows an explicit unavailable state rather than a partial
            or invented band.
          </p>
        </WithheldPanel>
      </section>
    );
  }

  const asset = read.asset;
  const remainingYears = parseLeaseInput(leaseText);
  const inRange =
    remainingYears !== null &&
    remainingYears >= LEASE_INPUT_MIN &&
    remainingYears <= LEASE_INPUT_MAX;
  const lookup = inRange
    ? selectLeaseBand(asset.bands, remainingYears as number)
    : null;

  const sortedBands = [...asset.bands].sort(
    (a, b) => a.min_lease_years - b.min_lease_years,
  );
  const conflicts = leaseLabelConflicts(asset);
  const gaps = leaseCoverageGaps(asset.bands);

  return (
    <section aria-labelledby="lease-heading" className="space-y-6">
      <ToolHeading
        id="lease-heading"
        title="Lease bands"
        subtitle="Remaining lease maps to one stored band. The statistic is a stored archive value, not a price forecast."
      />

      <div className="flex flex-wrap items-center gap-3">
        <EvidenceBadge>{TOOL_ARCHIVE_LABEL}</EvidenceBadge>
        <p className="max-w-2xl text-sm text-muted-foreground">
          {TOOL_ARCHIVE_NOTE}
        </p>
      </div>

      <div className="max-w-sm">
        <FieldLabel
          htmlFor="lease-years"
          label="Remaining lease"
          unit={`years (${LEASE_INPUT_MIN}\u2013${LEASE_INPUT_MAX})`}
        />
        <input
          id="lease-years"
          type="text"
          inputMode="numeric"
          autoComplete="off"
          value={leaseText}
          onChange={(event) => setLeaseText(event.target.value)}
          aria-invalid={!inRange}
          aria-describedby={
            inRange ? "lease-lookup-status" : "lease-input-error"
          }
          className="mt-1 w-full rounded border border-input bg-background px-3 py-2 text-sm text-foreground"
        />
        {!inRange ? (
          <p
            id="lease-input-error"
            className="mt-1 text-xs text-red-700 dark:text-red-300"
          >
            Enter a remaining lease between {LEASE_INPUT_MIN} and{" "}
            {LEASE_INPUT_MAX} years to look up a stored band.
          </p>
        ) : (
          <p
            id="lease-lookup-status"
            className="mt-1 text-xs text-muted-foreground"
          >
            Looking up {remainingYears} years in the stored bands.
          </p>
        )}
      </div>

      {lookup === null ? (
        <WithheldPanel title="No band selected">
          <p>
            The archive is only queried for a remaining lease between{" "}
            {LEASE_INPUT_MIN} and {LEASE_INPUT_MAX} years, the documented input
            range. Nothing is interpolated outside it.
          </p>
        </WithheldPanel>
      ) : (
        <>
          <div className="rounded-xl border border-border bg-card p-4 sm:p-5">
            <dl className="grid gap-4 text-sm sm:grid-cols-2 lg:grid-cols-4">
              <div>
                <dt className="text-muted-foreground">
                  Selected stored interval
                </dt>
                <dd className="font-bold text-foreground">
                  {lookup.band.min_lease_years}&ndash;
                  {lookup.band.max_lease_years} years
                </dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Band statistic</dt>
                <dd className="font-bold text-foreground">
                  {formatSignedPercent(lookup.band.discount_percent)}
                  {lookup.band.transaction_count === null
                    ? " · row count not supplied"
                    : ` · ${lookup.band.transaction_count.toLocaleString("en-SG")} source rows`}
                </dd>
              </div>
              <div>
                <dt className="text-muted-foreground">
                  Stored annual-rate field
                </dt>
                <dd className="font-bold text-foreground">
                  {lookup.band.annual_decay_rate}% / year
                </dd>
                <dd className="text-xs text-muted-foreground">
                  Stored field, not a projected loss.
                </dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Stored risk label</dt>
                <dd className="font-bold text-foreground">
                  {lookup.band.risk_zone}
                </dd>
                <dd className="text-xs text-muted-foreground">
                  Archive label &mdash; see the conflict note below.
                </dd>
              </div>
            </dl>

            {lookup.sharedEndpoint && lookup.matchingBands.length > 1 ? (
              <p className="mt-4 rounded border border-border bg-muted/30 p-3 text-sm text-foreground">
                <span className="font-bold">
                  {remainingYears} is a shared endpoint.
                </span>{" "}
                {lookup.matchingBands
                  .map(
                    (band) =>
                      `${band.lease_age_band} (${band.min_lease_years}\u2013${band.max_lease_years}, ${formatSignedPercent(band.discount_percent)})`,
                  )
                  .join(" and ")}{" "}
                all contain it. The archive&rsquo;s first-match rule selects{" "}
                {lookup.band.lease_age_band}.
              </p>
            ) : null}

            <p className="mt-3 text-sm text-muted-foreground">
              {LEASE_ENDPOINT_POLICY_NOTE}
            </p>
            <p className="mt-2 text-sm text-muted-foreground">
              {LEASE_SIGNED_NOTE}
            </p>
          </div>

          {conflicts.length > 0 ? (
            <div className="rounded-xl border border-border bg-muted/20 p-4 text-sm">
              <p className="font-bold text-foreground">
                Stored labels conflict
              </p>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-muted-foreground">
                {conflicts.map((conflict) => (
                  <li key={conflict}>{conflict}</li>
                ))}
              </ul>
              <p className="mt-2 text-muted-foreground">
                {LEASE_RISK_LABEL_NOTE}
              </p>
            </div>
          ) : null}

          {gaps.length > 0 ? (
            <p className="text-sm text-muted-foreground">
              No stored band covers{" "}
              {gaps
                .map((gap) => `${gap.from + 1}\u2013${gap.to - 1} years`)
                .join(", ")}{" "}
              of remaining lease. The lookup never fills such a gap.
            </p>
          ) : null}
        </>
      )}

      <div className="rounded-xl border border-border bg-card p-4 sm:p-5">
        <h3 className="text-sm font-bold uppercase tracking-wider text-muted-foreground">
          Stored band statistic vs remaining lease
        </h3>
        <p className="mt-1 text-sm text-muted-foreground">
          Signed percentage &middot; negative values indicate a premium.
        </p>
        <LeaseBandChart bands={sortedBands} selected={lookup?.band ?? null} />

        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[560px] border-collapse text-sm">
            <caption className="sr-only">
              Every stored lease band, its remaining-lease interval, signed
              statistic, row count and stored risk label
            </caption>
            <thead>
              <tr className="border-b border-border text-left">
                <th scope="col" className="py-2 pr-4 font-bold text-foreground">
                  Remaining lease
                </th>
                <th scope="col" className="py-2 pr-4 font-bold text-foreground">
                  Stored band
                </th>
                <th scope="col" className="py-2 pr-4 font-bold text-foreground">
                  Stored statistic
                </th>
                <th scope="col" className="py-2 pr-4 font-bold text-foreground">
                  Source rows
                </th>
                <th scope="col" className="py-2 font-bold text-foreground">
                  Stored risk label
                </th>
              </tr>
            </thead>
            <tbody>
              {sortedBands.map((band) => {
                const isSelected =
                  lookup !== null &&
                  band.lease_age_band === lookup.band.lease_age_band;
                return (
                  <tr
                    key={band.lease_age_band}
                    className={`border-b border-border/60 ${isSelected ? "bg-muted/40 font-bold" : ""}`}
                  >
                    <th scope="row" className="py-2 pr-4 text-foreground">
                      {band.min_lease_years}&ndash;{band.max_lease_years}
                      {isSelected ? (
                        <span className="ml-2 text-xs font-normal text-muted-foreground">
                          selected
                        </span>
                      ) : null}
                    </th>
                    <td className="py-2 pr-4 text-foreground">
                      {band.lease_age_band}
                    </td>
                    <td className="py-2 pr-4 text-foreground">
                      {formatSignedPercent(band.discount_percent)}
                    </td>
                    <td className="py-2 pr-4 text-foreground">
                      {band.transaction_count === null
                        ? "N/A"
                        : band.transaction_count.toLocaleString("en-SG")}
                    </td>
                    <td className="py-2 text-foreground">{band.risk_zone}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <p className="mt-2 text-xs text-muted-foreground">
          {LEASE_LOOKUP_NOTE}
        </p>
      </div>

      <WithheldPanel title="Recommendations withheld">
        <p>{LEASE_WITHHELD_NOTE}</p>
        <p>
          <a
            className="font-bold text-foreground underline"
            href={`${baseUrl}analytics/lease-decay`}
          >
            Read the lease-decay methodology notes
          </a>
        </p>
      </WithheldPanel>
    </section>
  );
}
