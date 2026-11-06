/**
 * MRT / CBD model inspection (slice S8, SVG 18).
 *
 * The controls are retained, but the total-dollar estimate is withheld: the
 * stored formula's units, distance direction and 500 m stop are unresolved, and
 * its ×1,000 is an undeclared floor-area assumption. The tool therefore shows
 * the supplied coefficients, the stored formula with this scenario's numbers,
 * and an explicit model-review state — never a premium total.
 */

import { useMemo, useState } from "react";
import { formatAreaName } from "@/utils/observed-data";
import { readMrtAsset } from "./lib/tool-assets";
import {
  MRT_DIRECTION_NOTE,
  MRT_FLOOR_AREA_NOTE,
  MRT_NO_FALLBACK_NOTE,
  MRT_STORED_DISTANCE_CAP_METRES,
  MRT_STORED_IMPLICIT_SQFT,
  MRT_TOWN_KEY_NOTE,
  MRT_UNIT_NOTE,
  MRT_WITHHELD_NOTE,
  mrtStoredTerms,
  resolveTownKey,
} from "./lib/tool-evidence";
import { formatSgd } from "./lib/tool-format";
import {
  EvidenceBadge,
  FieldLabel,
  ToolHeading,
  WithheldPanel,
} from "./ToolParts";

function parseNumber(text: string): number | null {
  const trimmed = text.trim().replace(/,/g, "");
  if (trimmed === "") return null;
  const value = Number(trimmed);
  return Number.isFinite(value) ? value : Number.NaN;
}

