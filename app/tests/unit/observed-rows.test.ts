/**
 * Unit tests for the explorer row builder (src/utils/observed-rows.ts).
 *
 * Hermetic: the 31-area `year_2025_hdb` fixture below is a copy of the
 * published section's approved metrics, taken on 2026-11-02 from
 * `map_metrics.json.gz` in a real exporter run
 * (`uv run python scripts/export_app_data.py --output-dir /tmp/s5/manifest-fixture`)
 * with only `median_price`/`median_psf`/`volume` kept; the national baseline is
 * the matching `dashboard_overview.json.gz` `stats.year_2025_hdb` block
 * (628000 / 603 / 25084). No payload file is read at test time.
 */

import { describe, expect, test } from "bun:test";

import {
  buildExplorerDataset,
  type ExplorerRow,
} from "../../src/utils/observed-rows";
import {
  EXPLORER_DEFAULTS,
  withSelection,
  type ExplorerSelection,
} from "../../src/utils/explorer-selection";
import type {
  ObservedMetric,
  ObservedObservation,
} from "../../src/utils/observed-data";

/**
 * The published `map_metrics.json.gz` `year_2025_hdb` section, reduced to the
 * three approved metrics. 31 areas: 25 at or above 150 sales, 6 thin
 * (Bukit Timah 60, Changi 8, Downtown Core 6, Outram 105, Rochor 62, Tanglin 2).
 */
const YEAR_2025_HDB_JSON = `{
  "ANG MO KIO": {"median_price": 499000, "median_psf": 583, "volume": 971},
  "BEDOK": {"median_price": 548000, "median_psf": 591, "volume": 1208},
  "BISHAN": {"median_price": 849000, "median_psf": 756, "volume": 376},
  "BUKIT BATOK": {"median_price": 600000, "median_psf": 599, "volume": 1304},
  "BUKIT MERAH": {"median_price": 785000, "median_psf": 810, "volume": 933},
  "BUKIT PANJANG": {"median_price": 610000, "median_psf": 580, "volume": 798},
  "BUKIT TIMAH": {"median_price": 945500, "median_psf": 821, "volume": 60},
  "CHANGI": {"median_price": 360000, "median_psf": 502, "volume": 8},
  "CHOA CHU KANG": {"median_price": 592888, "median_psf": 513, "volume": 1027},
  "CLEMENTI": {"median_price": 590000, "median_psf": 621, "volume": 551},
  "DOWNTOWN CORE": {"median_price": 812500, "median_psf": 920, "volume": 6},
  "GEYLANG": {"median_price": 570000, "median_psf": 621, "volume": 638},
  "HOUGANG": {"median_price": 615000, "median_psf": 611, "volume": 1311},
  "JURONG EAST": {"median_price": 524000, "median_psf": 545, "volume": 482},
  "JURONG WEST": {"median_price": 568000, "median_psf": 521, "volume": 1591},
  "KALLANG": {"median_price": 761500, "median_psf": 742, "volume": 588},
  "MARINE PARADE": {"median_price": 539750, "median_psf": 685, "volume": 162},
  "NOVENA": {"median_price": 630000, "median_psf": 652, "volume": 201},
  "OUTRAM": {"median_price": 808000, "median_psf": 927, "volume": 105},
  "PASIR RIS": {"median_price": 715000, "median_psf": 555, "volume": 626},
  "PUNGGOL": {"median_price": 672000, "median_psf": 686, "volume": 1538},
  "QUEENSTOWN": {"median_price": 816888, "median_psf": 920, "volume": 599},
  "ROCHOR": {"median_price": 572500, "median_psf": 705, "volume": 62},
  "SEMBAWANG": {"median_price": 620000, "median_psf": 631, "volume": 1191},
  "SENGKANG": {"median_price": 660888, "median_psf": 641, "volume": 1905},
  "SERANGOON": {"median_price": 669444, "median_psf": 657, "volume": 404},
  "TAMPINES": {"median_price": 710000, "median_psf": 620, "volume": 1921},
  "TANGLIN": {"median_price": 810000, "median_psf": 694, "volume": 2},
  "TOA PAYOH": {"median_price": 785000, "median_psf": 727, "volume": 1063},
  "WOODLANDS": {"median_price": 590000, "median_psf": 531, "volume": 1748},
  "YISHUN": {"median_price": 547000, "median_psf": 577, "volume": 1703}
}`;

const YEAR_2025_HDB: unknown = JSON.parse(YEAR_2025_HDB_JSON);

