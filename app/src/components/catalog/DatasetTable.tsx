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
import type { CatalogDataset } from "@/types/catalog";
import { humanSize, datasetIdToSlug } from "@/types/catalog";

interface DatasetTableProps {
  datasets: CatalogDataset[];
  baseUrl: string;
}

const columnHelper = createColumnHelper<CatalogDataset>();

export default function DatasetTable({ datasets, baseUrl }: DatasetTableProps) {
  const [globalFilter, setGlobalFilter] = useState("");
  const [sorting, setSorting] = useState<SortingState>([]);

  const columns = useMemo(
    () => [
      columnHelper.accessor("label", {
        header: "Name",
        cell: (info) => {
          const ds = info.row.original;
          return (
            <a
              href={`${baseUrl}${ds.layer}/${datasetIdToSlug(ds.id)}`}
              className="font-medium text-primary hover:underline"
            >
              {info.getValue()}
            </a>
          );
        },
      }),
      columnHelper.accessor((row) => row.parquet?.row_count ?? 0, {
        id: "rows",
        header: "Rows",
        cell: (info) => (
          <span className="text-sm tabular-nums">
            {info.getValue().toLocaleString()}
          </span>
        ),
      }),
      columnHelper.accessor((row) => row.parquet?.column_count ?? 0, {
        id: "columns",
        header: "Columns",
        cell: (info) => (
          <span className="text-sm tabular-nums">{info.getValue()}</span>
        ),
      }),
      columnHelper.accessor((row) => row.parquet?.file_size_bytes ?? 0, {
        id: "size",
        header: "Size",
        cell: (info) => (
          <span className="text-sm tabular-nums">
            {humanSize(info.getValue())}
          </span>
        ),
      }),
      columnHelper.accessor("schema", {
        header: "Schema",
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
        header: "Status",
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
    data: datasets,
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
      <div className="flex items-center gap-2">
        <input
          type="text"
          value={globalFilter ?? ""}
          onChange={(e) => setGlobalFilter(e.target.value)}
          placeholder="Search datasets..."
          className="px-3 py-2 text-sm bg-background border border-input rounded-md focus:outline-none focus:ring-2 focus:ring-ring w-64"
        />
        <span className="text-sm text-muted-foreground">
          {table.getFilteredRowModel().rows.length} datasets
        </span>
      </div>
      <div className="border border-border rounded-md overflow-hidden">
        <table className="w-full border-collapse">
          <thead className="bg-muted">
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <th
                    key={header.id}
                    className="px-4 py-3 text-left text-xs font-semibold text-foreground border-b border-border whitespace-nowrap"
                  >
                    {header.isPlaceholder ? null : (
                      <div
                        className={
                          header.column.getCanSort()
                            ? "cursor-pointer select-none flex items-center gap-1 hover:text-foreground"
                            : ""
                        }
                        onClick={header.column.getToggleSortingHandler()}
                      >
                        {flexRender(
                          header.column.columnDef.header,
                          header.getContext(),
                        )}
                        {header.column.getIsSorted() === "asc"
                          ? " ▲"
                          : header.column.getIsSorted() === "desc"
                            ? " ▼"
                            : ""}
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
