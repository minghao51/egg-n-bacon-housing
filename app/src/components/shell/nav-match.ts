/**
 * The **single** implementation of navigation matching.
 *
 * `PrimaryNav.astro`, `ResearchSubNav.astro` and `Sidebar.astro` all import
 * from here, so `aria-current` and the active visual treatment can never
 * disagree about what a path belongs to.
 *
 * `Astro.url.pathname` carries the deployment base (`/egg-n-bacon-housing/
 * dashboard/map`) while hrefs are built as `${BASE_URL}${barePath}`. Both
 * sides are normalised once — leading slash, no trailing slash, root stays
 * `/` — by `stripBase`, which every caller runs before matching.
 *
 * The base is passed in rather than read from `import.meta.env` because this
 * is a plain module: the use site (an `.astro` file) owns the base, following
 * the convention in `constants/dashboard-nav.ts`.
 */

/** Leading slash, no trailing slash; the root stays `/`. */
function normalizePath(path: string): string {
  const withLeadingSlash = path.startsWith("/") ? path : `/${path}`;
  return withLeadingSlash.replace(/\/+$/, "") || "/";
}

/**
 * Remove the deployment base from a pathname and normalise it.
 *
 * `("/egg-n-bacon-housing/analytics/", "/egg-n-bacon-housing/")` → `"/analytics"`.
 * A path that does not carry the base is normalised as-is, so the helpers also
 * work in a plain `/` deployment.
 */
export function stripBase(pathname: string, base: string): string {
  if (!pathname) return "/";
  // A base without a trailing slash must not produce a doubled `//` path.
  const baseWithoutSlash = base.replace(/\/+$/, "");
  // Strip only on a path boundary: a base of `/egg` must not match
  // `/eggs-and-things`, only `/egg` itself or `/egg/...`.
  const carriesBase =
    baseWithoutSlash.length > 0 &&
    (pathname === baseWithoutSlash ||
      pathname.startsWith(`${baseWithoutSlash}/`));
  const withoutBase = carriesBase
    ? pathname.slice(baseWithoutSlash.length)
    : pathname;
  return normalizePath(withoutBase);
}

/** The bare path an href points at, deployment base removed. */
export function hrefPath(href: string, base: string): string {
  return stripBase(href, base);
}

/**
 * Is `path` inside the destination `href` points at? Used for the active
 * visual treatment, so a section root also matches its child pages.
 *
 * - Overview (`/`) matches only the exact root; every other path would match
 *   it by prefix.
 * - A dashboard link such as `/dashboard/leaderboard` matches its own page
 *   only, since `/dashboard` is a page that also parents other pages.
 * - Section roots (`analytics/`, `research/`, `catalog/`) prefix-match,
 *   tolerant of a missing trailing slash on either side (`trailingSlash:
 *   "ignore"`).
 */
export function isActive(path: string, href: string, base: string): boolean {
  if (!path) return false;
  const pathname = normalizePath(path);
  const target = hrefPath(href, base);

  if (target === "/") return pathname === "/";
  if (target.startsWith("/dashboard/")) return pathname === target;
  return pathname === target || pathname.startsWith(`${target}/`);
}

/**
 * May this link carry `aria-current="page"`?
 *
 * `isActive` also matches section roots, so several links can share the active
 * visual treatment; only the page's own destination may be the current page.
 * Section roots therefore pass `exactOnly = true`, while deeper destinations
 * keep the prefix rule (a dataset page under `/catalog/<layer>/…` still
 * belongs to its layer link).
 */
export function isCurrentPage(
  path: string,
  href: string,
  base: string,
  exactOnly = false,
): boolean {
  if (!isActive(path, href, base)) return false;
  if (!exactOnly) return true;
  return normalizePath(path) === hrefPath(href, base);
}

/**
 * Research owns two path prefixes: the Studies library under `analytics/` and
 * the pilot workspaces under `research/`. The subnav is shown for both, and
 * the Research destination is current for both.
 */
export function isResearchPath(path: string): boolean {
  const pathname = normalizePath(path);
  return (
    pathname === "/analytics" ||
    pathname.startsWith("/analytics/") ||
    pathname === "/research" ||
    pathname.startsWith("/research/")
  );
}

/** What an anchor may report through `aria-current`. */
export type AriaCurrent = "page" | "location" | undefined;

/**
 * The shell's one `aria-current` rule for a **primary destination**.
 *
 * A page may carry exactly one `aria-current="page"`, and it must be the most
 * specific current link. A destination is therefore `"page"` only when the
 * reader is on that destination's own landing route *and* no section-subnav
 * link (a research item, a catalog layer, a dashboard item) is also current.
 * Otherwise it is `"location"`, which still tells assistive technology which
 * section the reader is inside, while the subnav link keeps `"page"`.
 *
 * `active` is the destination's own predicate (it may cover more than one path
 * prefix, as Research does for `/analytics/` and `/research/*`), and
 * `exactLandingRoute` says the reader is on the landing route itself.
 */
export function destinationAriaCurrent(
  active: boolean,
  exactLandingRoute: boolean,
  sectionHasCurrentLink: boolean,
): AriaCurrent {
  if (!active) return undefined;
  return exactLandingRoute && !sectionHasCurrentLink ? "page" : "location";
}
