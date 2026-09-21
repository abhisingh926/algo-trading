"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { CandlestickChart } from "lucide-react";
import { NAV_ITEMS } from "@/components/layout/nav";
import { cn } from "@/lib/utils";

export function Brand() {
  return (
    <Link href="/dashboard" className="flex items-center gap-2 px-2 font-heading font-semibold">
      <span className="flex size-7 items-center justify-center rounded-md bg-primary text-primary-foreground">
        <CandlestickChart className="size-4" />
      </span>
      <span className="tracking-tight">AlgoDesk</span>
    </Link>
  );
}

export function SidebarNav({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  return (
    <nav aria-label="Main" className="flex flex-col gap-0.5">
      {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
        const active = pathname === href || pathname.startsWith(`${href}/`);
        return (
          <Link
            key={href}
            href={href}
            onClick={onNavigate}
            aria-current={active ? "page" : undefined}
            className={cn(
              "flex h-9 items-center gap-2.5 rounded-md px-2.5 text-sm font-medium text-sidebar-foreground/70 transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
              active && "bg-sidebar-accent text-sidebar-accent-foreground",
            )}
          >
            <Icon className="size-4 shrink-0" />
            {label}
          </Link>
        );
      })}
    </nav>
  );
}

export function Sidebar() {
  return (
    <aside className="fixed inset-y-0 left-0 z-30 hidden w-56 flex-col border-r border-sidebar-border bg-sidebar lg:flex">
      <div className="flex h-14 items-center border-b border-sidebar-border px-2">
        <Brand />
      </div>
      <div className="flex-1 overflow-y-auto p-2">
        <SidebarNav />
      </div>
      <p className="border-t border-sidebar-border px-4 py-3 text-[11px] leading-snug text-muted-foreground">
        NSE / BSE · All times IST
      </p>
    </aside>
  );
}
