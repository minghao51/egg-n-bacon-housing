import { useMemo, useState } from 'react';
import type { Persona } from './PersonaSelector';
import ToolTabs, { type ToolTab } from './ToolTabs';
import MrtCbdCalculator from './tools/MrtCbdCalculator';
import LeaseDecayAnalyzer from './tools/LeaseDecayAnalyzer';
import AffordabilityCalculator from './tools/AffordabilityCalculator';
import SpatialHotspotExplorer from './tools/SpatialHotspotExplorer';

interface MrtCbdData {
  property_type_multipliers: {
    [key: string]: { premium_per_100m: number; cbd_per_km: number };
  };
  town_multipliers: { [key: string]: number };
  town_premiums: Array<{
    town: string;
    multiplier: number;
    hdb_premium_per_100m: number;
    condo_premium_per_100m: number;
  }>;
}

interface LeaseDecayData {
  bands: Array<{
    lease_age_band: string;
    min_lease_years: number;
    max_lease_years: number;
    discount_percent: number;
    annual_decay_rate: number;
    volume_category: string;
    risk_zone: string;
  }>;
  insights: {
    maturity_cliff: { band: string; discount: number; annual_rate: number; description: string };
    best_value: { band: string; discount: number; annual_rate: number; description: string };
    safe_zone: { band: string; discount: number; annual_rate: number; description: string };
  };
}

interface AffordabilityData {
  median_household_income: number;
  town_metrics: Array<{
    town: string;
    property_type: string;
    median_price: number;
    affordability_ratio: number;
    category: string;
    estimated_monthly_mortgage: number;
  }>;
}

interface SpatialData {
  clusters: Array<{
    cluster_type: 'HH' | 'LH' | 'HL' | 'LL';
    towns: string[];
    avg_appreciation_5y: number;
    avg_price_psf: number;
    persistence_probability: number;
    risk_level: 'Low' | 'Medium' | 'High';
  }>;
  analysis_date: string;
  methodology: string;
}

interface InteractiveToolsPanelProps {
  mrtCbdData: MrtCbdData;
  leaseDecayData: LeaseDecayData;
  affordabilityData: AffordabilityData;
  hotspotsData: SpatialData;
  segmentsData: { segments: Array<{ id: string; name: string; description: string; implications: any }> } | null;
}

