import type { Metadata } from "next";
import { PageHeader } from "@/components/layout/page-header";
import { EventsTable } from "@/components/tables/events-table";

export const metadata: Metadata = { title: "Logs" };

export default function EventsPage() {
  return (
    <>
      <PageHeader title="Logs" description="Audit trail of system events, newest first." />
      <EventsTable />
    </>
  );
}
