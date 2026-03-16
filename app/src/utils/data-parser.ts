/**
 * Parse markdown tables from markdown content
 */

export interface TableData {
  headers: string[];
  rows: string[][];
  caption?: string;
}

export interface ChartConfig {
  types: ('time-series' | 'comparison')[];
  columns?: string[];
  title?: string;
}

export interface ParsedMarkdown {
  content: string;
  tables: TableData[];
}

/**
 * Extract all tables from markdown content
 */
export function extractTables(markdown: string): TableData[] {
  const tables: TableData[] = [];
  const lines = markdown.split('\n');
  let currentTable: TableData | null = null;
  let inTable = false;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();

    // Check if line starts a table (has | characters)
    if (line.startsWith('|') && line.endsWith('|')) {
      if (!inTable) {
        // Start of new table
        inTable = true;
        currentTable = {
          headers: [],
          rows: [],
        };

        // Parse header row
        currentTable.headers = line
          .split('|')
          .slice(1, -1)
          .map((h) => h.trim());
      } else {
        // Check if this is separator row (contains only -, |, and spaces)
        const isSeparator = /^[\|\s\-:]+$/.test(line);

        if (!isSeparator && currentTable) {
          // Data row
          const row = line
            .split('|')
            .slice(1, -1)
            .map((cell) => cell.trim());
          currentTable.rows.push(row);
        }
      }
    } else if (inTable && currentTable) {
      // End of table
      tables.push(currentTable);
      currentTable = null;
      inTable = false;
    }
  }

  // Handle case where file ends with table
  if (inTable && currentTable) {
    tables.push(currentTable);
  }

  return tables;
}

/**
 * Detect if a table contains time-series data
 */
export function isTimeSeriesTable(table: TableData): boolean {
  if (table.headers.length === 0 || table.rows.length === 0) {
    return false;
  }

  // Check if first column header suggests time
  const firstHeader = table.headers[0].toLowerCase();
  const timeKeywords = [
    'month',
    'date',
    'year',
    'quarter',
    'time',
    'period',
    'q1',
    'q2',
    'q3',
    'q4',
  ];

  return timeKeywords.some((keyword) => firstHeader.includes(keyword));
}

/**
 * Detect if a table contains comparison data
 */
export function isComparisonTable(table: TableData): boolean {
  if (table.headers.length < 2) {
    return false;
  }

  const rowCount = table.rows.length;
  if (rowCount < 2) {
    return false;
  }

  const nonNumericFirstColCount = table.rows.filter(
    (row) => row.length > 0 && parseNumericValue(row[0]) === null
  ).length;

  const numericOtherCellCount = table.rows.reduce((count, row) => (
    count + row.slice(1).filter((cell) => parseNumericValue(cell) !== null).length
  ), 0);

  const totalOtherCellCount = table.rows.reduce((count, row) => (
    count + Math.max(0, row.length - 1)
  ), 0);

  if (totalOtherCellCount === 0) {
    return false;
  }

  return (
    nonNumericFirstColCount / rowCount >= 0.6 &&
    numericOtherCellCount / totalOtherCellCount >= 0.6
  );
}

/**
 * Parse numeric value from cell, handling currency and percentage formats
 */
export function parseNumericValue(value: string): number | null {
  if (!value || value.trim() === '') {
    return null;
  }

  const normalized = value.trim();

  // Skip cells that are mostly descriptive text or compound/range values.
  if (
    /[a-zA-Z]/.test(normalized) ||
    /\b(?:of|to|vs|baseline)\b/i.test(normalized) ||
    /^p\s*=/.test(normalized) ||
    /\[[^\]]+\]/.test(normalized)
  ) {
    return null;
  }

  if (/^\d+\s*-\s*\d+/.test(normalized) || /^[-+]?~?\d+%?\s+/.test(normalized)) {
    return null;
  }

  // Remove currency symbols, commas, and percentage signs
  const cleaned = normalized
    .replace(/[$SGD]/gi, '')
    .replace(/,/g, '')
    .replace(/%/g, '')
    .replace(/[()]/g, '')
    .replace(/^~/, '')
    .replace(/\s*\/\s*(100m|km)\b/gi, '')
    .replace(/\s*(psf|sqm|yoy)\b/gi, '')
    .trim();

  if (!/^[-+]?\d*\.?\d+$/.test(cleaned)) {
    return null;
  }

  const parsed = Number(cleaned);
  return isNaN(parsed) ? null : parsed;
}

