/**
 * Unit tests for the pure observed-data adapter (src/utils/observed-data.ts).
 *
 * Hermetic: every fixture is inline, nothing is read from disk or the network.
 * The one asset-derived spot check (test 9) was verified by hand against
 * app/public/data/map_metrics.json.gz and dashboard_overview.json.gz.
 *
 * Asset hashes recorded in docs/implementation/s0-baseline.md §1 and re-checked
 * before writing these assertions (SHA-256, first 16 hex chars):
 *   map_metrics.json.gz       0a2b8a0de2274a9c
 *   dashboard_overview.json.gz b49a518d260d2db6
 *   planning_areas.geojson     f23856251b467089
 */

import { describe, expect, it } from "bun:test";
import {
  ERA_DEFINITIONS,
  OBSERVED_METRICS,
  areaSlug,
  canonicalAreaId,
  compareWithBaseline,
  formatAreaName,
  getSection,
  readAreaObservation,
  readNationalBaseline,
  sectionKey,
  type EraId,
  type ObservedAreaRecord,
  type ObservedAsset,
  type ObservedMetric,
  type ObservedObservation,
  type ObservationStatus,
  type PropertyTypeId,
} from "../../src/utils/observed-data";

const ERA_IDS: readonly EraId[] = ["whole", "pre_covid", "recent", "year_2025"];
const PROPERTY_SUBSETS: readonly PropertyTypeId[] = ["hdb", "ec", "condo"];

function requireRecord(record: ObservedAreaRecord | null): ObservedAreaRecord {
  if (record === null) throw new Error("expected an observed area record");
  return record;
}

function requireObservations(
  observations: ObservedObservation[] | null,
): ObservedObservation[] {
  if (observations === null) throw new Error("expected observations");
  return observations;
}

function metric(
  observations: readonly ObservedObservation[],
  id: ObservedMetric,
): ObservedObservation {
  const found = observations.find((entry) => entry.metric === id);
  if (found === undefined) throw new Error(`missing metric ${id}`);
  return found;
}

function observation(
  id: ObservedMetric,
  value: number | null,
  status: ObservationStatus,
  asset: ObservedAsset,
  section: string,
  propertyType: PropertyTypeId,
  era: EraId,
): ObservedObservation {
  return {
    metric: id,
    value,
    status,
    source: { asset, section, propertyType, era },
  };
}

describe("sectionKey", () => {
  it("returns joint keys for property subsets and bare era keys for all", () => {
    expect(sectionKey("whole", "all")).toBe("whole");
    expect(sectionKey("pre_covid", "all")).toBe("pre_covid");
    expect(sectionKey("recent", "all")).toBe("recent");
    expect(sectionKey("year_2025", "all")).toBe("year_2025");

    expect(sectionKey("whole", "hdb")).toBe("whole_hdb");
    expect(sectionKey("pre_covid", "ec")).toBe("pre_covid_ec");
    expect(sectionKey("recent", "condo")).toBe("recent_condo");
    expect(sectionKey("year_2025", "hdb")).toBe("year_2025_hdb");
  });

  it("never collapses a property subset onto a property-only or period-only key", () => {
    for (const era of ERA_IDS) {
      for (const propertyType of PROPERTY_SUBSETS) {
        const key = sectionKey(era, propertyType);
        // The bug this slice removes: falling back to `hdb`/`ec`/`condo`
        // (property-only) or `pre_covid`/`recent`/`year_2025` (period-only).
        expect(key).not.toBe(propertyType);
        expect(key).not.toBe(era);
        expect(key).not.toBe("whole");
        expect(key).toBe(`${era}_${propertyType}`);
      }
    }
  });
});

