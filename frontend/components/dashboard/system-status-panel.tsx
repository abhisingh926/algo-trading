"use client";

import { ErrorState } from "@/components/tables/states";
import { ComponentStatusBadge, ModeBadge, Pill } from "@/components/trading/badges";
import { Skeleton } from "@/components/ui/skeleton";
import { useSystemStatus } from "@/hooks/use-system";
import { formatTime } from "@/lib/format";

export function SystemStatusPanel() {
  const { data, isLoading, error, refetch } = useSystemStatus();

  return (
    <div className="rounded-lg border bg-card">
      {isLoading ? (
        <div className="grid gap-3 p-4">
          {Array.from({ length: 6 }, (_, i) => (
            <Skeleton key={i} className="h-5 w-full" />
          ))}
        </div>
      ) : error && !data ? (
        <ErrorState error={error} onRetry={() => void refetch()} />
      ) : data ? (
        <dl className="divide-y text-sm">
          <Row label="Trading Mode">
            <ModeBadge mode={data.trading_mode} />
          </Row>
          <Row label="System State">
            <Pill tone={data.system_state === "RUNNING" ? "good" : "bad"} dot>
              {data.system_state}
            </Pill>
          </Row>
          {data.components.map((c) => (
            <Row key={c.key} label={c.name} detail={c.detail}>
              <ComponentStatusBadge status={c.status} />
            </Row>
          ))}
          <Row label="Market data provider">
            <span className="text-muted-foreground">{data.market_data_provider}</span>
          </Row>
          <Row label="Server time (IST)">
            <span className="tabular text-muted-foreground">{formatTime(data.server_time)}</span>
          </Row>
        </dl>
      ) : null}
    </div>
  );
}

function Row({ label, detail, children }: { label: string; detail?: string | null; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3 px-4 py-2">
      <dt className="min-w-0">
        <p className="truncate">{label}</p>
        {detail ? <p className="truncate text-xs text-muted-foreground" title={detail}>{detail}</p> : null}
      </dt>
      <dd className="shrink-0">{children}</dd>
    </div>
  );
}