/**
 * The joint 2025 HDB section plus the property-only (`hdb`), period-only
 * (`year_2025`) and other-joint sections the real asset also carries. Their
 * values are deliberately wrong so any fallback would be visible.
 */
const MAP_METRICS: unknown = {
  year_2025_hdb: YEAR_2025_HDB,
  hdb: { TAMPINES: { median_price: 1, median_psf: 1, volume: 1 } },
  year_2025: { TAMPINES: { median_price: 2, median_psf: 2, volume: 2 } },
  whole_hdb: { TAMPINES: { median_price: 3, median_psf: 3, volume: 3 } },
  year_2025_condo: {
    TAMPINES: { median_price: 999999, median_psf: 999, volume: 9 },
  },
};

const OVERVIEW_STATS: unknown = {
  metadata: { date_range: { start: "1990-01-01", end: "2026-10-31" } },
  stats: {
    year_2025_hdb: {
      count: 25084,
      median_price: 628000,
      median_psf: 603,
      volume: 25084,
    },
    hdb: { median_price: 111111, median_psf: 111, volume: 1 },
    year_2025: { median_price: 222222, median_psf: 222, volume: 2 },
  },
};

function selection(
  overrides: Partial<ExplorerSelection> = {},
): ExplorerSelection {
  return withSelection(EXPLORER_DEFAULTS, overrides);
}

function findRow(rows: ExplorerRow[], areaId: string): ExplorerRow {
  const row = rows.find((entry) => entry.areaId === areaId);
  if (row === undefined) throw new Error(`missing row for ${areaId}`);
  return row;
}

function metricOf(
  observations: ObservedObservation[],
  metric: ObservedMetric,
): number | null {
  const found = observations.find((entry) => entry.metric === metric);
  if (found === undefined) throw new Error(`missing metric ${metric}`);
  return found.value;
}

function ids(rows: ExplorerRow[]): string[] {
  return rows.map((row) => row.areaId);
}

const THIN_2025_HDB = [
  "BUKIT TIMAH",
  "CHANGI",
  "DOWNTOWN CORE",
  "OUTRAM",
  "ROCHOR",
  "TANGLIN",
];

