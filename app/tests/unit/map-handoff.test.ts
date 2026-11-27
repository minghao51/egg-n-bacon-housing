/**
 * Unit tests for the research-map → `/explore` handoff (WS-B2, UI-3).
 *
 * The reproduced defect: `?area=TAMPINES&metric=median_price&timeBasis=pre_covid&propertyType=condo`
 * handed off as `/explore?area=TAMPINES&metric=median_price`, so the explorer
 * silently compared HDB/2025 instead of condo/pre-COVID. The round-trip test
 * below walks every (property, period, metric) combination the map can be in,
 * so a dropped or renamed field can never pass silently.
 */

import { describe, expect, test } from "bun:test";

import {
  EXPLORER_METRIC_FOR_MAP_METRIC,
  EXPLORER_PERIOD_FOR_MAP_TIME_BASIS,
  EXPLORER_PROPERTY_FOR_MAP_TYPE,
  HANDOFF_FALLBACK_METRIC,
  MAP_METRIC_LABELS,
  buildMapHandoff,
  explorerSelectionForMapScope,
  type MapScope,
} from "../../src/components/dashboard/map/lib/handoff";
import {
  EXPLORER_METRICS,
  parseExplorerSelection,
} from "../../src/utils/explorer-selection";
import {
  MAP_METRICS,
  MAP_PROPERTY_TYPES,
  MAP_TIME_BASES,
} from "../../src/utils/map-url-state";

/** Every metric the map selector offers, with the explorer equivalent or none. */
function supportedMetrics() {
  return MAP_METRICS.filter(
    (metric) => EXPLORER_METRIC_FOR_MAP_METRIC[metric] !== null,
  );
}

function queryParams(scope: MapScope): URLSearchParams {
  return new URLSearchParams(buildMapHandoff(scope).query);
}

const TAMPINES_SCOPE: MapScope = {
  area: "TAMPINES",
  metric: "median_price",
  timeBasis: "pre_covid",
  propertyType: "condo",
};

describe("buildMapHandoff — the reported defect", () => {
  test("keeps property type and period, not just area and metric", () => {
    const handoff = buildMapHandoff(TAMPINES_SCOPE);
    const params = new URLSearchParams(handoff.query);

    expect(params.get("area")).toBe("TAMPINES");
    expect(params.get("property")).toBe("condo");
    expect(params.get("period")).toBe("pre_covid");
    // `metric=median_price` is the explorer's default, and the explorer's own
    // serializer omits defaults; parsing is what proves the scope survived.
    const destination = parseExplorerSelection(handoff.query);
    expect(destination.metric).toBe("median_price");
    expect(destination.property).toBe("condo");
    expect(destination.period).toBe("pre_covid");
    expect(destination.area).toBe("TAMPINES");
  });

  test("the destination never resolves to a different property or period", () => {
    // The pre-fix link dropped both fields, so the explorer fell back to
    // property=hdb / period=year_2025. Neither may ever appear here.
    const destination = parseExplorerSelection(
      buildMapHandoff(TAMPINES_SCOPE).query,
    );

    expect(destination.property).not.toBe("hdb");
    expect(destination.period).not.toBe("year_2025");
  });

  test("uses only the explorer's own query vocabulary", () => {
    const params = queryParams(TAMPINES_SCOPE);
    const allowed = new Set([
      "area",
      "metric",
      "property",
      "period",
      "sort",
      "direction",
      "minSales",
      "search",
      "page",
    ]);

    for (const key of params.keys()) {
      expect(allowed.has(key)).toBe(true);
    }
  });
});

