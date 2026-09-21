"use client";

import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableFooter,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { EmptyState, ErrorState } from "@/components/tables/states";
import { cn } from "@/lib/utils";

export interface Column<T> {
  key: string;
  header: React.ReactNode;
  cell: (row: T) => React.ReactNode;
  align?: "left" | "right" | "center";
  className?: string;
  /** Hide on small screens to keep tables usable on mobile. */
  hideBelow?: "sm" | "md" | "lg" | "xl";
}

const hideClass: Record<NonNullable<Column<unknown>["hideBelow"]>, string> = {
  sm: "hidden sm:table-cell",
  md: "hidden md:table-cell",
  lg: "hidden lg:table-cell",
  xl: "hidden xl:table-cell",
};
const alignClass = { left: "text-left", right: "text-right", center: "text-center" } as const;

interface DataTableProps<T> {
  columns: Column<T>[];
  rows: T[] | undefined;
  rowKey: (row: T) => string;
  isLoading: boolean;
  error: unknown;
  onRetry?: () => void;
  emptyTitle: string;
  emptyDescription?: React.ReactNode;
  emptyAction?: React.ReactNode;
  onRowClick?: (row: T) => void;
  rowClassName?: (row: T) => string | undefined;
  footer?: React.ReactNode;
  skeletonRows?: number;
  className?: string;
  /** Constrain height and scroll inside the table. */
  maxHeightClass?: string;
}

export function DataTable<T>({
  columns,
  rows,
  rowKey,
  isLoading,
  error,
  onRetry,
  emptyTitle,
  emptyDescription,
  emptyAction,
  onRowClick,
  rowClassName,
  footer,
  skeletonRows = 5,
  className,
  maxHeightClass,
}: DataTableProps<T>) {
  const colClass = (c: Column<T>) =>
    cn(alignClass[c.align ?? "left"], c.hideBelow && hideClass[c.hideBelow], c.className);

  // Keep showing stale rows when a background poll fails.
  const showError = !!error && !rows;
  const showEmpty = !isLoading && !showError && rows !== undefined && rows.length === 0;

  return (
    <div className={cn("overflow-hidden rounded-lg border bg-card", className)}>
      <div className={cn("overflow-x-auto", maxHeightClass && `${maxHeightClass} overflow-y-auto`)}>
        <Table>
          <TableHeader className="sticky top-0 z-10 bg-muted/60 backdrop-blur">
            <TableRow className="hover:bg-transparent">
              {columns.map((c) => (
                <TableHead
                  key={c.key}
                  className={cn("h-9 text-xs font-medium text-muted-foreground uppercase", colClass(c))}
                >
                  {c.header}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading && !rows
              ? Array.from({ length: skeletonRows }, (_, i) => (
                  <TableRow key={i} className="hover:bg-transparent">
                    {columns.map((c) => (
                      <TableCell key={c.key} className={colClass(c)}>
                        <Skeleton className="h-4 w-full max-w-24" />
                      </TableCell>
                    ))}
                  </TableRow>
                ))
              : null}
            {!showError && rows
              ? rows.map((row) => (
                  <TableRow
                    key={rowKey(row)}
                    onClick={onRowClick ? () => onRowClick(row) : undefined}
                    onKeyDown={
                      onRowClick
                        ? (e) => {
                            if (e.key === "Enter" && e.target === e.currentTarget) onRowClick(row);
                          }
                        : undefined
                    }
                    tabIndex={onRowClick ? 0 : undefined}
                    className={cn(onRowClick && "cursor-pointer", rowClassName?.(row))}
                  >
                    {columns.map((c) => (
                      <TableCell key={c.key} className={cn("py-2", colClass(c))}>
                        {c.cell(row)}
                      </TableCell>
                    ))}
                  </TableRow>
                ))
              : null}
          </TableBody>
          {footer && rows && rows.length > 0 ? <TableFooter>{footer}</TableFooter> : null}
        </Table>
      </div>
      {showError ? <ErrorState error={error} onRetry={onRetry} /> : null}
      {showEmpty ? (
        <EmptyState title={emptyTitle} description={emptyDescription} action={emptyAction} />
      ) : null}
    </div>
  );
}
