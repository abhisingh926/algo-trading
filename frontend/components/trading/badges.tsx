import { cn } from "@/lib/utils";
import type {
  BacktestStatus,
  BrokerConnectionStatus,
  ComponentStatus,
  EventLevel,
  OrderSide,
  OrderStatus,
  PositionSide,
  SignalStatus,
  SignalType,
  StrategyStatus,
  TradingMode,
} from "@/types";

type Tone = "neutral" | "good" | "bad" | "warn" | "info" | "live";

const toneClass: Record<Tone, string> = {
  neutral: "border-border bg-muted text-muted-foreground",
  good: "border-profit/30 bg-profit/10 text-profit",
  bad: "border-loss/30 bg-loss/10 text-loss",
  warn: "border-warning/30 bg-warning/10 text-warning",
  info: "border-info/30 bg-info/10 text-info",
  live: "border-red-600 bg-red-600 text-white",
};

export function Pill({
  tone = "neutral",
  children,
  className,
  dot,
}: {
  tone?: Tone;
  children: React.ReactNode;
  className?: string;
  dot?: boolean;
}) {
  return (
    <span
      className={cn(
        "inline-flex h-5 items-center gap-1.5 rounded-md border px-1.5 text-[11px] font-semibold tracking-wide whitespace-nowrap uppercase",
        toneClass[tone],
        className,
      )}
    >
      {dot ? <span className="size-1.5 rounded-full bg-current" aria-hidden /> : null}
      {children}
    </span>
  );
}

const label = (s: string) => s.replace(/_/g, " ");

const modeTone: Record<TradingMode, Tone> = {
  BACKTEST: "neutral",
  PAPER: "info",
  SANDBOX: "warn",
  LIVE: "live",
};
export function ModeBadge({ mode, className }: { mode: TradingMode; className?: string }) {
  return (
    <Pill tone={modeTone[mode] ?? "neutral"} className={className}>
      {mode}
    </Pill>
  );
}

const orderTone: Record<OrderStatus, Tone> = {
  CREATED: "info",
  SUBMITTED: "info",
  OPEN: "info",
  TRIGGER_PENDING: "warn",
  PARTIALLY_FILLED: "warn",
  FILLED: "good",
  CANCELLED: "neutral",
  EXPIRED: "neutral",
  REJECTED: "bad",
  FAILED: "bad",
};
export function OrderStatusBadge({ status }: { status: OrderStatus }) {
  return <Pill tone={orderTone[status] ?? "neutral"}>{label(status)}</Pill>;
}

const strategyTone: Record<StrategyStatus, Tone> = {
  RUNNING: "good",
  STOPPED: "neutral",
  ERROR: "bad",
};
export function StrategyStatusBadge({ status }: { status: StrategyStatus }) {
  return (
    <Pill tone={strategyTone[status] ?? "neutral"} dot>
      {status}
    </Pill>
  );
}

export function SideBadge({ side }: { side: OrderSide | PositionSide | SignalType }) {
  const tone: Tone = side === "BUY" || side === "LONG" ? "good" : side === "HOLD" ? "neutral" : "bad";
  return <Pill tone={tone}>{side}</Pill>;
}

const componentTone: Record<ComponentStatus, Tone> = {
  CONNECTED: "good",
  RUNNING: "good",
  DISCONNECTED: "bad",
  HALTED: "bad",
  STOPPED: "neutral",
  NOT_CONFIGURED: "neutral",
  DEGRADED: "warn",
};
export function ComponentStatusBadge({ status }: { status: ComponentStatus }) {
  return (
    <Pill tone={componentTone[status] ?? "neutral"} dot>
      {label(status)}
    </Pill>
  );
}

const connectionTone: Record<BrokerConnectionStatus, Tone> = {
  CONNECTED: "good",
  DISCONNECTED: "bad",
  NOT_CONFIGURED: "warn",
  UNKNOWN: "neutral",
};
export function ConnectionBadge({ status }: { status: BrokerConnectionStatus }) {
  return (
    <Pill tone={connectionTone[status] ?? "neutral"} dot>
      {label(status)}
    </Pill>
  );
}

const levelTone: Record<EventLevel, Tone> = { INFO: "info", WARNING: "warn", ERROR: "bad" };
export function LevelBadge({ level }: { level: EventLevel }) {
  return <Pill tone={levelTone[level] ?? "neutral"}>{level}</Pill>;
}

const signalTone: Record<SignalStatus, Tone> = {
  GENERATED: "info",
  EXECUTED: "good",
  REJECTED: "bad",
  IGNORED: "neutral",
};
export function SignalStatusBadge({ status }: { status: SignalStatus }) {
  return <Pill tone={signalTone[status] ?? "neutral"}>{status}</Pill>;
}

const backtestTone: Record<BacktestStatus, Tone> = {
  PENDING: "neutral",
  RUNNING: "info",
  COMPLETED: "good",
  FAILED: "bad",
};
export function BacktestStatusBadge({ status }: { status: BacktestStatus }) {
  return <Pill tone={backtestTone[status] ?? "neutral"}>{status}</Pill>;
}
