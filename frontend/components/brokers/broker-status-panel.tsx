"use client";

import { CheckCircle2, Route, XCircle } from "lucide-react";
import { ErrorState } from "@/components/tables/states";
import { ModeBadge, Pill } from "@/components/trading/badges";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useBrokerStatus } from "@/hooks/use-brokers";
import { humanize } from "@/lib/format";

export function BrokerStatusPanel() {
  const { data, isLoading, error, refetch } = useBrokerStatus();

  if (isLoading) return <Skeleton className="h-64 w-full" />;
  if (error && !data) {
    return (
      <div className="rounded-lg border bg-card">
        <ErrorState error={error} onRetry={() => void refetch()} />
      </div>
    );
  }
  if (!data) return null;
  const allPassed = data.live_guards.every((g) => g.passed);

  return (
    <div className="grid gap-4 xl:grid-cols-2">
      <div className="rounded-lg border bg-card p-4 xl:col-span-2">
        <div className="flex flex-wrap items-center gap-2">
          <Route className="size-4 text-muted-foreground" aria-hidden />
          <h3 className="text-sm font-semibold">Order routing</h3>
          <ModeBadge mode={data.trading_mode} />
          <Pill tone={data.live_trading_enabled ? "live" : "neutral"}>
            Live trading: {data.live_trading_enabled ? "Enabled" : "Disabled"}
          </Pill>
        </div>
        <p className="mt-2 text-sm">{data.order_routing}</p>
      </div>

      <div className="rounded-lg border bg-card p-4">
        <div className="mb-2 flex items-center justify-between gap-2">
          <h3 className="text-sm font-semibold">Live trading guards</h3>
          <Pill tone={allPassed ? "good" : "neutral"}>
            {data.live_guards.filter((g) => g.passed).length} / {data.live_guards.length} passed
          </Pill>
        </div>
        <p className="mb-3 text-xs text-muted-foreground">
          Every guard must pass before the backend sends an order to a real exchange.
        </p>
        {data.live_guards.length === 0 ? (
          <p className="text-sm text-muted-foreground">No guards reported.</p>
        ) : (
          <ul className="grid gap-2.5">
            {data.live_guards.map((g) => (
              <li key={g.name} className="flex gap-2.5 text-sm">
                {g.passed ? (
                  <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-profit" aria-label="Passed" />
                ) : (
                  <XCircle className="mt-0.5 size-4 shrink-0 text-loss" aria-label="Failed" />
                )}
                <div className="min-w-0">
                  <p className="font-medium">
                    {humanize(g.name)}{" "}
                    <span className="text-xs font-normal text-muted-foreground">{g.passed ? "passed" : "failed"}</span>
                  </p>
                  <p className="text-xs text-muted-foreground">{g.detail}</p>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="rounded-lg border bg-card p-4">
        <h3 className="mb-2 text-sm font-semibold">Broker adapters</h3>
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead>Broker</TableHead>
              <TableHead>Adapter</TableHead>
              <TableHead>Credentials</TableHead>
              <TableHead>Environments</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.supported.map((s) => (
              <TableRow key={s.broker_type}>
                <TableCell className="font-medium">{s.broker_type}</TableCell>
                <TableCell>
                  <Pill tone={s.implemented ? "good" : "neutral"}>{s.implemented ? "Implemented" : "Not implemented"}</Pill>
                </TableCell>
                <TableCell>
                  {s.broker_type === "PAPER" ? (
                    <span className="text-muted-foreground">Not required</span>
                  ) : (
                    <Pill tone={s.credentials_configured ? "good" : "warn"}>
                      {s.credentials_configured ? "Configured" : "Not configured"}
                    </Pill>
                  )}
                </TableCell>
                <TableCell className="text-muted-foreground">{s.environments.join(", ") || "—"}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
