/**
 * Area-fieldnote selection: the client-safe half of `area-page.ts`.
 *
 * `area-page.ts` reads the published assets with Node built-ins at build time,
 * so an island must never import it. Everything the fieldnote panel needs at
 * runtime lives here instead: the section vocabulary, the option projection and
 * the query resolution. Pure — no `node:*`, no React, no fetch.
 */

import {
  sectionKey,
  type ObservedAreaRecord,
  type ObservedMetric,
  type ObservedObservation,
} from "@/utils/observed-data";
import { isObservedPeriodId } from "@/utils/observed-periods";
import type { AreaActivity } from "@/utils/area-activity";

export type AreaPageEra = "year_2025" | "recent" | "pre_covid" | "whole";

/** The property subsets a fieldnote reports on, including the all-property aggregate. */
export type AreaPageProperty = "all" | "hdb" | "ec" | "condo";

export interface AreaPageCombination {
  era: AreaPageEra;
  property: AreaPageProperty;
  /** Reader-facing label, e.g. "2025 complete year · HDB". */
  label: string;
}

/**
 * Every joint section the exporter publishes, in reading order. A fieldnote
 * covers the whole matrix so an area that only appears for condominiums or only
 * in the all-property aggregate still gets a page, and the availability panel
 * can say precisely which combinations are missing.
 */
const AREA_PAGE_ERAS: readonly AreaPageEra[] = [
  "year_2025",
  "whole",
  "recent",
  "pre_covid",
];

const AREA_PAGE_PROPERTIES: readonly AreaPageProperty[] = [
  "hdb",
  "ec",
  "condo",
  "all",
];

const ERA_PAGE_LABELS: Record<AreaPageEra, string> = {
  year_2025: "2025 complete year",
  whole: "All history",
  recent: "2022 onward",
  pre_covid: "Through 2021",
};

const PROPERTY_PAGE_LABELS: Record<AreaPageProperty, string> = {
  hdb: "HDB",
  ec: "EC",
  condo: "Condominium",
  all: "All property types",
};

export const AREA_PAGE_COMBINATIONS: readonly AreaPageCombination[] =
  AREA_PAGE_ERAS.flatMap((era) =>
    AREA_PAGE_PROPERTIES.map((property) => ({
      era,
      property,
      label: `${ERA_PAGE_LABELS[era]} · ${PROPERTY_PAGE_LABELS[property]}`,
    })),
  );

/** Reader-facing scope sentence for the era a fieldnote is anchored on. */
export function areaEraScope(era: AreaPageEra): string {
  if (era === "year_2025") {
    return "the 2025 complete year (2025-01-01 through 2025-12-31)";
  }
  if (era === "whole") return "all published history (no period filter)";
  if (era === "recent") return "transactions from 2022 onward";
  return "transactions dated on or before 2021-12-31";
}

/** Reader-facing headline label, e.g. "HDB resale · All history". */
export function areaSectionScope(
  era: AreaPageEra,
  property: AreaPageProperty,
): string {
  const noun =
    property === "hdb"
      ? "HDB resale"
      : property === "ec"
        ? "Executive condominium"
        : property === "condo"
          ? "Condominium"
          : "All property types";
  return `${noun} · ${ERA_PAGE_LABELS[era]}`;
}

/** Combinations that decide the headline of a fieldnote, most specific first. */
export const AREA_PRIMARY_PREFERENCE: readonly {
  era: AreaPageEra;
  property: AreaPageProperty;
}[] = [
  { era: "year_2025", property: "hdb" },
  { era: "year_2025", property: "condo" },
  { era: "year_2025", property: "all" },
  { era: "year_2025", property: "ec" },
  { era: "whole", property: "hdb" },
  { era: "whole", property: "condo" },
  { era: "whole", property: "all" },
  { era: "whole", property: "ec" },
];

