import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

interface StatProps {
  label: string;
  value: React.ReactNode;
  sub?: React.ReactNode;
  loading?: boolean;
  valueClassName?: string;
}

export function Stat({ label, value, sub, loading, valueClassName }: StatProps) {
  return (
    <div className="min-w-0 bg-card px-4 py-3">
      <p className="truncate text-xs font-medium text-muted-foreground">{label}</p>
      {loading ? (
        <Skeleton className="mt-1.5 h-6 w-24" />
      ) : (
        <p className={cn("tabular mt-0.5 truncate text-lg font-semibold", valueClassName)}>{value}</p>
      )}
      {sub && !loading ? <p className="tabular truncate text-xs text-muted-foreground">{sub}</p> : null}
    </div>
  );
}

/** A row of stats separated by hairlines instead of one card per number. */
export function StatRow({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div
      className={cn(
        "grid grid-cols-2 gap-px overflow-hidden rounded-lg border bg-border sm:grid-cols-3 xl:grid-cols-6",
        className,
      )}
    >
      {children}
    </div>
  );
}