describe("missing sections", () => {
  const wholeOnly = {
    whole: {
      TAMPINES: { median_price: 360000, median_psf: 320, volume: 40000 },
    },
    whole_hdb: {
      TAMPINES: { median_price: 360000, median_psf: 320, volume: 40000 },
    },
  };

  it("returns null for an area when the requested section is absent (no all-history fallback)", () => {
    expect(
      readAreaObservation(wholeOnly, "recent", "hdb", "TAMPINES"),
    ).toBeNull();
    expect(
      readAreaObservation(wholeOnly, "recent", "all", "TAMPINES"),
    ).toBeNull();
    expect(
      readAreaObservation(wholeOnly, "year_2025", "condo", "TAMPINES"),
    ).toBeNull();
    expect(getSection(wholeOnly, "year_2025", "hdb")).toBeNull();
  });

  it("returns null for the national baseline when the requested section is absent", () => {
    const overview = {
      stats: {
        whole: { count: 1, median_price: 360000, median_psf: 320, volume: 1 },
      },
    };
    expect(readNationalBaseline(overview, "year_2025", "hdb")).toBeNull();
    expect(readNationalBaseline({ stats: {} }, "recent", "all")).toBeNull();
  });

  it("returns null for non-object payloads, non-object sections and non-object area entries", () => {
    expect(readAreaObservation(null, "recent", "hdb", "TAMPINES")).toBeNull();
    expect(
      readAreaObservation(undefined, "recent", "hdb", "TAMPINES"),
    ).toBeNull();
    expect(readAreaObservation([], "recent", "hdb", "TAMPINES")).toBeNull();
    expect(
      readAreaObservation(
        { recent_hdb: "not-a-section" },
        "recent",
        "hdb",
        "TAMPINES",
      ),
    ).toBeNull();
    expect(
      readAreaObservation(
        { recent_hdb: { TAMPINES: 42 } },
        "recent",
        "hdb",
        "TAMPINES",
      ),
    ).toBeNull();
    expect(readNationalBaseline(null, "recent", "hdb")).toBeNull();
    expect(
      readNationalBaseline({ stats: { recent_hdb: [] } }, "recent", "hdb"),
    ).toBeNull();
  });
});

describe("area coverage", () => {
  // Coverage is genuinely narrower for EC: in the published asset
  // year_2025_hdb carries 31 areas while year_2025_ec carries 16, and BEDOK is
  // present for HDB only. An absent area must stay unavailable, not inherit a
  // value from another property subset.
  const coverage = {
    year_2025_hdb: {
      BEDOK: { median_price: 640000, median_psf: 570, volume: 1500 },
      TAMPINES: { median_price: 710000, median_psf: 620, volume: 1921 },
    },
    year_2025_ec: {
      TAMPINES: { median_price: 1450000, median_psf: 1400, volume: 120 },
    },
  };

  it("returns a record for an area present in the joint section", () => {
    const record = requireRecord(
      readAreaObservation(coverage, "year_2025", "hdb", "BEDOK"),
    );
    expect(metric(record.metrics, "median_price").value).toBe(640000);
  });

  it("returns null for a property subset that exists but lacks the requested area", () => {
    expect(
      readAreaObservation(coverage, "year_2025", "ec", "BEDOK"),
    ).toBeNull();
    expect(
      readAreaObservation(coverage, "year_2025", "condo", "BEDOK"),
    ).toBeNull();
  });
});

describe("availability states", () => {
  it("classifies null, undefined, NaN and Infinity as missing", () => {
    const record = requireRecord(
      readAreaObservation(
        {
          year_2025_hdb: {
            TAMPINES: {
              median_price: null,
              median_psf: Number.NaN,
              // volume omitted entirely
            },
          },
        },
        "year_2025",
        "hdb",
        "TAMPINES",
      ),
    );

    for (const id of OBSERVED_METRICS) {
      const entry = metric(record.metrics, id);
      expect(entry.status).toBe("missing");
      expect(entry.value).toBeNull();
    }

    const bedok = requireRecord(
      readAreaObservation(
        {
          year_2025_hdb: {
            BEDOK: {
              median_price: Number.POSITIVE_INFINITY,
              median_psf: Number.NEGATIVE_INFINITY,
              volume: "1921",
            },
          },
        },
        "year_2025",
        "hdb",
        "BEDOK",
      ),
    );
    expect(metric(bedok.metrics, "volume").status).toBe("missing");
    expect(metric(bedok.metrics, "volume").value).toBeNull();
  });

  it("classifies an exact 0 as empty with a null value", () => {
    // The exporter's empty block: `get_stats` returns
    // {count: 0, median_price: 0, median_psf: 0, volume: 0} when the subset has
    // no rows (scripts/export_app_data.py, get_stats). That all-zero block is
    // written to dashboard_overview.stats for an era x property with no
    // transactions. For map_metrics an empty subset yields `{}` instead, so a
    // zero there is defensive only — the published asset has no zero fields.
    const record = requireRecord(
      readAreaObservation(
        {
          year_2025_hdb: {
            TAMPINES: { median_price: 0, median_psf: 0, volume: 0 },
          },
        },
        "year_2025",
        "hdb",
        "TAMPINES",
      ),
    );

    for (const id of OBSERVED_METRICS) {
      const entry = metric(record.metrics, id);
      expect(entry.status).toBe("empty");
      expect(entry.value).toBeNull();
    }

    const baseline = requireObservations(
      readNationalBaseline(
        {
          stats: {
            year_2025_ec: {
              count: 0,
              median_price: 0,
              median_psf: 0,
              volume: 0,
            },
          },
        },
        "year_2025",
        "ec",
      ),
    );
    expect(metric(baseline, "median_price").status).toBe("empty");
    expect(metric(baseline, "median_price").value).toBeNull();
  });

  it("classifies positive finite numbers as available without rounding", () => {
    const record = requireRecord(
      readAreaObservation(
        {
          year_2025_hdb: {
            TAMPINES: {
              median_price: 710000.5,
              median_psf: 620.25,
              volume: 1921,
            },
          },
        },
        "year_2025",
        "hdb",
        "TAMPINES",
      ),
    );
    expect(metric(record.metrics, "median_price")).toMatchObject({
      status: "available",
      value: 710000.5,
    });
    expect(metric(record.metrics, "median_psf")).toMatchObject({
      status: "available",
      value: 620.25,
    });
  });

  it("uses volume as the count field and ignores count", () => {
    const record = requireRecord(
      readAreaObservation(
        {
          year_2025_hdb: {
            TAMPINES: {
              count: 999999,
              median_price: 710000,
              median_psf: 620,
              volume: 1921,
            },
          },
        },
        "year_2025",
        "hdb",
        "TAMPINES",
      ),
    );
    expect(record.metrics.map((entry) => entry.metric)).toEqual([
      ...OBSERVED_METRICS,
    ]);
    expect(metric(record.metrics, "volume").value).toBe(1921);
  });
});

