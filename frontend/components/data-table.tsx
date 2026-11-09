"use client";
import { useState } from "react";
import {
  flexRender, rowSortingFeature, createSortedRowModel, sortFns, tableFeatures, useTable,
  type ColumnDef, type RowData, type SortingState,
} from "@tanstack/react-table";
import { ArrowDown, ArrowUp, ArrowUpDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCaption, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { EmptyState, ErrorState } from "./states";

const features = tableFeatures({ rowSortingFeature, sortedRowModel: createSortedRowModel(), sortFns });

// eslint-disable-next-line @typescript-eslint/no-explicit-any -- value types vary per column
export type Col<T extends RowData> = ColumnDef<typeof features, T, any>;
export type DataTableLabels = { empty: string; error: string; retry: string; prev: string; next: string };
export type Paging = { total: number; limit: number; offset: number; onOffset: (o: number) => void };
type Props<T extends RowData> = {
  columns: Col<T>[];
  data: T[];
  labels: DataTableLabels;
  loading?: boolean;
  error?: string | null;
  onRetry?: () => void;
  paging?: Paging;
  /** Screen-reader caption naming the table. */
  caption?: string;
};

/** Sorting is client-side on the loaded page; paging is server-side (limit/offset). */
export function DataTable<T extends RowData>({ columns, data, labels, loading, error, onRetry, paging, caption }: Props<T>) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const table = useTable({ features, columns, data, state: { sorting }, onSortingChange: setSorting });

  if (error) return <ErrorState message={error || labels.error} retryLabel={labels.retry} onRetry={onRetry} />;
  const rows = table.getRowModel().rows;

  return (
    <div className="flex flex-col gap-3">
      <div className="overflow-x-auto rounded-md border border-border">
        <Table className="tabular-nums">
          {caption && <TableCaption className="sr-only">{caption}</TableCaption>}
          <TableHeader>
            <TableRow>
              {table.getHeaderGroups()[0]?.headers.map((h) => {
                const dir = h.column.getIsSorted();
                const Icon = dir === "asc" ? ArrowUp : dir === "desc" ? ArrowDown : ArrowUpDown;
                return (
                  <TableHead key={h.id} aria-sort={dir === "asc" ? "ascending" : dir === "desc" ? "descending" : undefined}>
                    {h.column.getCanSort() ? (
                      <button type="button" className="inline-flex items-center gap-1 font-medium" onClick={h.column.getToggleSortingHandler()}>
                        {flexRender(h.column.columnDef.header, h.getContext())}
                        <Icon aria-hidden className="size-3.5 text-muted-foreground" />
                      </button>
                    ) : (
                      flexRender(h.column.columnDef.header, h.getContext())
                    )}
                  </TableHead>
                );
              })}
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading
              ? Array.from({ length: 5 }, (_, i) => (
                  <TableRow key={i}>
                    {columns.map((_c, j) => (
                      <TableCell key={j}><Skeleton className="h-4 w-full" /></TableCell>
                    ))}
                  </TableRow>
                ))
              : rows.map((r) => (
                  <TableRow key={r.id}>
                    {r.getAllCells().map((c) => (
                      <TableCell key={c.id}>{flexRender(c.column.columnDef.cell, c.getContext())}</TableCell>
                    ))}
                  </TableRow>
                ))}
          </TableBody>
        </Table>
      </div>
      {!loading && rows.length === 0 && <EmptyState title={labels.empty} />}
      {paging && paging.total > paging.limit && (
        <div className="flex items-center justify-end gap-2 text-sm">
          <span className="text-muted-foreground">
            {paging.offset + 1}-{Math.min(paging.offset + paging.limit, paging.total)} / {paging.total}
          </span>
          <Button variant="outline" size="sm" disabled={paging.offset === 0}
                  onClick={() => paging.onOffset(Math.max(0, paging.offset - paging.limit))}>{labels.prev}</Button>
          <Button variant="outline" size="sm" disabled={paging.offset + paging.limit >= paging.total}
                  onClick={() => paging.onOffset(paging.offset + paging.limit)}>{labels.next}</Button>
        </div>
      )}
    </div>
  );
}
