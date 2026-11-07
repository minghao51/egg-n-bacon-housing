/**
 * Catalog dataset table (slice S9, SVG 15).
 *
 * Counts and sizes are labelled as catalog-snapshot values, never as a live
 * pipeline read. Sorting and the dataset filter are keyboard operable.
 *
 * The island receives slim `CatalogTableRow` projections (S10-F1) rather than
 * whole catalog datasets, so the six rendered columns are the only fields sent.
 */

import { useMemo, useState } from "react";
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  flexRender,
  createColumnHelper,
  type SortingState,
} from "@tanstack/react-table";
import { humanSize, datasetIdToSlug } from "@/types/catalog";
import type { CatalogTableRow } from "@/utils/catalog-payload";

interface DatasetTableProps {
  rows: CatalogTableRow[];
  baseUrl: string;
}

const columnHelper = createColumnHelper<CatalogTableRow>();

function ariaSort(
  sorted: false | "asc" | "desc",
): "ascending" | "descending" | "none" {
  if (sorted === "asc") return "ascending";
  if (sorted === "desc") return "descending";
  return "none";
}

export default function DatasetTable({ rows, baseUrl }: DatasetTableProps) {
  const [globalFilter, setGlobalFilter] = useState("");
  const [sorting, setSorting] = useState<SortingState>([]);

  const columns = useMemo(
    () => [
      columnHelper.accessor("label", {
        header: "Name",
        cell: (info) => {
          const row = info.row.original;
          return (
            <a
              href={`${baseUrl}${row.layer}/${datasetIdToSlug(row.id)}`}
              className="font-medium text-primary hover:underline"
            >
              {info.getValue()}
            </a>
          );
        },
      }),
      columnHelper.accessor("rowCount", {
        id: "rows",
        header: "Rows (snapshot)",
        cell: (info) => {
          const value = info.getValue();
          return (
            <span className="text-sm tabular-nums">
              {value === null ? "not observed" : value.toLocaleString("en-SG")}
            </span>
          );
        },
      }),
      columnHelper.accessor("columnCount", {
        id: "columns",
        header: "Columns (snapshot)",
        cell: (info) => {
          const value = info.getValue();
          return (
            <span className="text-sm tabular-nums">
              {value === null ? "not observed" : value}
            </span>
          );
        },
      }),
      columnHelper.accessor("bytes", {
        id: "size",
        header: "Size (snapshot)",
        cell: (info) => {
          const value = info.getValue();
          return (
            <span className="text-sm tabular-nums">
              {value === null ? "not observed" : humanSize(value)}
            </span>
          );
        },
      }),
      columnHelper.accessor("hasSchema", {
        header: "Declared schema",
        cell: (info) =>
          info.getValue() ? (
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-900/20 text-green-400 border border-green-700">
              Pydantic
            </span>
          ) : (
            <span className="text-xs text-muted-foreground">—</span>
          ),
      }),
      columnHelper.accessor("status", {
        header: "Artifact presence",
        cell: (info) => {
          const status = info.getValue();
          const colors: Record<string, string> = {
            available: "bg-green-900/20 text-green-400 border-green-700",
            missing: "bg-amber-900/20 text-amber-400 border-amber-700",
            error: "bg-red-900/20 text-red-400 border-red-700",
          };
          return (
            <span
              className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${colors[status] || colors.missing}`}
            >
              {status}
            </span>
          );
        },
      }),
    ],
    [baseUrl],
  );

  const table = useReactTable({
    data: rows,
    columns,
    state: { sorting, globalFilter },
    onSortingChange: setSorting,
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  });

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Counts and sizes are from the catalog snapshot. “Available” means the
        artifact was present when the catalog was generated — not that it is
        correct or current.
      </p>
      <div className="flex flex-wrap items-center gap-3">
        <label htmlFor="catalog-dataset-search" className="sr-only">
          Search datasets
        </label>
        <input
          id="catalog-dataset-search"
          type="search"
          value={globalFilter ?? ""}
          onChange={(e) => setGlobalFilter(e.target.value)}
          placeholder="Search datasets…"
          className="px-3 py-2 text-sm bg-background border border-input rounded-md focus:outline-none focus:ring-2 focus:ring-ring w-64"
        />
        <span className="text-sm text-muted-foreground">
          {table.getFilteredRowModel().rows.length} datasets
        </span>
      </div>
      <div className="border border-border rounded-md overflow-x-auto">
        <table className="w-full border-collapse">
          <caption className="sr-only">
            Catalog datasets with snapshot row, column and size counts
          </caption>
          <thead className="bg-muted">
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map((header) => {
                  const sorted = header.column.getIsSorted();
                  const canSort = header.column.getCanSort();
                  return (
                    <th
                      key={header.id}
                      aria-sort={ariaSort(sorted)}
                      className="px-4 py-3 text-left text-xs font-semibold text-foreground border-b border-border whitespace-nowrap"
                    >
                      {header.isPlaceholder ? null : canSort ? (
                        <button
                          type="button"
                          onClick={header.column.getToggleSortingHandler()}
                          className="flex items-center gap-1 text-left text-xs font-semibold text-foreground"
                        >
                          {flexRender(
                            header.column.columnDef.header,
                            header.getContext(),
                          )}
                          <span aria-hidden="true">
                            {sorted === "asc"
                              ? "▲"
                              : sorted === "desc"
                                ? "▼"
                                : ""}
                          </span>
                        </button>
                      ) : (
                        flexRender(
                          header.column.columnDef.header,
                          header.getContext(),
                        )
                      )}
                    </th>
                  );
                })}
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
                    className="px-4 py-2.5 text-sm text-foreground align-top"
                  >
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
