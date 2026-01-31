import React, { useMemo, useState } from 'react';
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  flexRender,
  createColumnHelper,
  type ColumnDef,
  type SortingState,
  type ColumnFiltersState,
} from '@tanstack/react-table';
import type { TableData } from '@/utils/data-parser';

interface InteractiveTableProps {
  data: TableData;
}

export default function InteractiveTable({ data }: InteractiveTableProps) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);
  const [globalFilter, setGlobalFilter] = useState('');

  // Transform table data for TanStack Table
  const tableData = useMemo(() => {
    return data.rows.map((row) => {
      const obj: Record<string, string> = {};
      data.headers.forEach((header, index) => {
        obj[header] = row[index] || '';
      });
      return obj;
    });
  }, [data]);

  // Create columns dynamically
  const columns = useMemo<ColumnDef<Record<string, string>>[]>(() => {
    return data.headers.map((header) => ({
      accessorKey: header,
      header: header,
      cell: (info) => info.getValue() as string,
    }));
  }, [data.headers]);

  const table = useReactTable({
    data: tableData,
    columns,
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    onGlobalFilterChange: setGlobalFilter,
    state: {
      sorting,
      columnFilters,
      globalFilter,
    },
  });

  return (
    <div className="w-full space-y-4">
      {/* Search */}
      <div className="flex items-center gap-2">
        <input
          type="text"
          value={globalFilter ?? ''}
          onChange={(e) => setGlobalFilter(e.target.value)}
          placeholder="Search all columns..."
          className="px-3 py-2 text-sm bg-background border border-input rounded-md focus:outline-none focus:ring-2 focus:ring-ring w-64"
        />
        <span className="text-sm text-muted-foreground">
          {table.getFilteredRowModel().rows.length} rows
        </span>
      </div>

      {/* Table */}
      <div className="border border-border rounded-md overflow-hidden">
        <table className="w-full border-collapse">
          <thead className="bg-muted">
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <th
                    key={header.id}
                    className="px-4 py-3 text-left text-sm font-semibold text-foreground border-b border-border"
                  >
                    {header.isPlaceholder ? null : (
                      <div
                        className={
                          header.column.getCanSort()
                            ? 'cursor-pointer select-none flex items-center gap-2 hover:text-foreground'
                            : ''
                        }
                        onClick={header.column.getToggleSortingHandler()}
                      >
                        {flexRender(
                          header.column.columnDef.header,
                          header.getContext()
                        )}
                        {{
                          asc: ' 🔼',
                          desc: ' 🔽',
                        }[header.column.getIsSorted() as string] ?? null}
                      </div>
                    )}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.map((row) => (
              <tr
                key={row.id}
                className="hover:bg-muted/50 transition-colors border-b border-border last:border-b-0"
              >
                {row.getVisibleCells().map((cell) => (
                  <td
                    key={cell.id}
                    className="px-4 py-3 text-sm text-foreground"
                  >
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination info */}
      <div className="text-sm text-muted-foreground">
        Showing {table.getFilteredRowModel().rows.length} of{' '}
        {table.getCoreRowModel().rows.length} rows
      </div>
    </div>
  );
}
