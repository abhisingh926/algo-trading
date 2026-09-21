import {
  Activity,
  ArrowLeftRight,
  Briefcase,
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
}

export const NAV_ITEMS: NavItem[] = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/strategies", label: "Strategies", icon: Activity },
  { href: "/orders", label: "Orders", icon: ListOrdered },
  { href: "/positions", label: "Positions", icon: Briefcase },
  { href: "/trades", label: "Trades", icon: ArrowLeftRight },
  { href: "/backtesting", label: "Backtesting", icon: FlaskConical },
  { href: "/brokers", label: "Brokers", icon: Plug },
  { href: "/risk", label: "Risk", icon: ShieldAlert },
  { href: "/events", label: "Logs", icon: ScrollText },
  { href: "/settings", label: "Settings", icon: Settings },
];
