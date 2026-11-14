/**
 * Which observed release the UI reads.
 *
 * The v2 pack is additive: it ships alongside the v1 release, and nothing
 * switches until this selector says so. Rollout order (plan §5.5):
 *
 *   1. parser and loader deployed with `legacy` — absent v2 is a normal state;
 *   2. pack staged and verified outside the published directory;
 *   3. immutable payloads + manifest published, deployed bytes verified;
 *   4. `PUBLIC_OBSERVED_RELEASE=v2` for one build, all observed surfaces
 *      switched together in that build.
 *
 * A missing or invalid v2 pack never silently falls back to v1 numbers: the
 * loader reports `absent`/`invalid` and the surface decides what to show.
 */

export type ObservedReleaseMode = "legacy" | "v2";

export const OBSERVED_RELEASE_ENV = "PUBLIC_OBSERVED_RELEASE";

/** Read the build-time switch. Defaults to the legacy release. */
export function resolveObservedReleaseMode(
  raw: unknown = import.meta.env?.PUBLIC_OBSERVED_RELEASE,
): ObservedReleaseMode {
  return raw === "v2" ? "v2" : "legacy";
}

export const OBSERVED_RELEASE_MODE: ObservedReleaseMode =
  resolveObservedReleaseMode();

export function isObservedV2Enabled(): boolean {
  return OBSERVED_RELEASE_MODE === "v2";
}
