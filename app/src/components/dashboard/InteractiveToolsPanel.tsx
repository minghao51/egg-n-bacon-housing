import { useState } from 'react';
import PersonaSelector, { type Persona } from './PersonaSelector';
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
}

export default function InteractiveToolsPanel({
  mrtCbdData,
  leaseDecayData,
  affordabilityData,
  hotspotsData,
}: InteractiveToolsPanelProps) {
  const [selectedPersona, setSelectedPersona] = useState<Persona>('first-time-buyer');
  const [activeTab, setActiveTab] = useState<ToolTab>('mrt-cbd');

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
          Interactive Investment Tools
        </h2>
        <p className="text-gray-600 dark:text-gray-400">
          Explore property dynamics with personalized analytics based on your investment profile
        </p>
      </div>

      {/* Persona Selector */}
      <PersonaSelector selected={selectedPersona} onChange={setSelectedPersona} />

      {/* Tool Tabs */}
      <ToolTabs active={activeTab} onChange={setActiveTab} />

      {/* Active Tool */}
      <div className="mt-6">
        {renderTool()}
      </div>
    </div>
  );
}
