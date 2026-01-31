import React, { useEffect, useRef } from 'react';
import {
  extractTables,
  isTimeSeriesTable,
  isComparisonTable,
  tableToChartData,
  type TableData,
} from '@/utils/data-parser';
import TimeSeriesChart from './TimeSeriesChart';
import ComparisonChart from './ComparisonChart';
import StatisticalPlot from './StatisticalPlot';

interface InlineChartRendererProps {
  tables: Array<{ id: string; markdown: string }>;
}

export default function InlineChartRenderer({ tables }: InlineChartRendererProps) {
  const renderedRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    // Only render each chart once
    if (tables.length === 0) return;

    tables.forEach((tableData, index) => {
      if (renderedRef.current.has(tableData.id)) return;

      const placeholder = document.getElementById(tableData.id);
      if (!placeholder) return;

      // Parse table markdown
      const extractedTables = extractTables(tableData.markdown);
      if (extractedTables.length === 0) {
        console.log(`Table ${tableData.id} not recognized as chart-able, showing HTML table only`);
        return; // Table still visible in HTML
      }

      const table = extractedTables[0];
      const chartData = tableToChartData(table);
      if (!chartData) {
        console.log(`Table ${tableData.id} data not chart-able, showing HTML table only`);
        return; // Table still visible in HTML
      }

      const isTimeSeries = isTimeSeriesTable(table);
      const isComparison = isComparisonTable(table);

      // Create chart container
      const chartContainer = document.createElement('div');
      chartContainer.className = 'my-6 bg-card border border-border rounded-lg p-6';

      // Create title
      const title = document.createElement('h4');
      title.className = 'text-lg font-semibold mb-4 text-foreground';
      title.textContent = isTimeSeries
        ? 'Time Series Visualization'
        : isComparison
        ? 'Comparison Chart'
        : 'Data Visualization';
      chartContainer.appendChild(title);

      // Create chart sections based on type
      if (isTimeSeries) {
        const trendSection = createChartSection('Trend Over Time', 'trend-chart');
        chartContainer.appendChild(trendSection);

        // Time series chart will be rendered by React
        const trendDiv = trendSection.querySelector('.chart-mount') as HTMLElement;
        if (trendDiv) {
          const root = React.createRoot(trendDiv);
          root.render(<TimeSeriesChart data={chartData} height={300} />);
        }
      }

      if (isComparison) {
        const comparisonSection = createChartSection('Comparison', 'comparison-chart');
        chartContainer.appendChild(comparisonSection);

        const comparisonDiv = comparisonSection.querySelector('.chart-mount') as HTMLElement;
        if (comparisonDiv) {
          const root = React.createRoot(comparisonDiv);
          root.render(<ComparisonChart data={chartData} height={300} />);
        }
      }

      // Always add statistical plot
      const distSection = createChartSection('Distribution', 'distribution-chart');
      chartContainer.appendChild(distSection);

      const distDiv = distSection.querySelector('.chart-mount') as HTMLElement;
      if (distDiv) {
        const root = React.createRoot(distDiv);
        root.render(<StatisticalPlot data={chartData} height={300} />);
      }

      // Insert chart BEFORE placeholder (placeholder is after table, so chart appears after table)
      placeholder.insertAdjacentElement('beforebegin', chartContainer);

      // Remove placeholder after rendering (cleanup)
      placeholder.remove();

      renderedRef.current.add(tableData.id);
    });
  }, [tables]);

  // This component doesn't render anything directly
  // It just attaches charts to placeholder divs
  return null;
}

function createChartSection(title: string, className: string): HTMLElement {
  const section = document.createElement('div');
  section.className = 'mb-6 last:mb-0';

  const heading = document.createElement('h5');
  heading.className = 'text-sm font-medium mb-2 text-muted-foreground';
  heading.textContent = title;
  section.appendChild(heading);

  const mount = document.createElement('div');
  mount.className = `chart-mount ${className}`;
  section.appendChild(mount);

  return section;
}
