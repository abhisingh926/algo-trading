"use client";

import { ErrorState } from "@/components/tables/states";
import { ModeBadge, OrderStatusBadge, SideBadge } from "@/components/trading/badges";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { useOrder } from "@/hooks/use-orders";
import { formatDateTime, formatNumber, formatPrice, humanize } from "@/lib/format";

export function OrderDetailDialog({
  orderId,
  onOpenChange,
}: {
  orderId: string | null;
  onOpenChange: (open: boolean) => void;
}) {
  const { data: order, isLoading, error, refetch } = useOrder(orderId);
  const events = [...(order?.events ?? [])].sort((a, b) => a.created_at.localeCompare(b.created_at));

  return (
    <Dialog open={!!orderId} onOpenChange={(o) => onOpenChange(o)}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex flex-wrap items-center gap-2">
            {order ? (
              <>
                <SideBadge side={order.side} /> {formatNumber(order.quantity)} × {order.symbol}
                <OrderStatusBadge status={order.status} /> <ModeBadge mode={order.trading_mode} />
              </>
            ) : (
              "Order details"
            )}
          </DialogTitle>
          <DialogDescription className="font-mono text-xs break-all">{orderId}</DialogDescription>
        </DialogHeader>

        {isLoading ? (
          <div className="grid gap-2">
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-32 w-full" />
          </div>
        ) : error && !order ? (
          <ErrorState error={error} onRetry={() => void refetch()} />
        ) : order ? (
          <>
            <dl className="grid grid-cols-2 gap-x-4 gap-y-2 rounded-lg border bg-muted/30 p-3 text-sm sm:grid-cols-4">
              <Item label="Type" value={`${order.order_type} · ${humanize(order.product_type)}`} />
              <Item label="Exchange" value={order.exchange} />
              <Item label="Filled / Qty" value={`${formatNumber(order.filled_quantity)} / ${formatNumber(order.quantity)}`} />
              <Item label="Pending" value={formatNumber(order.pending_quantity)} />
              <Item label="Price" value={formatPrice(order.price)} />
              <Item label="Trigger" value={formatPrice(order.trigger_price)} />
              <Item label="Avg fill" value={formatPrice(order.average_fill_price)} />
              <Item label="Retries" value={formatNumber(order.retry_count)} />
              <Item label="Stop loss" value={formatPrice(order.stop_loss)} />
              <Item label="Target" value={formatPrice(order.target)} />
              <Item label="Source" value={humanize(order.source)} />
              <Item label="Strategy" value={order.strategy_name ?? "—"} />
              <Item label="Broker" value={order.broker_type ?? "—"} />
              <Item label="Broker order ID" value={order.broker_order_id ?? "—"} />
              <Item label="Created" value={formatDateTime(order.created_at)} />
              <Item label="Updated" value={formatDateTime(order.updated_at)} />
            </dl>
            {order.status_message ? (
              <p className="rounded-md border bg-muted/30 p-2.5 text-sm">
                <span className="text-muted-foreground">Status message: </span>
                {order.status_message}
              </p>
            ) : null}

            <div>
              <h3 className="mb-2 text-sm font-semibold">Event timeline</h3>
              {events.length === 0 ? (
                <p className="text-sm text-muted-foreground">No events recorded for this order.</p>
              ) : (
                <ol className="relative ml-1.5 grid gap-3 border-l pl-4">
                  {events.map((ev) => (
                    <li key={ev.id} className="relative text-sm">
                      <span className="absolute top-1.5 -left-[21px] size-2.5 rounded-full border-2 border-popover bg-muted-foreground" aria-hidden />
                      <div className="flex flex-wrap items-baseline gap-x-2">
                        <span className="font-medium">{humanize(ev.event_type)}</span>
                        {ev.to_status ? (
                          <span className="text-xs text-muted-foreground">
                            {ev.from_status ? `${ev.from_status} → ` : ""}
                            {ev.to_status}
                          </span>
                        ) : null}
                        <time className="tabular ml-auto text-xs text-muted-foreground">
                          {formatDateTime(ev.created_at)}
                        </time>
                      </div>
                      {ev.message ? <p className="text-muted-foreground">{ev.message}</p> : null}
                      {ev.payload && Object.keys(ev.payload).length > 0 ? (
                        <pre className="mt-1 max-h-32 overflow-auto rounded bg-muted/50 p-2 font-mono text-[11px]">
                          {JSON.stringify(ev.payload, null, 2)}
                        </pre>
                      ) : null}
                    </li>
                  ))}
                </ol>
              )}
            </div>
          </>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}

function Item({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="tabular truncate" title={value}>
        {value}
      </dd>
    </div>
  );
}
