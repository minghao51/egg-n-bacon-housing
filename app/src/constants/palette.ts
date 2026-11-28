/**
 * Fieldnotes data palette — the single source of truth for chart colours.
 *
 * Every chart colour here is a `hsl(var(--token))` reference, never a raw hex,
 * so a change to the tokens in `app/src/styles/globals.css` moves every chart
 * with it. Nothing here duplicates a numeric colour value.
 *
 * The map roles at the bottom of this file (the sequential and diverging
 * ramps, the no-data fill, the surface and outline roles) follow the same rule
 * and are the only place a map may take a fill or a stroke from.
 *
 * A hue means a property type, or nothing at all. Teal is HDB, rust is EC and
 * plum is condominium, so a colour is only meaningful when the series it marks
 * is one of those. Everything else (a measure, an arbitrary category) uses the
 * single-series colour or the neutral `CATEGORICAL` ramp. Direction of change —
 * prices up or down, more or fewer sales — must be carried by an arrow, a sign
 * or a word, never by red versus green: those two hues are already spoken for
 * by EC and nothing in this file means "worse".
 *
 * Plain TypeScript: no React, no Astro, no imports. Safe to read from any layer.
 */

/** The named Fieldnotes tokens (see the `:root` block in globals.css). */
export const PRIMITIVES = {
  teal: "hsl(var(--teal))",
  rust: "hsl(var(--rust))",
  plum: "hsl(var(--plum))",
  ink: "hsl(var(--ink))",
  mutedInk: "hsl(var(--muted-ink))",
} as const;

export type PropertyTypeColourId = "hdb" | "ec" | "condo" | "all";

/**
 * Property-type colours in the order the site presents them:
 * hdb -> ec -> condo -> all. `all` is ink because an aggregate is not a type.
 */
export const PROPERTY_COLOURS = {
  hdb: PRIMITIVES.teal,
  ec: PRIMITIVES.rust,
  condo: PRIMITIVES.plum,
  all: PRIMITIVES.ink,
} satisfies Record<PropertyTypeColourId, string>;

/**
 * Look up a property colour from the loose ids the data actually uses:
 * `hdb` / `HDB`, `ec` / `EC`, `condo` / `Condominium`, `all`. Unknown ids fall
 * back to ink, the aggregate colour, rather than inventing a hue.
 */
const PROPERTY_ID_ALIASES: Record<string, PropertyTypeColourId> = {
  hdb: "hdb",
  ec: "ec",
  condo: "condo",
  condominium: "condo",
  all: "all",
};

export function propertyColour(id: string): string {
  const key = id.trim().toLowerCase();
  return PROPERTY_COLOURS[PROPERTY_ID_ALIASES[key] ?? "all"];
}

/**
 * Ordered ramp for series that are genuinely arbitrary (not property types).
 * Cycled with `% CATEGORICAL.length`; it carries no meaning beyond "a
 * different series than the one before it".
 */
export const CATEGORICAL: readonly string[] = [
  PRIMITIVES.teal,
  PRIMITIVES.rust,
  PRIMITIVES.plum,
  PRIMITIVES.ink,
  PRIMITIVES.mutedInk,
];

/**
 * A chart that plots one measure (volume, counts, a single median) is not a
 * property type, so it gets one colour and no legend implication.
 */
export const SINGLE_SERIES = PRIMITIVES.teal;

/**
 * Seven steps of the teal hue, light to dark, for a choropleth that encodes one
 * magnitude — a price, a yield, a count of sales.
 *
 * A `fill` / `stroke` attribute cannot interpolate `hsl(var(--teal))`, so the
 * steps are literal hex. They are *derived* from the token: the darkest step
 * (`#006B65`) is exactly `hsl(var(--teal))`, and the six lighter steps are that
 * same hue at rising lightness. Retuning `--teal` means re-deriving all seven
 * together; do not edit the top step alone.
 *
 * Seven, not fewer, because `PriceMap` cuts seven buckets on purpose (its
 * thresholds explain the observed distribution) and two buckets that render
 * identically would hide a real step. The lightest step sits just above the
 * paper surface so a lowest bin still separates from the page behind it.
 *
 * This ramp carries no property-type meaning. A polygon coloured from it says
 * "more of the one thing this map measures", never "HDB".
 */
