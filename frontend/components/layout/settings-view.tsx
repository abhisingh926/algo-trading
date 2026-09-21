"use client";

import { useSyncExternalStore } from "react";
import { useRouter } from "next/navigation";
import { useTheme } from "next-themes";
import { LogOut, Monitor, Moon, Sun } from "lucide-react";
import { useAuth } from "@/components/layout/auth-provider";
import { Section } from "@/components/layout/page-header";
import { ErrorState } from "@/components/tables/states";
import { ModeBadge, Pill } from "@/components/trading/badges";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useSystemConfig } from "@/hooks/use-system";
import { API_BASE_URL, API_PREFIX } from "@/lib/api";
import { formatDateTime, formatFraction, formatINR, formatNumber } from "@/lib/format";
import { cn } from "@/lib/utils";

const THEMES = [
  { value: "light", label: "Light", icon: Sun },
  { value: "dark", label: "Dark", icon: Moon },
  { value: "system", label: "System", icon: Monitor },
] as const;

const noopSubscribe = () => () => {};
const YesNo = ({ value }: { value: boolean }) => <Pill tone={value ? "good" : "neutral"}>{value ? "Yes" : "No"}</Pill>;

export function SettingsView() {
  const { state, user, signOut } = useAuth();
  const router = useRouter();
  const { theme, setTheme } = useTheme();
  const mounted = useSyncExternalStore(noopSubscribe, () => true, () => false);
  const config = useSystemConfig();
  const c = config.data;

  return (
    <div className="grid gap-6 xl:grid-cols-2">
      <div className="grid content-start gap-6">
        <Section title="Account">
          <div className="rounded-lg border bg-card p-4 text-sm">
            {state === "open" ? (
              <p className="text-muted-foreground">
                Authentication is disabled on the backend (<code className="font-mono text-xs">auth_enabled = false</code>
                ). Anyone who can reach this app can trade. Enable auth before exposing it beyond localhost.
              </p>
            ) : user ? (
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="min-w-0">
                  <p className="flex items-center gap-2 font-medium">
                    {user.full_name} {user.is_admin ? <Pill tone="info">Admin</Pill> : null}
                  </p>
                  <p className="truncate text-muted-foreground">{user.email}</p>
                  <p className="text-xs text-muted-foreground">Member since {formatDateTime(user.created_at)}</p>
                </div>
                <Button
                  variant="outline"
                  onClick={() => {
                    signOut();
                    router.replace("/login");
                  }}
                >
                  <LogOut /> Log out
                </Button>
              </div>
            ) : (
              <Skeleton className="h-12 w-full" />
            )}
          </div>
        </Section>

        <Section title="Appearance">
          <div className="rounded-lg border bg-card p-4">
            <div role="radiogroup" aria-label="Theme" className="inline-grid grid-cols-3 gap-1 rounded-lg border p-0.5">
              {THEMES.map(({ value, label, icon: Icon }) => {
                const active = mounted && theme === value;
                return (
                  <button
                    key={value}
                    type="button"
                    role="radio"
                    aria-checked={active}
                    onClick={() => setTheme(value)}
                    className={cn(
                      "flex h-8 items-center justify-center gap-1.5 rounded-md px-3 text-sm font-medium transition-colors",
                      active ? "bg-secondary text-secondary-foreground" : "text-muted-foreground hover:bg-muted",
                    )}
                  >
                    <Icon className="size-4" /> {label}
                  </button>
                );
              })}
            </div>
          </div>
        </Section>

        <Section title="Frontend">
          <dl className="divide-y rounded-lg border bg-card text-sm">
            <Row label="Backend API">
              <code className="font-mono text-xs break-all">
                {API_BASE_URL}
                {API_PREFIX}
              </code>
            </Row>
            <Row label="Timezone">Asia/Kolkata (IST)</Row>
            <Row label="Currency">INR</Row>
          </dl>
        </Section>
      </div>

      <Section title="System configuration" description="Read-only. Change these through backend environment variables.">
        {config.isLoading ? (
          <Skeleton className="h-96 w-full" />
        ) : config.error && !c ? (
          <div className="rounded-lg border bg-card">
            <ErrorState error={config.error} onRetry={() => void config.refetch()} />
          </div>
        ) : c ? (
          <dl className="divide-y rounded-lg border bg-card text-sm">
            <Row label="Application">
              {c.app_name} <span className="text-muted-foreground">v{c.version}</span>
            </Row>
            <Row label="Environment">{c.app_env}</Row>
            <Row label="Trading mode">
              <ModeBadge mode={c.trading_mode} />
            </Row>
            <Row label="Live trading enabled">
              <Pill tone={c.live_trading_enabled ? "live" : "neutral"}>{c.live_trading_enabled ? "Enabled" : "Disabled"}</Pill>
            </Row>
            <Row label="Authentication enabled">
              <YesNo value={c.auth_enabled} />
            </Row>
            <Row label="Background workers enabled">
              <YesNo value={c.workers_enabled} />
            </Row>
            <Row label="Market data provider">{c.market_data_provider}</Row>
            <Row label="Paper initial capital">{formatINR(c.paper_initial_capital)}</Row>
            <Row label="Paper slippage">{formatFraction(c.paper_slippage_pct, 4)}</Row>
            <Row label="Strategy poll interval">{formatNumber(c.strategy_poll_seconds)} s</Row>
            <Row label="Order monitor poll interval">{formatNumber(c.order_monitor_poll_seconds)} s</Row>
            <Row label="Market data poll interval">{formatNumber(c.market_data_poll_seconds)} s</Row>
            <Row label="Brokerage per order">{formatINR(c.default_charges.brokerage_per_order)}</Row>
            <Row label="Brokerage">{formatFraction(c.default_charges.brokerage_pct, 4)}</Row>
            <Row label="STT (sell side)">{formatFraction(c.default_charges.stt_sell_pct, 4)}</Row>
            <Row label="Exchange transaction charge">{formatFraction(c.default_charges.exchange_txn_pct, 5)}</Row>
            <Row label="SEBI charge">{formatFraction(c.default_charges.sebi_pct, 5)}</Row>
            <Row label="Stamp duty (buy side)">{formatFraction(c.default_charges.stamp_duty_buy_pct, 4)}</Row>
            <Row label="GST">{formatFraction(c.default_charges.gst_pct, 2)}</Row>
            <Row label="Broker credentials configured">
              <span className="flex flex-wrap justify-end gap-1.5">
                {Object.entries(c.brokers_configured).map(([name, ok]) => (
                  <Pill key={name} tone={ok ? "good" : "neutral"}>
                    {name}: {ok ? "Yes" : "No"}
                  </Pill>
                ))}
              </span>
            </Row>
          </dl>
        ) : null}
      </Section>
    </div>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4 px-4 py-2">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="tabular min-w-0 text-right">{children}</dd>
    </div>
  );
}
