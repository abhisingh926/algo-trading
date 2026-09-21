"use client";

import { useState } from "react";
import { Menu } from "lucide-react";
import { KillSwitchButton } from "@/components/layout/kill-switch";
import { Brand, SidebarNav } from "@/components/layout/sidebar";
import { ModeBadge, Pill } from "@/components/trading/badges";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { useSystemStatus } from "@/hooks/use-system";

export function Topbar() {
  const [navOpen, setNavOpen] = useState(false);
  const { data, isLoading, isError } = useSystemStatus();
  const halted = data?.system_state === "HALTED" || data?.kill_switch_active === true;

  return (
    <header className="sticky top-0 z-20 flex min-h-14 flex-wrap items-center gap-x-3 gap-y-2 border-b bg-background/95 px-3 py-2 backdrop-blur sm:px-5">
      <Button
        variant="ghost"
        size="icon"
        className="lg:hidden"
        onClick={() => setNavOpen(true)}
        aria-label="Open navigation"
      >
        <Menu />
      </Button>
      <Sheet open={navOpen} onOpenChange={(o) => setNavOpen(o)}>
        <SheetContent side="left" className="w-64 gap-0 bg-sidebar p-0">
          <SheetHeader className="flex h-14 justify-center border-b px-2 py-0">
            <SheetTitle className="sr-only">Navigation</SheetTitle>
            <SheetDescription className="sr-only">Main navigation</SheetDescription>
            <Brand />
          </SheetHeader>
          <div className="p-2">
            <SidebarNav onNavigate={() => setNavOpen(false)} />
          </div>
        </SheetContent>
      </Sheet>

      <div className="flex min-w-0 flex-1 flex-wrap items-center gap-2" aria-live="polite">
        {isLoading ? (
          <>
            <Skeleton className="h-5 w-16" />
            <Skeleton className="h-5 w-40" />
            <Skeleton className="h-5 w-20" />
          </>
        ) : data ? (
          <>
            <ModeBadge mode={data.trading_mode} />
            <Pill tone={data.live_trading_enabled ? "live" : "neutral"}>
              Live trading: {data.live_trading_enabled ? "Enabled" : "Disabled"}
            </Pill>
            <Pill tone={halted ? "bad" : "good"} dot>
              {halted ? "HALTED" : data.system_state}
            </Pill>
            {isError ? <Pill tone="warn">Status stale</Pill> : null}
          </>
        ) : (
          <Pill tone="bad" dot>
            Backend unreachable
          </Pill>
        )}
      </div>

      <KillSwitchButton disabled={halted} />
    </header>
  );
}
