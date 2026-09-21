import type { Metadata } from "next";
import { PageHeader, Section } from "@/components/layout/page-header";
import { RiskLimitsForm } from "@/components/risk/risk-limits-form";
import { RiskUsagePanel } from "@/components/risk/risk-usage-panel";

export const metadata: Metadata = { title: "Risk" };

export default function RiskPage() {
  return (
    <>
      <PageHeader title="Risk" description="Account-level limits enforced on every order before it reaches a broker." />
      <div className="grid gap-6 xl:grid-cols-5">
        <Section title="Limits" className="xl:col-span-3">
          <RiskLimitsForm />
        </Section>
        <Section title="Usage today" className="xl:col-span-2">
          <RiskUsagePanel />
        </Section>
      </div>
    </>
  );
}