/**
 * Convert table data to chart-ready format
 */
export interface ChartData {
  labels: string[];
  datasets: {
    label: string;
    data: (number | null)[];
  }[];
}

export function tableToChartData(
  table: TableData,
  valueColumns?: string[]
): ChartData | null {
  if (table.rows.length === 0) {
    return null;
  }

  // Determine which columns to use
  const labelIndex = 0;
  const dataIndices: number[] = [];

  if (valueColumns) {
    // Use specified columns
    valueColumns.forEach((col) => {
      const idx = table.headers.indexOf(col);
      if (idx !== -1) {
        dataIndices.push(idx);
      }
    });
  } else {
    // Auto-detect numeric columns (skip first column as labels)
    for (let i = 1; i < table.headers.length; i++) {
      const hasNumericData = table.rows.some((row) => {
        const val = parseNumericValue(row[i] || '');
        return val !== null;
      });

      if (hasNumericData) {
        dataIndices.push(i);
      }
    }
  }

  if (dataIndices.length === 0) {
    return null;
  }

  // Extract labels
  const labels = table.rows.map((row) => row[labelIndex] || '');

  // Extract datasets
  const datasets = dataIndices.map((colIndex) => ({
    label: table.headers[colIndex],
    data: table.rows.map((row) => parseNumericValue(row[colIndex] || '')),
  }));

  return { labels, datasets };
}

/**
 * Parse HTML Table Element into TableData
 */
export function parseTableFromElement(tableElement: HTMLTableElement): TableData | null {
  const headers: string[] = [];
  const rows: string[][] = [];

  // Parse Headers
  const thead = tableElement.querySelector('thead');
  if (thead) {
    const headerCells = thead.querySelectorAll('th');
    headerCells.forEach((th) => headers.push(th.textContent?.trim() || ''));
  } else {
    // Try to find first row as header if no thead
    const firstRow = tableElement.querySelector('tr');
    if (firstRow) {
      const cells = firstRow.querySelectorAll('th, td');
      cells.forEach((cell) => headers.push(cell.textContent?.trim() || ''));
    }
  }

  // Parse Rows
  const tbody = tableElement.querySelector('tbody');
  const rowElements = tbody ? tbody.querySelectorAll('tr') : tableElement.querySelectorAll('tr');

  rowElements.forEach((tr) => {
    // Skip header row if we already parsed it from tr (when no thead)
    if (!tbody && tr === tableElement.querySelector('tr')) return;

    const row: string[] = [];
    const cells = tr.querySelectorAll('td');

    // Only process if it looks like a data row
    if (cells.length > 0) {
      cells.forEach((td) => row.push(td.textContent?.trim() || ''));
      rows.push(row);
    }
  });

  if (headers.length === 0 && rows.length === 0) return null;

  return {
    headers,
    rows,
    caption: tableElement.caption?.textContent || undefined,
  };
}

export function parseChartConfigFromElement(tableElement: HTMLTableElement): ChartConfig | null {
  const previousElement = tableElement.previousElementSibling;

  if (!(previousElement instanceof HTMLElement)) {
    return null;
  }

  if (previousElement.dataset.chartMetadata !== 'true') {
    return null;
  }

  const rawTypes = previousElement.dataset.chart?.split(',').map((type) => type.trim()) ?? [];
  const validTypes = rawTypes.filter(
    (type): type is 'time-series' | 'comparison' => (
      type === 'time-series' || type === 'comparison'
    )
  );

  if (validTypes.length === 0) {
    return null;
  }

  const columns = previousElement.dataset.chartColumns
    ?.split(',')
    .map((column) => column.trim())
    .filter(Boolean);

  const title = previousElement.dataset.chartTitle?.trim();

  return {
    types: validTypes,
    columns: columns && columns.length > 0 ? columns : undefined,
    title: title || undefined,
  };
}
