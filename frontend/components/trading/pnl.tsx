import { formatPnl, pnlClass } from "@/lib/format";
import { cn } from "@/lib/utils";

export function Pnl({ value, className }: { value: number | null | undefined; className?: string }) {
  return <span className={cn("tabular font-medium", pnlClass(value), className)}>{formatPnl(value)}</span>;
}
