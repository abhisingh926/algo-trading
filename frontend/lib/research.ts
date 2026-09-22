import { DASH, formatDateTimeShort, formatTime } from "@/lib/format";
import type {
  AgentStatus,
  ClaimStatus,
  MarketState,
  RegimeLabel,
  ResearchDirection,
  ResearchSourceType,
  RiskLevel,
  SetupQuality,
  Trend,
} from "@/types/research";

type Maybe = number | null | undefined;
const missing = (v: Maybe): v is null | undefined => v === null || v === undefined || Number.isNaN(v);

/** Research Score / Data Confidence: 0..100 with at most one decimal. */
export function formatScore(v: Maybe): string {
  if (missing(v)) return DASH;
  return String(Math.round(v * 10) / 10);
}
/** A percent number that is already 0..100 (coverage, success rate). */
export function formatPct(v: Maybe, digits = 1, signed = false): string {
  if (missing(v)) return DASH;
  const s = `${Math.abs(v).toFixed(digits)}%`;
  if (v < 0) return `-${s}`;
  return signed && v > 0 ? `+${s}` : s;
}
/** Agent, provenance, claim, source and regime confidences are fractions (0..1). */
export function formatUnit(v: Maybe): string {
  if (missing(v)) return DASH;
  return `${Math.round(v * 100)}%`;
}
/** Relative volume, e.g. 1.02x */
export function formatMultiple(v: Maybe, digits = 2): string {
  if (missing(v)) return DASH;
  return `${v.toFixed(digits)}x`;
}
export function formatDecimal(v: Maybe, digits = 2): string {
  if (missing(v)) return DASH;
  return v.toFixed(digits);
}
/** Compact volume: 9,63,525 */
export function formatVolume(v: Maybe): string {
  if (missing(v)) return DASH;
  return new Intl.NumberFormat("en-IN").format(Math.round(v));
}

/** "15:30 IST" */
export function istClock(value: string | null | undefined): string {
  const t = formatTime(value);
  return t === DASH ? DASH : `${t.slice(0, 5)} IST`;
}
/** "21 Sept, 15:30 IST" */
export function istStamp(value: string | null | undefined): string {
  const t = formatDateTimeShort(value);
  return t === DASH ? DASH : `${t} IST`;
}
/** "Data as of 21 Sept, 15:30 IST" */
export function dataAsOf(value: string | null | undefined): string {
  const t = istStamp(value);
  return t === DASH ? "Data time unknown" : `Data as of ${t}`;
}

export function humanizeKey(key: string): string {
  const s = key.replace(/[_-]+/g, " ").toLowerCase();
  return s.charAt(0).toUpperCase() + s.slice(1);
}

/** Labels shown as chips on the report header, in reading order. */
export const LABEL_ORDER: { key: string; title: string }[] = [
  { key: "intraday_setup", title: "Setup quality" },
  { key: "direction", title: "Direction" },
  { key: "market_regime", title: "Market regime" },
  { key: "sector", title: "Sector" },
  { key: "liquidity", title: "Liquidity" },
  { key: "momentum", title: "Momentum" },
  { key: "volume", title: "Volume" },
  { key: "volatility", title: "Volatility" },
  { key: "news_catalyst", title: "News" },
  { key: "technical_structure", title: "Technical structure" },
  { key: "historical_setup", title: "Historical setup" },
  { key: "risk", title: "Risk" },
];

export const MARKET_STATE_TEXT: Record<MarketState, string> = {
  OPEN: "Market open",
  PRE_MARKET: "Pre-market",
  POST_MARKET: "Post-market",
  CLOSED: "Market closed",
};
export const REGIME_TEXT: Record<RegimeLabel, string> = {
  STRONG_BULLISH: "Strong bullish",
  BULLISH: "Bullish",
  RANGE: "Range-bound",
  BEARISH: "Bearish",
  STRONG_BEARISH: "Strong bearish",
  UNKNOWN: "Unknown",
};
export const DIRECTION_TEXT: Record<ResearchDirection, string> = {
  BULLISH: "Bullish",
  BEARISH: "Bearish",
  NEUTRAL: "Neutral",
};
export const QUALITY_TEXT: Record<SetupQuality, string> = {
  STRONG: "Strong setup",
  MODERATE: "Moderate setup",
  WEAK: "Weak setup",
  UNKNOWN: "Setup unknown",
};
export const RISK_TEXT: Record<RiskLevel, string> = {
  LOW: "Low",
  MEDIUM: "Medium",
  HIGH: "High",
  UNKNOWN: "Unknown",
};
export const TREND_TEXT: Record<Trend, string> = {
  UP: "Up",
  DOWN: "Down",
  SIDEWAYS: "Sideways",
  UNKNOWN: "Unknown",
};
export const SOURCE_TYPE_TEXT: Record<ResearchSourceType, string> = {
  EXCHANGE: "Exchange",
  REGULATOR: "Regulator",
  COMPANY_FILING: "Company filing",
  NEWS_PROVIDER: "News provider",
  FINANCIAL_PORTAL: "Financial portal",
  MARKET_DATA_PROVIDER: "Market data provider",
  SIMULATED: "Simulated feed",
  DERIVED: "Derived",
  OTHER: "Other",
};
export const CLAIM_STATUS_TEXT: Record<ClaimStatus, string> = {
  VERIFIED: "Verified",
  PARTIALLY_VERIFIED: "Partially verified",
  CONFLICTING: "Conflicting",
  UNVERIFIED: "Unverified",
  STALE: "Stale",
};
export const AGENT_STATUS_TEXT: Record<AgentStatus, string> = {
  PENDING: "Pending",
  RUNNING: "Running",
  SUCCESS: "Done",
  PARTIAL: "Partly done",
  FAILED: "Failed",
  SKIPPED: "Skipped",
  NOT_AVAILABLE: "Not available",
};

/** Shown next to every research page. Wording is deliberately neutral: this is decision support. */
export const SHORT_DISCLAIMER =
  "Research and decision support only. This is not investment advice or a recommendation to buy or sell. Scores describe how a setup measures up against explicit rules on the data available at the time, and have not been shown to predict profit.";

export const DEPTH_INFO = {
  QUICK: {
    label: "Quick",
    text: "Technical analysis of the top 10 scanned stocks. No historical setup statistics and no cross-source verification.",
  },
  STANDARD: {
    label: "Standard",
    text: "Top 20 scanned stocks, with 5-minute to daily analysis, historical setup statistics and data verification.",
  },
  DEEP: {
    label: "Deep",
    text: "Top 50 scanned stocks: everything in Standard plus the weekly timeframe. Takes the longest.",
  },
} as const;

/** Route to a stock report; the symbol is URL-encoded (M&M, BAJAJ-AUTO). */
export const reportHref = (symbol: string, runId?: string | null) =>
  `/research/${encodeURIComponent(symbol)}${runId ? `?run_id=${encodeURIComponent(runId)}` : ""}`;
/** Next may hand dynamic params over still encoded; decoding twice is harmless because symbols never contain %. */
export function decodeSymbol(raw: string): string {
  try {
    return decodeURIComponent(raw);
  } catch {
    return raw;
  }
}
