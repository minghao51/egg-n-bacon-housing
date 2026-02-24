// app/src/components/dashboard/leaderboard/LeaderboardTable.tsx
import React, { useMemo, useState, useRef, useEffect } from 'react';
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  flexRender,
  createColumnHelper,
  type SortingState,
} from '@tanstack/react-table';
import { LeaderboardEntry, LeaderboardMetric } from '@/types/leaderboard';

interface LeaderboardTableProps {
  data: LeaderboardEntry[];
  highlightedArea: string | null;
  onRowHover: (area: string | null) => void;
  onRowClick: (area: string) => void;
  sortBy: LeaderboardMetric;
  onSortChange: (metric: LeaderboardMetric) => void;
}

export default function LeaderboardTable({
  data,
  highlightedArea,
  onRowHover,
  onRowClick,
  sortBy,
  onSortChange,
}: LeaderboardTableProps) {
  const [sorting, setSorting] = useState<SortingState>([{ id: sortBy, desc: true }]);
  const [globalFilter, setGlobalFilter] = useState('');
  const highlightedRowRef = useRef<HTMLTableRowElement>(null);

  // Scroll highlighted row into view
  useEffect(() => {
    if (highlightedArea && highlightedRowRef.current) {
      highlightedRowRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, [highlightedArea]);

  const columnHelper = createColumnHelper<LeaderboardEntry>();

  const columns = useMemo(() => [
    columnHelper.accessor('rank_overall', {
      header: 'Rank',
      cell: info => <span className="font-bold">#{info.getValue()}</span>,
    }),
    columnHelper.accessor('planning_area', {
      header: 'Planning Area',
      cell: info => {
        const area = info.getValue();
        const isHighlighted = highlightedArea === area.toUpperCase();
        return (
          <span className={`font-medium ${isHighlighted ? 'text-blue-600' : ''}`}>
            {area}
          </span>
        );
      },
    }),
    columnHelper.accessor('region', {
      header: 'Region',
      cell: info => {
        const region = info.getValue();
        // Shorten region names for display
        const shortRegion = region
          .replace(' REGION', '')
          .replace('CENTRAL', 'Core')
          .replace('REST OF CENTRAL', 'RCR')
          .replace('OUTSIDE CENTRAL', 'OCR');
        return <span className="text-xs text-muted-foreground">{shortRegion}</span>;
      },
    }),
    columnHelper.accessor('median_price', {
      header: 'Median Price',
      cell: info => {
        const value = info.getValue();
        return value ? `$${value.toLocaleString()}` : '—';
      },
    }),
    columnHelper.accessor('median_psf', {
      header: 'Median PSF',
      cell: info => {
        const value = info.getValue();
        return value ? `$${value.toLocaleString()}` : '—';
      },
    }),
    columnHelper.accessor(row => ({
      mean: row.rental_yield_mean,
      median: row.rental_yield_median,
    }), {
      id: 'rental_yield',
      header: 'Rental Yield',
      cell: info => {
        const { mean, median } = info.getValue();
        const displayValue = mean ?? median;
        return (
          <div className="flex items-center gap-2">
            {displayValue !== null ? (
              <>
                <span className={displayValue > 4 ? 'text-green-600 font-bold' : ''}>
                  {displayValue.toFixed(1)}%
                </span>
                <div className="w-16 h-2 bg-muted rounded-full overflow-hidden">
                  <div
                    className="h-full bg-green-500"
                    style={{ width: `${Math.min(displayValue * 20, 100)}%` }}
                  />
                </div>
              </>
            ) : (
              <span className="text-muted-foreground">—</span>
            )}
          </div>
        );
      },
    }),
    columnHelper.accessor('yoy_growth_pct', {
      header: 'YoY Growth',
      cell: info => {
        const val = info.getValue();
        const color = val > 0 ? 'text-green-600' : val < 0 ? 'text-red-600' : 'text-muted-foreground';
        return <span className={`${color} font-medium`}>{val > 0 ? '+' : ''}{val.toFixed(1)}%</span>;
      },
    }),
    columnHelper.accessor('mom_change_pct', {
      header: 'MoM Change',
      cell: info => {
        const val = info.getValue();
        const color = val > 0 ? 'text-green-600' : val < 0 ? 'text-red-600' : 'text-muted-foreground';
        return <span className={`${color} text-xs`}>{val > 0 ? '+' : ''}{val.toFixed(1)}%</span>;
      },
    }),
    columnHelper.accessor('momentum', {
      header: 'Momentum',
      cell: info => {
        const val = info.getValue();
        const color = val > 2 ? 'text-green-600' : val < -2 ? 'text-red-600' : 'text-muted-foreground';
        return <span className={`${color} text-xs`}>{val > 0 ? '+' : ''}{val.toFixed(1)}</span>;
      },
    }),
    columnHelper.accessor('volume', {
      header: 'Volume',
      cell: info => info.getValue().toLocaleString(),
    }),
    columnHelper.accessor(row => ({
      hdb: row.by_property_type.hdb.volume,
      ec: row.by_property_type.ec.volume,
      condo: row.by_property_type.condo.volume,
      total: row.volume,
    }), {
      id: 'property_type_mix',
      header: 'Property Mix',
      cell: info => {
        const { hdb, ec, condo, total } = info.getValue();
        const hdbPct = total > 0 ? (hdb / total) * 100 : 0;
        const ecPct = total > 0 ? (ec / total) * 100 : 0;
        const condoPct = total > 0 ? (condo / total) * 100 : 0;

        return (
          <div className="flex gap-0.5 h-4 w-24">
            {hdbPct > 0 && (
              <div
                className="bg-blue-500 rounded-l-sm"
                style={{ width: `${hdbPct}%` }}
                title={`HDB ${hdbPct.toFixed(0)}`}
              />
            )}
            {ecPct > 0 && (
              <div
                className="bg-orange-500"
                style={{ width: `${ecPct}%` }}
                title={`EC ${ecPct.toFixed(0)}`}
              />
            )}
            {condoPct > 0 && (
              <div
                className="bg-purple-500 rounded-r-sm"
                style={{ width: `${condoPct}%` }}
                title={`Condo ${condoPct.toFixed(0)}`}
              />
            )}
          </div>
        );
      },
    }),
  ], [highlightedArea]);

  const table = useReactTable({
    data,
    columns,
    state: {
      sorting,
      globalFilter,
    },
    onSortingChange: setSorting,
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  });

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="text-xl font-bold text-foreground">Planning Area Rankings</h3>
        <input
          type="text"
          value={globalFilter ?? ''}
          onChange={(e) => setGlobalFilter(e.target.value)}
          placeholder="Search planning areas..."
          className="px-3 py-2 text-sm bg-background border border-input rounded-md focus:outline-none focus:ring-2 focus:ring-ring w-64"
        />
      </div>

      {data.length === 0 ? (
        <div className="text-center py-12 bg-muted/20 rounded-lg">
          <p className="text-muted-foreground mb-2">No planning areas match your current filters.</p>
          <p className="text-sm text-muted-foreground">Try adjusting your filters to see more results.</p>
        </div>
      ) : (
        <div className="border border-border rounded-lg overflow-hidden bg-card">
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="bg-muted text-muted-foreground font-medium uppercase">
                {table.getHeaderGroups().map(headerGroup => (
                  <tr key={headerGroup.id}>
                    {headerGroup.headers.map(header => (
                      <th
                        key={header.id}
                        className="px-4 py-3 cursor-pointer hover:bg-muted/80 whitespace-nowrap"
                        onClick={header.column.getToggleSortingHandler()}
                      >
                        <div className="flex items-center gap-1">
                          {flexRender(header.column.columnDef.header, header.getContext())}
                          {{
                            asc: ' 🔼',
                            desc: ' 🔽',
                          }[header.column.getIsSorted() as string] ?? null}
                        </div>
                      </th>
                    ))}
                  </tr>
                ))}
              </thead>
              <tbody className="divide-y divide-border">
                {table.getRowModel().rows.map(row => {
                  const area = row.original.planning_area.toUpperCase();
                  const isHighlighted = highlightedArea === area;

                  return (
                    <tr
                      key={row.id}
                      ref={isHighlighted ? highlightedRowRef : null}
                      className={`hover:bg-muted/50 transition-colors cursor-pointer ${
                        isHighlighted ? 'bg-blue-50 border-l-4 border-l-blue-500' : ''
                      }`}
                      onMouseEnter={() => onRowHover(area)}
                      onMouseLeave={() => onRowHover(null)}
                      onClick={() => onRowClick(row.original.planning_area)}
                    >
                      {row.getVisibleCells().map(cell => (
                        <td key={cell.id} className="px-4 py-3 text-foreground whitespace-nowrap">
                          {flexRender(cell.column.columnDef.cell, cell.getContext())}
                        </td>
                      ))}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