export interface AreaPageSection {
  era: AreaPageEra;
  property: AreaPageProperty;
  /** Exact asset section identity, e.g. `map_metrics.year_2025_hdb`'s key. */
  section: string;
  /** The area record for this combination, or `null` when not published. */
  area: ObservedAreaRecord | null;
  /** The national baseline for this combination, or `null` when not published. */
  national: ObservedObservation[] | null;
}

export interface AreaPageData {
  areaId: string;
  areaName: string;
  slug: string;
  sections: AreaPageSection[];
  baselineCompatible: boolean;
  baselineStatus: string;
  generation: string | null;
  /**
   * Rolling-quarter activity from the verified v2 pack, or `null` when no pack
   * was loadable. Computed at build time so the fieldnote renders it as static
   * HTML instead of fetching a monthly payload (RF10, RF09 §6 risk (a)).
   */
  activity: AreaActivity | null;
}
export interface AreaPageValues {
  medianPrice: number | null;
  medianPsf: number | null;
  volume: number | null;
}

/** One selectable section of a fieldnote, already reduced to display values. */
export interface AreaPageOption {
  /** Stable id: the joint section key, e.g. `year_2025_hdb`. */
  id: string;
  label: string;
  /** Reader-facing scope sentence for this era. */
  scope: string;
  /** Provenance, e.g. `map_metrics.year_2025_hdb`. */
  source: string;
  property: AreaPageProperty;
  period: AreaPageEra;
  area: AreaPageValues;
  /** National baseline for the same joint section, or `null`. */
  national: AreaPageValues | null;
  nationalSource: string | null;
  /** True only when the build-time generation proves both assets agree. */
  comparable: boolean;
  /** Why this combination is empty, or `null` when it publishes values. */
  emptyNote: string | null;
}

function valuesOf(
  observations: readonly ObservedObservation[] | null | undefined,
): AreaPageValues {
  const value = (metric: ObservedMetric): number | null =>
    observations?.find((entry) => entry.metric === metric)?.value ?? null;
  return {
    medianPrice: value("median_price"),
    medianPsf: value("median_psf"),
    volume: value("volume"),
  };
}

function isPublishableValues(values: AreaPageValues): boolean {
  return (
    values.medianPrice !== null ||
    values.medianPsf !== null ||
    values.volume !== null
  );
}

/**
 * Reduce one fieldnote to the sections a reader may select.
 *
 * Order is the reading order `AREA_PAGE_COMBINATIONS` documents: the 2025
 * matrix first (the fieldnote's default scope), then all history, 2022 onward
 * and pre-2021. A combination with nothing published stays in the list with an
 * explicit note — missing is not zero, and it is not an absent option either.
 */
export function areaPageOptions(area: AreaPageData): AreaPageOption[] {
  return AREA_PAGE_COMBINATIONS.map((combination) => {
    const section =
      area.sections.find(
        (candidate) =>
          candidate.era === combination.era &&
          candidate.property === combination.property,
      ) ?? null;

    const areaValues = valuesOf(section?.area?.metrics);
    const nationalValues = section?.national
      ? valuesOf(section.national)
      : null;
    const hasNational =
      nationalValues !== null && isPublishableValues(nationalValues);

    const sectionId =
      section?.section ?? sectionKey(combination.era, combination.property);

    return {
      id: sectionId,
      label: combination.label,
      scope: areaEraScope(combination.era),
      source: `map_metrics.${sectionId}`,
      property: combination.property,
      period: combination.era,
      area: areaValues,
      national: hasNational ? nationalValues : null,
      nationalSource: hasNational
        ? `dashboard_overview.stats.${sectionId}`
        : null,
      comparable:
        area.baselineCompatible &&
        hasNational &&
        areaValues.medianPrice !== null &&
        nationalValues?.medianPrice !== null,
      emptyNote: isPublishableValues(areaValues)
        ? null
        : "No transactions are published for this area in this joint section.",
    };
  });
}

