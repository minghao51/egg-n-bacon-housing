/**
 * Catalog schema table (slice S9, SVG 15).
 *
 * Keeps two different claims apart:
 * - **Declared** requiredness and constraints come from the Pydantic schema.
 * - **Observed** null counts/percentages describe the parquet artifact at the
 *   catalog snapshot.
 *
 * A declared “required” field can still contain nulls in the artifact; the
 * table says so explicitly instead of letting one column stand for the other.
 * Sorting and the field filter are keyboard operable.
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
import type { FieldInfo, ParquetColumn } from "@/types/catalog";

interface SchemaField {
  name: string;
  type: string;
  nullable: boolean | null;
  constraints: Record<string, number>;
  default: string;
  description?: string;
  parquet_type?: string;
  null_pct: number | null;
  null_count: number | null;
  sample_value: string | null;
}

interface SchemaTableProps {
  schemaFields: Record<string, FieldInfo> | null;
  parquetColumns: Record<string, ParquetColumn> | null;
  /** Catalog generation time, shown beside the observed columns. */
  snapshotLabel?: string | null;
}

const columnHelper = createColumnHelper<SchemaField>();

type SortableHeaderProps = {
  label: string;
  sorted: false | "asc" | "desc";
  onToggle: ((event: unknown) => void) | undefined;
};

function SortableHeader({ label, sorted, onToggle }: SortableHeaderProps) {
  return (
    <button
      type="button"
      onClick={onToggle}
      disabled={!onToggle}
      className="flex items-center gap-1 text-left text-xs font-semibold text-foreground disabled:cursor-default"
    >
      {label}
      <span aria-hidden="true">
        {sorted === "asc" ? "▲" : sorted === "desc" ? "▼" : ""}
      </span>
    </button>
  );
}

function ariaSort(
  sorted: false | "asc" | "desc",
): "ascending" | "descending" | "none" {
  if (sorted === "asc") return "ascending";
  if (sorted === "desc") return "descending";
  return "none";
}

