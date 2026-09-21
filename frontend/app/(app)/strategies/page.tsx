import type { Metadata } from "next";
import Link from "next/link";
import { Plus } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { StrategiesTable } from "@/components/tables/strategies-table";
import { buttonVariants } from "@/components/ui/button";

export const metadata: Metadata = { title: "Strategies" };

export default function StrategiesPage() {
  return (
    <>
      <PageHeader
        title="Strategies"
        description="Click a row to see configuration and recent signals."
        actions={
          <Link href="/strategies/new" className={buttonVariants()}>
            <Plus /> Create Strategy
          </Link>
        }
      />
      <StrategiesTable />
    </>
  );
}