describe("source identity", () => {
  const mapMetrics = {
    year_2025_hdb: {
      TAMPINES: { median_price: 710000, median_psf: 620, volume: 1921 },
    },
  };

  it("carries section, era, propertyType and asset on an available area record", () => {
    const record = requireRecord(
      readAreaObservation(mapMetrics, "year_2025", "hdb", "tampines"),
    );

    expect(record.areaId).toBe("TAMPINES");
    expect(record.areaName).toBe("Tampines");
    expect(record.slug).toBe("tampines");
    expect(record.era).toBe("year_2025");
    expect(record.propertyType).toBe("hdb");
    expect(record.section).toBe("year_2025_hdb");

    for (const entry of record.metrics) {
      expect(entry.source).toEqual({
        asset: "map_metrics",
        section: "year_2025_hdb",
        propertyType: "hdb",
        era: "year_2025",
      });
    }
  });

  it("carries dashboard_overview identity on the national baseline", () => {
    const baseline = requireObservations(
      readNationalBaseline(
        {
          stats: {
            year_2025_hdb: {
              count: 25084,
              median_price: 628000,
              median_psf: 603,
              volume: 25084,
            },
          },
        },
        "year_2025",
        "hdb",
      ),
    );
    for (const entry of baseline) {
      expect(entry.source).toEqual({
        asset: "dashboard_overview",
        section: "year_2025_hdb",
        propertyType: "hdb",
        era: "year_2025",
      });
    }
  });
});

describe("national baseline", () => {
  // The baseline is the overview aggregate, not the mean of the area medians.
  // Here the area medians average to 710000 while the overview reports 628000.
  const mapMetrics = {
    recent_hdb: {
      "ANG MO KIO": { median_price: 700000, median_psf: 600, volume: 900 },
      BEDOK: { median_price: 720000, median_psf: 606, volume: 1100 },
    },
  };
  const overview = {
    metadata: { generated_at: "2026-01-01T00:00:00" },
    stats: {
      recent_hdb: {
        count: 25084,
        median_price: 628000,
        median_psf: 603,
        volume: 25084,
      },
    },
    distributions: { property_type: {}, planning_area: {} },
  };

  it("reads the overview block instead of averaging area medians", () => {
    const baseline = requireObservations(
      readNationalBaseline(overview, "recent", "hdb"),
    );
    expect(metric(baseline, "median_price").value).toBe(628000);
    expect(metric(baseline, "median_price").value).not.toBe(710000);
    expect(metric(baseline, "median_psf").value).toBe(603);
    expect(metric(baseline, "volume").value).toBe(25084);

    // The area section is independent and keeps its own values.
    const area = requireRecord(
      readAreaObservation(mapMetrics, "recent", "hdb", "BEDOK"),
    );
    expect(metric(area.metrics, "median_price").value).toBe(720000);
  });

  it("accepts the bare stats block as well as the full overview payload", () => {
    const fromPayload = requireObservations(
      readNationalBaseline(overview, "recent", "hdb"),
    );
    const fromStats = requireObservations(
      readNationalBaseline(overview.stats, "recent", "hdb"),
    );
    expect(fromStats).toEqual(fromPayload);
  });
});

