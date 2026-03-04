import type {
  FilterState,
  PlanningArea,
  Segment,
  SegmentAreaRow,
  SegmentInvestigationMetric,
} from '@/types/segments';

function normalizeAreaKey(areaName: string): string {
  return areaName.toUpperCase();
}

function intersects<T>(left: T[], right: T[]): boolean {
  return left.some((value) => right.includes(value));
}

function matchesAreaFilters(area: PlanningArea, filters: FilterState): boolean {
  const inBudget =
    area.avgPricePsf >= filters.budgetRange[0] && area.avgPricePsf <= filters.budgetRange[1];
  const inRegion = filters.locations.includes(area.region);
  const inHotspot =
    filters.hotspotFilter === 'all' || area.spatialCluster === filters.hotspotFilter;

  return inBudget && inRegion && inHotspot;
}

function resolveMetricValue(row: SegmentAreaRow, metric: SegmentInvestigationMetric): number {
  return row[metric];
}

export function buildSegmentAreaRows(
  segment: Segment,
  planningAreas: Record<string, PlanningArea>,
  filters: FilterState,
  metric: SegmentInvestigationMetric
): SegmentAreaRow[] {
  if (!intersects(segment.propertyTypes, filters.propertyTypes)) {
    return [];
  }

  const rows = segment.planningAreas
    .map((areaName) => {
      const area = planningAreas[areaName];
      if (!area) {
        return null;
      }

      const matchesCurrentFilters = matchesAreaFilters(area, filters);

      return {
        areaKey: normalizeAreaKey(area.name),
        planningArea: area.name,
        region: area.region,
        avgPricePsf: area.avgPricePsf,
        avgYield: area.avgYield,
        forecast6m: area.forecast6m,
        mrtPremium: area.mrtPremium,
        hotspotConfidence: area.hotspotConfidence,
        persistenceProbability: area.persistenceProbability,
        spatialCluster: area.spatialCluster,
        mrtSensitivity: area.mrtSensitivity,
        schoolTier: area.schoolTier,
        matchesCurrentFilters,
      } satisfies SegmentAreaRow;
    })
    .filter((row): row is SegmentAreaRow => Boolean(row))
    .filter((row) => row.matchesCurrentFilters);

  return rows.sort((a, b) => resolveMetricValue(b, metric) - resolveMetricValue(a, metric));
}
