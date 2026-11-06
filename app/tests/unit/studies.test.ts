/**
 * Unit tests for the S9 studies library contract
 * (src/components/studies/lib/studies.ts).
 */

import { describe, expect, test } from "bun:test";

import {
  DEFAULT_STUDY_FILTERS,
  filterStudies,
  filtersAreActive,
  STUDY_CATEGORIES,
  studyEvidence,
  type StudyCardData,
} from "../../src/components/studies/lib/studies";

const STUDIES: StudyCardData[] = [
  {
    slug: "lease-decay",
    title: "Lease Decay Impact",
    description: "How remaining lease and prices relate.",
    category: "market-analysis",
    date: "2026-02-04",
    readingTime: "7 min read",
    technicalLevel: "intermediate",
    personas: ["investor", "first-time-buyer"],
    evidenceReview: true,
  },
  {
    slug: "data-sources",
    title: "Data Sources",
    description: "Every dataset that powers the platform.",
    category: "quick-reference",
    date: "2026-06-15",
    readingTime: "5 min read",
    technicalLevel: null,
    personas: [],
    evidenceReview: false,
  },
];

describe("filterStudies", () => {
  test("the default filters keep every study", () => {
    expect(filterStudies(STUDIES, DEFAULT_STUDY_FILTERS)).toHaveLength(2);
    expect(filtersAreActive(DEFAULT_STUDY_FILTERS)).toBe(false);
  });

  test("free text matches title, description and slug", () => {
    expect(
      filterStudies(STUDIES, { ...DEFAULT_STUDY_FILTERS, query: "lease" }).map(
        (study) => study.slug,
      ),
    ).toEqual(["lease-decay"]);
    expect(
      filterStudies(STUDIES, {
        ...DEFAULT_STUDY_FILTERS,
        query: "powers the platform",
      }).map((study) => study.slug),
    ).toEqual(["data-sources"]);
    expect(
      filterStudies(STUDIES, {
        ...DEFAULT_STUDY_FILTERS,
        query: "quick",
      }),
    ).toEqual([]);
  });

  test("topic filters to the exact category", () => {
    expect(
      filterStudies(STUDIES, {
        ...DEFAULT_STUDY_FILTERS,
        category: "quick-reference",
      }).map((study) => study.slug),
    ).toEqual(["data-sources"]);
  });

  test("audience uses published persona entry points only", () => {
    expect(
      filterStudies(STUDIES, {
        ...DEFAULT_STUDY_FILTERS,
        audience: "investor",
      }).map((study) => study.slug),
    ).toEqual(["lease-decay"]);
    expect(
      filterStudies(STUDIES, {
        ...DEFAULT_STUDY_FILTERS,
        audience: "all-personas",
      }).map((study) => study.slug),
    ).toEqual(["lease-decay"]);
    expect(
      filterStudies(STUDIES, {
        ...DEFAULT_STUDY_FILTERS,
        audience: "upgrader",
      }),
    ).toEqual([]);
  });

  test("filters combine and never invent a fallback list", () => {
    expect(
      filterStudies(STUDIES, {
        query: "lease",
        category: "market-analysis",
        audience: "first-time-buyer",
      }),
    ).toHaveLength(1);
    expect(
      filterStudies(STUDIES, {
        query: "lease",
        category: "quick-reference",
        audience: "all",
      }),
    ).toEqual([]);
    expect(
      filtersAreActive({ query: "  ", category: "all", audience: "all" }),
    ).toBe(false);
  });

  test("every declared topic exists in the label map", () => {
    expect(STUDY_CATEGORIES).toHaveLength(4);
  });
});

describe("studyEvidence", () => {
  test("the lease study withholds charts for a unit review", () => {
    const evidence = studyEvidence("lease-decay");
    expect(evidence.unitReview).toBe(true);
    expect(evidence.chartsWithheld).toBe(true);
    expect(evidence.note).toContain("per-square-metre");
    expect(evidence.note).toContain("Median PSF");
  });

  test("other studies keep their opt-in charts", () => {
    const evidence = studyEvidence("mrt-impact");
    expect(evidence.unitReview).toBe(false);
    expect(evidence.chartsWithheld).toBe(false);
    expect(evidence.note).toContain("observation period");
  });
});
