import { AlertTriangle, Clock, FlaskConical, Scissors, ShieldQuestion, Swords } from "lucide-react";
import { istStamp } from "@/lib/research";
import { cn } from "@/lib/utils";

type Tone = "danger" | "warn" | "info";
const TONE: Record<Tone, string> = {
  danger: "border-red-500/50 bg-red-500/10 text-red-500",
  warn: "border-warning/40 bg-warning/10 text-warning",
  info: "border-info/30 bg-info/10 text-info",
};

export function Banner({
  tone,
  icon: Icon,
  title,
  children,
  className,
}: {
  tone: Tone;
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  children?: React.ReactNode;
  className?: string;
}) {
  return (
    <div role="note" className={cn("flex gap-2.5 rounded-lg border p-3 text-sm", TONE[tone], className)}>
      <Icon className="mt-0.5 size-4 shrink-0" aria-hidden />
      <div className="min-w-0">
        <p className="font-semibold">{title}</p>
        {children ? <div className="mt-0.5 text-[13px] opacity-90">{children}</div> : null}
      </div>
    </div>
  );
}

/** Red-amber banner for runs and reports built on the simulated feed. */
export function SyntheticDataBanner({ className }: { className?: string }) {
  return (
    <Banner tone="danger" icon={FlaskConical} title="Synthetic data: these numbers are test data" className={className}>
      Prices and volumes come from the simulated feed, not the real market. Scores are for exercising the platform only.
      Data Confidence is capped at 30 and nothing here should inform a real decision.
    </Banner>
  );
}

export function MarketClosedBanner({ note, asOf, className }: { note?: string; asOf?: string; className?: string }) {
  return (
    <Banner
      tone="warn"
      icon={Clock}
      title="Market not open: this is an analysis of the last regular session"
      className={className}
    >
      {note ?? "The figures are not live."}
      {asOf ? ` Data as of ${istStamp(asOf)}.` : ""}
    </Banner>
  );
}

export function StaleDataBanner({ message, className }: { message?: string; className?: string }) {
  return (
    <Banner tone="warn" icon={AlertTriangle} title="Stale data" className={className}>
      {message ?? "Some of the data is older than expected, so recent moves may be missing."}
    </Banner>
  );
}

export function ConflictBanner({ count, className }: { count: number; className?: string }) {
  return (
    <Banner tone="danger" icon={Swords} title={`Conflicting data (${count})`} className={className}>
      Sources disagree on at least one figure. See Data verification for both values and how it was handled.
    </Banner>
  );
}

export function ScoreCappedBanner({
  reason,
  raw,
  capped,
  className,
}: {
  reason?: string | null;
  raw?: number | null;
  capped?: number | null;
  className?: string;
}) {
  return (
    <Banner tone="warn" icon={Scissors} title="Score capped" className={className}>
      {reason ?? "The Research Score was limited because of data or risk problems."}
      {raw !== null && raw !== undefined && capped !== null && capped !== undefined
        ? ` Raw score ${raw}, shown ${capped}.`
        : ""}
    </Banner>
  );
}

export function PartialCoverageBanner({ pct, className }: { pct: number; className?: string }) {
  return (
    <Banner
      tone="info"
      icon={ShieldQuestion}
      title={`The score covers ${Math.round(pct)}% of the scoring weights`}
      className={className}
    >
      Components that could not be assessed are shown as &quot;Not assessed&quot;. They are not counted as zero, but the
      score says nothing about them.
    </Banner>
  );
}