export default function InteractiveToolsPanel({
  mrtCbdData,
  leaseDecayData,
  affordabilityData,
  hotspotsData,
  segmentsData,
}: InteractiveToolsPanelProps) {
  const [selectedPersona] = useState<Persona>('all');
  const [activeTab, setActiveTab] = useState<ToolTab>('mrt-cbd');

  const toolMeta = useMemo(() => {
    switch (activeTab) {
      case 'mrt-cbd':
        return {
          title: 'Commute-price tradeoff estimator',
          description: 'Estimate how MRT and CBD distance pull values up or down for a target area.',
          learnMoreUrl: `${import.meta.env.BASE_URL}analytics/mrt-impact`,
          learnMoreLabel: 'Read MRT impact methodology',
        };
      case 'lease-decay':
        return {
          title: 'Remaining-lease discount estimator',
          description: 'Check where a property sits on the lease-decay curve and how fast value pressure builds.',
          learnMoreUrl: `${import.meta.env.BASE_URL}analytics/lease-decay`,
          learnMoreLabel: 'Read lease-decay methodology',
        };
      case 'affordability':
        return {
          title: 'Income-to-price capacity checker',
          description: 'Test affordability ranges by income, property type, and town before you shortlist an area.',
          learnMoreUrl: `${import.meta.env.BASE_URL}analytics/findings`,
          learnMoreLabel: 'Read affordability context',
        };
      case 'hotspots':
        return {
          title: 'Spatial signal lookup',
          description: 'Check hotspot and transition-zone signals when you already have towns in mind.',
          learnMoreUrl: `${import.meta.env.BASE_URL}analytics/spatial-autocorrelation`,
          learnMoreLabel: 'Read spatial methodology',
        };
      default:
        return {
          title: 'Decision support',
          description: 'Run a scenario before you move back into area ranking or segment discovery.',
          learnMoreUrl: `${import.meta.env.BASE_URL}analytics/`,
          learnMoreLabel: 'Read analytics',
        };
    }
  }, [activeTab]);

  const renderTool = () => {
    switch (activeTab) {
      case 'mrt-cbd':
        return <MrtCbdCalculator data={mrtCbdData} persona={selectedPersona} />;
      case 'lease-decay':
        return <LeaseDecayAnalyzer data={leaseDecayData} persona={selectedPersona} />;
      case 'affordability':
        return <AffordabilityCalculator data={affordabilityData} persona={selectedPersona} />;
      case 'hotspots':
        return <SpatialHotspotExplorer data={hotspotsData} persona={selectedPersona} />;
      default:
        return null;
    }
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
      {/* Header */}
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
          Decision Workspace
        </h2>
        <p className="text-gray-600 dark:text-gray-400">
          Use one calculator at a time, get an answer, then jump back into area comparison or segment discovery with that result.
        </p>
        {segmentsData?.segments?.length ? (
          <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
            Cross-check your result later against {segmentsData.segments.length} market segments in the discovery flow.
          </p>
        ) : null}
      </div>

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <button
          type="button"
          onClick={() => setActiveTab('mrt-cbd')}
          className={`rounded-2xl border p-4 text-left transition-colors ${
            activeTab === 'mrt-cbd'
              ? 'border-primary bg-primary/5'
              : 'border-gray-200 hover:bg-gray-50 dark:border-gray-700 dark:hover:bg-gray-900/30'
          }`}
        >
          <div className="text-sm font-semibold text-gray-900 dark:text-white">MRT / CBD Impact</div>
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">Quantify commute-distance pricing tradeoffs.</p>
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('lease-decay')}
          className={`rounded-2xl border p-4 text-left transition-colors ${
            activeTab === 'lease-decay'
              ? 'border-primary bg-primary/5'
              : 'border-gray-200 hover:bg-gray-50 dark:border-gray-700 dark:hover:bg-gray-900/30'
          }`}
        >
          <div className="text-sm font-semibold text-gray-900 dark:text-white">Lease Decay</div>
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">Estimate remaining-lease discount and risk zone.</p>
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('affordability')}
          className={`rounded-2xl border p-4 text-left transition-colors ${
            activeTab === 'affordability'
              ? 'border-primary bg-primary/5'
              : 'border-gray-200 hover:bg-gray-50 dark:border-gray-700 dark:hover:bg-gray-900/30'
          }`}
        >
          <div className="text-sm font-semibold text-gray-900 dark:text-white">Affordability</div>
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">Check income capacity before shortlisting.</p>
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('hotspots')}
          className={`rounded-2xl border p-4 text-left transition-colors ${
            activeTab === 'hotspots'
              ? 'border-primary bg-primary/5'
              : 'border-gray-200 hover:bg-gray-50 dark:border-gray-700 dark:hover:bg-gray-900/30'
          }`}
        >
          <div className="text-sm font-semibold text-gray-900 dark:text-white">Spatial Hotspots</div>
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">Lookup clustering signals for candidate towns.</p>
        </button>
      </div>

      {/* Tool Tabs */}
      <ToolTabs active={activeTab} onChange={setActiveTab} />

      <div className="rounded-2xl border border-gray-200 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-900/30">
        <div className="text-sm font-semibold text-gray-900 dark:text-white">{toolMeta.title}</div>
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">{toolMeta.description}</p>
      </div>

      {/* Active Tool */}
      <div className="mt-6">
        {renderTool()}
      </div>

      <div className="mt-6 grid gap-4 md:grid-cols-2">
        <a
          href={toolMeta.learnMoreUrl}
          className="rounded-2xl border border-gray-200 p-4 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50 dark:border-gray-700 dark:text-gray-200 dark:hover:bg-gray-900/30"
        >
          {toolMeta.learnMoreLabel}
        </a>
        <a
          href={`${import.meta.env.BASE_URL}${activeTab === 'affordability' ? 'dashboard/leaderboard' : 'dashboard/segments'}`}
          className="rounded-2xl border border-gray-200 p-4 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50 dark:border-gray-700 dark:text-gray-200 dark:hover:bg-gray-900/30"
        >
          {activeTab === 'affordability' ? 'Next: compare areas' : 'Next: discover matching segments'}
        </a>
      </div>
    </div>
  );
}
