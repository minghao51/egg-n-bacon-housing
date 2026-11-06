/**
 * Unit tests for the S9 research-map archive contract
 * (src/utils/map-archive.ts).
 *
 * Reads the **published** analytics extracts, so the pinned archive facts fail
 * loudly if the assets change: nine retained layer IDs, 41 archived areas,
 * Bishan's STABLE / z 0 / p 1 placeholders, the past forecast target, and
 * group-isolated load failures.
 */

import { describe, expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import { gunzipSync } from "node:zlib";

import { LAYER_METADATA } from "../../src/types/analytics";
import {
  ARCHIVE_LAYER_IDS,
  ARCHIVE_LAYER_SOURCES,
  archiveLayerStatuses,
  inspectArchiveArea,
  observedLegend,
  type AnalyticsGroupState,
} from "../../src/utils/map-archive";

function readAsset(name: string): unknown {
  const path = `../../public/data/analytics/${name}.json.gz`;
  return JSON.parse(
    gunzipSync(readFileSync(new URL(path, import.meta.url))).toString("utf-8"),
  );
}

const spatial = readAsset("spatial_analysis");
const feature = readAsset("feature_impact");
const predictive = readAsset("predictive_analytics");

function available(data: unknown): AnalyticsGroupState {
  return { data, loading: false, error: null };
}

const ALL_READY = {
  spatial: available(spatial),
  feature: available(feature),
  predictive: available(predictive),
};

describe("retained layer IDs", () => {
  test("exactly the nine published layer IDs are declared", () => {
    expect(ARCHIVE_LAYER_IDS).toHaveLength(9);
    expect(new Set(ARCHIVE_LAYER_IDS)).toEqual(
      new Set(Object.keys(LAYER_METADATA)),
    );
  });

  test("every layer names its asset, units and gate", () => {
    for (const layerId of ARCHIVE_LAYER_IDS) {
      const source = ARCHIVE_LAYER_SOURCES[layerId];
      expect(source.asset.endsWith(".json.gz")).toBe(true);
      expect(source.unit.length).toBeGreaterThan(3);
      expect(source.gate.length).toBeGreaterThan(10);
    }
  });
});

describe("per-layer status", () => {
  test("all nine are ready when every group loaded", () => {
    const statuses = archiveLayerStatuses(ALL_READY);
    for (const layerId of ARCHIVE_LAYER_IDS) {
      expect(statuses[layerId].state).toBe("available");
    }
  });

  test("a spatial failure marks only the spatial layers", () => {
    const statuses = archiveLayerStatuses({
      ...ALL_READY,
      spatial: {
        data: null,
        loading: false,
        error: "analytics/spatial_analysis.json.gz could not be read",
      },
    });
    expect(statuses["spatial.hotspot"].state).toBe("error");
    expect(statuses["spatial.lisa"].state).toBe("error");
    expect(statuses["spatial.neighborhood"].state).toBe("error");
    expect(statuses["feature.mrt"].state).toBe("available");
    expect(statuses["predictive.forecast"].state).toBe("available");
    expect(statuses["spatial.lisa"].detail).toContain("could not be read");
  });

  test("a pending group reports loading, not an empty value", () => {
    const statuses = archiveLayerStatuses({
      ...ALL_READY,
      predictive: { data: null, loading: true, error: null },
    });
    expect(statuses["predictive.policy"].state).toBe("loading");
    expect(statuses["predictive.forecast"].detail).toContain("Loading");
  });
});

describe("archive inspection", () => {
  test("Bishan exposes the stored placeholders for active layers", () => {
    const inspection = inspectArchiveArea({
      spatial,
      feature,
      predictive,
      selectedArea: "bishan",
      activeLayers: ["spatial.hotspot", "spatial.lisa", "spatial.neighborhood"],
      mapFeatureCount: 55,
    });

    expect(inspection.areaId).toBe("BISHAN");
    expect(inspection.rows).toHaveLength(3);
    const hotspot = inspection.rows[0].values;
    expect(
      hotspot.find((value) => value.label === "Stored z-score")?.value,
    ).toBe("0.00");
    expect(
      hotspot.find((value) => value.label === "Stored p-value")?.value,
    ).toBe("1.00");
    const lisa = inspection.rows[1].values;
    expect(
      lisa.find((value) => value.label === "Stored LISA class")?.value,
    ).toBe("STABLE");
    expect(inspection.coverage).toEqual({
      archivedAreas: 41,
      mapFeatures: 55,
    });
    // Uniform placeholder warning is computed from the asset, not hardcoded.
    expect(inspection.warnings.join(" ")).toContain(
      "All 41 archived areas share the same stored spatial pattern",
    );
  });

  test("the archived forecast keeps its past target and signal labels", () => {
    const inspection = inspectArchiveArea({
      spatial,
      feature,
      predictive,
      selectedArea: "BISHAN",
      activeLayers: ["predictive.forecast"],
      mapFeatureCount: 55,
    });
    const values = inspection.rows[0].values;
    expect(
      values.find((value) => value.label === "Stored forecast target")?.value,
    ).toBe("2025-07-01");
    expect(
      values.find(
        (value) => value.label === "Stored signal (archive, not advice)",
      )?.value,
    ).toBe("BUY");
    // A past target is not relabelled current: it predates the extract
    // generation, and the published projected changes vary.
    expect(inspection.warnings.join(" ")).toContain("target 2025-07-01");
    expect(inspection.warnings.join(" ")).toContain("archived forecast");
    expect(inspection.warnings.join(" ")).not.toContain(
      "All 41 archived areas store the same projected change",
    );
  });

  test("does not call a pattern uniform while any claimed field varies", () => {
    const mixed = JSON.parse(JSON.stringify(spatial));
    const first = Object.values(
      mixed.planning_areas as Record<string, { hotspot: { p_value: number } }>,
    )[0];
    first.hotspot.p_value = 0.42;
    const inspection = inspectArchiveArea({
      spatial: mixed,
      feature,
      predictive,
      selectedArea: "BISHAN",
      activeLayers: ["spatial.hotspot", "spatial.lisa"],
      mapFeatureCount: 55,
    });
    expect(inspection.warnings.join(" ")).not.toContain(
      "share the same stored spatial pattern",
    );
  });

  test("warnings follow the active groups only", () => {
    const spatialOnly = inspectArchiveArea({
      spatial,
      feature,
      predictive,
      selectedArea: "BISHAN",
      activeLayers: ["spatial.lisa"],
      mapFeatureCount: 55,
    });
    expect(spatialOnly.warnings).toHaveLength(1);
    expect(spatialOnly.warnings[0]).toContain("spatial");

    const featureOnly = inspectArchiveArea({
      spatial,
      feature,
      predictive,
      selectedArea: "BISHAN",
      activeLayers: ["feature.school"],
      mapFeatureCount: 55,
    });
    expect(featureOnly.warnings).toHaveLength(1);
    expect(featureOnly.warnings[0]).toContain("school");
  });

  test("no selected area yields no rows and no invented value", () => {
    const inspection = inspectArchiveArea({
      spatial,
      feature,
      predictive,
      selectedArea: null,
      activeLayers: ARCHIVE_LAYER_IDS,
      mapFeatureCount: 55,
    });
    expect(inspection.areaId).toBeNull();
    expect(inspection.rows).toEqual([]);
    expect(inspection.warnings).toEqual([]);
  });

  test("an absent area is unavailable, not neutral", () => {
    const inspection = inspectArchiveArea({
      spatial,
      feature,
      predictive,
      selectedArea: "SUNGEI KADUT",
      activeLayers: ["spatial.lisa"],
      mapFeatureCount: 55,
    });
    expect(inspection.areaId).toBe("SUNGEI KADUT");
    expect(inspection.rows).toEqual([]);
    expect(inspection.warnings.join(" ")).toContain("unavailable, not a zero");
  });

  test("metadata names the source assets and generation times", () => {
    const inspection = inspectArchiveArea({
      spatial,
      feature,
      predictive,
      selectedArea: "BISHAN",
      activeLayers: ["predictive.policy"],
      mapFeatureCount: 55,
    });
    expect(inspection.metadata.map((meta) => meta.asset)).toEqual([
      "analytics/spatial_analysis.json.gz",
      "analytics/feature_impact.json.gz",
      "analytics/predictive_analytics.json.gz",
    ]);
    for (const meta of inspection.metadata) {
      expect(meta.generatedAt).not.toBeNull();
    }
    expect(inspection.metadata[2].extra).toContain("trained 2025-01-01");
  });
});

describe("observed legend", () => {
  test("names the quantity, unit, period and evidence status", () => {
    expect(observedLegend("median_price", "2025 complete year", "HDB")).toEqual(
      {
        quantity: "Median price",
        unit: "SGD",
        period: "2025 complete year · HDB",
        status: "Observed transactions",
      },
    );
    expect(observedLegend("volume", "All history", "All types").unit).toBe(
      "count",
    );
    expect(
      observedLegend("median_psf", "Through 2021", "Condominium").unit,
    ).toBe("SGD per square foot");
  });
});