/** The option a fieldnote renders when the URL asks for nothing. */
export function areaPageDefaultOption(
  options: readonly AreaPageOption[],
): AreaPageOption {
  for (const preference of AREA_PRIMARY_PREFERENCE) {
    const match = options.find(
      (option) =>
        option.period === preference.era &&
        option.property === preference.property &&
        option.emptyNote === null,
    );
    if (match !== undefined) return match;
  }
  return options[0];
}

export type AreaPageSelection =
  | { kind: "default"; option: AreaPageOption }
  | { kind: "selected"; option: AreaPageOption }
  | {
      kind: "unavailable";
      /** What the reader asked for, verbatim, for the message. */
      requestedPeriod: string | null;
      requestedProperty: string | null;
      message: string;
      /** What is shown instead — never silently, always with the message. */
      fallback: AreaPageOption;
    };

const AREA_PAGE_PROPERTY_IDS: readonly AreaPageProperty[] = [
  "hdb",
  "ec",
  "condo",
  "all",
];

function isAreaPageProperty(value: string): value is AreaPageProperty {
  return (AREA_PAGE_PROPERTY_IDS as readonly string[]).includes(value);
}

function isAreaPageEra(value: string): value is AreaPageEra {
  return (
    value === "year_2025" ||
    value === "whole" ||
    value === "recent" ||
    value === "pre_covid"
  );
}

/**
 * Resolve `?property=` / `?period=` against the sections this fieldnote carries.
 *
 * The fieldnote publishes the historical `map_metrics` joint sections. A
 * concrete v2 period id is recognised but **not carried here**: the reader gets
 * an explicit message and a link to the surface that does publish it, while the
 * fixed default stays on screen. Nothing is substituted silently.
 */
export function resolveAreaPageSelection(input: {
  options: readonly AreaPageOption[];
  defaultOption: AreaPageOption;
  requestedPeriod: string | null;
  requestedProperty: string | null;
}): AreaPageSelection {
  const { options, defaultOption } = input;
  const requestedProperty =
    input.requestedProperty?.trim().toLowerCase() ?? null;
  const requestedPeriod = input.requestedPeriod?.trim() ?? null;

  const noneRequested =
    (requestedPeriod === null || requestedPeriod === "") &&
    (requestedProperty === null || requestedProperty === "");
  if (noneRequested) return { kind: "default", option: defaultOption };

  if (requestedPeriod !== null && isObservedPeriodId(requestedPeriod)) {
    return {
      kind: "unavailable",
      requestedPeriod,
      requestedProperty,
      message: `This fieldnote publishes the historical joint sections. The published ${requestedPeriod} window is shown in Explore and Compare Areas, not here.`,
      fallback: defaultOption,
    };
  }

  if (requestedProperty !== null && !isAreaPageProperty(requestedProperty)) {
    return {
      kind: "unavailable",
      requestedPeriod,
      requestedProperty,
      message: `“${requestedProperty}” is not a property type this fieldnote publishes. Choose HDB, EC, Condominium or All property types.`,
      fallback: defaultOption,
    };
  }

  if (requestedPeriod !== null && !isAreaPageEra(requestedPeriod)) {
    return {
      kind: "unavailable",
      requestedPeriod,
      requestedProperty,
      message: `“${requestedPeriod}” is not a period this fieldnote publishes. Choose one of the listed sections.`,
      fallback: defaultOption,
    };
  }

  const period = requestedPeriod ?? defaultOption.period;
  const property = requestedProperty ?? defaultOption.property;
  const match = options.find(
    (option) => option.period === period && option.property === property,
  );

  if (match === undefined) {
    return {
      kind: "unavailable",
      requestedPeriod,
      requestedProperty,
      message: "This fieldnote does not publish that combination.",
      fallback: defaultOption,
    };
  }

  const isDefault = match.id === defaultOption.id;
  return isDefault
    ? { kind: "default", option: match }
    : { kind: "selected", option: match };
}