export default function SchemaTable({
  schemaFields,
  parquetColumns,
  snapshotLabel,
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
        nullable: sf ? sf.nullable : null,
        constraints: sf?.constraints || {},
        default: sf?.default || "",
        description: sf?.description || pc?.description,
        parquet_type: pc?.parquet_type,
        null_pct: pc?.null_pct ?? null,
        null_count: pc?.null_count ?? null,
        sample_value: pc?.sample_value ?? null,
      } satisfies SchemaField;
    });
  }, [schemaFields, parquetColumns]);

  const columns = useMemo(
    () => [
      columnHelper.accessor("name", {
        header: "Field",
        cell: (info) => (
          <span className="font-mono text-sm font-medium">
            {info.getValue()}
          </span>
        ),
      }),
      columnHelper.accessor((row) => row.parquet_type ?? row.type, {
        id: "storage",
        header: "Storage type",
        cell: (info) => (
          <code className="text-xs text-muted-foreground">
            {info.getValue() || "—"}
          </code>
        ),
      }),
      columnHelper.accessor((row) => row.nullable, {
        id: "declared",
        header: "Declared in schema",
        cell: (info) => {
          const nullable = info.getValue();
          if (nullable === null)
            return <span className="text-xs text-muted-foreground">—</span>;
          return (
            <span className="text-xs">
              {nullable ? "Nullable" : "Required"}
            </span>
          );
        },
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
      columnHelper.accessor("null_count", {
        header: "Observed nulls",
        cell: (info) => {
          const count = info.getValue();
          if (count === null)
            return (
              <span className="text-xs text-muted-foreground">
                not observed
              </span>
            );
          return (
            <span className="text-xs tabular-nums">
              {count.toLocaleString("en-SG")}
            </span>
          );
        },
      }),
      columnHelper.accessor("null_pct", {
        header: "Observed null %",
        cell: (info) => {
          const pct = info.getValue();
          if (pct === null)
            return (
              <span className="text-xs text-muted-foreground">
                not observed
              </span>
            );
          return (
            <span className="text-xs tabular-nums">{pct.toFixed(1)}%</span>
          );
        },
      }),
      columnHelper.display({
        id: "requiredness",
        header: "Requiredness check",
        cell: (info) => {
          const field = info.row.original;
          if (field.nullable === null) {
            return (
              <span className="text-xs text-muted-foreground">
                no declared schema
              </span>
            );
          }
          if (field.null_count === null) {
            return (
              <span className="text-xs text-muted-foreground">
                not observed
              </span>
            );
          }
          if (!field.nullable && field.null_count > 0) {
            return (
              <span className="rounded-sm border border-amber-600 px-2 py-0.5 text-xs font-bold text-amber-700 dark:text-amber-300">
                required · observed nulls
              </span>
            );
          }
          if (field.nullable && field.null_count === 0) {
            return (
              <span className="text-xs text-muted-foreground">
                optional · none observed
              </span>
            );
          }
          return (
            <span className="text-xs text-muted-foreground">consistent</span>
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
        header: "Sample value",
        cell: (info) => {
          const val = info.getValue();
          return val ? (
            <code className="text-xs bg-muted px-1 py-0.5 rounded">{val}</code>
          ) : (
            <span className="text-xs text-muted-foreground italic">null</span>
          );
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

  const filteredRows = table.getFilteredRowModel().rows;
  const requiredWithObservedNulls = filteredRows.filter(
    ({ original }) =>
      original.nullable === false &&
      original.null_count !== null &&
      original.null_count > 0,
  ).length;

  if (data.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        No schema information available.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        <span className="font-bold text-foreground">Declared</span> columns come
        from the Pydantic schema.{" "}
        <span className="font-bold text-foreground">Observed</span> columns
        describe the parquet artifact at the catalog snapshot
        {snapshotLabel ? ` (generated ${snapshotLabel})` : ""}. A schema
        requirement is not a guarantee about the artifact.
      </p>
      <div className="flex flex-wrap items-center gap-3">
        <label htmlFor="schema-field-search" className="sr-only">
          Search schema fields
        </label>
        <input
          id="schema-field-search"
          type="search"
          value={globalFilter ?? ""}
          onChange={(e) => setGlobalFilter(e.target.value)}
          placeholder="Search fields…"
          className="px-3 py-2 text-sm bg-background border border-input rounded-md focus:outline-none focus:ring-2 focus:ring-ring w-64"
        />
        <span className="text-sm text-muted-foreground">
          {table.getFilteredRowModel().rows.length} fields
        </span>
        {requiredWithObservedNulls > 0 ? (
          <span className="rounded-sm border border-amber-600 px-2 py-0.5 text-xs font-bold text-amber-700 dark:text-amber-300">
            {requiredWithObservedNulls} required field
            {requiredWithObservedNulls === 1 ? "" : "s"} show observed nulls
          </span>
        ) : null}
      </div>
      <div className="border border-border rounded-md overflow-x-auto">
        <table className="w-full border-collapse">
          <caption className="sr-only">
            Declared schema fields alongside the null counts observed in the
            catalog snapshot&rsquo;s parquet artifact
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
                      aria-sort={
                        sorted === false ? undefined : ariaSort(sorted)
                      }
                      className="px-4 py-3 text-left text-xs font-semibold text-foreground border-b border-border whitespace-nowrap"
                    >
                      {header.isPlaceholder ? null : canSort ? (
                        <SortableHeader
                          label={String(
                            header.column.columnDef.header ?? header.id,
                          )}
                          sorted={sorted}
                          onToggle={header.column.getToggleSortingHandler()}
                        />
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
            {table.getRowModel().rows.length === 0 ? (
              <tr>
                <td
                  colSpan={table.getAllLeafColumns().length}
                  className="px-4 py-6 text-sm text-muted-foreground"
                >
                  No schema fields match “{globalFilter}”. Clear the search to
                  see all {data.length} fields.
                </td>
              </tr>
            ) : (
              table.getRowModel().rows.map((row) => (
                <tr
                  key={row.id}
                  className="hover:bg-muted/50 transition-colors border-b border-border last:border-b-0"
                >
                  {row.getVisibleCells().map((cell) => (
                    <td
                      key={cell.id}
                      className="px-4 py-2.5 text-sm text-foreground align-top"
                    >
                      {flexRender(
                        cell.column.columnDef.cell,
                        cell.getContext(),
                      )}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
