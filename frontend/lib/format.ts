const IST = "Asia/Kolkata";
export const DASH = "—";

const inr = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});
const inrWhole = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 0,
});
const inrCompact = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  notation: "compact",
  maximumFractionDigits: 1,
});
const num = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 2 });
const price = new Intl.NumberFormat("en-IN", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

type Maybe = number | null | undefined;
const missing = (v: Maybe): v is null | undefined => v === null || v === undefined || Number.isNaN(v);

/** ₹5,00,000.00 */
export function formatINR(value: Maybe, opts: { whole?: boolean } = {}): string {
  if (missing(value)) return DASH;
  return (opts.whole ? inrWhole : inr).format(value);
}
/** ₹5L, ₹1.2Cr: for chart axes. */
export function formatINRCompact(value: Maybe): string {
  if (missing(value)) return DASH;
  return inrCompact.format(value);
}
/** +₹1,250.00 / -₹300.00 */
export function formatPnl(value: Maybe): string {
  if (missing(value)) return DASH;
  const abs = inr.format(Math.abs(value));
  if (value > 0) return `+${abs}`;
  if (value < 0) return `-${abs}`;
  return abs;
}
export function pnlClass(value: Maybe): string {
  if (missing(value) || value === 0) return "text-muted-foreground";
  return value > 0 ? "text-profit" : "text-loss";
}
/** Plain price without currency symbol, 2 decimals, Indian grouping. */
export function formatPrice(value: Maybe): string {
  if (missing(value)) return DASH;
  return price.format(value);
}
export function formatNumber(value: Maybe): string {
  if (missing(value)) return DASH;
  return num.format(value);
}
/** For metrics that are already percent numbers (71.4 -> "71.4%"). */
export function formatPercent(value: Maybe, digits = 1, signed = false): string {
  if (missing(value)) return DASH;
  const s = `${Math.abs(value).toFixed(digits)}%`;
  if (signed && value > 0) return `+${s}`;
  return value < 0 ? `-${s}` : s;
}
/** For config fractions (0.01 -> "1%"). */
export function formatFraction(value: Maybe, digits = 2): string {
  if (missing(value)) return DASH;
  return `${trimZeros((value * 100).toFixed(digits))}%`;
}
function trimZeros(s: string): string {
  return s.includes(".") ? s.replace(/\.?0+$/, "") : s;
}

/** fraction -> percent number for form inputs, avoiding float noise (0.07 * 100). */
export function fractionToPercent(value: Maybe): number | null {
  if (missing(value)) return null;
  return Number((value * 100).toFixed(6));
}
export function percentToFraction(value: number): number {
  return Number((value / 100).toFixed(8));
}

function toDate(value: string | Date | null | undefined): Date | null {
  if (!value) return null;
  const d = value instanceof Date ? value : new Date(value);
  return Number.isNaN(d.getTime()) ? null : d;
}
const dtf = new Intl.DateTimeFormat("en-IN", {
  timeZone: IST,
  day: "2-digit",
  month: "short",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
  hour12: false,
});
const dtfShort = new Intl.DateTimeFormat("en-IN", {
  timeZone: IST,
  day: "2-digit",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});
const tf = new Intl.DateTimeFormat("en-IN", {
  timeZone: IST,
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
  hour12: false,
});
const df = new Intl.DateTimeFormat("en-IN", {
  timeZone: IST,
  day: "2-digit",
  month: "short",
  year: "numeric",
});

/** 18 Sep 2026, 15:30:00 (IST) */
export function formatDateTime(value: string | Date | null | undefined): string {
  const d = toDate(value);
  return d ? dtf.format(d) : DASH;
}
export function formatDateTimeShort(value: string | Date | null | undefined): string {
  const d = toDate(value);
  return d ? dtfShort.format(d) : DASH;
}
export function formatTime(value: string | Date | null | undefined): string {
  const d = toDate(value);
  return d ? tf.format(d) : DASH;
}
/** Accepts ISO datetimes and plain YYYY-MM-DD dates. */
export function formatDate(value: string | Date | null | undefined): string {
  if (typeof value === "string" && /^\d{4}-\d{2}-\d{2}$/.test(value)) {
    const [y, m, d] = value.split("-").map(Number);
    return df.format(new Date(Date.UTC(y, m - 1, d, 12)));
  }
  const d = toDate(value);
  return d ? df.format(d) : DASH;
}
/** Today (or an offset of days) as YYYY-MM-DD in IST. */
export function istDateString(offsetDays = 0): string {
  const d = new Date(Date.now() + offsetDays * 86_400_000);
  return new Intl.DateTimeFormat("en-CA", { timeZone: IST }).format(d);
}

export function humanize(value: string | null | undefined): string {
  if (!value) return DASH;
  const s = value.replace(/[_-]+/g, " ").toLowerCase();
  return s.charAt(0).toUpperCase() + s.slice(1);
}
