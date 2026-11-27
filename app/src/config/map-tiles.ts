/**
 * Basemap configuration for every Leaflet map in the app.
 *
 * Before this module the raster URL was copy-pasted into three components
 * (`PriceMap`, `LeaderboardMap`, `SegmentAreaMap`), so a key or a provider
 * change meant three edits and `PriceMap` had already drifted: it credited only
 * OpenStreetMap while the other two also credited CARTO, whose basemap terms
 * require the attribution.
 *
 * ## Supplying a CARTO key
 *
 * Both values are read from `import.meta.env`, i.e. **build time**. Astro only
 * exposes variables to browser code when they are `PUBLIC_`-prefixed, so a key
 * supplied under any other name silently never reaches the map.
 *
 * 1. `.env` at the repository root (the same file the Python pipeline reads —
 *    `astro.config.mjs` sets `envDir: ".."` so there is only one env file):
 *
 *    ```
 *    PUBLIC_CARTO_API_KEY=your_token
 *    ```
 *
 * 2. CI and the GitHub Pages deploy build from `dist`, so the value must also be
 *    present there — set it as a repository variable/secret and export it in the
 *    workflow that runs `bun run build`.
 *
 * ## What the key does and does not protect
 *
 * A `PUBLIC_`-prefixed value is **inlined into the client bundle**: it is public
 * by construction and must be a domain-restricted, publishable token — never a
 * secret with account or billing scope. If the provider only issues
 * account-scoped tokens for the endpoint you want, restrict the token to this
 * site's origin or front the tiles with a proxy rather than shipping it.
 *
 * `PUBLIC_MAP_TILES_URL` overrides the whole template for a different provider
 * or for a keyed endpoint whose shape is not "append `api_key`". When it is
 * unset the keyless CARTO basemaps endpoint is used and no key is appended.
 */

/** Environment variable names this module reads. */
export const MAP_TILES_ENV = {
  url: "PUBLIC_MAP_TILES_URL",
  apiKey: "PUBLIC_CARTO_API_KEY",
} as const;

/** Keyless CARTO basemaps endpoint: free with attribution, rate-limited. */
export const DEFAULT_MAP_TILES_URL =
  "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png";

/**
 * Required attribution: OpenStreetMap for the data, CARTO for the basemap.
 *
 * Leaflet injects this as HTML into the attribution control, so it carries
 * anchors; it is a constant here, never interpolated input.
 */
export const MAP_TILES_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors ' +
  '&copy; <a href="https://carto.com/attributions">CARTO</a>';

/** Trimmed string, or `null` when the value is absent/blank/non-string. */
function configured(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed === "" ? null : trimmed;
}

const envUrl: unknown = import.meta.env?.PUBLIC_MAP_TILES_URL;
const envKey: unknown = import.meta.env?.PUBLIC_CARTO_API_KEY;

/**
 * The tile template every map should use.
 *
 * A configured `PUBLIC_MAP_TILES_URL` wins outright (it may already carry its
 * own credentials). Otherwise the default endpoint is used, and
 * `PUBLIC_CARTO_API_KEY` — when set — is appended as `api_key`.
 */
export const MAP_TILES_URL: string = (() => {
  const base = configured(envUrl) ?? DEFAULT_MAP_TILES_URL;
  const key = configured(envKey);
  if (key === null) return base;
  const separator = base.includes("?") ? "&" : "?";
  return `${base}${separator}api_key=${encodeURIComponent(key)}`;
})();

/** Whether a key was supplied, for the map legend/debug surfaces. */
export const HAS_MAP_API_KEY: boolean = configured(envKey) !== null;
