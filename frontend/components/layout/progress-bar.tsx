import { cn } from "@/lib/utils";

/** Simple accessible progress bar. `value` is 0..100. */
export function ProgressBar({
  value,
  label,
  className,
  barClassName,
}: {
  value: number;
  label: string;
  className?: string;
  barClassName?: string;
}) {
  const pct = Math.max(0, Math.min(100, Number.isFinite(value) ? value : 0));
  return (
    <div
      role="progressbar"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={Math.round(pct)}
      className={cn("h-1.5 overflow-hidden rounded-full bg-muted", className)}
    >
      <div
        className={cn("h-full rounded-full bg-profit transition-[width]", barClassName)}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}
