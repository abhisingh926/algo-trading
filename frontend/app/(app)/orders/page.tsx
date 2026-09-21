import type { Metadata } from "next";
import { PageHeader } from "@/components/layout/page-header";
import { OrdersTable } from "@/components/tables/orders-table";
import { NewOrderDialog } from "@/components/trading/new-order-dialog";

export const metadata: Metadata = { title: "Orders" };

export default function OrdersPage() {
  return (
    <>
      <PageHeader
        title="Orders"
        description="Click an order to see its full event timeline."
        actions={<NewOrderDialog />}
      />
      <OrdersTable />
    </>
  );
}
