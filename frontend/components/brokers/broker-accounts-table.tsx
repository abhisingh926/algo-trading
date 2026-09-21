"use client";

import { useState } from "react";
import { Loader2, PlugZap, Star, Trash2 } from "lucide-react";
import { ConfirmDialog } from "@/components/layout/confirm-dialog";
import { DataTable, type Column } from "@/components/tables/data-table";
import { ConnectionBadge, ModeBadge, Pill } from "@/components/trading/badges";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { useBrokers, useDeleteBroker, useTestBroker, useUpdateBroker } from "@/hooks/use-brokers";
import { formatDateTimeShort } from "@/lib/format";
import type { BrokerAccount } from "@/types";

export function BrokerAccountsTable() {
  const { data, isLoading, error, refetch } = useBrokers();
  const test = useTestBroker();
  const update = useUpdateBroker();
  const remove = useDeleteBroker();
  const [toDelete, setToDelete] = useState<BrokerAccount | null>(null);

  const columns: Column<BrokerAccount>[] = [
    {
      key: "name",
      header: "Account",
      cell: (b) => (
        <div className="flex items-center gap-2">
          <span className="font-medium">{b.name}</span>
          {b.is_default ? <Pill tone="info">Default</Pill> : null}
        </div>
      ),
    },
    { key: "type", header: "Broker", cell: (b) => b.broker_type },
    {
      key: "env",
      header: "Environment",
      hideBelow: "sm",
      cell: (b) => <ModeBadge mode={b.environment} />,
    },
    {
      key: "creds",
      header: "Credentials",
      hideBelow: "md",
      cell: (b) =>
        b.broker_type === "PAPER" ? (
          <span className="text-muted-foreground">Not required</span>
        ) : (
          <Pill tone={b.credentials_configured ? "good" : "warn"}>
            {b.credentials_configured ? "Configured" : "Not configured"}
          </Pill>
        ),
    },
    {
      key: "status",
      header: "Connection",
      cell: (b) => (
        <div>
          <ConnectionBadge status={b.connection_status} />
          {b.last_error ? (
            <p className="mt-0.5 max-w-56 truncate text-xs text-loss" title={b.last_error}>
              {b.last_error}
            </p>
          ) : null}
        </div>
      ),
    },
    {
      key: "checked",
      header: "Last Checked",
      hideBelow: "lg",
      className: "text-muted-foreground",
      cell: (b) => formatDateTimeShort(b.last_checked_at),
    },
    {
      key: "active",
      header: "Active",
      hideBelow: "md",
      cell: (b) => (
        <Switch
          size="sm"
          checked={b.is_active}
          aria-label={`${b.name} active`}
          disabled={update.isPending}
          onCheckedChange={(c) => update.mutate({ id: b.id, body: { is_active: c } })}
        />
      ),
    },
    {
      key: "actions",
      header: <span className="sr-only">Actions</span>,
      align: "right",
      cell: (b) => {
        const testing = test.isPending && test.variables === b.id;
        return (
          <div className="flex justify-end gap-1">
            <Button variant="outline" size="xs" disabled={testing} onClick={() => test.mutate(b.id)}>
              {testing ? <Loader2 className="animate-spin" /> : <PlugZap />} Test connection
            </Button>
            {!b.is_default ? (
              <Button
                variant="ghost"
                size="xs"
                disabled={update.isPending}
                onClick={() => update.mutate({ id: b.id, body: { is_default: true } })}
              >
                <Star /> Set default
              </Button>
            ) : null}
            <Button variant="destructive" size="icon-xs" aria-label={`Delete ${b.name}`} onClick={() => setToDelete(b)}>
              <Trash2 />
            </Button>
          </div>
        );
      },
    },
  ];

  return (
    <>
      <DataTable
        columns={columns}
        rows={data}
        rowKey={(b) => b.id}
        isLoading={isLoading}
        error={error}
        onRetry={() => void refetch()}
        skeletonRows={3}
        emptyTitle="No broker accounts"
        emptyDescription="Add a PAPER account to start paper trading, or register a real broker whose credentials are configured on the backend."
      />
      <ConfirmDialog
        open={!!toDelete}
        onOpenChange={(o) => {
          if (!o) setToDelete(null);
        }}
        title={`Delete "${toDelete?.name ?? ""}"?`}
        description="Strategies linked to this account fall back to the system default broker. Credentials on the backend are not affected."
        confirmLabel="Delete account"
        destructive
        pending={remove.isPending}
        onConfirm={() => toDelete && remove.mutate(toDelete.id, { onSuccess: () => setToDelete(null) })}
      />
    </>
  );
}
