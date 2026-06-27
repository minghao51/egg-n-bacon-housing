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
import type { FieldInfo, ParquetColumn } from "@/types/catalog";

interface SchemaField {
  name: string;
  type: string;
  nullable: boolean;
  constraints: Record<string, number>;
  default: string;
  description?: string;
  parquet_type?: string;
  null_pct: number | null;
  sample_value: string | null;
}

interface SchemaTableProps {
  schemaFields: Record<string, FieldInfo> | null;
  parquetColumns: Record<string, ParquetColumn> | null;
}

const columnHelper = createColumnHelper<SchemaField>();

export default function SchemaTable({
  schemaFields,
  parquetColumns,
}: SchemaTableProps) {
  const [globalFilter, setGlobalFilter] = useState("");
  const [sorting, setSorting] = useState<SortingState>([]);

  const data = useMemo(() => {
    const allFields = new Set<string>();
    if (schemaFields)
      Object.keys(schemaFields).forEach((k) => allFields.add(k));
    if (parquetColumns)
      Object.keys(parquetColumns).forEach((k) => allFields.add(k));

    return Array.from(allFields).map((name) => {
      const sf = schemaFields?.[name];
      const pc = parquetColumns?.[name];
      return {
        name,
        type: sf?.type || pc?.parquet_type || "",
        nullable: sf?.nullable ?? false,
        constraints: sf?.constraints || {},
        default: sf?.default || "",
        description: sf?.description || pc?.description,
        parquet_type: pc?.parquet_type,
        null_pct: pc?.null_pct ?? null,
        sample_value: pc?.sample_value ?? null,
      };
    });
  }, [schemaFields, parquetColumns]);

  const columns = useMemo(
    () => [
      columnHelper.accessor("name", {
        header: "Field Name",
        cell: (info) => (
          <span className="font-mono text-sm font-medium">
            {info.getValue()}
          </span>
        ),
      }),
      columnHelper.accessor("type", {
        header: "Type",
        cell: (info) => (
          <code className="text-xs text-muted-foreground">
            {info.getValue()}
          </code>
        ),
      }),
      columnHelper.accessor("nullable", {
        header: "Nullable",
        cell: (info) =>
          info.getValue() ? (
            <span className="text-xs text-muted-foreground">Yes</span>
          ) : (
            <span className="text-xs font-medium">No</span>
          ),
      }),
      columnHelper.accessor("constraints", {
        header: "Constraints",
        cell: (info) => {
          const c = info.getValue();
          const entries = Object.entries(c);
          if (entries.length === 0)
            return <span className="text-xs text-muted-foreground">—</span>;
          return (
            <code className="text-xs">
              {entries.map(([k, v]) => `${k}: ${v}`).join(", ")}
            </code>
          );
        },
      }),
      columnHelper.accessor("description", {
        header: "Description",
        cell: (info) => (
          <span className="text-xs leading-relaxed">
            {info.getValue() || (
              <span className="text-muted-foreground italic">—</span>
            )}
          </span>
        ),
      }),
      columnHelper.accessor("sample_value", {
        header: "Sample Value",
        cell: (info) => {
          const val = info.getValue();
          return val ? (
            <code className="text-xs bg-muted px-1 py-0.5 rounded">{val}</code>
          ) : (
            <span className="text-xs text-muted-foreground italic">null</span>
          );
        },
      }),
      columnHelper.accessor("null_pct", {
        header: "Null %",
        cell: (info) => {
          const pct = info.getValue();
          if (pct === null)
            return <span className="text-xs text-muted-foreground">—</span>;
          return <span className="text-xs">{pct.toFixed(1)}%</span>;
        },
      }),
    ],
    [],
  );

  const table = useReactTable({
    data,
    columns,
    state: { sorting, globalFilter },
    onSortingChange: setSorting,
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  });

  if (data.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        No schema information available.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <input
          type="text"
          value={globalFilter ?? ""}
          onChange={(e) => setGlobalFilter(e.target.value)}
          placeholder="Search fields..."
          className="px-3 py-2 text-sm bg-background border border-input rounded-md focus:outline-none focus:ring-2 focus:ring-ring w-64"
        />
        <span className="text-sm text-muted-foreground">
          {table.getFilteredRowModel().rows.length} fields
        </span>
      </div>
      <div className="border border-border rounded-md overflow-x-auto">
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
