export interface DashboardNavItem {
  key: 'overview' | 'map' | 'tools' | 'segments' | 'leaderboard';
  label: string;
  shortLabel: string;
  description: string;
  path: string;
}

export const DASHBOARD_NAV_ITEMS: DashboardNavItem[] = [
  {
    key: 'overview',
    label: 'Overview',
    shortLabel: 'Overview',
    description: 'Quick market snapshot and where to go next.',
    path: 'dashboard',
  },
  {
    key: 'map',
    label: 'Explore Areas',
    shortLabel: 'Map',
    description: 'Spatial exploration for hotspots, value pockets, and overlays.',
    path: 'dashboard/map',
  },
  {
    key: 'tools',
    label: 'Decision Tools',
    shortLabel: 'Tools',
    description: 'Scenario calculators for commute, lease, and affordability tradeoffs.',
    path: 'dashboard/trends',
  },
  {
    key: 'segments',
    label: 'Discover Segments',
    shortLabel: 'Segments',
    description: 'Guided segment discovery, investigation, and comparison.',
    path: 'dashboard/segments',
  },
  {
    key: 'leaderboard',
    label: 'Compare Areas',
    shortLabel: 'Rankings',
    description: 'Rank planning areas on one metric and shortlist targets.',
    path: 'dashboard/leaderboard',
  },
];
