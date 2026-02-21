import React from 'react';
import InteractiveToolsPanel from './InteractiveToolsPanel';

interface TrendsDashboardProps {
  mrtCbdData: any;
  leaseDecayData: any;
  affordabilityData: any;
  hotspotsData: any;
}

export default function TrendsDashboard({
  mrtCbdData,
  leaseDecayData,
  affordabilityData,
  hotspotsData
}: TrendsDashboardProps) {
  return (
    <div className="space-y-8">
      {/* Interactive Tools Panel */}
      <InteractiveToolsPanel
        mrtCbdData={mrtCbdData}
        leaseDecayData={leaseDecayData}
        affordabilityData={affordabilityData}
        hotspotsData={hotspotsData}
      />
    </div>
  );
}
