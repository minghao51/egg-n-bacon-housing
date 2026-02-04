import React, { useMemo, useState } from 'react';
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  flexRender,
  createColumnHelper,
  type SortingState,
} from '@tanstack/react-table';

interface TownData {
  rank: number;
  town: string;
  median_price: number;
  median_psf: number;
  yield: number;
  growth: number;
  volume: number;
}

export default function TownLeaderboard({ data }: { data: TownData[] }) {
  const [sorting, setSorting] = useState<SortingState>([{ id: 'rank', desc: false }]);
  const [globalFilter, setGlobalFilter] = useState('');

  const columnHelper = createColumnHelper<TownData>();

  const columns = useMemo(() => [
    columnHelper.accessor('rank', {
      header: 'Rank',
      cell: info => <span className="font-bold">#{info.getValue()}</span>,
    }),
    columnHelper.accessor('town', {
      header: 'Town',
      cell: info => <span className="font-medium">{info.getValue()}</span>,
    }),
    columnHelper.accessor('median_price', {
      header: 'Median Price',
      cell: info => `$${info.getValue().toLocaleString()}`,
    }),
    columnHelper.accessor('median_psf', {
      header: 'Median PSF',
      cell: info => `$${info.getValue().toLocaleString()}`,
    }),
    columnHelper.accessor('yield', {
      header: 'Yield',
      cell: info => (
        <div className="flex items-center gap-2">
          <span className={info.getValue() > 4 ? "text-green-600 font-bold" : ""}>
            {info.getValue()}%
          </span>
          <div className="w-16 h-2 bg-muted rounded-full overflow-hidden">
            <div 
              className="h-full bg-green-500" 
              style={{ width: `${Math.min(info.getValue() * 20, 100)}%` }}
            />
          </div>
        </div>
      ),
    }),
    columnHelper.accessor('growth', {
      header: 'YoY Growth',
      cell: info => {
        const val = info.getValue();
        const color = val > 0 ? "text-green-600" : val < 0 ? "text-red-600" : "text-muted-foreground";
        return <span className={`${color} font-medium`}>{val > 0 ? '+' : ''}{val}%</span>;
      },
    }),
    columnHelper.accessor('volume', {
      header: 'Volume',
      cell: info => info.getValue().toLocaleString(),
    }),
  ], []);

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
        <h3 className="text-xl font-bold text-foreground">Town Rankings</h3>
        <input
          type="text"
          value={globalFilter ?? ''}
          onChange={(e) => setGlobalFilter(e.target.value)}
          placeholder="Search towns..."
          className="px-3 py-2 text-sm bg-background border border-input rounded-md focus:outline-none focus:ring-2 focus:ring-ring w-64"
        />
      </div>

      <div className="border border-border rounded-lg overflow-hidden bg-card">
        <table className="w-full text-sm text-left">
          <thead className="bg-muted text-muted-foreground font-medium uppercase">
            {table.getHeaderGroups().map(headerGroup => (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map(header => (
                  <th key={header.id} className="px-6 py-3 cursor-pointer hover:bg-muted/80" onClick={header.column.getToggleSortingHandler()}>
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
            {table.getRowModel().rows.map(row => (
              <tr key={row.id} className="hover:bg-muted/50 transition-colors">
                {row.getVisibleCells().map(cell => (
                  <td key={cell.id} className="px-6 py-4 text-foreground">
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
