/**
 * The shell's navigation model: four primary destinations — Overview ·
 * Explore · Research · Data & methods — and the one shared research subnav,
 * as specified by `assets/svg/07-information-architecture.svg`.
 *
 * Hrefs are stored **bare** (no leading slash, no deployment base), exactly
 * like `constants/dashboard-nav.ts`. `import.meta.env.BASE_URL` is not
 * readable from a plain module outside the Astro/Vite module graph, so every
 * caller prefixes the base at the use site:
 *
 *     const href = `${import.meta.env.BASE_URL}${destination.href}`;
 *
 * The empty `href` for Overview is deliberate: it resolves to the site root
 * under `/` and under `/egg-n-bacon-housing/` alike.
 *
 * This module is data only. Matching lives in `nav-match.ts` (one
 * implementation, shared by `PrimaryNav.astro`, `ResearchSubNav.astro` and
 * `Sidebar.astro`).
 */

export type DestinationKey = "overview" | "explore" | "research" | "data";

export interface Destination {
  key: DestinationKey;
  label: string;
  description: string;
  href: string;
}

export const DESTINATIONS: Destination[] = [
  {
    key: "overview",
    label: "Overview",
    description:
      "The national picture on one page, with the sources behind it.",
    href: "",
  },
  {
    key: "explore",
    label: "Explore",
    description:
      "Planning areas side by side on one year and property type, with sales counts.",
    href: "explore",
  },
  {
    key: "research",
    label: "Research",
    description:
      "Published studies, trends, segments, tools and the archived research map.",
    // The Studies library is the research landing page today.
    href: "analytics/",
  },
  {
    key: "data",
    label: "Data & methods",
    description: "Catalog layers, schema, lineage and freshness.",
    // The provenance guide now exists at `/data`: it reports the observation
    // period, coverage and export time of each published asset, and links on
    // to `/catalog/` for the per-dataset view rather than replacing it.
    href: "data",
  },
];

export type ResearchSubNavKey =
  | "studies"
  | "trends"
  | "segments"
  | "tools"
  | "map";

export interface ResearchSubNavItem {
  key: ResearchSubNavKey;
  label: string;
  href: string;
}

/** The single research subnav, rendered by `ResearchSubNav.astro` only. */
export const RESEARCH_SUBNAV: ResearchSubNavItem[] = [
  { key: "studies", label: "Studies", href: "analytics/" },
  { key: "trends", label: "Trends", href: "research/trends" },
  { key: "segments", label: "Segments", href: "research/segments" },
  { key: "tools", label: "Tools", href: "research/tools" },
  { key: "map", label: "Research map", href: "research/map" },
];
