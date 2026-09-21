import type { Metadata } from "next";
import { PageHeader } from "@/components/layout/page-header";
import { TradesTable } from "@/components/tables/trades-table";

export const metadata: Metadata = { title: "Trades" };

export default function TradesPage() {
  return (
    <>
      <PageHeader title="Trades" description="Closed round trips with charges and net P&L. Totals reflect the rows shown." />
      <TradesTable />
    </>
  );
}