describe("buildMapHandoff — round trip for every combination", () => {
  test("every (property, period, supported metric) survives the handoff", () => {
    let combinations = 0;

    for (const propertyType of MAP_PROPERTY_TYPES) {
      for (const timeBasis of MAP_TIME_BASES) {
        for (const metric of supportedMetrics()) {
          const scope: MapScope = {
            area: "BISHAN",
            metric,
            timeBasis,
            propertyType,
          };
          const handoff = buildMapHandoff(scope);
          const destination = parseExplorerSelection(handoff.query);

          expect(destination.area).toBe("BISHAN");
          expect(destination.property).toBe(
            EXPLORER_PROPERTY_FOR_MAP_TYPE[propertyType],
          );
          expect(destination.period).toBe(
            EXPLORER_PERIOD_FOR_MAP_TIME_BASIS[timeBasis],
          );
          expect(destination.metric).toBe(
            EXPLORER_METRIC_FOR_MAP_METRIC[metric],
          );

          // A supported metric is never substituted, so there is nothing to
          // disclose beside the link.
          expect(handoff.metricSubstituted).toBe(false);
          expect(handoff.note).toBeNull();

          combinations += 1;
        }
      }
    }

    // 4 properties x 4 periods x 3 supported metrics.
    expect(combinations).toBe(4 * 4 * 3);
  });

  test("every (property, period, unsupported metric) discloses the fallback", () => {
    const unsupported = MAP_METRICS.filter(
      (metric) => EXPLORER_METRIC_FOR_MAP_METRIC[metric] === null,
    );
    expect(unsupported).toEqual([
      "rental_yield_median",
      "yoy_change_pct",
      "affordability_ratio",
    ]);

    for (const propertyType of MAP_PROPERTY_TYPES) {
      for (const timeBasis of MAP_TIME_BASES) {
        for (const metric of unsupported) {
          const handoff = buildMapHandoff({
            area: "BISHAN",
            metric,
            timeBasis,
            propertyType,
          });
          const destination = parseExplorerSelection(handoff.query);

          // The choice is explicit, named, and never silent.
          expect(handoff.metricSubstituted).toBe(true);
          expect(handoff.requestedMetric).toBe(metric);
          expect(handoff.appliedMetric).toBe(HANDOFF_FALLBACK_METRIC);
          expect(destination.metric).toBe(HANDOFF_FALLBACK_METRIC);

          // ... and the disclosure names what the map shows, what the
          // explorer will show, and that they differ.
          expect(handoff.note).not.toBeNull();
          expect(handoff.note).toContain(MAP_METRIC_LABELS[metric]);
          expect(handoff.note).toContain(
            MAP_METRIC_LABELS[HANDOFF_FALLBACK_METRIC],
          );
          expect(handoff.note).toContain(
            "has no observed-comparison equivalent",
          );

          // The scope that *can* be preserved still is.
          expect(destination.property).toBe(
            EXPLORER_PROPERTY_FOR_MAP_TYPE[propertyType],
          );
          expect(destination.period).toBe(
            EXPLORER_PERIOD_FOR_MAP_TIME_BASIS[timeBasis],
          );
        }
      }
    }
  });

  test("the fallback metric is one the explorer actually compares", () => {
    expect(EXPLORER_METRICS).toContain(HANDOFF_FALLBACK_METRIC);
  });
});

describe("buildMapHandoff — period pinning", () => {
  test("the era is always written, even when it is the legacy default", () => {
    // Under `PUBLIC_OBSERVED_RELEASE=v2` the explorer's bare URL opens a
    // published window, so an omitted period would silently change eras.
    for (const timeBasis of MAP_TIME_BASES) {
      const params = queryParams({
        area: "BISHAN",
        metric: "median_price",
        timeBasis,
        propertyType: "hdb",
      });

      expect(params.get("period")).toBe(timeBasis);
    }
  });

  test("a pinned legacy era cannot be re-resolved onto a pack window", () => {
    const destination = parseExplorerSelection(
      buildMapHandoff({ ...TAMPINES_SCOPE, timeBasis: "year_2025" }).query,
    );

    expect(destination.period).toBe("year_2025");
  });
});

describe("buildMapHandoff — area handling", () => {
  test("no area selected omits the parameter rather than writing an empty one", () => {
    const handoff = buildMapHandoff({ ...TAMPINES_SCOPE, area: null });

    expect(new URLSearchParams(handoff.query).has("area")).toBe(false);
    expect(handoff.query).not.toContain("area=");
    expect(parseExplorerSelection(handoff.query).area).toBeNull();
  });

  test("area names are canonicalised and round-trip through encoding", () => {
    for (const rawArea of ["tampines", "  Tampines  ", "ANG MO KIO"]) {
      const handoff = buildMapHandoff({ ...TAMPINES_SCOPE, area: rawArea });
      const destination = parseExplorerSelection(handoff.query);

      expect(destination.area).toBe(rawArea.trim().toUpperCase());
    }
  });
});

describe("buildMapHandoff — path shape", () => {
  test("produces an /explore path with the query appended", () => {
    const handoff = buildMapHandoff(TAMPINES_SCOPE);

    expect(handoff.path.startsWith("explore?")).toBe(true);
    expect(handoff.path).toBe(`explore?${handoff.query}`);
    expect(handoff.path).not.toContain("//");
    expect(handoff.path).not.toContain("?&");
  });

  test("a default-everything scope still yields a valid path", () => {
    const handoff = buildMapHandoff({
      area: null,
      metric: "median_price",
      timeBasis: "year_2025",
      propertyType: "hdb",
    });

    // Only the pinned period is written; everything else equals the explorer's
    // default, so the explorer's serializer omits it.
    expect(handoff.query).toBe("period=year_2025");
    expect(handoff.path).toBe("explore?period=year_2025");
  });
});

describe("explorerSelectionForMapScope", () => {
  test("maps property and period one-to-one", () => {
    for (const propertyType of MAP_PROPERTY_TYPES) {
      for (const timeBasis of MAP_TIME_BASES) {
        const selection = explorerSelectionForMapScope({
          area: null,
          metric: "volume",
          timeBasis,
          propertyType,
        });

        expect(selection.property).toBe(propertyType);
        expect(selection.period).toBe(timeBasis);
        expect(selection.metric).toBe("volume");
      }
    }
  });

  test("keeps the explorer's other defaults untouched", () => {
    const selection = explorerSelectionForMapScope(TAMPINES_SCOPE);

    expect(selection.direction).toBe("asc");
    expect(selection.search).toBe("");
    expect(selection.page).toBe(1);
  });
});