export default function MrtCbdInspection({
  data,
  baseUrl,
}: {
  data: unknown;
  baseUrl: string;
}) {
  const read = useMemo(() => readMrtAsset(data), [data]);
  const [typeKey, setTypeKey] = useState("HDB");
  const [townInput, setTownInput] = useState("Bishan");
  const [distanceText, setDistanceText] = useState("500");
  const [cbdText, setCbdText] = useState("10");
  const [floorAreaText, setFloorAreaText] = useState("1000");

  if (!read.ok) {
    return (
      <section aria-labelledby="mrt-heading" className="space-y-6">
        <ToolHeading
          id="mrt-heading"
          title="MRT / CBD model inspection"
          subtitle="Show the assumptions before the answer. The total-dollar estimate is withheld."
        />
        <WithheldPanel title="MRT / CBD coefficients are unavailable">
          <p>{read.reason}</p>
          <p>{MRT_NO_FALLBACK_NOTE}</p>
        </WithheldPanel>
      </section>
    );
  }

  const asset = read.asset;
  const typeKeys = Object.keys(asset.property_type_multipliers).sort();
  const townKeys = Object.keys(asset.town_multipliers).sort();

  const distance = parseNumber(distanceText);
  const cbdKm = parseNumber(cbdText);
  const floorArea = parseNumber(floorAreaText);
  const townKey = resolveTownKey(asset.town_multipliers, townInput);

  const terms = mrtStoredTerms(
    asset,
    typeKey,
    townInput,
    distance !== null && Number.isFinite(distance) ? distance : null,
    cbdKm !== null && Number.isFinite(cbdKm) ? cbdKm : null,
  );

  const distanceValid =
    distance !== null && Number.isFinite(distance) && distance >= 0;
  const cbdValid = cbdKm !== null && Number.isFinite(cbdKm) && cbdKm >= 0;
  const floorAreaValid =
    floorArea !== null && Number.isFinite(floorArea) && floorArea > 0;

  return (
    <section aria-labelledby="mrt-heading" className="space-y-6">
      <ToolHeading
        id="mrt-heading"
        title="MRT / CBD model inspection"
        subtitle="The controls are retained. Both stored terms and their coefficients are disclosed; the total-dollar estimate is not."
      />

      <div className="flex flex-wrap items-center gap-3">
        <EvidenceBadge>Model review required</EvidenceBadge>
        <p className="max-w-2xl text-sm text-muted-foreground">
          {MRT_WITHHELD_NOTE}
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <div>
          <FieldLabel htmlFor="mrt-property" label="Property type" />
          <select
            id="mrt-property"
            value={typeKey}
            onChange={(event) => setTypeKey(event.target.value)}
            className="mt-1 w-full rounded border border-input bg-background px-3 py-2 text-sm text-foreground"
          >
            {typeKeys.map((key) => (
              <option key={key} value={key}>
                {key}
              </option>
            ))}
          </select>
        </div>

        <div>
          <FieldLabel htmlFor="mrt-town" label="Canonical area key" />
          <select
            id="mrt-town"
            value={townKey ?? ""}
            onChange={(event) => {
              const next = event.target.value;
              setTownInput(next);
            }}
            className="mt-1 w-full rounded border border-input bg-background px-3 py-2 text-sm text-foreground"
          >
            {townKeys.map((key) => (
              <option key={key} value={key}>
                {formatAreaName(key)} ({key})
              </option>
            ))}
          </select>
          <p className="mt-1 text-xs text-muted-foreground">
            Stored key: {townKey ?? "no match"}. A title-case label resolves to
            the same canonical key.
          </p>
        </div>

        <div>
          <FieldLabel
            htmlFor="mrt-distance"
            label="Distance to MRT"
            unit="metres"
          />
          <input
            id="mrt-distance"
            type="text"
            inputMode="decimal"
            autoComplete="off"
            value={distanceText}
            onChange={(event) => setDistanceText(event.target.value)}
            aria-invalid={!distanceValid}
            className="mt-1 w-full rounded border border-input bg-background px-3 py-2 text-sm text-foreground"
          />
          <p className="mt-1 text-xs text-muted-foreground">
            The stored formula stops changing above{" "}
            {MRT_STORED_DISTANCE_CAP_METRES} m.
          </p>
        </div>

        <div>
          <FieldLabel htmlFor="mrt-cbd" label="Distance to CBD" unit="km" />
          <input
            id="mrt-cbd"
            type="text"
            inputMode="decimal"
            autoComplete="off"
            value={cbdText}
            onChange={(event) => setCbdText(event.target.value)}
            aria-invalid={!cbdValid}
            className="mt-1 w-full rounded border border-input bg-background px-3 py-2 text-sm text-foreground"
          />
          <p className="mt-1 text-xs text-muted-foreground">
            Stored CBD rate is per km.
          </p>
        </div>

        <div>
          <FieldLabel
            htmlFor="mrt-floor-area"
            label="Floor area (S8 explicit input)"
            unit="square feet"
          />
          <input
            id="mrt-floor-area"
            type="text"
            inputMode="decimal"
            autoComplete="off"
            value={floorAreaText}
            onChange={(event) => setFloorAreaText(event.target.value)}
            aria-invalid={!floorAreaValid}
            className="mt-1 w-full rounded border border-input bg-background px-3 py-2 text-sm text-foreground"
          />
          <p className="mt-1 text-xs text-muted-foreground">
            {MRT_FLOOR_AREA_NOTE}
          </p>
        </div>
      </div>

      <div className="rounded-xl border border-border bg-card p-4 sm:p-5">
        <h3 className="text-sm font-bold uppercase tracking-wider text-muted-foreground">
          Supplied coefficients and stored formula
        </h3>
        <dl className="mt-3 grid gap-4 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-muted-foreground">
              {typeKey} premium coefficient (as supplied)
            </dt>
            <dd className="font-bold text-foreground">
              {terms.typeCoefficient === null
                ? "Not supplied for this property type"
                : `${formatSgd(terms.typeCoefficient.premium_per_100m)} per 100 m`}
            </dd>
          </div>
          <div>
            <dt className="text-muted-foreground">
              {typeKey} CBD coefficient (as supplied)
            </dt>
            <dd className="font-bold text-foreground">
              {terms.typeCoefficient === null
                ? "Not supplied for this property type"
                : `${formatSgd(terms.typeCoefficient.cbd_per_km)} per km`}
            </dd>
          </div>
          <div>
            <dt className="text-muted-foreground">
              Town multiplier &middot; stored key
            </dt>
            <dd className="font-bold text-foreground">
              {terms.townMultiplier === null || terms.townKey === null
                ? "No stored match"
                : `${terms.townMultiplier}\u00d7 · ${terms.townKey}`}
            </dd>
          </div>
          <div>
            <dt className="text-muted-foreground">
              Effective stored premium per 100 m
            </dt>
            <dd className="font-bold text-foreground">
              {terms.effectivePremiumPer100m === null
                ? "N/A"
                : formatSgd(terms.effectivePremiumPer100m)}
            </dd>
          </div>
          <div>
            <dt className="text-muted-foreground">
              Distance applied by the stored formula
            </dt>
            <dd className="font-bold text-foreground">
              {terms.appliedDistanceMetres === null
                ? "Enter a valid distance"
                : `${terms.appliedDistanceMetres} m${terms.distanceMetres !== null && terms.distanceMetres > MRT_STORED_DISTANCE_CAP_METRES ? ` (capped from ${terms.distanceMetres} m)` : ""}`}
            </dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Floor area declared</dt>
            <dd className="font-bold text-foreground">
              {floorAreaValid
                ? `${floorArea.toLocaleString("en-SG")} sqft · not consumed by this archive`
                : "Enter a floor area greater than 0"}
            </dd>
          </div>
        </dl>

        <p className="mt-4 rounded border border-border bg-muted/30 p-3 font-mono text-sm text-foreground">
          {terms.formula === null
            ? "Stored MRT premium term cannot be evaluated for this selection."
            : `Stored MRT premium term: (${terms.appliedDistanceMetres} ÷ 100) × ${terms.effectivePremiumPer100m} × ${MRT_STORED_IMPLICIT_SQFT} · total withheld`}
        </p>
        <p className="mt-2 rounded border border-border bg-muted/30 p-3 font-mono text-sm text-foreground">
          {terms.cbdFormula === null
            ? "CBD term cannot be evaluated for this selection."
            : `CBD term (as supplied, not combined): ${terms.cbdFormula} · total withheld`}
        </p>
        <p className="mt-2 text-xs text-muted-foreground">
          The ×{MRT_STORED_IMPLICIT_SQFT} is the archive&rsquo;s implicit
          floor-area assumption, not a declared square-foot basis. The CBD term
          is shown with its supplied units and is never added to the MRT term.
        </p>
      </div>

      <div className="rounded-xl border border-border bg-muted/20 p-4 text-sm text-muted-foreground">
        <p className="font-bold text-foreground">
          Why the total-dollar estimate is withheld
        </p>
        <p className="mt-2">{MRT_DIRECTION_NOTE}</p>
        <p className="mt-2">{MRT_UNIT_NOTE}</p>
        <p className="mt-2">{MRT_TOWN_KEY_NOTE}</p>
        <p className="mt-2">{MRT_NO_FALLBACK_NOTE}</p>
        <p className="mt-3 flex flex-wrap gap-4">
          <a
            className="font-bold text-foreground underline"
            href={`${baseUrl}analytics/mrt-impact`}
          >
            Read the transport methodology
          </a>
          <a
            className="font-bold text-foreground underline"
            href={`${baseUrl}analytics/spatial-autocorrelation`}
          >
            Read the spatial-audit notes
          </a>
        </p>
      </div>
    </section>
  );
}
