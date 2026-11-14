import React, { useEffect, useRef } from "react";
import {
  CHART_UNIT_LABELS,
  dropEmptyDatasets,
  parseChartConfigFromElement,
  splitDatasetsByUnit,
  tableToChartData,
  parseTableFromElement,
} from "@/utils/data-parser";
import TimeSeriesChart from "./TimeSeriesChart";
import ComparisonChart from "./ComparisonChart";
// @ts-ignore
import { createRoot } from "react-dom/client";

// No props needed, it scans the DOM
export default function InlineChartRenderer() {
  const processedTables = useRef<Set<HTMLTableElement>>(new Set());

  useEffect(() => {
    // Find all tables in the article content
    const article = document.getElementById("article-content");
    if (!article) return;

    const tables = article.querySelectorAll("table");

    tables.forEach((table) => {
      // Cast to HTMLTableElement
      const tableElement = table as HTMLTableElement;

      if (processedTables.current.has(tableElement)) return;

      // Prevent processing if it's already part of a chart we created (nested check)
      if (tableElement.closest(".chart-container")) return;

      const chartConfig = parseChartConfigFromElement(tableElement);
      if (!chartConfig) return;

      const tableData = parseTableFromElement(tableElement);
      if (!tableData) return;

      const chartData = tableToChartData(tableData, chartConfig.columns);
      if (!chartData) {
        // Requested columns are missing or hold no numeric values: say so
        // instead of leaving the marker silently unrendered.
        const noteContainer = document.createElement("div");
        noteContainer.className =
          "chart-container my-8 rounded-lg border border-border bg-card p-4";
        noteContainer.appendChild(
          createChartNote(
            "No chart is drawn for this table: the selected columns are missing or contain only ranges and text. The table above remains the source of record.",
          ),
        );
        tableElement.insertAdjacentElement("afterend", noteContainer);
        processedTables.current.add(tableElement);
        return;
      }

      const renderTimeSeries = chartConfig.types.includes("time-series");
      const renderComparison = chartConfig.types.includes("comparison");

      // A series whose cells cannot be parsed (for example a "±18.58%"
      // uncertainty column) is reported instead of plotted as an empty bar set.
      const { data: plottable, dropped } = dropEmptyDatasets(chartData);

      // Create chart container
      const chartContainer = document.createElement("div");
      chartContainer.className =
        "chart-container my-8 bg-card border border-border rounded-lg p-6 shadow-sm";

      // Create title
      const title = document.createElement("h4");
      title.className = "text-lg font-semibold mb-4 text-foreground";
      title.textContent =
        chartConfig.title ??
        (renderTimeSeries && !renderComparison
          ? "Time Series Visualization"
          : renderComparison && !renderTimeSeries
            ? "Comparison Chart"
            : "Data Visualization");
      chartContainer.appendChild(title);

      // Insert the container before mounting charts so ResponsiveContainer can measure it.
      tableElement.insertAdjacentElement("afterend", chartContainer);

      if (plottable.datasets.length === 0) {
        chartContainer.appendChild(
          createChartNote(
            "No numeric series available for this table, so no chart is drawn. The values above stay in the table.",
          ),
        );
      }

      // Render Charts
      if (renderTimeSeries && plottable.datasets.length > 0) {
        const section = createChartSection("Trend", "trend-chart");
        chartContainer.appendChild(section);
        const mount = section.querySelector(".chart-mount") as HTMLElement;
        const root = createRoot(mount);
        requestAnimationFrame(() => {
          root.render(<TimeSeriesChart data={plottable} height={300} />);
        });
      }

      if (renderComparison && plottable.datasets.length > 0) {
        // One chart per unit: counts, S$ and percentages do not share an axis.
        const groups = splitDatasetsByUnit(plottable);
        groups.forEach((group) => {
          const label =
            groups.length === 1
              ? "Comparison"
              : `Comparison — ${CHART_UNIT_LABELS[group.unit]}`;
          const section = createChartSection(label, "comparison-chart");
          chartContainer.appendChild(section);
          const mount = section.querySelector(".chart-mount") as HTMLElement;
          const root = createRoot(mount);
          requestAnimationFrame(() => {
            root.render(<ComparisonChart data={group.data} height={300} />);
          });
        });
      }

      if (dropped.length > 0) {
        chartContainer.appendChild(
          createChartNote(
            `Not charted: ${dropped.join(", ")} — the table cells do not contain a single numeric value (ranges, ± uncertainty or text). Read those columns in the table.`,
          ),
        );
      }

      processedTables.current.add(tableElement);
    });
  }, []);

  return null;
}

function createChartNote(message: string): HTMLElement {
  const note = document.createElement("p");
  note.className = "text-sm text-muted-foreground";
  note.setAttribute("data-chart-note", "true");
  note.textContent = message;
  return note;
}

function createChartSection(title: string, className: string): HTMLElement {
  const section = document.createElement("div");
  section.className = "mb-6 last:mb-0";

  const heading = document.createElement("h5");
  heading.className = "text-sm font-medium mb-2 text-muted-foreground";
  heading.textContent = title;
  section.appendChild(heading);

  const mount = document.createElement("div");
  mount.className = `chart-mount ${className}`;
  section.appendChild(mount);

  return section;
}
