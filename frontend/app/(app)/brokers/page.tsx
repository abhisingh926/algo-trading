import type { Metadata } from "next";
import { KeyRound } from "lucide-react";
import { AddBrokerDialog } from "@/components/brokers/add-broker-dialog";
import { BrokerAccountsTable } from "@/components/brokers/broker-accounts-table";
import { BrokerStatusPanel } from "@/components/brokers/broker-status-panel";
import { PageHeader, Section } from "@/components/layout/page-header";

export const metadata: Metadata = { title: "Brokers" };

export default function BrokersPage() {
  return (
    <>
      <PageHeader
        title="Brokers"
        description="Broker accounts, connection health and order routing."
        actions={<AddBrokerDialog />}
      />
      <div className="grid gap-6">
        <p className="flex gap-2.5 rounded-lg border bg-muted/40 p-3 text-sm text-muted-foreground">
          <KeyRound className="mt-0.5 size-4 shrink-0" aria-hidden />
          <span>
            Broker credentials are set only through backend environment variables and are never sent to, stored in
            or displayed by this app. This page only shows whether credentials are configured. To change them, update
            the backend <code className="font-mono text-xs">.env</code> and restart the backend.
          </span>
        </p>
        <Section title="Accounts">
          <BrokerAccountsTable />
        </Section>
        <Section title="Routing & safety">
          <BrokerStatusPanel />
        </Section>
      </div>
    </>
  );
}
