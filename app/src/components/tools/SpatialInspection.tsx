/**
 * Spatial-pattern label inspection (slice S8, SVG 18).
 *
 * The published snapshot supplies `towns[]` (40 records). This tool exposes the
 * stored labels and fields for inspection — with an explicit archive badge —
 * and withholds portfolio allocation, BUY/SELL prompts and return simulations.
 * It never derives a five-year or PSF figure from a total price and never
 * compounds an undefined-period change into an annual rate.
 */

import { useMemo, useState } from "react";
import { formatAreaName } from "@/utils/observed-data";
import type { HotspotClusterType } from "@/types/spatial-hotspots";
import { readSpatialAsset } from "./lib/tool-assets";
import {
  SPATIAL_ARCHIVE_NOTE,
  SPATIAL_LABEL_NOTE,
  SPATIAL_NO_AGGREGATE_NOTE,
  SPATIAL_WITHHELD_NOTE,
} from "./lib/tool-evidence";
import { formatSgd } from "./lib/tool-format";
import {
  EvidenceBadge,
  FieldLabel,
  ToolHeading,
  WithheldPanel,
} from "./ToolParts";

const CLUSTER_TYPES: readonly HotspotClusterType[] = ["HH", "HL", "LH", "LL"];

type ClusterFilter = HotspotClusterType | "all";

export default function SpatialInspection({ data }: { data: unknown }) {
  const read = useMemo(() => readSpatialAsset(data), [data]);
  const [cluster, setCluster] = useState<ClusterFilter>("all");

  if (!read.ok) {
    return (
      <section aria-labelledby="spatial-heading" className="space-y-6">
        <ToolHeading
          id="spatial-heading"
          title="Spatial-pattern label inspection"
          subtitle="Retained, but the model contract is unresolved. Labels only."
        />
        <WithheldPanel title="Spatial labels are unavailable">
          <p>{read.reason}</p>
          <p>{SPATIAL_NO_AGGREGATE_NOTE}</p>
        </WithheldPanel>
      </section>
    );
  }

  const asset = read.asset;
  const filtered = asset.towns.filter(
    (town) => cluster === "all" || town.cluster === cluster,
  );
  const counts = CLUSTER_TYPES.map((type) => ({
    type,
    count: asset.towns.filter((town) => town.cluster === type).length,
  }));

  return (
    <section aria-labelledby="spatial-heading" className="space-y-6">
      <ToolHeading
        id="spatial-heading"
        title="Spatial-pattern label inspection"
        subtitle="Stored cluster labels for the published towns. No allocation, no BUY/SELL prompt and no simulated return."
      />

      <div className="flex flex-wrap items-center gap-3">
        <EvidenceBadge>
          Archive labels · model contract unresolved
        </EvidenceBadge>
        <p className="max-w-2xl text-sm text-muted-foreground">
          {SPATIAL_ARCHIVE_NOTE}
        </p>
      </div>

      <p className="text-sm text-foreground">
        {CLUSTER_TYPES.length} cluster types across {asset.towns.length}{" "}
        published town records.
      </p>

      <div className="max-w-sm">
        <FieldLabel htmlFor="spatial-cluster" label="Stored cluster label" />
        <select
          id="spatial-cluster"
          value={cluster}
          onChange={(event) => setCluster(event.target.value as ClusterFilter)}
          className="mt-1 w-full rounded border border-input bg-background px-3 py-2 text-sm text-foreground"
        >
          <option value="all">All stored labels ({asset.towns.length})</option>
          {counts.map(({ type, count }) => (
            <option key={type} value={type}>
              {type} ({count})
            </option>
          ))}
        </select>
      </div>

      <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
        {counts.map(({ type, count }) => (
          <span
            key={type}
            className="rounded-sm border border-border bg-card px-2 py-1"
          >
            <span className="font-bold text-foreground">{type}</span>{" "}
            {asset.cluster_descriptions[type] ?? "No stored description"} ·{" "}
            {count} towns
          </span>
        ))}
      </div>

      {filtered.length === 0 ? (
        <WithheldPanel title="No town carries this label">
          <p>
            The published snapshot assigns this stored label to no town. Nothing
            is inferred from neighbouring labels.
          </p>
        </WithheldPanel>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-border bg-card">
          <table className="w-full min-w-[720px] border-collapse text-sm">
            <caption className="px-4 pt-4 text-left text-sm text-muted-foreground">
              Stored spatial fields by town. Every column is an archive field;
              sample size and analysis date are not supplied.
            </caption>
            <thead>
              <tr className="border-b border-border text-left">
                <th scope="col" className="px-4 py-3 font-bold text-foreground">
                  Town
                </th>
                <th scope="col" className="px-4 py-3 font-bold text-foreground">
                  Stored cluster
                </th>
                <th scope="col" className="px-4 py-3 font-bold text-foreground">
                  Stored appreciation field
                </th>
                <th scope="col" className="px-4 py-3 font-bold text-foreground">
                  Stored persistence field
                </th>
                <th scope="col" className="px-4 py-3 font-bold text-foreground">
                  Stored risk label
                </th>
                <th scope="col" className="px-4 py-3 font-bold text-foreground">
                  Stored median price
                </th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((town) => (
                <tr key={town.town} className="border-b border-border/60">
                  <th
                    scope="row"
                    className="px-4 py-2 text-left font-bold text-foreground"
                  >
                    {formatAreaName(town.town)}
                  </th>
                  <td className="px-4 py-2 text-foreground">{town.cluster}</td>
                  <td className="px-4 py-2 text-foreground">
                    {town.appreciation_rate.toFixed(2)}%
                  </td>
                  <td className="px-4 py-2 text-foreground">
                    {(town.persistence_probability * 100).toFixed(0)}%
                  </td>
                  <td className="px-4 py-2 text-foreground">
                    {town.risk_level}
                  </td>
                  <td className="px-4 py-2 text-foreground">
                    {formatSgd(town.median_price)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="rounded-xl border border-border bg-muted/20 p-4 text-sm text-muted-foreground">
        <p className="font-bold text-foreground">What is withheld, and why</p>
        <p className="mt-2">{SPATIAL_WITHHELD_NOTE}</p>
        <p className="mt-2">{SPATIAL_LABEL_NOTE}</p>
        <p className="mt-2">{SPATIAL_NO_AGGREGATE_NOTE}</p>
      </div>
    </section>
  );
}