describe("compareWithBaseline", () => {
  it("returns the unrounded difference and percent of baseline", () => {
    const area = observation(
      "median_price",
      710000,
      "available",
      "map_metrics",
      "year_2025_hdb",
      "hdb",
      "year_2025",
    );
    const baseline = observation(
      "median_price",
      628000,
      "available",
      "dashboard_overview",
      "year_2025_hdb",
      "hdb",
      "year_2025",
    );

    const comparison = compareWithBaseline(area, baseline);
    expect(comparison).toEqual({
      difference: 82000,
      percentOfBaseline: 13.057324840764331,
    });
    expect(comparison?.percentOfBaseline).not.toBe(13.1);
  });

  it("returns null when either value is missing or empty", () => {
    const area = observation(
      "median_price",
      710000,
      "available",
      "map_metrics",
      "year_2025_hdb",
      "hdb",
      "year_2025",
    );
    const missingBaseline = observation(
      "median_price",
      null,
      "missing",
      "dashboard_overview",
      "year_2025_hdb",
      "hdb",
      "year_2025",
    );
    const emptyArea = observation(
      "median_price",
      null,
      "empty",
      "map_metrics",
      "year_2025_hdb",
      "hdb",
      "year_2025",
    );

    expect(compareWithBaseline(area, missingBaseline)).toBeNull();
    expect(compareWithBaseline(emptyArea, area)).toBeNull();
    expect(compareWithBaseline(missingBaseline, area)).toBeNull();
  });

  it("returns null when the baseline is 0", () => {
    const area = observation(
      "volume",
      100,
      "available",
      "map_metrics",
      "year_2025_ec",
      "ec",
      "year_2025",
    );
    const zeroBaseline = observation(
      "volume",
      0,
      "available",
      "dashboard_overview",
      "year_2025_ec",
      "ec",
      "year_2025",
    );
    expect(compareWithBaseline(area, zeroBaseline)).toBeNull();
  });
});

describe("area identity", () => {
  // The 55 planning-area names of public/data/planning_areas.geojson (the
  // geometry asset area routes use). map_metrics itself publishes the 41
  // residential areas among them.
  const PLANNING_AREAS = [
    "ANG MO KIO",
    "BEDOK",
    "BISHAN",
    "BOON LAY",
    "BUKIT BATOK",
    "BUKIT MERAH",
    "BUKIT PANJANG",
    "BUKIT TIMAH",
    "CENTRAL WATER CATCHMENT",
    "CHANGI",
    "CHANGI BAY",
    "CHOA CHU KANG",
    "CLEMENTI",
    "DOWNTOWN CORE",
    "GEYLANG",
    "HOUGANG",
    "JURONG EAST",
    "JURONG WEST",
    "KALLANG",
    "LIM CHU KANG",
    "MANDAI",
    "MARINA EAST",
    "MARINA SOUTH",
    "MARINE PARADE",
    "MUSEUM",
    "NEWTON",
    "NORTH-EASTERN ISLANDS",
    "NOVENA",
    "ORCHARD",
    "OUTRAM",
    "PASIR RIS",
    "PAYA LEBAR",
    "PIONEER",
    "PUNGGOL",
    "QUEENSTOWN",
    "RIVER VALLEY",
    "ROCHOR",
    "SELETAR",
    "SEMBAWANG",
    "SENGKANG",
    "SERANGOON",
    "SIMPANG",
    "SINGAPORE RIVER",
    "SOUTHERN ISLANDS",
    "STRAITS VIEW",
    "SUNGEI KADUT",
    "TAMPINES",
    "TANGLIN",
    "TENGAH",
    "TOA PAYOH",
    "TUAS",
    "WESTERN ISLANDS",
    "WESTERN WATER CATCHMENT",
    "WOODLANDS",
    "YISHUN",
  ] as const;

  it("formats multi-word names for display", () => {
    expect(formatAreaName("ANG MO KIO")).toBe("Ang Mo Kio");
    expect(formatAreaName("BUKIT TIMAH")).toBe("Bukit Timah");
    expect(formatAreaName("CHOA CHU KANG")).toBe("Choa Chu Kang");
    expect(formatAreaName("NORTH-EASTERN ISLANDS")).toBe(
      "North-Eastern Islands",
    );
  });

  it("normalises already-canonical and untidy input to the same id", () => {
    expect(canonicalAreaId("TAMPINES")).toBe("TAMPINES");
    expect(canonicalAreaId("tampines")).toBe("TAMPINES");
    expect(canonicalAreaId("  ang   mo kio ")).toBe("ANG MO KIO");
    expect(canonicalAreaId("\tang mo kio\n")).toBe("ANG MO KIO");
    expect(areaSlug("ANG MO KIO")).toBe("ang-mo-kio");
    expect(areaSlug("ang mo kio")).toBe("ang-mo-kio");
    expect(areaSlug("BUKIT TIMAH")).toBe("bukit-timah");
    expect(areaSlug("NORTH-EASTERN ISLANDS")).toBe("north-eastern-islands");
  });

  it("round-trips id -> display -> id and id -> slug for all 55 planning areas", () => {
    for (const name of PLANNING_AREAS) {
      expect(canonicalAreaId(name)).toBe(name);
      expect(canonicalAreaId(formatAreaName(name))).toBe(name);
      expect(canonicalAreaId(name.toLowerCase())).toBe(name);
      expect(areaSlug(formatAreaName(name))).toBe(areaSlug(name));
      expect(formatAreaName(name)).not.toBe(name);
      expect(areaSlug(name)).toBe(name.toLowerCase().replace(/\s+/g, "-"));
    }
  });
});

