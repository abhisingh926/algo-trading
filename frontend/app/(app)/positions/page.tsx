import type { Metadata } from "next";
import { PageHeader } from "@/components/layout/page-header";
import { PositionsTable } from "@/components/tables/positions-table";

export const metadata: Metadata = { title: "Positions" };

export default function PositionsPage() {
  return (
    <>
      <PageHeader title="Positions" description="Live positions with stop loss and target management." />
      <PositionsTable />
    </>
  );
}
