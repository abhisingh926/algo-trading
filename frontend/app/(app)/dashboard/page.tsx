import type { Metadata } from "next";
import { ActiveStrategiesTable } from "@/components/dashboard/active-strategies-table";
import { GettingStartedCard } from "@/components/dashboard/getting-started-card";
import { EquityCurvePanel } from "@/components/dashboard/equity-curve-panel";
import { OpenPositionsTable } from "@/components/dashboard/open-positions-table";
import { PortfolioStats } from "@/components/dashboard/portfolio-stats";
import { RecentOrdersTable } from "@/components/dashboard/recent-orders-table";
import { SystemStatusPanel } from "@/components/dashboard/system-status-panel";
import { PageHeader, Section } from "@/components/layout/page-header";

export const metadata: Metadata = { title: "Dashboard" };

export default function DashboardPage() {
  return (
    <>
      <PageHeader title="Dashboard" description="Portfolio, strategies and system health at a glance." />
      <div className="grid gap-5">
        <GettingStartedCard />
        <PortfolioStats />
        <div className="grid items-start gap-5 xl:grid-cols-3">
          <EquityCurvePanel className="xl:col-span-2" />
          <Section title="System Status">
            <SystemStatusPanel />
          </Section>
        </div>
        <div className="grid gap-5 xl:grid-cols-2">
          <Section title="Active Strategies">
            <ActiveStrategiesTable />
          </Section>
          <Section title="Open Positions">
            <OpenPositionsTable />
          </Section>
        </div>
        <Section title="Recent Orders">
          <RecentOrdersTable />
        </Section>
      </div>
    </>
  );
}
