import React from 'react';
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
import InteractiveTable from './InteractiveTable';

interface ChartRendererProps {
  markdown: string;
}

export default function ChartRenderer({ markdown }: ChartRendererProps) {
  const tables = extractTables(markdown);

  if (tables.length === 0) {
    return null;
  }

  return (
    <div className="space-y-8 my-8">
      {tables.map((table, index) => {
        const chartData = tableToChartData(table);
        if (!chartData) {
          return null;
        }

        const isTimeSeries = isTimeSeriesTable(table);
        const isComparison = isComparisonTable(table);

        return (
          <div
            key={index}
            className="bg-card border border-border rounded-lg p-6"
          >
            <h4 className="text-lg font-semibold mb-4 text-foreground">
              {isTimeSeries
                ? 'Time Series Visualization'
                : isComparison
                ? 'Comparison Chart'
                : 'Data Visualization'}
            </h4>

            {/* Render multiple chart types for comprehensive analysis */}
            <div className="space-y-6">
              {/* Time series or comparison chart */}
              {isTimeSeries && (
                <div>
                  <h5 className="text-sm font-medium mb-2 text-muted-foreground">
                    Trend Over Time
                  </h5>
                  <TimeSeriesChart data={chartData} height={300} />
                </div>
              )}

              {isComparison && (
                <div>
                  <h5 className="text-sm font-medium mb-2 text-muted-foreground">
                    Comparison
                  </h5>
                  <ComparisonChart data={chartData} height={300} />
                </div>
              )}

              {/* Statistical plot */}
              <div>
                <h5 className="text-sm font-medium mb-2 text-muted-foreground">
                  Distribution
                </h5>
                <StatisticalPlot data={chartData} height={300} />
              </div>

              {/* Interactive table */}
              <div>
                <h5 className="text-sm font-medium mb-2 text-muted-foreground">
                  Data Table
                </h5>
                <InteractiveTable data={table} />
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