describe("buildExplorerDataset — published 2025 HDB section", () => {
  const dataset = buildExplorerDataset({
    mapMetrics: MAP_METRICS,
    overviewStats: OVERVIEW_STATS,
    selection: selection(),
    baselineCompatible: true,
  });

  test("reads only the joint section", () => {
    expect(dataset.section).toBe("year_2025_hdb");
    expect(dataset.property).toBe("hdb");
    expect(dataset.period).toBe("year_2025");
    expect(dataset.totalAreas).toBe(31);
    expect(dataset.rows).toHaveLength(31);
  });

  test("Tampines 2025 HDB carries the published values", () => {
    const tampines = findRow(dataset.rows, "TAMPINES");

    expect(tampines.areaName).toBe("Tampines");
    expect(tampines.slug).toBe("tampines");
    expect(tampines.medianPrice).toBe(710000);
    expect(tampines.medianPsf).toBe(620);
    expect(tampines.volume).toBe(1921);
    expect(tampines.observation.section).toBe("year_2025_hdb");
    expect(tampines.observation.era).toBe("year_2025");
    expect(tampines.observation.propertyType).toBe("hdb");
  });

  test("keeps published values unrounded", () => {
    const marineParade = findRow(dataset.rows, "MARINE PARADE");
    const angMoKio = findRow(dataset.rows, "ANG MO KIO");

    expect(marineParade.medianPrice).toBe(539750);
    expect(marineParade.medianPsf).toBe(685);
    expect(marineParade.volume).toBe(162);
    expect(angMoKio.medianPrice).toBe(499000);
    expect(angMoKio.medianPsf).toBe(583);
    expect(angMoKio.volume).toBe(971);
  });

  test("the national baseline is the joint overview block, not the area mean", () => {
    const national = dataset.national;
    if (national === null) throw new Error("expected a national baseline");

    expect(metricOf(national, "median_price")).toBe(628000);
    expect(metricOf(national, "median_psf")).toBe(603);
    expect(metricOf(national, "volume")).toBe(25084);
    expect(national[0]?.source.asset).toBe("dashboard_overview");
    expect(national[0]?.source.section).toBe("year_2025_hdb");
    expect(dataset.baselineCompatible).toBe(true);
  });

  test("threshold 150 hides exactly the thin areas and counts them", () => {
    expect(dataset.thinCount).toBe(6);
    expect(dataset.filtered).toHaveLength(25);
    expect(dataset.totalAreas - dataset.filtered.length).toBe(
      dataset.thinCount,
    );

    for (const areaId of THIN_2025_HDB) {
      expect(ids(dataset.filtered)).not.toContain(areaId);
      expect(ids(dataset.rows)).toContain(areaId);
    }
    expect(ids(dataset.filtered)).toContain("MARINE PARADE");
    expect(ids(dataset.filtered)).toContain("NOVENA");
  });

  test("a higher threshold hides exactly the areas below it", () => {
    const stricter = buildExplorerDataset({
      mapMetrics: MAP_METRICS,
      overviewStats: OVERVIEW_STATS,
      selection: selection({ minSales: 200 }),
      baselineCompatible: true,
    });

    expect(stricter.thinCount).toBe(7);
    expect(stricter.filtered).toHaveLength(24);
    expect(ids(stricter.filtered)).not.toContain("MARINE PARADE");
    expect(ids(stricter.filtered)).toContain("NOVENA");
  });

  test("no threshold keeps every area and reports no thin rows", () => {
    const all = buildExplorerDataset({
      mapMetrics: MAP_METRICS,
      overviewStats: OVERVIEW_STATS,
      selection: selection({ minSales: null }),
      baselineCompatible: true,
    });

    expect(all.thinCount).toBe(0);
    expect(all.filtered).toHaveLength(31);
    expect(all.totalAreas).toBe(31);
  });

  test("search matches the display name case-insensitively", () => {
    const lower = buildExplorerDataset({
      mapMetrics: MAP_METRICS,
      overviewStats: OVERVIEW_STATS,
      selection: selection({ search: "tam" }),
      baselineCompatible: true,
    });
    const upper = buildExplorerDataset({
      mapMetrics: MAP_METRICS,
      overviewStats: OVERVIEW_STATS,
      selection: selection({ search: "TAMPINES" }),
      baselineCompatible: true,
    });

    expect(ids(lower.filtered)).toEqual(["TAMPINES"]);
    expect(ids(upper.filtered)).toEqual(["TAMPINES"]);
    expect(lower.totalAreas).toBe(31);
  });

  test("an incompatible baseline keeps the rows and withholds the baseline", () => {
    const incompatible = buildExplorerDataset({
      mapMetrics: MAP_METRICS,
      overviewStats: OVERVIEW_STATS,
      selection: selection(),
      baselineCompatible: false,
    });

    expect(incompatible.national).toBeNull();
    expect(incompatible.baselineCompatible).toBe(false);
    expect(incompatible.totalAreas).toBe(31);
    expect(findRow(incompatible.rows, "TAMPINES").medianPrice).toBe(710000);
  });
});

describe("buildExplorerDataset — no fallback sections", () => {
  const propertyOnlyAndPeriodOnly: unknown = {
    hdb: { TAMPINES: { median_price: 1, median_psf: 1, volume: 1 } },
    year_2025: { TAMPINES: { median_price: 2, median_psf: 2, volume: 2 } },
  };
  const overviewWithoutJoint: unknown = {
    stats: {
      hdb: { median_price: 111111, median_psf: 111, volume: 1 },
      year_2025: { median_price: 222222, median_psf: 222, volume: 2 },
    },
  };

  test("a missing joint section yields no rows and no baseline", () => {
    const dataset = buildExplorerDataset({
      mapMetrics: propertyOnlyAndPeriodOnly,
      overviewStats: overviewWithoutJoint,
      selection: selection(),
      baselineCompatible: true,
    });

    expect(dataset.section).toBe("year_2025_hdb");
    expect(dataset.rows).toHaveLength(0);
    expect(dataset.filtered).toHaveLength(0);
    expect(dataset.totalAreas).toBe(0);
    expect(dataset.thinCount).toBe(0);
    expect(dataset.national).toBeNull();
  });

  test("a property-only or period-only key never stands in for the joint section", () => {
    const dataset = buildExplorerDataset({
      mapMetrics: propertyOnlyAndPeriodOnly,
      overviewStats: overviewWithoutJoint,
      selection: selection(),
      baselineCompatible: true,
    });

    expect(dataset.rows).toHaveLength(0);
    expect(
      dataset.rows.find((row) => row.areaId === "TAMPINES"),
    ).toBeUndefined();
  });

  test("a non-object section is treated as missing", () => {
    const dataset = buildExplorerDataset({
      mapMetrics: { year_2025_hdb: "not a section" },
      overviewStats: overviewWithoutJoint,
      selection: selection(),
      baselineCompatible: false,
    });

    expect(dataset.rows).toHaveLength(0);
    expect(dataset.totalAreas).toBe(0);
  });
});

