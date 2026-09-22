import {
  AlertTriangle,
  CheckCircle2,
  CircleDashed,
  Info,
  Loader2,
  MinusCircle,
  OctagonAlert,
  SkipForward,
  XCircle,
  type LucideIcon,
} from "lucide-react";
import { Pill } from "@/components/trading/badges";
import {
  AGENT_STATUS_TEXT,
  CLAIM_STATUS_TEXT,
  DIRECTION_TEXT,
  MARKET_STATE_TEXT,
  QUALITY_TEXT,
  REGIME_TEXT,
  RISK_TEXT,
  TREND_TEXT,
} from "@/lib/research";
import { cn } from "@/lib/utils";
import type {
  AgentStatus,
  ClaimStatus,
  MarketState,
  RegimeLabel,
  ResearchDirection,
  RiskLevel,
  SetupQuality,
  Trend,
  WarningSeverity,
} from "@/types/research";

type Tone = "neutral" | "good" | "bad" | "warn" | "info";

export function RiskBadge({ level }: { level: RiskLevel | string | null | undefined }) {
  const l = (level ?? "UNKNOWN") as RiskLevel;
  const tone: Tone = l === "LOW" ? "good" : l === "MEDIUM" ? "warn" : l === "HIGH" ? "bad" : "neutral";
  return <Pill tone={tone}>{RISK_TEXT[l] ?? "Unknown"}</Pill>;
}

export function DirectionBadge({ direction }: { direction: ResearchDirection | string | null | undefined }) {
  if (!direction) return <span className="text-muted-foreground">—</span>;
  const d = direction as ResearchDirection;
  const tone: Tone = d === "BULLISH" ? "good" : d === "BEARISH" ? "bad" : "neutral";
  return <Pill tone={tone}>{DIRECTION_TEXT[d] ?? direction}</Pill>;
}

export function QualityBadge({ quality }: { quality: SetupQuality | string | null | undefined }) {
  if (!quality) return <span className="text-muted-foreground">—</span>;
  const q = quality as SetupQuality;
  const tone: Tone = q === "STRONG" ? "info" : q === "MODERATE" ? "neutral" : "neutral";
  return <Pill tone={tone}>{QUALITY_TEXT[q] ?? quality}</Pill>;
}

export function TrendBadge({ trend }: { trend: Trend | null | undefined }) {
  const t = trend ?? "UNKNOWN";
  const tone: Tone = t === "UP" ? "good" : t === "DOWN" ? "bad" : "neutral";
  return <Pill tone={tone}>{TREND_TEXT[t]}</Pill>;
}

export function RegimeBadge({ label }: { label: RegimeLabel }) {
  const tone: Tone =
    label === "STRONG_BULLISH" || label === "BULLISH"
      ? "good"
      : label === "STRONG_BEARISH" || label === "BEARISH"
        ? "bad"
        : "neutral";
  return <Pill tone={tone}>{REGIME_TEXT[label] ?? label}</Pill>;
}

export function MarketStateBadge({ state }: { state: MarketState }) {
  return (
    <Pill tone={state === "OPEN" ? "good" : "warn"} dot>
      {MARKET_STATE_TEXT[state] ?? state}
    </Pill>
  );
}

export function SyntheticBadge({ className }: { className?: string }) {
  return (
    <Pill tone="warn" className={cn("border-red-500/40 bg-red-500/10 text-red-500", className)}>
      Synthetic data
    </Pill>
  );
}

const CLAIM_TONE: Record<ClaimStatus, Tone> = {
  VERIFIED: "good",
  PARTIALLY_VERIFIED: "info",
  CONFLICTING: "bad",
  UNVERIFIED: "neutral",
  STALE: "warn",
};
export function ClaimStatusBadge({ status }: { status: ClaimStatus }) {
  return (
    <Pill tone={CLAIM_TONE[status] ?? "neutral"} dot>
      {CLAIM_STATUS_TEXT[status] ?? status}
    </Pill>
  );
}

const AGENT_ICON: Record<AgentStatus, { icon: LucideIcon; className: string }> = {
  SUCCESS: { icon: CheckCircle2, className: "text-profit" },
  PARTIAL: { icon: AlertTriangle, className: "text-warning" },
  RUNNING: { icon: Loader2, className: "animate-spin text-info" },
  PENDING: { icon: CircleDashed, className: "text-muted-foreground" },
  SKIPPED: { icon: SkipForward, className: "text-muted-foreground" },
  NOT_AVAILABLE: { icon: MinusCircle, className: "text-muted-foreground/70" },
  FAILED: { icon: XCircle, className: "text-loss" },
};
export function AgentStatusIcon({ status, className }: { status: AgentStatus | string; className?: string }) {
  const cfg = AGENT_ICON[status as AgentStatus] ?? AGENT_ICON.PENDING;
  const Icon = cfg.icon;
  return (
    <Icon
      className={cn("size-4 shrink-0", cfg.className, className)}
      aria-label={AGENT_STATUS_TEXT[status as AgentStatus] ?? status}
    />
  );
}

const SEVERITY: Record<WarningSeverity, { icon: LucideIcon; className: string; label: string }> = {
  INFO: { icon: Info, className: "text-info", label: "Info" },
  WARNING: { icon: AlertTriangle, className: "text-warning", label: "Warning" },
  HIGH: { icon: OctagonAlert, className: "text-loss", label: "High" },
};
export function SeverityIcon({ severity, className }: { severity: WarningSeverity; className?: string }) {
  const cfg = SEVERITY[severity] ?? SEVERITY.INFO;
  const Icon = cfg.icon;
  return <Icon className={cn("size-4 shrink-0", cfg.className, className)} aria-label={cfg.label} />;
}
