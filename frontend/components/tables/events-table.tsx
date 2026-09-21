"use client";

import { Fragment, useState } from "react";
import { ChevronDown, ChevronRight, RefreshCw } from "lucide-react";
import { SimpleSelect, type SelectOption } from "@/components/layout/form-controls";
import { EmptyState, ErrorState } from "@/components/tables/states";
import { LevelBadge } from "@/components/trading/badges";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useEvents } from "@/hooks/use-system";
import { formatDateTime, humanize } from "@/lib/format";
import { cn } from "@/lib/utils";
import { EVENT_TYPES, type EventLevel } from "@/types";

const ALL = "__all__";
const PAGE_SIZE = 100;

const LEVEL_OPTIONS: SelectOption[] = [
  { value: ALL, label: "All levels" },
  { value: "INFO", label: "Info" },
  { value: "WARNING", label: "Warning" },
  { value: "ERROR", label: "Error" },
];
const TYPE_OPTIONS: SelectOption[] = [
  { value: ALL, label: "All event types" },
  ...EVENT_TYPES.map((t) => ({ value: t, label: humanize(t) })),
];

export function EventsTable() {
  const [level, setLevel] = useState<string>(ALL);
  const [eventType, setEventType] = useState<string>(ALL);
  const [page, setPage] = useState(0);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  const { data, isLoading, isFetching, error, refetch } = useEvents(
    {
      limit: PAGE_SIZE,
      offset: page * PAGE_SIZE,
      level: level === ALL ? undefined : (level as EventLevel),
      event_type: eventType === ALL ? undefined : eventType,
    },
    // Only auto refresh the newest page so older pages do not shift under the reader.
    autoRefresh && page === 0,
  );

  const toggle = (id: string) =>
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  const showError = !!error && !data;

  return (
    <div className="grid gap-3">
      <div className="flex flex-wrap items-center gap-2">
        <div className="w-full sm:w-40">
          <SimpleSelect
            value={level}
            onChange={(v) => {
              setLevel(v);
              setPage(0);
            }}
            options={LEVEL_OPTIONS}
          />
        </div>
        <div className="w-full sm:w-56">
          <SimpleSelect
            value={eventType}
            onChange={(v) => {
              setEventType(v);
              setPage(0);
            }}
            options={TYPE_OPTIONS}
          />
        </div>
        <div className="ml-auto flex items-center gap-3">
          <div className="flex items-center gap-2">
            <Switch id="events-auto" size="sm" checked={autoRefresh} onCheckedChange={(c) => setAutoRefresh(c)} />
            <Label htmlFor="events-auto" className="text-xs text-muted-foreground">
              Auto refresh (5s)
            </Label>
          </div>
          <Button variant="outline" size="sm" onClick={() => void refetch()} disabled={isFetching}>
            <RefreshCw className={cn(isFetching && "animate-spin")} /> Refresh
          </Button>
        </div>
      </div>

      <div className="overflow-hidden rounded-lg border bg-card">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader className="bg-muted/60">
              <TableRow className="hover:bg-transparent">
                <TableHead className="w-8" />
                <TableHead className="h-9 text-xs text-muted-foreground uppercase">Time (IST)</TableHead>
                <TableHead className="h-9 text-xs text-muted-foreground uppercase">Level</TableHead>
                <TableHead className="h-9 text-xs text-muted-foreground uppercase">Type</TableHead>
                <TableHead className="h-9 text-xs text-muted-foreground uppercase">Message</TableHead>
                <TableHead className="hidden h-9 text-xs text-muted-foreground uppercase sm:table-cell">Symbol</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading && !data
                ? Array.from({ length: 10 }, (_, i) => (
                    <TableRow key={i} className="hover:bg-transparent">
                      {Array.from({ length: 6 }, (_, j) => (
                        <TableCell key={j} className={j === 5 ? "hidden sm:table-cell" : undefined}>
                          <Skeleton className="h-4 w-full max-w-32" />
                        </TableCell>
                      ))}
                    </TableRow>
                  ))
                : null}
              {!showError
                ? data?.map((ev) => {
                    const hasPayload = !!ev.payload && Object.keys(ev.payload).length > 0;
                    const hasDetails = hasPayload || !!ev.strategy_id || !!ev.order_id;
                    const open = expanded.has(ev.id);
                    return (
                      <Fragment key={ev.id}>
                        <TableRow
                          className={cn(hasDetails && "cursor-pointer", ev.level === "ERROR" && "bg-loss/5")}
                          onClick={hasDetails ? () => toggle(ev.id) : undefined}
                        >
                          <TableCell className="py-2 pr-0">
                            {hasDetails ? (
                              <button
                                type="button"
                                aria-expanded={open}
                                aria-label={open ? "Hide details" : "Show details"}
                                className="flex size-5 items-center justify-center rounded text-muted-foreground hover:bg-muted"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  toggle(ev.id);
                                }}
                              >
                                {open ? <ChevronDown className="size-4" /> : <ChevronRight className="size-4" />}
                              </button>
                            ) : null}
                          </TableCell>
                          <TableCell className="py-2 whitespace-nowrap text-muted-foreground">
                            {formatDateTime(ev.created_at)}
                          </TableCell>
                          <TableCell className="py-2">
                            <LevelBadge level={ev.level} />
                          </TableCell>
                          <TableCell className="py-2 font-mono text-xs whitespace-nowrap">{ev.event_type}</TableCell>
                          <TableCell className="max-w-xl min-w-64 py-2 whitespace-normal">{ev.message}</TableCell>
                          <TableCell className="hidden py-2 font-medium sm:table-cell">{ev.symbol ?? "—"}</TableCell>
                        </TableRow>
                        {open ? (
                          <TableRow className="bg-muted/30 hover:bg-muted/30">
                            <TableCell />
                            <TableCell colSpan={5} className="py-2 whitespace-normal">
                              <div className="flex flex-wrap gap-x-4 gap-y-1 font-mono text-xs text-muted-foreground">
                                {ev.strategy_id ? <span>strategy_id: {ev.strategy_id}</span> : null}
                                {ev.order_id ? <span>order_id: {ev.order_id}</span> : null}
                              </div>
                              {hasPayload ? (
                                <pre className="mt-1 max-h-72 overflow-auto rounded-md bg-muted/60 p-2.5 font-mono text-xs">
                                  {JSON.stringify(ev.payload, null, 2)}
                                </pre>
                              ) : null}
                            </TableCell>
                          </TableRow>
                        ) : null}
                      </Fragment>
                    );
                  })
                : null}
            </TableBody>
          </Table>
        </div>
        {showError ? <ErrorState error={error} onRetry={() => void refetch()} /> : null}
        {!isLoading && !showError && data?.length === 0 ? (
          <EmptyState
            title={page > 0 ? "No more events" : "No events match"}
            description="System events such as signals, orders, fills and kill switch activity are logged here."
          />
        ) : null}
      </div>

      <div className="flex items-center justify-between gap-2 text-xs text-muted-foreground">
        <span>
          Page {page + 1}
          {data ? ` · ${data.length} events` : ""}
        </span>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" disabled={page === 0} onClick={() => setPage((p) => Math.max(0, p - 1))}>
            Newer
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={!data || data.length < PAGE_SIZE}
            onClick={() => setPage((p) => p + 1)}
          >
            Older
          </Button>
        </div>
      </div>
    </div>
  );
}
