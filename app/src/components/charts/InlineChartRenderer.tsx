import React, { useEffect, useRef } from 'react';
import {
  isTimeSeriesTable,
  isComparisonTable,
  tableToChartData,
  parseTableFromElement,
} from '@/utils/data-parser';
import TimeSeriesChart from './TimeSeriesChart';
import ComparisonChart from './ComparisonChart';
import StatisticalPlot from './StatisticalPlot';
// @ts-ignore
import { createRoot } from 'react-dom/client';

// No props needed, it scans the DOM
export default function InlineChartRenderer() {
  const processedTables = useRef<Set<HTMLTableElement>>(new Set());

  useEffect(() => {
    // Find all tables in the article content
    const article = document.getElementById('article-content');
    if (!article) return;

    const tables = article.querySelectorAll('table');

    tables.forEach((table) => {
      // Cast to HTMLTableElement
      const tableElement = table as HTMLTableElement;

      if (processedTables.current.has(tableElement)) return;

      // Prevent processing if it's already part of a chart we created (nested check)
      if (tableElement.closest('.chart-container')) return;

      const tableData = parseTableFromElement(tableElement);
      if (!tableData) return;

      const chartData = tableToChartData(tableData);
      if (!chartData) return;

      const isTimeSeries = isTimeSeriesTable(tableData);
      const isComparison = isComparisonTable(tableData);

      // Only render if we have a valid visualization type
      if (!isTimeSeries && !isComparison) {
        // Maybe just statistical plot? 
        // For now, let's only auto-chart explicit types to avoid noise
        return;
      }

      // Create chart container
      const chartContainer = document.createElement('div');
      chartContainer.className = 'chart-container my-8 bg-card border border-border rounded-lg p-6 shadow-sm';

      // Create title
      const title = document.createElement('h4');
      title.className = 'text-lg font-semibold mb-4 text-foreground';
      title.textContent = isTimeSeries
        ? 'Time Series Visualization'
        : isComparison
          ? 'Comparison Chart'
          : 'Data Visualization';
      chartContainer.appendChild(title);

      // Render Charts
      if (isTimeSeries) {
        const section = createChartSection('Trend', 'trend-chart');
        chartContainer.appendChild(section);
        const mount = section.querySelector('.chart-mount') as HTMLElement;
        const root = createRoot(mount);
        root.render(<TimeSeriesChart data={chartData} height={300} />);
      }

      if (isComparison) {
        const section = createChartSection('Comparison', 'comparison-chart');
        chartContainer.appendChild(section);
        const mount = section.querySelector('.chart-mount') as HTMLElement;
        const root = createRoot(mount);
        root.render(<ComparisonChart data={chartData} height={300} />);
      }

      // Insert chart AFTER the table
      tableElement.insertAdjacentElement('afterend', chartContainer);

      processedTables.current.add(tableElement);
    });
  }, []);

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