describe("era definitions", () => {
  it("uses literal labels and boundaries that never depend on today", () => {
    expect(ERA_DEFINITIONS.map((era) => era.id)).toEqual([...ERA_IDS]);
    expect(ERA_DEFINITIONS.map((era) => era.label)).toEqual([
      "All history",
      "Through 2021",
      "2022 onward",
      "2025 complete year",
    ]);

    const byId = new Map(ERA_DEFINITIONS.map((era) => [era.id, era]));
    expect(byId.get("pre_covid")?.coverageNote).toContain("2021-12-31");
    expect(byId.get("year_2025")?.coverageNote).toContain("2025-01-01");
    expect(byId.get("year_2025")?.coverageNote).toContain("2025-12-31");
    expect(byId.get("recent")?.coverageNote).toContain("2022-01-01");
    expect(byId.get("recent")?.coverageNote?.toLowerCase()).toContain(
      "actual coverage",
    );
  });
});

describe("published asset spot check", () => {
  // Verified against the published assets (hashes in the file header):
  //   map_metrics["year_2025_hdb"]["TAMPINES"]
  //     = { median_price: 710000, median_psf: 620, volume: 1921, ... }
  //   dashboard_overview.stats["year_2025_hdb"]
  //     = { count: 25084, median_price: 628000, median_psf: 603, volume: 25084 }
  // The overview value is not the mean of the area medians (657318.0 for this
  // section), which is why the baseline must come from the overview block.
  const mapMetrics = {
    year_2025_hdb: {
      TAMPINES: {
        median_price: 710000,
        median_psf: 620,
        volume: 1921,
        rental_yield_mean: 5.99,
        rental_yield_median: 6.03,
        rental_yield_std: 0.52,
        affordability_ratio: 4.24,
        affordability_class: "Affordable",
        mortgage_to_income_pct: 20.35,
      },
    },
  };
  const overview = {
    metadata: { generated_at: "2026-01-01T00:00:00", total_records: 1234928 },
    stats: {
      year_2025_hdb: {
        count: 25084,
        median_price: 628000,
        median_psf: 603,
        volume: 25084,
      },
    },
    distributions: { property_type: {}, planning_area: {} },
  };

  it("reads Tampines 2025 HDB and the national 2025 HDB baseline", () => {
    const area = requireRecord(
      readAreaObservation(mapMetrics, "year_2025", "hdb", "TAMPINES"),
    );
    expect(metric(area.metrics, "median_price").value).toBe(710000);
    expect(metric(area.metrics, "median_psf").value).toBe(620);
    expect(metric(area.metrics, "volume").value).toBe(1921);

    const baseline = requireObservations(
      readNationalBaseline(overview, "year_2025", "hdb"),
    );
    expect(metric(baseline, "median_price").value).toBe(628000);
    expect(metric(baseline, "median_psf").value).toBe(603);
    expect(metric(baseline, "volume").value).toBe(25084);

    expect(
      compareWithBaseline(
        metric(area.metrics, "median_price"),
        metric(baseline, "median_price"),
      ),
    ).toEqual({ difference: 82000, percentOfBaseline: 13.057324840764331 });
  });
});
