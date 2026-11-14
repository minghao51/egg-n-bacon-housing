/**
 * D03's bare-URL defaults for the observed routes, resolved against the verified
 * pack and gated by the release switch.
 *
 * The contract (§5.3) is explicit that changing a bare-URL default is a
 * migration, not a side effect: the route must show the exact window that is
 * active and offer a link to the window it used to open on. This module decides
 * *which* window that is; each page owns its previous-window link because the
 * query vocabulary differs per route (`?period=` vs `?timeBasis=`).
 *
 * Pure: no React, no DOM, no clock. A missing pack or a disabled switch returns
 * `null`, which means "keep the legacy default" — never "invent a window".
 */

import {
  resolvePeriodAlias,
  type PeriodAlias,
  type PeriodPack,
} from "@/utils/observed-periods";

export interface ObservedRouteDefault {
  /** Concrete period id the bare route opens on, e.g. `ttm_2026_10`. */
  periodId: string;
  /** Human label for that window, e.g. "12 months to 2026-10". */
  label: string;
}

/** The window a route used to open on, with the query that still reaches it. */
export interface PreviousRouteDefault {
  label: string;
  /** Query string (no leading `?`) that selects the previous window. */
  query: string;
}

/**
 * Resolve the route default for one observed surface.
 *
 * `v2Enabled` is the build-time `PUBLIC_OBSERVED_RELEASE` switch: while it is
 * `legacy`, every route keeps its existing default and no migration notice is
 * shown. When it is `v2`, the route opens on D03's alias for that surface,
 * resolved through the loaded pack so a stale pack cannot look fresher than it
 * is.
 */
export function resolveObservedRouteDefault(input: {
  v2Enabled: boolean;
  pack: PeriodPack | null;
  alias?: PeriodAlias;
}): ObservedRouteDefault | null {
  if (!input.v2Enabled) return null;
  if (input.pack === null) return null;

  const period = resolvePeriodAlias(input.pack, input.alias ?? "ttm");
  if (period === null) return null;
  return { periodId: period.id, label: period.label };
}