describe("buildExplorerDataset — missing metrics and ordering", () => {
  const sparse: unknown = {
    year_2025_hdb: {
      ALPHA: { median_price: 500000, median_psf: 600, volume: 200 },
      BRAVO: { median_price: 600000, median_psf: 700 },
      CHARLIE: { median_price: 400000, median_psf: 500, volume: 10 },
      DELTA: { median_price: 0, median_psf: 0, volume: 0 },
      ECHO: { median_price: 550000, volume: 250 },
    },
  };

  test("a row with a missing volume is kept and never counted thin", () => {
    const dataset = buildExplorerDataset({
      mapMetrics: sparse,
      overviewStats: OVERVIEW_STATS,
      selection: selection(),
      baselineCompatible: true,
    });

    const bravo = findRow(dataset.rows, "BRAVO");
    expect(bravo.volume).toBeNull();
    expect(bravo.medianPrice).toBe(600000);
    expect(bravo.medianPsf).toBe(700);

    expect(dataset.totalAreas).toBe(4);
    expect(dataset.thinCount).toBe(1);
    expect(ids(dataset.filtered)).toContain("BRAVO");
    expect(ids(dataset.filtered)).toContain("ECHO");
    expect(ids(dataset.filtered)).not.toContain("CHARLIE");
  });

  test("an area with no available metric is not a row", () => {
    const dataset = buildExplorerDataset({
      mapMetrics: sparse,
      overviewStats: OVERVIEW_STATS,
      selection: selection({ minSales: null }),
      baselineCompatible: false,
    });

    expect(ids(dataset.rows)).not.toContain("DELTA");
    expect(dataset.totalAreas).toBe(4);
    expect(dataset.national).toBeNull();
  });

  test("nulls sort last in both directions", () => {
    const ascPsf = buildExplorerDataset({
      mapMetrics: sparse,
      overviewStats: OVERVIEW_STATS,
      selection: selection({
        minSales: null,
        sort: "median_psf",
        direction: "asc",
      }),
      baselineCompatible: false,
    });
    const descPsf = buildExplorerDataset({
      mapMetrics: sparse,
      overviewStats: OVERVIEW_STATS,
      selection: selection({
        minSales: null,
        sort: "median_psf",
        direction: "desc",
      }),
      baselineCompatible: false,
    });
    const ascPrice = buildExplorerDataset({
      mapMetrics: sparse,
      overviewStats: OVERVIEW_STATS,
      selection: selection({
        minSales: null,
        sort: "median_price",
        direction: "asc",
      }),
      baselineCompatible: false,
    });
    const descPrice = buildExplorerDataset({
      mapMetrics: sparse,
      overviewStats: OVERVIEW_STATS,
      selection: selection({
        minSales: null,
        sort: "median_price",
        direction: "desc",
      }),
      baselineCompatible: false,
    });

    // ECHO has no median_psf, BRAVO has no volume: both keep their row and
    // sort after every area that has the value, ascending or descending.
    expect(ids(ascPsf.rows)).toEqual(["CHARLIE", "ALPHA", "BRAVO", "ECHO"]);
    expect(ids(descPsf.rows)).toEqual(["BRAVO", "ALPHA", "CHARLIE", "ECHO"]);
    expect(ids(ascPrice.rows)).toEqual(["CHARLIE", "ALPHA", "ECHO", "BRAVO"]);
    expect(ids(descPrice.rows)).toEqual(["BRAVO", "ECHO", "ALPHA", "CHARLIE"]);
  });

  test("equal values fall back to the name in both directions", () => {
    const ties: unknown = {
      year_2025_hdb: {
        ZULU: { median_price: 500000, median_psf: 600, volume: 300 },
        ALFA: { median_price: 500000, median_psf: 600, volume: 300 },
        MIKE: { median_price: 500000, median_psf: 600, volume: 300 },
      },
    };
    const asc = buildExplorerDataset({
      mapMetrics: ties,
      overviewStats: OVERVIEW_STATS,
      selection: selection({ minSales: null, direction: "asc" }),
      baselineCompatible: false,
    });
    const desc = buildExplorerDataset({
      mapMetrics: ties,
      overviewStats: OVERVIEW_STATS,
      selection: selection({ minSales: null, direction: "desc" }),
      baselineCompatible: false,
    });

    expect(ids(asc.rows)).toEqual(["ALFA", "MIKE", "ZULU"]);
    expect(ids(desc.rows)).toEqual(["ALFA", "MIKE", "ZULU"]);
  });
});
