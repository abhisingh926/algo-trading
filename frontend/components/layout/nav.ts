import {
  Activity,
  ArrowLeftRight,
  BookOpen,
  Briefcase,
  Clock3,
  Gauge,
  Layers,
  Microscope,
  SlidersHorizontal,
  FlaskConical,
  LayoutDashboard,
  ListOrdered,
  Plug,
  ScrollText,
  Settings,
  ShieldAlert,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  /** Custom active test, for routes such as /research/[symbol] that belong to a nav item without matching its href. */
  match?: (pathname: string) => boolean;
}

export interface NavGroup {
  label: string;
  icon: LucideIcon;
  children: NavItem[];
}

export type NavEntry = NavItem | NavGroup;
export const isGroup = (entry: NavEntry): entry is NavGroup => "children" in entry;

const RESEARCH_SUBPAGES = ["/research/sectors", "/research/history", "/research/settings"];

export const NAV_ENTRIES: NavEntry[] = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/guide", label: "Guide", icon: BookOpen },
  { href: "/strategies", label: "Strategies", icon: Activity },
  { href: "/orders", label: "Orders", icon: ListOrdered },
  { href: "/positions", label: "Positions", icon: Briefcase },
  { href: "/trades", label: "Trades", icon: ArrowLeftRight },
  { href: "/backtesting", label: "Backtesting", icon: FlaskConical },
  {
    label: "Research",
    icon: Microscope,
    children: [
      {
        href: "/research",
        label: "Overview",
        icon: Gauge,
        // Overview also covers stock reports (/research/[symbol]).
        match: (p) => p.startsWith("/research") && !RESEARCH_SUBPAGES.some((s) => p === s || p.startsWith(`${s}/`)),
      },
      { href: "/research/sectors", label: "Sectors", icon: Layers },
      { href: "/research/history", label: "History", icon: Clock3 },
      { href: "/research/settings", label: "Settings", icon: SlidersHorizontal },
    ],
  },
  { href: "/brokers", label: "Brokers", icon: Plug },
  { href: "/risk", label: "Risk", icon: ShieldAlert },
  { href: "/events", label: "Logs", icon: ScrollText },
  { href: "/settings", label: "Settings", icon: Settings },
];