export const SEQUENTIAL_RAMP: readonly string[] = [
  "#F1F7F5",
  "#E4EFEC",
  "#BBD8D2",
  "#8CBFB6",
  "#57A096",
  "#2A8379",
  "#006B65",
];

/** The darkest step: the highest bin, and what a legend may call "High". */
export const SEQUENTIAL_TOP = SEQUENTIAL_RAMP[SEQUENTIAL_RAMP.length - 1];

/**
 * The ramp colour for step `index` of `stepCount`, lightest first.
 *
 * A choropleth cuts its buckets (or normalises its values) before it asks this
 * question, so the only decision left here is which ramp step a given bin lands
 * on. The mapping spreads `stepCount` bins across the whole ramp:
 *
 *     position = round(index x (ramp length - 1) / (stepCount - 1))
 *
 * Consecutive positions are `(ramp length - 1) / (stepCount - 1)` apart, which
 * is at least 1 whenever `stepCount` does not exceed the ramp length (2 to 7
 * today). Rounding a strictly increasing sequence with gaps of at least 1 keeps
 * it strictly increasing, so **no two bins ever share a colour** and both ends
 * are always used — the darkest step means the highest bin, the lightest the
 * lowest. A `stepCount` above the ramp length can still collide; no map asks
 * for one.
 */
export function sequentialStep(index: number, stepCount: number): string {
  if (stepCount <= 1) return SEQUENTIAL_RAMP[0];
  const lastStep = SEQUENTIAL_RAMP.length - 1;
  const position = Math.round((index / (stepCount - 1)) * lastStep);
  return SEQUENTIAL_RAMP[Math.min(lastStep, Math.max(0, position))];
}

/**
 * Seven steps for a *signed* metric only: rust below zero, neutral at zero,
 * teal above.
 *
 * This reuses the property hues for a direction, which is acceptable only
 * because a signed choropleth carries one dimension and no property-type
 * series — there is no second series for rust to be confused with. Any legend
 * showing this ramp must name the direction in words ("above zero: higher
 * growth"), because the colours alone are not the message, and `rust` still
 * means EC everywhere a property type is plotted.
 */
export const DIVERGING_RAMP: readonly string[] = [
  "#8F3520",
  "#B64426",
  "#D58A70",
  "#ECE7DB",
  "#7FB8AE",
  "#2A8379",
  "#006B65",
];

/**
 * The fill for "this area has no value here".
 *
 * The warm surface neutral, which sits outside the teal ramp in hue as well as
 * lightness, so a missing value can never be misread as the ramp's lightest
 * bin. Where a hatch already marks the gap (the explorer's SVG map) the hatch
 * stays and this colour goes underneath it.
 */
export const NO_DATA = "hsl(var(--muted))";

/** The two page surfaces a polygon edge may sit on. */
export const SURFACE = {
  paper: "hsl(var(--paper))",
  card: "hsl(var(--card))",
} as const;

/**
 * How a polygon is outlined when it is *selected* or holds keyboard *focus*.
 *
 * Both are ink, never a property hue: a reader must not see a teal edge and
 * wonder whether the area is HDB. Solid versus dashed keeps the two states
 * distinguishable without relying on colour at all. `dashArray` is written for
 * both Leaflet's `dashArray` option and SVG's `stroke-dasharray`.
 */
export const MAP_OUTLINE = {
  selected: { color: PRIMITIVES.ink, weight: 3 },
  focus: { color: PRIMITIVES.ink, weight: 3, dashArray: "4 4" },
} as const;
