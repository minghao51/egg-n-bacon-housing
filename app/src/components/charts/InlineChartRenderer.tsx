import React, { useEffect, useRef } from 'react';
import {
  parseChartConfigFromElement,
  tableToChartData,
  parseTableFromElement,
} from '@/utils/data-parser';
import TimeSeriesChart from './TimeSeriesChart';
import ComparisonChart from './ComparisonChart';
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

      const chartConfig = parseChartConfigFromElement(tableElement);
      if (!chartConfig) return;

      const tableData = parseTableFromElement(tableElement);
      if (!tableData) return;

      const chartData = tableToChartData(tableData, chartConfig.columns);
      if (!chartData) return;

      const renderTimeSeries = chartConfig.types.includes('time-series');
      const renderComparison = chartConfig.types.includes('comparison');

      // Create chart container
      const chartContainer = document.createElement('div');
      chartContainer.className = 'chart-container my-8 bg-card border border-border rounded-lg p-6 shadow-sm';

      // Create title
      const title = document.createElement('h4');
      title.className = 'text-lg font-semibold mb-4 text-foreground';
      title.textContent = chartConfig.title
        ?? (renderTimeSeries && !renderComparison
          ? 'Time Series Visualization'
          : renderComparison && !renderTimeSeries
            ? 'Comparison Chart'
            : 'Data Visualization');
      chartContainer.appendChild(title);

      // Insert the container before mounting charts so ResponsiveContainer can measure it.
      tableElement.insertAdjacentElement('afterend', chartContainer);

      // Render Charts
      if (renderTimeSeries) {
        const section = createChartSection('Trend', 'trend-chart');
        chartContainer.appendChild(section);
        const mount = section.querySelector('.chart-mount') as HTMLElement;
        const root = createRoot(mount);
        requestAnimationFrame(() => {
          root.render(<TimeSeriesChart data={chartData} height={300} />);
        });
      }

      if (renderComparison) {
        const section = createChartSection('Comparison', 'comparison-chart');
        chartContainer.appendChild(section);
        const mount = section.querySelector('.chart-mount') as HTMLElement;
        const root = createRoot(mount);
        requestAnimationFrame(() => {
          root.render(<ComparisonChart data={chartData} height={300} />);
        });
      }

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
