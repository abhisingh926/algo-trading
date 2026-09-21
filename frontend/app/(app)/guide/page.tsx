import type { Metadata } from "next";
import { Info } from "lucide-react";
import { GuideContent } from "@/components/guide/guide-content";
import { OnboardingChecklist } from "@/components/guide/onboarding-checklist";
import { PageHeader, Section } from "@/components/layout/page-header";

export const metadata: Metadata = { title: "Guide" };

export default function GuidePage() {
  return (
    <>
      <PageHeader
        title="Guide"
        description="New here? Follow the checklist, then read how the platform works and what good practice looks like."
      />
      <div className="grid gap-6">
        <p className="flex gap-2.5 rounded-lg border bg-muted/40 p-3 text-sm text-muted-foreground">
          <Info className="mt-0.5 size-4 shrink-0" aria-hidden />
          <span>
            Nothing on this page is investment advice. Trading can lose money, and backtests or paper results do not
            guarantee future results.
          </span>
        </p>
        <OnboardingChecklist />
        <Section title="Learn the basics">
          <GuideContent />
        </Section>
      </div>
    </>
  );
}
