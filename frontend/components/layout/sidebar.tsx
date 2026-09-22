"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { CandlestickChart } from "lucide-react";
import { isGroup, NAV_ENTRIES, type NavItem } from "@/components/layout/nav";
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

function NavLink({
  item,
  active,
  nested,
  onNavigate,
}: {
  item: NavItem;
  active: boolean;
  nested?: boolean;
  onNavigate?: () => void;
}) {
  const Icon = item.icon;
  return (
    <Link
      href={item.href}
      onClick={onNavigate}
      aria-current={active ? "page" : undefined}
      className={cn(
        "flex h-9 items-center gap-2.5 rounded-md px-2.5 text-sm font-medium text-sidebar-foreground/70 transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
        nested && "h-8 pl-3 text-[13px]",
        active && "bg-sidebar-accent text-sidebar-accent-foreground",
      )}
    >
      <Icon className={cn("size-4 shrink-0", nested && "size-3.5")} />
      {item.label}
    </Link>
  );
}

const isActive = (pathname: string, item: NavItem) =>
  item.match ? item.match(pathname) : pathname === item.href || pathname.startsWith(`${item.href}/`);

export function SidebarNav({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  return (
    <nav aria-label="Main" className="flex flex-col gap-0.5">
      {NAV_ENTRIES.map((entry) => {
        if (!isGroup(entry)) {
          return (
            <NavLink key={entry.href} item={entry} active={isActive(pathname, entry)} onNavigate={onNavigate} />
          );
        }
        const GroupIcon = entry.icon;
        return (
          <div key={entry.label} role="group" aria-label={entry.label} className="mt-1.5 flex flex-col gap-0.5">
            <p className="flex h-7 items-center gap-2.5 px-2.5 text-[11px] font-semibold tracking-wide text-muted-foreground uppercase">
              <GroupIcon className="size-3.5" aria-hidden />
              {entry.label}
            </p>
            {entry.children.map((child) => (
              <NavLink
                key={child.href}
                item={child}
                nested
                active={isActive(pathname, child)}
                onNavigate={onNavigate}
              />
            ))}
          </div>
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
