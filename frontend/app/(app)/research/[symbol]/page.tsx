import { Suspense } from "react";
import type { Metadata } from "next";
import { ReportPage } from "@/components/research/report/report-page";

export const metadata: Metadata = { title: "Research report" };

export default async function ResearchSymbolPage({ params }: { params: Promise<{ symbol: string }> }) {
  const { symbol } = await params;
  return (
    <Suspense fallback={null}>
      <ReportPage rawSymbol={symbol} />
    </Suspense>
  );
}
