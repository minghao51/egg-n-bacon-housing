/**
 * Pure filtering for the studies library (slice S9).
 *
 * The library is a static Astro page; this module is shared by the page's
 * build-time data shaping, the React filter island and the unit tests. It is
 * deliberately free of React, DOM and Astro imports.
 */

export type StudyCategory =
  | "investment-guides"
  | "market-analysis"
  | "technical-reports"
  | "quick-reference";

export type StudyPersona = "first-time-buyer" | "investor" | "upgrader";

export interface StudyCardData {
  slug: string;
  title: string;
  description: string;
  category: StudyCategory;
  /** ISO date string, or `null` when the study supplies none. */
  date: string | null;
  readingTime: string | null;
  technicalLevel: "beginner" | "intermediate" | "advanced" | null;
  personas: StudyPersona[];
  /** True when the study has a unit/observation-period review flag. */
  evidenceReview: boolean;
}

export const STUDY_CATEGORIES: readonly StudyCategory[] = [
  "investment-guides",
  "market-analysis",
  "technical-reports",
  "quick-reference",
];

export const STUDY_CATEGORY_LABELS: Readonly<Record<StudyCategory, string>> = {
  "investment-guides": "Investment guides",
  "market-analysis": "Market analysis",
  "technical-reports": "Technical reports",
  "quick-reference": "Quick reference",
};

export const STUDY_PERSONAS: readonly StudyPersona[] = [
  "first-time-buyer",
  "investor",
  "upgrader",
];

export const STUDY_PERSONA_LABELS: Readonly<Record<StudyPersona, string>> = {
  "first-time-buyer": "First-time buyer",
  investor: "Investor",
  upgrader: "Upgrader",
};

export type StudyAudience = StudyPersona | "all-personas" | "all";

export interface StudyFilters {
  query: string;
  category: StudyCategory | "all";
  audience: StudyAudience;
}

export const DEFAULT_STUDY_FILTERS: StudyFilters = {
  query: "",
  category: "all",
  audience: "all",
};

function matchesQuery(study: StudyCardData, query: string): boolean {
  const needle = query.trim().toLowerCase();
  if (needle === "") return true;
  return (
    study.title.toLowerCase().includes(needle) ||
    study.description.toLowerCase().includes(needle) ||
    study.slug.toLowerCase().includes(needle)
  );
}

function matchesAudience(
  study: StudyCardData,
  audience: StudyAudience,
): boolean {
  if (audience === "all") return true;
  if (audience === "all-personas") return study.personas.length > 0;
  return study.personas.includes(audience);
}

/** Apply the library filters. Order is preserved (the page sorts first). */
export function filterStudies(
  studies: readonly StudyCardData[],
  filters: StudyFilters,
): StudyCardData[] {
  return studies.filter(
    (study) =>
      matchesQuery(study, filters.query) &&
      (filters.category === "all" || study.category === filters.category) &&
      matchesAudience(study, filters.audience),
  );
}

/** True when any filter narrows the library. */
export function filtersAreActive(filters: StudyFilters): boolean {
  return (
    filters.query.trim() !== "" ||
    filters.category !== "all" ||
    filters.audience !== "all"
  );
}

/**
 * Evidence status for a study slug.
 *
 * `lease-decay` carries a documented per-square-metre / per-square-foot
 * mismatch in its source tables, so its charts are withheld until units and
 * discount arithmetic are reconciled (feature-specifications "Studies").
 * Every other study is published research whose observation period and units
 * should be read in the study body; that is a caution, not a defect claim.
 */
export interface StudyEvidence {
  unitReview: boolean;
  chartsWithheld: boolean;
  note: string;
}

const LEASE_DECAY_EVIDENCE: StudyEvidence = {
  unitReview: true,
  chartsWithheld: true,
  note: "Unit review required: one source table labels a per-square-metre statistic as “Median PSF”. The tables stay readable, but no chart is drawn from them until units and discount arithmetic are reconciled.",
};

const DEFAULT_EVIDENCE: StudyEvidence = {
  unitReview: false,
  chartsWithheld: false,
  note: "Published research: read the observation period and units in the study body. Tables are charted only where the author opted in with a chart marker.",
};

export function studyEvidence(slug: string): StudyEvidence {
  return slug === "lease-decay" ? LEASE_DECAY_EVIDENCE : DEFAULT_EVIDENCE;
}
