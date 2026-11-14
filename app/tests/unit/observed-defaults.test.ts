/**
 * Unit tests for the D03 bare-URL default resolver
 * (src/utils/observed-defaults.ts).
 *
 * Hermetic: a miniature pack parsed by the real contract validator. The point
 * of these cases is that a disabled switch or an absent pack can only mean
 * "keep the legacy default" — never an invented or guessed window.
 */

import { describe, expect, test } from "bun:test";

import { resolveObservedRouteDefault } from "../../src/utils/observed-defaults";
import {
  V2_SCHEMA_VERSION,
  parsePeriodPack,
  type PeriodPack,
} from "../../src/utils/observed-periods";

const PERIODS = {
  schemaVersion: V2_SCHEMA_VERSION,
  cutoffMonth: "2026-10",
  cutoffSource: "test",
  methodVersion: "test-1",
  periods: [
    {
      id: "month_2026_10",
      kind: "month",
      startMonth: "2026-10",
      endMonth: "2026-10",
      months: ["2026-10"],
      label: "2026-10 (one month)",
      comparatorId: null,
    },
    {
      id: "ttm_2026_10",
      kind: "ttm",
      startMonth: "2025-11",
      endMonth: "2026-10",
      months: [
        "2025-11",
        "2025-12",
        "2026-01",
        "2026-02",
        "2026-03",
        "2026-04",
        "2026-05",
        "2026-06",
        "2026-07",
        "2026-08",
        "2026-09",
        "2026-10",
      ],
      label: "12 months to 2026-10",
      comparatorId: null,
    },
  ],
};

const SUMMARY = {
  schemaVersion: V2_SCHEMA_VERSION,
  cutoffMonth: "2026-10",
  cutoffSource: "test",
  methodVersion: "test-1",
  observations: [],
};

function loadPack(): PeriodPack {
  const parsed = parsePeriodPack(PERIODS, SUMMARY);
  if (!parsed.ok) throw new Error(parsed.errors.join("; "));
  return parsed.pack;
}

const PACK = loadPack();

describe("resolveObservedRouteDefault", () => {
  test("keeps the legacy default while the release switch is off", () => {
    expect(
      resolveObservedRouteDefault({ v2Enabled: false, pack: PACK }),
    ).toBeNull();
  });

  test("never invents a default without a verified pack", () => {
    expect(
      resolveObservedRouteDefault({ v2Enabled: true, pack: null }),
    ).toBeNull();
  });

  test("resolves D03's trailing-12-month window when v2 is enabled", () => {
    expect(
      resolveObservedRouteDefault({ v2Enabled: true, pack: PACK }),
    ).toEqual({
      periodId: "ttm_2026_10",
      label: "12 months to 2026-10",
    });
  });

  test("resolves another alias through the same pack", () => {
    expect(
      resolveObservedRouteDefault({
        v2Enabled: true,
        pack: PACK,
        alias: "latest",
      }),
    ).toEqual({ periodId: "month_2026_10", label: "2026-10 (one month)" });
  });

  test("a pack without that window yields no default, not a nearby one", () => {
    const withoutTtm = parsePeriodPack(
      { ...PERIODS, periods: PERIODS.periods.slice(0, 1) },
      SUMMARY,
    );
    if (!withoutTtm.ok) throw new Error("fixture should parse");

    expect(
      resolveObservedRouteDefault({ v2Enabled: true, pack: withoutTtm.pack }),
    ).toBeNull();
  });
});
